import json
import re
import shutil
import sys
from pathlib import Path

RAIZ_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ_DIR))

from backend.personagem import FONTE_PADRAO, listar_biblioteca, resolver_asset  # noqa: E402
from scripts.cortar_sprites import garantir_pose_sem_fundo  # noqa: E402


def encontrar_projeto_pronto(base_dir: Path) -> Path:
    projetos_dir = base_dir / "projetos"
    pastas = sorted(
        [p for p in projetos_dir.iterdir() if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for pasta in pastas:
        if (pasta / "cenas.json").exists():
            return pasta
    raise FileNotFoundError("Nenhum 'cenas.json' encontrado dentro de projetos/.")


def atualizar_index_html(template_dir: Path, cenas_data: dict, nome_audio: str):
    index_path = template_dir / "index.html"
    if not index_path.exists():
        return

    formato = cenas_data.get("formato", "9:16")
    width = "1920" if formato == "16:9" else "1080"
    height = "1080" if formato == "16:9" else "1920"
    fps = str(cenas_data.get("fps", 30))
    duracao = str(cenas_data.get("duracao_total", 10))

    html = index_path.read_text(encoding="utf-8")
    html = re.sub(
        r'<div id="composition"[^>]*>',
        f'<div id="composition" data-composition-id="main" data-width="{width}" data-height="{height}" data-fps="{fps}" data-duration="{duracao}">',
        html,
        count=1,
    )
    html = re.sub(
        r'<audio id="voiceover"[^>]*></audio>',
        f'<audio id="voiceover" src="./assets_atual/{nome_audio}" data-start="0" data-duration="{duracao}" preload="auto"></audio>',
        html,
        count=1,
    )
    index_path.write_text(html, encoding="utf-8")


def _escolher_cor_bloco(texto: str, idx: int) -> str:
    low = texto.lower()
    if "!" in texto or any(
        k in low for k in ("não", "nao", "nunca", "problema", "ansioso", "estressado", "crise", "erro", "pior", "zero")
    ):
        return "alerta"
    if "?" in texto or any(ch.isdigit() for ch in texto) or idx % 3 == 1:
        return "canal"
    return "branco"


def _garantir_legendas_cenas(cenas_data: dict, pasta_projeto: Path | None = None):
    """
    Garante micro-legendas dinâmicas de 1 a 3 palavras (0.4s a 0.9s) sincronizadas
    com o áudio real (03-timestamps.json quando disponível), sem coordenadas x/y.
    """
    palavras_ts: list[dict] = []
    if pasta_projeto:
        ts_path = pasta_projeto / "03-timestamps.json"
        if ts_path.exists():
            try:
                ts_data = json.loads(ts_path.read_text(encoding="utf-8"))
                for seg in ts_data.get("segmentos", []):
                    for w in seg.get("palavras", []):
                        txt = str(w.get("palavra", "")).strip()
                        if txt:
                            palavras_ts.append(
                                {
                                    "palavra": txt,
                                    "inicio": float(w.get("inicio", 0.0)),
                                    "fim": float(w.get("fim", 0.0)),
                                }
                            )
            except Exception:
                palavras_ts = []

    cenas_lista = cenas_data.get("cenas", [])
    palavra_cursor = 0

    for idx_cena, cena in enumerate(cenas_lista):
        cena.pop("x", None)
        cena.pop("y", None)

        inicio = float(cena.get("inicio", 0.0))
        fim = float(cena.get("fim", inicio + 1.5))
        eh_ultima_cena = idx_cena == len(cenas_lista) - 1

        # Se já existem micro-legendas válidas (<= 3 palavras cada), apenas garante cor
        if cena.get("legendas") and all(len(str(l.get("texto", "")).split()) <= 3 for l in cena["legendas"]):
            for idx, l in enumerate(cena["legendas"]):
                if not l.get("cor"):
                    l["cor"] = _escolher_cor_bloco(str(l.get("texto", "")), idx)
            continue

        # Consome cada palavra do Whisper apenas uma vez (intervalo semi-aberto [inicio, fim))
        palavras_cena = []
        while palavra_cursor < len(palavras_ts):
            w = palavras_ts[palavra_cursor]
            meio = (w["inicio"] + w["fim"]) / 2.0
            if eh_ultima_cena or meio < fim:
                palavras_cena.append(w)
                palavra_cursor += 1
            else:
                break

        if palavras_cena:
            grupos_ts: list[list[dict]] = []
            grupo: list[dict] = []
            for idx, w in enumerate(palavras_cena):
                grupo.append(w)
                dur = float(w["fim"]) - float(grupo[0]["inicio"])
                pont = str(w["palavra"]).endswith((",", ".", "?", "!", ";", ":"))
                if idx == len(palavras_cena) - 1 or len(grupo) >= 3 or (dur >= 0.45 and (pont or len(grupo) >= 2)) or dur >= 0.85:
                    grupos_ts.append(grupo)
                    grupo = []

            legendas = []
            for idx, g in enumerate(grupos_ts):
                b_ini = inicio if idx == 0 else legendas[-1]["fim"]
                if idx == len(grupos_ts) - 1:
                    b_fim = round(fim, 2)
                else:
                    prox_ini = float(grupos_ts[idx + 1][0]["inicio"])
                    b_fim = round(max(b_ini + 0.25, min(fim - 0.15, (float(g[-1]["fim"]) + prox_ini) / 2.0)), 2)
                txt = " ".join(str(x["palavra"]) for x in g).strip()
                if txt:
                    legendas.append(
                        {
                            "texto": txt,
                            "inicio": round(b_ini, 2),
                            "fim": max(round(b_ini + 0.2, 2), b_fim),
                            "cor": _escolher_cor_bloco(txt, idx),
                        }
                    )
            if legendas:
                legendas[-1]["fim"] = round(fim, 2)
                cena["legendas"] = legendas
                continue

        fala = str(cena.get("narracao") or cena.get("texto") or "").strip()
        if not fala:
            continue

        palavras = fala.split()
        dur = max(0.25, fim - inicio)
        max_p = 3 if dur >= 1.2 else 2
        grupos = [palavras[i : i + max_p] for i in range(0, len(palavras), max_p)]

        legendas = []
        cursor = inicio
        for idx, g in enumerate(grupos):
            b_fim = round(fim, 2) if idx == len(grupos) - 1 else round(cursor + dur * (len(g) / len(palavras)), 2)
            txt = " ".join(g)
            legendas.append(
                {
                    "texto": txt,
                    "inicio": round(cursor, 2),
                    "fim": max(round(cursor + 0.2, 2), b_fim),
                    "cor": _escolher_cor_bloco(txt, idx),
                }
            )
            cursor = b_fim
        cena["legendas"] = legendas


def _preparar_personagens(cenas_data: dict, assets_atual: Path) -> list[str]:
    """Copia só os PNGs de personagem usados para assets_atual/personagem/ e resolve o 'arquivo' de cada cena.

    Cenas sem 'personagem' (projetos antigos) ou com tipo 'none' passam intactas: renderizam só o fundo.
    """
    avisos: list[str] = []
    biblioteca = {(a["fonte"], a["id"]): a for a in listar_biblioteca()["assets"]}

    for numero, cena in enumerate(cenas_data.get("cenas", []), start=1):
        personagem = cena.get("personagem")
        if not isinstance(personagem, dict) or personagem.get("tipo") not in ("pose", "sprite"):
            continue

        fonte = str(personagem.get("fonte") or FONTE_PADRAO)
        asset = str(personagem.get("asset") or "")
        origem = resolver_asset(fonte, asset)
        if origem is None:
            avisos.append(f"Cena {numero}: asset de personagem '{asset}' não encontrado; renderizando só o fundo.")
            personagem["tipo"] = "none"
            personagem.pop("arquivo", None)
            continue

        if personagem["tipo"] == "pose" and not Path(asset).name.startswith("frame_"):
            garantir_pose_sem_fundo(origem)

        destino = assets_atual / "personagem" / fonte / asset
        destino.parent.mkdir(parents=True, exist_ok=True)
        if not destino.exists():
            shutil.copy2(origem, destino)
        personagem["arquivo"] = f"assets_atual/personagem/{fonte}/{asset}"

        if personagem["tipo"] == "sprite":
            info = biblioteca.get((fonte, asset), {})
            sprite = personagem.get("sprite") if isinstance(personagem.get("sprite"), dict) else {}
            sprite["frames"] = int(sprite.get("frames") or info.get("frames") or 1)
            sprite["quadro"] = int(sprite.get("quadro") or info.get("quadro") or 512)
            sprite["fps"] = int(sprite.get("fps") or info.get("fps") or 8)
            personagem["sprite"] = sprite

    return avisos


def preparar(pasta_projeto: Path, template_dir: Path, com_legenda: bool | None = None):
    public_dir = template_dir / "public"
    public_dir.mkdir(parents=True, exist_ok=True)
    assets_atual = public_dir / "assets_atual"
    if assets_atual.exists():
        shutil.rmtree(assets_atual)
    assets_atual.mkdir(parents=True)

    # Carrega cenas.json, garante micro-legendas sincronizadas e grava em public/cenas.json
    cenas_origem_json = pasta_projeto / "cenas.json"
    cenas_data = json.loads(cenas_origem_json.read_text(encoding="utf-8"))
    if com_legenda is not None:
        cenas_data["mostrar_legendas"] = com_legenda
    elif "mostrar_legendas" not in cenas_data:
        cenas_data["mostrar_legendas"] = True

    if cenas_data.get("mostrar_legendas", True):
        _garantir_legendas_cenas(cenas_data, pasta_projeto)
    avisos_personagem = _preparar_personagens(cenas_data, assets_atual)
    for aviso in avisos_personagem:
        print(f"[AVISO] {aviso}")

    # Copia audio.wav, audio.mp3 ou audio.m4a
    midia_dir = pasta_projeto / "midia"
    nome_audio = ""
    for ext in ("audio.wav", "audio.mp3", "audio.m4a"):
        origem_audio = midia_dir / ext
        if origem_audio.exists():
            shutil.copy2(origem_audio, assets_atual / ext)
            nome_audio = ext
            break

    cenas_data["tem_audio"] = bool(nome_audio)
    cenas_data["audio"] = f"assets_atual/{nome_audio}" if nome_audio else ""

    # Copia todas as imagens de fundo das cenas
    cenas_origem = midia_dir / "cenas"
    if cenas_origem.exists():
        shutil.copytree(cenas_origem, assets_atual / "cenas")

    (public_dir / "cenas.json").write_text(
        json.dumps(cenas_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    qtd_personagens = sum(
        1
        for c in cenas_data.get("cenas", [])
        if isinstance(c.get("personagem"), dict) and c["personagem"].get("tipo") in ("pose", "sprite")
    )
    print(
        f"Remotion pronto para renderizar o projeto: {pasta_projeto.name} "
        f"({cenas_data.get('formato', '9:16')}, {cenas_data.get('duracao_total', 0)}s, "
        f"{qtd_personagens} cena(s) com personagem em camada)"
    )


if __name__ == "__main__":
    raiz = Path(__file__).resolve().parent.parent
    template = raiz / "template-remotion"

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    com_legenda_flag: bool | None = None
    if "--sem-legenda" in sys.argv[1:]:
        com_legenda_flag = False
    elif "--com-legenda" in sys.argv[1:]:
        com_legenda_flag = True

    alvo = Path(args[0]).resolve() if args else encontrar_projeto_pronto(raiz)
    preparar(alvo, template, com_legenda=com_legenda_flag)
