import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

import json
import sys
import wave
from pathlib import Path
import numpy as np
from faster_whisper import WhisperModel


def formatar_mm_ss(segundos: float) -> str:
    minutos = int(segundos // 60)
    segs = int(segundos % 60)
    return f"{minutos:02d}:{segs:02d}"


def _mesclar_dois_segmentos(primeiro: dict, segundo: dict) -> dict:
    inicio = round(float(primeiro["inicio"]), 2)
    fim = round(max(float(primeiro["fim"]), float(segundo["fim"])), 2)
    texto = f"{str(primeiro.get('texto', '')).strip()} {str(segundo.get('texto', '')).strip()}".strip()
    palavras = list(primeiro.get("palavras") or []) + list(segundo.get("palavras") or [])
    return {
        "marca": f"[{formatar_mm_ss(inicio)}]",
        "inicio": inicio,
        "fim": fim,
        "texto": texto,
        "palavras": palavras,
    }


def fundir_segmentos_curtos_e_duplicados(
    segmentos: list[dict], min_duracao: float = 1.1
) -> list[dict]:
    """
    Funde segmentos adjacentes que tenham a mesma marca [MM:SS] ou duracao
    menor que `min_duracao` segundos, preservando inicio, fim, texto e palavras.
    """
    segs = [dict(s) for s in segmentos]
    for s in segs:
        s["inicio"] = round(float(s["inicio"]), 2)
        s["fim"] = round(float(s["fim"]), 2)
        s["marca"] = f"[{formatar_mm_ss(s['inicio'])}]"

    # 1. Remove marcas [MM:SS] duplicadas consecutivas
    alterou = True
    while alterou and len(segs) > 1:
        alterou = False
        novos: list[dict] = []
        for seg in segs:
            if novos and novos[-1]["marca"] == seg["marca"]:
                novos[-1] = _mesclar_dois_segmentos(novos[-1], seg)
                alterou = True
            else:
                novos.append(seg)
        segs = novos

    # 2. Funde segmentos menores que min_duracao ao vizinho mais proximo no tempo
    alterou = True
    while alterou and len(segs) > 1:
        alterou = False
        for i, seg in enumerate(segs):
            dur = seg["fim"] - seg["inicio"]
            if dur < min_duracao:
                if i == 0:
                    segs[0 : 2] = [_mesclar_dois_segmentos(segs[0], segs[1])]
                elif i == len(segs) - 1:
                    segs[i - 1 : i + 1] = [_mesclar_dois_segmentos(segs[i - 1], segs[i])]
                else:
                    gap_ant = seg["inicio"] - segs[i - 1]["fim"]
                    gap_prox = segs[i + 1]["inicio"] - seg["fim"]
                    # Se a frase anterior terminou com pontuacao forte e o proximo esta mais perto, junta no proximo;
                    # caso contrario junta no vizinho com menor pausa.
                    ant_termina_pont = str(segs[i - 1].get("texto", "")).strip().endswith((".", "?", "!"))
                    if ant_termina_pont and not str(seg.get("texto", "")).strip().endswith((".", "?", "!")) and gap_prox <= gap_ant + 0.3:
                        segs[i : i + 2] = [_mesclar_dois_segmentos(segs[i], segs[i + 1])]
                    elif gap_prox < gap_ant:
                        segs[i : i + 2] = [_mesclar_dois_segmentos(segs[i], segs[i + 1])]
                    else:
                        segs[i - 1 : i + 1] = [_mesclar_dois_segmentos(segs[i - 1], segs[i])]
                alterou = True
                break

    return segs


def encontrar_projeto_recente(base_dir: Path) -> Path:
    projetos_dir = base_dir / "projetos"
    if not projetos_dir.exists():
        raise FileNotFoundError("Pasta 'projetos/' nao encontrada na raiz.")

    pastas = [p for p in projetos_dir.iterdir() if p.is_dir()]
    pastas.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    for pasta in pastas:
        for ext in ("audio.wav", "audio.mp3", "audio.m4a"):
            if (pasta / "midia" / ext).exists():
                return pasta

    raise FileNotFoundError(
        "Nenhum arquivo de audio (audio.wav ou audio.mp3) encontrado em projetos/*/midia/."
    )


def carregar_wav_16k(caminho_wav: Path):
    """Le arquivos WAV PCM direto via numpy sem passar pelo PyAV."""
    try:
        with wave.open(str(caminho_wav), "rb") as wf:
            canais = wf.getnchannels()
            taxa_original = wf.getframerate()
            largura = wf.getsampwidth()
            frames = wf.readframes(wf.getnframes())

        if largura == 2:
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        elif largura == 4:
            audio = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            return str(caminho_wav)

        if canais > 1:
            audio = audio.reshape(-1, canais).mean(axis=1)

        if taxa_original != 16000:
            duracao = len(audio) / taxa_original
            novo_tamanho = int(duracao * 16000)
            x_antigo = np.linspace(0, duracao, num=len(audio), endpoint=False)
            x_novo = np.linspace(0, duracao, num=novo_tamanho, endpoint=False)
            audio = np.interp(x_novo, x_antigo, audio).astype(np.float32)

        return audio
    except wave.Error:
        return str(caminho_wav)


def extrair_timestamps(pasta_projeto: Path, modelo_tamanho: str = "small"):
    midia_dir = pasta_projeto / "midia"
    arquivo_audio = None

    for ext in ("audio.wav", "audio.mp3", "audio.m4a"):
        candidato = midia_dir / ext
        if candidato.exists():
            arquivo_audio = candidato
            break

    if not arquivo_audio:
        raise FileNotFoundError(f"Audio nao encontrado em {midia_dir}")

    print(f"Carregando modelo Whisper ({modelo_tamanho})...")
    model = WhisperModel(modelo_tamanho, device="cpu", compute_type="int8")

    print(f"Transcrevendo: {arquivo_audio.name}...")
    entrada_audio = (
        carregar_wav_16k(arquivo_audio)
        if arquivo_audio.suffix.lower() == ".wav"
        else str(arquivo_audio)
    )

    segments, info = model.transcribe(
        entrada_audio,
        language="pt",
        word_timestamps=True,
        vad_filter=True,
    )

    resultado = {
        "projeto": pasta_projeto.name,
        "duracao_total": round(info.duration, 2),
        "segmentos": [],
    }

    for seg in segments:
        palavras = []
        if seg.words:
            for w in seg.words:
                palavras.append(
                    {
                        "palavra": w.word.strip(),
                        "inicio": round(w.start, 2),
                        "fim": round(w.end, 2),
                    }
                )

        resultado["segmentos"].append(
            {
                "marca": f"[{formatar_mm_ss(seg.start)}]",
                "inicio": round(seg.start, 2),
                "fim": round(seg.end, 2),
                "texto": seg.text.strip(),
                "palavras": palavras,
            }
        )

    resultado["segmentos"] = fundir_segmentos_curtos_e_duplicados(
        resultado["segmentos"], min_duracao=1.1
    )

    saida_json = pasta_projeto / "03-timestamps.json"
    with open(saida_json, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print(f"Concluido! Timestamps salvos em: {saida_json}")


if __name__ == "__main__":
    raiz = Path(__file__).resolve().parent.parent

    if len(sys.argv) > 1:
        pasta_alvo = Path(sys.argv[1]).resolve()
    else:
        pasta_alvo = encontrar_projeto_recente(raiz)

    extrair_timestamps(pasta_alvo)