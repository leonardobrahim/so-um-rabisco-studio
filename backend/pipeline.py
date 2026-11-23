import json
import re
import unicodedata
from pathlib import Path
from typing import Any

STYLE_SUFFIX_TEMPLATE = (
    "Featuring a minimalist 2D cartoon character with a large rounded pale-white head "
    "(about 1/3 of total body height) with a slight light-blue shading area on the left side of the head, "
    "messy spiky black hair, simple oval black eyes, expressive minimalist face with eyebrows and mouth, "
    "compact small body wearing a vibrant yellow hoodie (#FFC928), dark navy blue pants, "
    "and low white sneakers with black details. 2D minimalist cartoon illustration, "
    "hand-drawn doodle and marker aesthetic, thick clean black outlines, flat colors, "
    "slightly irregular lines, pure solid white background (#FFFFFF), no photorealism, "
    "no 3D, no heavy gradients, no realistic shadows, no excessive detail, {aspect} aspect ratio."
)

# Regras semânticas PT-BR -> ação visual em inglês + efeito preferido
REGRAS_VISUAIS: list[tuple[tuple[str, ...], str, str]] = [
    (
        ("ansioso", "ansiedade", "estressado", "estresse", "panico", "surto", "desespero", "nervoso", "medo"),
        "The protagonist holding his head with both hands, wide panicked eyes, jagged red stress scribbles exploding around his head",
        "shake",
    ),
    (
        ("celular", "telefone", "notificacao", "tela", "scroll", "rolando", "rede", "instagram", "tiktok", "aba", "mensagem"),
        "The protagonist staring wide-eyed at a glowing smartphone screen in his hands while floating notification bubble doodles pop around him",
        "pop-in",
    ),
    (
        ("dinheiro", "salario", "conta", "boleto", "rico", "loteria", "pagar", "comprar", "gastar", "caro", "banco"),
        "The protagonist staring at an empty wallet and floating coin doodles with an awkward sweating expression",
        "pop-in",
    ),
    (
        ("tempo", "mes", "meses", "semana", "dia", "terca", "segunda", "relogio", "hora", "horas", "ano", "calendario", "espera"),
        "The protagonist staring at a wall calendar and a ticking clock doodle floating above his head",
        "zoom-in",
    ),
    (
        ("trabalho", "emprego", "chefe", "reuniao", "escritorio", "pc", "computador", "tarefa", "meta", "produtivo"),
        "The protagonist sitting slumped at a minimalist desk in front of a laptop surrounded by tall stacks of paper",
        "slide-up",
    ),
    (
        ("prova", "estudar", "estudo", "livro", "ler", "aprender", "nota", "faculdade", "escola"),
        "The protagonist sweating nervously while holding a pencil over a pile of exam papers and books",
        "zoom-in",
    ),
    (
        ("cerebro", "cabeca", "mente", "pensando", "pensar", "dopamina", "evolucao", "ancestral", "habito", "vicio"),
        "The protagonist tapping his chin thoughtfully while a glowing cartoon brain doodle with lightning sparks floats above his head",
        "pop-in",
    ),
    (
        ("feliz", "alegria", "conseguiu", "vitoria", "trofeu", "sucesso", "paraiso", "comemorar", "sorrir"),
        "The protagonist celebrating with both arms raised in the air and tiny confetti and star doodles around him, huge joyful grin",
        "pop-in",
    ),
    (
        ("dormir", "sono", "cansado", "exausto", "descansar", "cama", "noite", "madrugada", "acordar"),
        "The protagonist lying exhausted face-down with heavy dark circles under his eyes and floating Zzz doodles",
        "zoom-out",
    ),
    (
        ("espelho", "voce", "si mesmo", "culpa", "comparar", "outro", "pessoas", "ninguem"),
        "The protagonist standing in front of a minimalist standing mirror, pointing awkwardly at his own reflection",
        "zoom-in",
    ),
    (
        ("procrastinar", "depois", "amanha", "preguica", "enrolar", "sofá", "sofa"),
        "The protagonist lounging lazily upside down while ignoring a floating alarm clock ringing loudly nearby",
        "slide-up",
    ),
    (
        ("bia", "amiga", "namorada", "ela", "conversa"),
        "The protagonist talking expressively with Bia (brown ponytail, green tank top, black leggings, holding a small notebook)",
        "cut",
    ),
]

ACOES_FALLBACK = [
    "The protagonist gesturing expressively with both hands while explaining a surprising realization, raised eyebrows",
    "The protagonist leaning forward curiously with wide oval eyes and small floating exclamation doodles",
    "The protagonist standing with arms crossed and a skeptical half-smile, one eyebrow raised",
    "The protagonist walking forward thoughtfully while small question mark doodles float above his head",
    "The protagonist looking slightly sideways with a deadpan sarcastic expression and shrugged shoulders",
    "The protagonist pointing upward with one finger as a glowing lightbulb doodle pops over his head",
]

STOPWORDS_PT = {
    "a", "o", "as", "os", "um", "uma", "uns", "umas", "de", "do", "da", "dos", "das",
    "em", "no", "na", "nos", "nas", "por", "para", "pra", "pro", "com", "sem", "sob",
    "e", "ou", "mas", "que", "se", "como", "quando", "onde", "porque", "por que",
    "voce", "você", "eu", "ele", "ela", "nos", "nós", "eles", "elas", "meu", "minha",
    "seu", "sua", "isso", "isto", "aquilo", "esse", "essa", "este", "esta", "ser",
    "estar", "ter", "fazer", "ir", "foi", "era", "vai", "ja", "já", "muito", "mais",
    "menos", "nao", "não", "sim", "ai", "aí", "entao", "então", "só", "so", "ate", "até",
    "dia", "coisa", "tudo", "nada", "bem", "mal", "todo", "toda", "todos", "todas",
    "gente", "aqui", "ali", "lá", "la", "ainda", "mesmo", "mesma", "tambem", "também",
}


def _normalizar_ascii(texto: str) -> str:
    return (
        unicodedata.normalize("NFKD", texto.lower())
        .encode("ascii", "ignore")
        .decode("ascii")
    )


def _formatar_mm_ss(segundos: float) -> str:
    minutos = int(max(0.0, segundos) // 60)
    segs = int(max(0.0, segundos) % 60)
    return f"[{minutos:02d}:{segs:02d}]"


def inferir_tipo_projeto(pasta: Path, config_cenas: dict[str, Any] | None = None) -> str:
    meta_path = pasta / "projeto.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta.get("tipo") in ("longo", "short"):
                return str(meta["tipo"])
        except Exception:
            pass

    if config_cenas and config_cenas.get("formato") == "9:16":
        return "short"

    cenas_path = pasta / "cenas.json"
    if cenas_path.exists():
        try:
            dados = json.loads(cenas_path.read_text(encoding="utf-8"))
            if dados.get("formato") == "9:16":
                return "short"
        except Exception:
            pass

    nome_norm = _normalizar_ascii(pasta.name)
    if any(tag in nome_norm for tag in ("short", "shorts", "reel", "reels", "tiktok")):
        return "short"

    return "longo"


def ler_ou_criar_meta_projeto(pasta: Path) -> dict[str, Any]:
    meta_path = pasta / "projeto.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta.get("tipo") in ("longo", "short"):
                return meta
        except Exception:
            pass

    tipo = inferir_tipo_projeto(pasta)
    meta = {
        "tipo": tipo,
        "formato": "9:16" if tipo == "short" else "16:9",
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def salvar_meta_projeto(pasta: Path, tipo: str, extras: dict[str, Any] | None = None) -> dict[str, Any]:
    meta_path = pasta / "projeto.json"
    atual: dict[str, Any] = {}
    if meta_path.exists():
        try:
            atual = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            atual = {}

    tipo_limpo = "short" if tipo == "short" else "longo"
    atual["tipo"] = tipo_limpo
    atual["formato"] = "9:16" if tipo_limpo == "short" else "16:9"
    if extras:
        atual.update(extras)

    meta_path.write_text(json.dumps(atual, ensure_ascii=False, indent=2), encoding="utf-8")
    return atual


def _extrair_texto_impacto(fala: str, indice: int, efeito: str) -> str:
    palavras_brutas = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9-]+", fala)
    if not palavras_brutas:
        return ""

    tem_enfase = "?" in fala or "!" in fala or efeito in ("shake", "pop-in")
    # Mantém o texto de impacto só nos momentos chave (~40% das cenas)
    if not tem_enfase and indice % 3 != 1:
        return ""

    fortes = [
        p for p in palavras_brutas
        if len(p) >= 3 and _normalizar_ascii(p) not in STOPWORDS_PT
    ]
    selecionadas = fortes[:2] if len(fortes) >= 2 else palavras_brutas[:2]
    if not selecionadas:
        return ""

    texto = " ".join(selecionadas).upper()
    if "?" in fala and not texto.endswith("?"):
        texto += "?"
    return texto


def _escolher_acao_e_efeito(fala: str, indice: int) -> tuple[str, str]:
    norm = _normalizar_ascii(fala)
    for keywords, acao, efeito in REGRAS_VISUAIS:
        if any(k in norm for k in keywords):
            return acao, efeito

    efeitos_ciclo = ["pop-in", "zoom-in", "cut", "zoom-out", "slide-up", "zoom-in"]
    acao = ACOES_FALLBACK[(indice - 1) % len(ACOES_FALLBACK)]
    efeito = efeitos_ciclo[(indice - 1) % len(efeitos_ciclo)]
    if "?" in fala:
        efeito = "pop-in"
    elif "!" in fala:
        efeito = "shake"
    return acao, efeito


def _fatiar_por_timestamps(timestamps: dict[str, Any], tipo: str) -> tuple[list[dict[str, Any]], float]:
    min_dur = 0.95 if tipo == "short" else 1.35
    max_dur = 1.65 if tipo == "short" else 2.20

    segmentos = timestamps.get("segmentos") or []
    blocos: list[dict[str, Any]] = []

    for seg in segmentos:
        palavras = seg.get("palavras") or []
        if not palavras:
            inicio = float(seg.get("inicio", 0.0))
            fim = float(seg.get("fim", inicio + 1.5))
            texto = str(seg.get("texto", "")).strip()
            if texto:
                blocos.append({"inicio": inicio, "fim": max(inicio + 0.4, fim), "texto": texto})
            continue

        grupo: list[dict[str, Any]] = []
        for idx, w in enumerate(palavras):
            grupo.append(w)
            g_inicio = float(grupo[0].get("inicio", 0.0))
            g_fim = float(w.get("fim", g_inicio + 0.4))
            dur = g_fim - g_inicio
            palavra_txt = str(w.get("palavra", "")).strip()
            pontuacao = palavra_txt.endswith((",", ".", "?", "!", ";", ":"))
            eh_ultima = idx == len(palavras) - 1

            if eh_ultima or dur >= max_dur or (pontuacao and dur >= min_dur):
                texto_bloco = " ".join(str(x.get("palavra", "")).strip() for x in grupo).strip()
                if texto_bloco:
                    blocos.append(
                        {
                            "inicio": round(g_inicio, 2),
                            "fim": round(max(g_inicio + 0.35, g_fim), 2),
                            "texto": texto_bloco,
                        }
                    )
                grupo = []

    # Garante continuidade limpa entre cenas para o player/template HyperFrames
    for i in range(len(blocos) - 1):
        atual = blocos[i]
        proximo = blocos[i + 1]
        if proximo["inicio"] > atual["fim"]:
            atual["fim"] = proximo["inicio"]
        elif proximo["inicio"] < atual["fim"]:
            proximo["inicio"] = atual["fim"]
            if proximo["fim"] <= proximo["inicio"]:
                proximo["fim"] = round(proximo["inicio"] + 0.5, 2)

    duracao_total = float(timestamps.get("duracao_total") or 0.0)
    if blocos:
        if blocos[0]["inicio"] > 0.0:
            blocos[0]["inicio"] = 0.0
        if duracao_total > blocos[-1]["fim"]:
            blocos[-1]["fim"] = round(duracao_total, 2)
        elif duracao_total == 0.0:
            duracao_total = blocos[-1]["fim"]

    return blocos, round(duracao_total, 2)


def _fatiar_por_narracao(narracao: str, tipo: str) -> tuple[list[dict[str, Any]], float]:
    palavras_por_bloco = 4 if tipo == "short" else 6
    palavras_por_seg = 2.7

    frases = [f.strip() for f in re.split(r"(?<=[.!?;:\n])\s+", narracao.strip()) if f.strip()]
    blocos: list[dict[str, Any]] = []
    cursor = 0.0

    for frase in frases:
        palavras = frase.split()
        for i in range(0, len(palavras), palavras_por_bloco):
            pedaco = palavras[i : i + palavras_por_bloco]
            if not pedaco:
                continue
            dur = max(1.0 if tipo == "short" else 1.4, min(2.2, len(pedaco) / palavras_por_seg))
            inicio = round(cursor, 2)
            fim = round(cursor + dur, 2)
            blocos.append({"inicio": inicio, "fim": fim, "texto": " ".join(pedaco)})
            cursor = fim

    return blocos, round(cursor, 2)


def gerar_storyboard_automatico(
    pasta_projeto: Path,
    tipo_forcado: str | None = None,
    sincronizar_raiz: bool = True,
) -> dict[str, Any]:
    """
    Gera automaticamente cenas.json, 04-storyboard-e-prompts.md, prompts_flow.txt
    e (opcionalmente) prompts_imagens.txt na raiz a partir de 03-timestamps.json
    ou 02-narracao.txt.
    """
    meta = ler_ou_criar_meta_projeto(pasta_projeto)
    tipo = tipo_forcado if tipo_forcado in ("longo", "short") else meta["tipo"]
    if tipo != meta["tipo"]:
        meta = salvar_meta_projeto(pasta_projeto, tipo)

    formato = "9:16" if tipo == "short" else "16:9"

    ts_path = pasta_projeto / "03-timestamps.json"
    nar_path = pasta_projeto / "02-narracao.txt"

    origem = "timestamps"
    blocos: list[dict[str, Any]] = []
    duracao_total = 0.0

    if ts_path.exists():
        ts_data = json.loads(ts_path.read_text(encoding="utf-8"))
        blocos, duracao_total = _fatiar_por_timestamps(ts_data, tipo)

    if not blocos and nar_path.exists():
        narracao = nar_path.read_text(encoding="utf-8").strip()
        if narracao:
            origem = "narracao"
            blocos, duracao_total = _fatiar_por_narracao(narracao, tipo)

    if not blocos:
        raise ValueError(
            "Não há áudio transcrito (03-timestamps.json) nem roteiro (02-narracao.txt) preenchido para gerar as cenas."
        )

    cenas_json_lista: list[dict[str, Any]] = []
    linhas_md: list[str] = [
        f"# Storyboard e Prompts - {pasta_projeto.name}",
        "",
        f"- **Formato:** `{formato}` ({'Short / Reels' if tipo == 'short' else 'YouTube Longo'})",
        f"- **Origem da decupagem:** `{'03-timestamps.json' if origem == 'timestamps' else '02-narracao.txt (estimado)'}`",
        f"- **Duração total:** `{duracao_total:.2f}s`",
        f"- **Total de cenas:** `{len(blocos)}`",
        "",
        "---",
        "",
    ]
    prompts_txt_lista: list[str] = []

    sufixo = STYLE_SUFFIX_TEMPLATE.format(aspect=formato)

    for idx, bloco in enumerate(blocos, start=1):
        fala = bloco["texto"]
        inicio = float(bloco["inicio"])
        fim = float(bloco["fim"])
        marca = _formatar_mm_ss(inicio)

        acao, efeito = _escolher_acao_e_efeito(fala, idx)
        texto_impacto = _extrair_texto_impacto(fala, idx, efeito)
        prompt_completo = f"{marca} {acao}. {sufixo}"

        cenas_json_lista.append(
            {
                "arquivo": f"assets_atual/cenas/cena_{idx:02d}.png",
                "inicio": inicio,
                "fim": fim,
                "efeito": efeito,
                "texto": texto_impacto,
                "escala": 1.0,
            }
        )

        linhas_md.append(
            f"### Cena {idx:03d} — {marca} (`{inicio:.2f}s` → `{fim:.2f}s` | Efeito: `{efeito}`)"
        )
        linhas_md.append(f'> *"{fala}"*')
        if texto_impacto:
            linhas_md.append(f"- **Texto de impacto:** `{texto_impacto}`")
        linhas_md.append("")
        linhas_md.append(prompt_completo)
        linhas_md.append("")

        prompts_txt_lista.append(prompt_completo)

    cenas_payload = {
        "projeto": pasta_projeto.name,
        "formato": formato,
        "fps": 30,
        "duracao_total": duracao_total,
        "audio": "assets_atual/audio.wav",
        "cenas": cenas_json_lista,
    }

    (pasta_projeto / "cenas.json").write_text(
        json.dumps(cenas_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    storyboard_md = "\n".join(linhas_md)
    (pasta_projeto / "04-storyboard-e-prompts.md").write_text(storyboard_md, encoding="utf-8")

    # Salva prompts_flow.txt no projeto (usado pelo scripts/gerar_no_flow.py)
    prompts_flow = [re.sub(r"^\[\d{2}:\d{2}\]\s*", "", p) for p in prompts_txt_lista]
    (pasta_projeto / "prompts_flow.txt").write_text(
        "\n".join(prompts_flow) + "\n", encoding="utf-8"
    )

    if sincronizar_raiz:
        raiz = pasta_projeto.parent.parent
        (raiz / "prompts_imagens.txt").write_text(
            "\n\n".join(prompts_txt_lista) + "\n", encoding="utf-8"
        )

    return {
        "ok": True,
        "origem": origem,
        "tipo": tipo,
        "formato": formato,
        "duracao_total": duracao_total,
        "qtd_cenas": len(cenas_json_lista),
        "cenas": cenas_payload,
        "storyboard": storyboard_md,
    }
