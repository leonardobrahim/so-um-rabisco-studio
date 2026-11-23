import json
import math
import os
import re
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

STYLE_SUFFIX_SHORT_TEMPLATE = (
    "Featuring a minimalist 2D cartoon character with a large rounded pale-white head "
    "(about 1/3 of total body height) with a slight light-blue shading area on the left side of the head, "
    "messy spiky black hair, simple oval black eyes, expressive minimalist face with eyebrows and mouth, "
    "compact small body wearing a vibrant yellow hoodie (#FFC928), dark navy blue pants, "
    "and low white sneakers with black details. 2D minimalist cartoon illustration, "
    "hand-drawn doodle and marker aesthetic, thick clean black outlines, flat colors, "
    "slightly irregular lines, pure solid white background (#FFFFFF), no photorealism, "
    "no 3D, no heavy gradients, no realistic shadows, no excessive detail, {aspect} aspect ratio."
)

STYLE_SUFFIX_LONGO_TEMPLATE = (
    "Featuring a minimalist 2D cartoon character with a large rounded pale-white head "
    "(about 1/3 of total body height) with a slight light-blue shading area on the left side of the head, "
    "messy spiky black hair, simple oval black eyes, expressive minimalist face with eyebrows and mouth, "
    "compact small body wearing a vibrant yellow hoodie (#FFC928), dark navy blue pants, "
    "and low white sneakers with black details. 2D minimalist cartoon illustration, "
    "hand-drawn doodle and marker aesthetic, thick clean black outlines, flat colors, "
    "slightly irregular lines, full illustrated background with soft muted pastel or desaturated colors, "
    "subtle scenery and objects matching the scene, strictly avoid overly saturated or harsh bright primary "
    "background colors (no loud neon blue, bright red, or harsh yellow walls/skies), no photorealism, "
    "no 3D, no heavy gradients, no realistic shadows, no excessive detail, {aspect} aspect ratio."
)


def _obter_sufixo_estilo(tipo: str, formato: str) -> str:
    template = STYLE_SUFFIX_SHORT_TEMPLATE if tipo == "short" else STYLE_SUFFIX_LONGO_TEMPLATE
    return template.format(aspect=formato)

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


def limpar_prefixo_timestamp(prompt: str) -> str:
    """Remove prefixo [MM:SS] do prompt antes de enviar para geradores de imagem."""
    return re.sub(r"^\[\d{2}:\d{2}\]\s*", "", prompt.strip())


def _escolher_cor_legenda(texto: str, indice_bloco: int) -> str:
    norm = _normalizar_ascii(texto)
    palavras_alerta = (
        "nao", "nunca", "ninguem", "problema", "ansioso", "estressado",
        "panico", "crise", "erro", "pior", "zero", "impossivel", "exausto",
        "cansado", "pare", "cuidado",
    )
    if "!" in texto or any(p in norm for p in palavras_alerta):
        return "alerta"
    if "?" in texto or re.search(r"\d", texto) or indice_bloco % 3 == 1:
        return "canal"
    return "branco"


def _gerar_blocos_legenda(
    fala: str,
    inicio: float,
    fim: float,
    palavras_ts: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Quebra a fala real em micro-blocos de 1 a 3 palavras (0.4s a 0.9s)
    sincronizados palavra por palavra ao longo de [inicio, fim].
    """
    if palavras_ts:
        grupos_ts: list[list[dict[str, Any]]] = []
        grupo_atual: list[dict[str, Any]] = []
        for idx, w in enumerate(palavras_ts):
            grupo_atual.append(w)
            g_ini = float(grupo_atual[0]["inicio"])
            g_fim = float(w["fim"])
            dur = g_fim - g_ini
            pontuacao = str(w["palavra"]).strip().endswith((",", ".", "?", "!", ";", ":"))
            eh_ultima = idx == len(palavras_ts) - 1

            if eh_ultima or len(grupo_atual) >= 3 or (dur >= 0.45 and (pontuacao or len(grupo_atual) >= 2)) or dur >= 0.85:
                grupos_ts.append(grupo_atual)
                grupo_atual = []

        # Garante zero lacunas dentro da cena
        resultado: list[dict[str, Any]] = []
        for idx, g in enumerate(grupos_ts):
            b_ini = inicio if idx == 0 else resultado[-1]["fim"]
            if idx == len(grupos_ts) - 1:
                b_fim = round(fim, 2)
            else:
                prox_ini = float(grupos_ts[idx + 1][0]["inicio"])
                b_fim = round(max(b_ini + 0.25, min(fim - 0.15, (float(g[-1]["fim"]) + prox_ini) / 2.0)), 2)
            txt = " ".join(str(x["palavra"]).strip() for x in g).strip()
            if txt:
                resultado.append(
                    {
                        "texto": txt,
                        "inicio": round(b_ini, 2),
                        "fim": max(round(b_ini + 0.2, 2), b_fim),
                        "cor": _escolher_cor_legenda(txt, idx),
                    }
                )
        if resultado:
            resultado[-1]["fim"] = round(fim, 2)
        return resultado

    palavras = fala.strip().split()
    if not palavras:
        return []

    dur_total = max(0.25, fim - inicio)
    max_palavras = 3 if dur_total >= 1.2 else 2
    grupos: list[list[str]] = []
    i = 0
    while i < len(palavras):
        bloco = palavras[i : i + max_palavras]
        i += max_palavras
        grupos.append(bloco)

    total_palavras = len(palavras)
    cursor = inicio
    resultado = []
    for idx, grupo in enumerate(grupos):
        if idx == len(grupos) - 1:
            b_fim = round(fim, 2)
        else:
            proporcao = len(grupo) / total_palavras
            b_fim = round(cursor + dur_total * proporcao, 2)
        txt = " ".join(grupo)
        resultado.append(
            {
                "texto": txt,
                "inicio": round(cursor, 2),
                "fim": max(round(cursor + 0.2, 2), b_fim),
                "cor": _escolher_cor_legenda(txt, idx),
            }
        )
        cursor = b_fim

    return resultado


def _escolher_acao_e_efeito(
    fala: str,
    indice: int,
    acao_anterior: str = "",
) -> tuple[str, str]:
    norm = _normalizar_ascii(fala)
    for keywords, acao, efeito in REGRAS_VISUAIS:
        if any(k in norm for k in keywords) and acao != acao_anterior:
            return acao, efeito

    # Sem poses genéricas fixas: deriva a cena diretamente da fala exata do corte
    palavras_chave = [
        p for p in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9-]+", fala)
        if len(p) >= 3 and _normalizar_ascii(p) not in STOPWORDS_PT
    ]
    conceito = " ".join(palavras_chave[:4]) if palavras_chave else fala.strip()

    if "?" in fala:
        acao = f"The protagonist reacting with puzzled raised eyebrows and a questioning expression while visualizing the idea of '{conceito}'"
        efeito = "pop-in"
    elif "!" in fala:
        acao = f"The protagonist reacting with wide shocked eyes and emphatic hand gestures illustrating '{conceito}'"
        efeito = "shake"
    elif any(k in norm for k in ("nao", "nunca", "mas", "porém", "porem", "errado", "problema")):
        acao = f"The protagonist shaking his head with a skeptical frown while contrasting the situation '{conceito}'"
        efeito = "slide-up"
    else:
        acao = f"The protagonist expressively acting out the moment '{conceito}' with clear body language and matching facial emotion"
        efeito = "zoom-in" if indice % 2 == 1 else "cut"

    if acao == acao_anterior:
        acao = f"{acao}, viewed from a slightly closer dynamic framing"

    return acao, efeito


def _obter_gemini_api_key(raiz: Path) -> str | None:
    chave = os.environ.get("GEMINI_API_KEY", "").strip()
    if chave:
        return chave

    env_path = raiz / ".env"
    if env_path.exists():
        for linha in env_path.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if linha.startswith("GEMINI_API_KEY="):
                valor = linha.split("=", 1)[1].strip().strip('"').strip("'")
                if valor:
                    return valor
    return None


def _carregar_regras_visuais(raiz: Path) -> str:
    regra_path = raiz / ".agent" / "rules" / "02-identidade-visual-e-prompts.md"
    if regra_path.exists():
        return regra_path.read_text(encoding="utf-8").strip()
    return ""


def _gerar_acoes_via_gemini(
    roteiro_completo: str,
    blocos: list[dict[str, Any]],
    formato: str,
    regras_visuais: str,
    api_key: str,
) -> list[dict[str, str]] | None:
    lista_cortes = "\n".join(
        f"{idx}. {_formatar_mm_ss(float(b['inicio']))} ({b['inicio']}s -> {b['fim']}s): \"{b['texto']}\""
        for idx, b in enumerate(blocos, start=1)
    )

    instrucao_fundo = (
        "- Fundo branco sólido (#FFFFFF), sem cenário complexo."
        if formato == "9:16"
        else "- Inclua cenário/ambiente/objetos/paisagem de fundo em 2D minimalista coerentes com a fala, usando cores suaves/pastel/dessaturadas (nunca use cores muito fortes ou saturadas no fundo)."
    )

    prompt_sistema = (
        "Você é o diretor de storyboard do canal 'Só um Rabisco'.\n"
        "Gere uma ação/cena visual ÚNICA e específica em INGLÊS para cada corte abaixo, "
        "traduzindo literalmente ou metaforicamente a fala exata daquele momento dentro do contexto do roteiro completo.\n"
        "Regras obrigatórias:\n"
        "- NÃO repita a mesma pose ou enquadramento em cenas seguidas.\n"
        "- NÃO inclua a descrição física fixa do protagonista nem o sufixo de estilo (isso será concatenado depois).\n"
        "- Descreva a ação, expressão facial, objeto/cenário e interação da cena.\n"
        f"{instrucao_fundo}\n"
        "- Se houver texto escrito dentro da ilustração (ex: placa, papel, tela), coloque esse texto em PORTUGUÊS DO BRASIL entre aspas simples.\n"
        f"- Formato do vídeo: {formato}.\n"
        "- Escolha o efeito entre: pop-in, zoom-in, zoom-out, slide-up, shake, cut.\n"
        "- Retorne EXCLUSIVAMENTE um JSON array com objetos {\"indice\": int, \"acao\": string, \"efeito\": string}, na mesma quantidade e ordem dos cortes.\n\n"
        f"REGRAS VISUAIS:\n{regras_visuais}\n\n"
        f"ROTEIRO COMPLETO:\n{roteiro_completo}\n\n"
        f"CORTES DECUPADOS:\n{lista_cortes}"
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    body = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt_sistema}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.7},
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        texto_json = payload["candidates"][0]["content"]["parts"][0]["text"]
        itens = json.loads(texto_json)
        if isinstance(itens, list) and len(itens) == len(blocos):
            efeitos_validos = {"pop-in", "zoom-in", "zoom-out", "slide-up", "shake", "cut"}
            resultado: list[dict[str, str]] = []
            for item in itens:
                acao = str(item.get("acao", "")).strip().rstrip(".")
                efeito = str(item.get("efeito", "pop-in")).strip().lower()
                if efeito not in efeitos_validos:
                    efeito = "pop-in"
                if not acao:
                    return None
                resultado.append({"acao": acao, "efeito": efeito})
            return resultado
    except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError, TimeoutError):
        return None
    return None


def _carregar_roteiro_e_blocos(
    pasta_projeto: Path,
    tipo: str,
) -> tuple[str, list[dict[str, Any]], float, str]:
    ts_path = pasta_projeto / "03-timestamps.json"
    nar_path = pasta_projeto / "02-narracao.txt"

    narracao = nar_path.read_text(encoding="utf-8").strip() if nar_path.exists() else ""
    origem = "timestamps"
    blocos: list[dict[str, Any]] = []
    duracao_total = 0.0

    if ts_path.exists():
        ts_data = json.loads(ts_path.read_text(encoding="utf-8"))
        blocos, duracao_total = _fatiar_por_timestamps(ts_data, tipo)

    if not blocos and narracao:
        origem = "narracao"
        blocos, duracao_total = _fatiar_por_narracao(narracao, tipo)

    if not blocos:
        raise ValueError(
            "Não há áudio transcrito (03-timestamps.json) nem roteiro (02-narracao.txt) preenchido para gerar as cenas."
        )

    roteiro_completo = narracao or " ".join(b["texto"] for b in blocos)
    return roteiro_completo, blocos, duracao_total, origem


def montar_pacote_chat(
    pasta_projeto: Path,
    tipo_forcado: str | None = None,
) -> dict[str, Any]:
    """
    Monta um pacote completo pronto para copiar e colar no chat com:
    regras de estilo/ritmo + roteiro inteiro + lista de timestamps e falas.
    """
    meta = ler_ou_criar_meta_projeto(pasta_projeto)
    tipo = tipo_forcado if tipo_forcado in ("longo", "short") else meta["tipo"]
    formato = "9:16" if tipo == "short" else "16:9"

    raiz = pasta_projeto.parent.parent
    regras = _carregar_regras_visuais(raiz)
    roteiro_completo, blocos, duracao_total, origem = _carregar_roteiro_e_blocos(
        pasta_projeto, tipo
    )

    sufixo = _obter_sufixo_estilo(tipo, formato)
    linhas_cortes = [
        f"- {_formatar_mm_ss(float(b['inicio']))} ({float(b['inicio']):.2f}s -> {float(b['fim']):.2f}s): \"{b['texto']}\""
        for b in blocos
    ]

    regra_fallback_fundo = (
        "fundo #FFFFFF."
        if tipo == "short"
        else "fundo ilustrado completo (cores, objetos ou paisagens) em tons suaves/dessaturados, sem cores fortes."
    )

    pacote = "\n".join(
        [
            f"# PACOTE PARA GERAR PROMPTS — {pasta_projeto.name}",
            f"Formato: {formato} ({'Short / Reels' if tipo == 'short' else 'Vídeo Longo'}) | Duração: {duracao_total:.2f}s | Cortes: {len(blocos)} | Origem: {origem}",
            "",
            "## 1. REGRAS DE ESTILO E RITMO",
            regras or f"Cortes dinâmicos de 1,5s a 3,0s; prompts em inglês; textos na imagem em PT-BR; {regra_fallback_fundo}",
            "",
            f"Sufixo obrigatório no final de TODA linha:\n{sufixo}",
            "",
            "## 2. ROTEIRO COMPLETO DO PROJETO",
            roteiro_completo,
            "",
            "## 3. TIMESTAMPS DECUPADOS (1,5s a 3,0s) E FALA EXATA DE CADA CORTE",
            *linhas_cortes,
            "",
            "## INSTRUÇÃO FINAL",
            "Gere 1 linha por timestamp no formato `[MM:SS] <ação específica em inglês traduzindo a fala do corte>. <sufixo obrigatório>`, sem repetir poses em sequência.",
        ]
    )

    return {
        "ok": True,
        "projeto": pasta_projeto.name,
        "tipo": tipo,
        "formato": formato,
        "duracao_total": duracao_total,
        "qtd_cortes": len(blocos),
        "origem": origem,
        "pacote": pacote,
    }


def _subdividir_texto_em_intervalo(
    texto: str, inicio: float, fim: float, min_dur: float = 1.5, max_dur: float = 3.0
) -> list[dict[str, Any]]:
    dur = max(0.1, fim - inicio)
    if dur <= max_dur:
        return [{"inicio": round(inicio, 2), "fim": round(fim, 2), "texto": texto.strip()}]

    palavras = texto.strip().split()
    n_cortes = max(2, math.ceil(dur / 2.2))
    # Garante que cada corte fique entre min_dur e max_dur quando possível
    while n_cortes > 1 and (dur / n_cortes) < min_dur:
        n_cortes -= 1
    while (dur / n_cortes) > max_dur:
        n_cortes += 1

    blocos: list[dict[str, Any]] = []
    for i in range(n_cortes):
        b_ini = round(inicio + (dur * i) / n_cortes, 2)
        b_fim = round(inicio + (dur * (i + 1)) / n_cortes, 2)
        p_ini = (len(palavras) * i) // n_cortes
        p_fim = (len(palavras) * (i + 1)) // n_cortes
        trecho = " ".join(palavras[p_ini:p_fim]).strip() or texto.strip()
        blocos.append({"inicio": b_ini, "fim": b_fim, "texto": trecho})
    return blocos


def _fatiar_por_timestamps(timestamps: dict[str, Any], tipo: str) -> tuple[list[dict[str, Any]], float]:
    # Nos primeiros 10s (gancho), cortes ainda mais rápidos (1.05s a 1.6s) para segurar retenção;
    # depois segue ritmo dinâmico (1.3s a 2.4s em Shorts, 1.5s a 2.6s em Longos) com [MM:SS] únicos.
    min_dur_padrao = 1.3 if tipo == "short" else 1.5
    max_dur_padrao = 2.4 if tipo == "short" else 2.6
    alvo_dur_padrao = 1.55 if tipo == "short" else 1.85

    segmentos = timestamps.get("segmentos") or []

    # Achata todas as palavras com seus tempos exatos em sequência única,
    # evitando cortes curtos (< 1.5s) nas quebras de segmento do Whisper.
    todas_palavras: list[dict[str, Any]] = []
    for seg in segmentos:
        palavras = seg.get("palavras") or []
        if palavras:
            for w in palavras:
                txt = str(w.get("palavra", "")).strip()
                if txt:
                    todas_palavras.append(
                        {
                            "palavra": txt,
                            "inicio": float(w.get("inicio", 0.0)),
                            "fim": float(w.get("fim", float(w.get("inicio", 0.0)) + 0.3)),
                        }
                    )
        else:
            s_ini = float(seg.get("inicio", 0.0))
            s_fim = float(seg.get("fim", s_ini + 1.8))
            s_txt = str(seg.get("texto", "")).strip()
            if s_txt:
                for sub in _subdividir_texto_em_intervalo(s_txt, s_ini, max(s_ini + min_dur_padrao, s_fim), min_dur_padrao, max_dur_padrao):
                    todas_palavras.append(
                        {"palavra": sub["texto"], "inicio": sub["inicio"], "fim": sub["fim"]}
                    )

    blocos: list[dict[str, Any]] = []
    grupo: list[dict[str, Any]] = []

    for idx, w in enumerate(todas_palavras):
        grupo.append(w)
        g_inicio = float(grupo[0]["inicio"])
        g_fim = float(w["fim"])
        dur = g_fim - g_inicio
        eh_gancho = g_inicio < 10.0
        min_dur = 1.05 if eh_gancho else min_dur_padrao
        alvo_dur = 1.25 if eh_gancho else alvo_dur_padrao
        max_dur = 1.65 if eh_gancho else max_dur_padrao

        pontuacao = w["palavra"].endswith((",", ".", "?", "!", ";", ":"))
        eh_ultima = idx == len(todas_palavras) - 1

        proximo_inicio = float(todas_palavras[idx + 1]["inicio"]) if not eh_ultima else g_fim
        # Garante que o próximo corte só comece em um segundo [MM:SS] estritamente maior
        proximo_muda_segundo = int(proximo_inicio) > int(g_inicio)

        atingiu_alvo_pontuacao = pontuacao and dur >= min_dur
        atingiu_alvo_dinamico = dur >= alvo_dur and (pontuacao or idx % 2 == 0 or dur >= alvo_dur + 0.3)
        proxima_ultrapassa_max = (
            not eh_ultima
            and (float(todas_palavras[idx + 1]["fim"]) - g_inicio) > max_dur
            and dur >= min_dur
        )
        atingiu_max = dur >= max_dur or proxima_ultrapassa_max

        if eh_ultima or (proximo_muda_segundo and (atingiu_max or atingiu_alvo_pontuacao or atingiu_alvo_dinamico)):
            texto_bloco = " ".join(x["palavra"] for x in grupo).strip()
            if texto_bloco:
                blocos.append(
                    {
                        "inicio": round(g_inicio, 2),
                        "fim": round(max(g_inicio + 0.35, g_fim), 2),
                        "texto": texto_bloco,
                        "palavras": list(grupo),
                    }
                )
            grupo = []

    # Se a última cena sobrou menor que min_dur_padrao, funde com a anterior (ou divide igualmente)
    if len(blocos) >= 2 and (blocos[-1]["fim"] - blocos[-1]["inicio"]) < min_dur_padrao:
        ultima = blocos.pop()
        anterior = blocos[-1]
        dur_combinada = ultima["fim"] - anterior["inicio"]
        texto_combinado = f"{anterior['texto']} {ultima['texto']}".strip()
        palavras_comb_ts = [*(anterior.get("palavras") or []), *(ultima.get("palavras") or [])]
        if dur_combinada <= max_dur_padrao:
            anterior["fim"] = ultima["fim"]
            anterior["texto"] = texto_combinado
            anterior["palavras"] = palavras_comb_ts
        else:
            meio = round(anterior["inicio"] + dur_combinada / 2.0, 2)
            # Garante segundo distinto para o segundo corte
            if int(meio) <= int(anterior["inicio"]):
                meio = round(float(int(anterior["inicio"]) + 1), 2)
            palavras_comb = texto_combinado.split()
            corte_p = max(1, len(palavras_comb) // 2)
            anterior["fim"] = meio
            anterior["texto"] = " ".join(palavras_comb[:corte_p])
            anterior["palavras"] = palavras_comb_ts[:corte_p] if palavras_comb_ts else []
            blocos.append(
                {
                    "inicio": meio,
                    "fim": ultima["fim"],
                    "texto": " ".join(palavras_comb[corte_p:]) or anterior["texto"],
                    "palavras": palavras_comb_ts[corte_p:] if palavras_comb_ts else [],
                }
            )

    # Garante continuidade limpa sem lacunas e com [MM:SS] estritamente crescentes
    duracao_total = float(timestamps.get("duracao_total") or 0.0)
    if blocos:
        blocos[0]["inicio"] = 0.0
        for i in range(len(blocos) - 1):
            atual = blocos[i]
            proximo = blocos[i + 1]
            if proximo["inicio"] > atual["fim"]:
                if (proximo["inicio"] - atual["inicio"]) <= max_dur_padrao:
                    atual["fim"] = proximo["inicio"]
                else:
                    atual["fim"] = round(atual["inicio"] + max_dur_padrao, 2)
                    proximo["inicio"] = atual["fim"]
            elif proximo["inicio"] < atual["fim"]:
                proximo["inicio"] = atual["fim"]

            # Garante [MM:SS] estritamente crescente (nunca repetir o mesmo segundo)
            if int(proximo["inicio"]) <= int(atual["inicio"]):
                novo_ini = round(float(int(atual["inicio"]) + 1), 2)
                if novo_ini < proximo["fim"] - 0.5:
                    atual["fim"] = novo_ini
                    proximo["inicio"] = novo_ini

        if duracao_total > blocos[-1]["fim"]:
            if (duracao_total - blocos[-1]["inicio"]) <= max_dur_padrao:
                blocos[-1]["fim"] = round(duracao_total, 2)
            else:
                blocos[-1]["fim"] = round(blocos[-1]["inicio"] + max_dur_padrao, 2)
        elif duracao_total == 0.0:
            duracao_total = blocos[-1]["fim"]

    return blocos, round(duracao_total, 2)


def _fatiar_por_narracao(narracao: str, tipo: str) -> tuple[list[dict[str, Any]], float]:
    min_dur = 1.5
    max_dur = 3.0
    palavras_por_bloco = 5 if tipo == "short" else 6
    palavras_por_seg = 2.7

    frases = [f.strip() for f in re.split(r"(?<=[.!?;:\n])\s+", narracao.strip()) if f.strip()]
    blocos: list[dict[str, Any]] = []
    cursor = 0.0

    for frase in frases:
        palavras = frase.split()
        i = 0
        while i < len(palavras):
            pedaco = palavras[i : i + palavras_por_bloco]
            # Evita resto minúsculo no fim da frase juntando ao bloco anterior
            if len(palavras) - (i + palavras_por_bloco) == 1:
                pedaco = palavras[i:]
                i = len(palavras)
            else:
                i += palavras_por_bloco

            dur = max(min_dur, min(max_dur, round(len(pedaco) / palavras_por_seg, 2)))
            inicio = round(cursor, 2)
            fim = round(cursor + dur, 2)
            # Garante [MM:SS] estritamente crescente
            if blocos and int(inicio) <= int(blocos[-1]["inicio"]):
                inicio = round(float(int(blocos[-1]["inicio"]) + 1), 2)
                blocos[-1]["fim"] = inicio
                fim = round(max(inicio + min_dur, fim), 2)

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

    raiz = pasta_projeto.parent.parent
    roteiro_completo, blocos, duracao_total, origem = _carregar_roteiro_e_blocos(
        pasta_projeto, tipo
    )
    regras_visuais = _carregar_regras_visuais(raiz)

    acoes_gemini: list[dict[str, str]] | None = None
    api_key = _obter_gemini_api_key(raiz)
    if api_key:
        acoes_gemini = _gerar_acoes_via_gemini(
            roteiro_completo=roteiro_completo,
            blocos=blocos,
            formato=formato,
            regras_visuais=regras_visuais,
            api_key=api_key,
        )

    cenas_json_lista: list[dict[str, Any]] = []
    linhas_md: list[str] = [
        f"# Storyboard e Prompts - {pasta_projeto.name}",
        "",
        f"- **Formato:** `{formato}` ({'Short / Reels' if tipo == 'short' else 'YouTube Longo'})",
        f"- **Origem da decupagem:** `{'03-timestamps.json' if origem == 'timestamps' else '02-narracao.txt (estimado)'}`",
        f"- **Geração de cenas:** `{'Gemini API (roteiro completo)' if acoes_gemini else 'Contextual local (fala do corte)'}`",
        f"- **Duração total:** `{duracao_total:.2f}s`",
        f"- **Total de cenas:** `{len(blocos)}`",
        "",
        "---",
        "",
    ]
    prompts_txt_lista: list[str] = []
    tempos_txt_lista: list[str] = []

    sufixo = _obter_sufixo_estilo(tipo, formato)
    acao_anterior = ""

    for idx, bloco in enumerate(blocos, start=1):
        fala = bloco["texto"]
        inicio = float(bloco["inicio"])
        fim = float(bloco["fim"])
        marca = _formatar_mm_ss(inicio)

        if acoes_gemini:
            acao = acoes_gemini[idx - 1]["acao"]
            efeito = acoes_gemini[idx - 1]["efeito"]
        else:
            acao, efeito = _escolher_acao_e_efeito(fala, idx, acao_anterior)
        acao_anterior = acao

        legendas = _gerar_blocos_legenda(fala, inicio, fim, bloco.get("palavras"))
        prompt_completo = f"{marca} {acao}. {sufixo}"

        cenas_json_lista.append(
            {
                "arquivo": f"assets_atual/cenas/cena_{idx:02d}.png",
                "inicio": inicio,
                "fim": fim,
                "efeito": efeito,
                "texto": fala,
                "narracao": fala,
                "legendas": legendas,
                "escala": 1.0,
            }
        )

        linhas_md.append(
            f"### Cena {idx:03d} — {marca} (`{inicio:.2f}s` → `{fim:.2f}s` | Efeito: `{efeito}`)"
        )
        linhas_md.append(f'> *"{fala}"*')
        linhas_md.append("")
        linhas_md.append(prompt_completo)
        linhas_md.append("")

        prompts_txt_lista.append(limpar_prefixo_timestamp(prompt_completo))
        tempos_txt_lista.append(marca)

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

    # Salva prompts_flow.txt no projeto e prompts_imagens.txt na raiz sem prefixo [MM:SS]
    (pasta_projeto / "prompts_flow.txt").write_text(
        "\n".join(prompts_txt_lista) + "\n", encoding="utf-8"
    )

    if sincronizar_raiz:
        raiz = pasta_projeto.parent.parent
        (raiz / "prompts_imagens.txt").write_text(
            "\n\n".join(prompts_txt_lista) + "\n", encoding="utf-8"
        )
        (raiz / "tempos_imagens.txt").write_text(
            "\n\n".join(tempos_txt_lista) + "\n", encoding="utf-8"
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


def _parsear_mm_ss(marca: str) -> float:
    m = re.match(r"^\[(\d{2}):(\d{2})\]", marca.strip())
    if not m:
        return 0.0
    return int(m.group(1)) * 60.0 + int(m.group(2))


def gerar_cenas_de_prompts_salvos(
    pasta_projeto: Path,
    tipo_forcado: str | None = None,
) -> dict[str, Any]:
    """
    Gera cenas.json lendo diretamente os prompts salvos (prompts_imagens.txt do projeto,
    04-storyboard-e-prompts.md ou prompts_imagens.txt da raiz), SEM modificar nem sobrescrever
    nenhum arquivo de prompts.
    """
    meta = ler_ou_criar_meta_projeto(pasta_projeto)
    tipo = tipo_forcado if tipo_forcado in ("longo", "short") else meta["tipo"]
    formato = "9:16" if tipo == "short" else "16:9"
    raiz = pasta_projeto.parent.parent

    # Procura a fonte de prompts na ordem: projeto/prompts_imagens.txt -> 04-storyboard-e-prompts.md -> raiz/prompts_imagens.txt
    candidatos = [
        pasta_projeto / "prompts_imagens.txt",
        pasta_projeto / "04-storyboard-e-prompts.md",
        raiz / "prompts_imagens.txt",
    ]
    linhas_brutas: list[str] = []
    fonte_usada = ""
    for cand in candidatos:
        if cand.exists():
            linhas = [l.strip() for l in cand.read_text(encoding="utf-8").splitlines() if l.strip()]
            com_ts = [l for l in linhas if re.match(r"^\[\d{2}:\d{2}\]", l)]
            if com_ts:
                linhas_brutas = com_ts
                fonte_usada = cand.name
                break
            elif linhas and cand.name == "prompts_imagens.txt" and not linhas_brutas:
                linhas_brutas = linhas
                fonte_usada = cand.name

    if not linhas_brutas:
        raise ValueError(
            "Nenhum prompt encontrado em prompts_imagens.txt ou 04-storyboard-e-prompts.md deste projeto."
        )

    # Carrega transcrição palavra por palavra e duração total do áudio (se disponível)
    palavras_ts: list[dict[str, Any]] = []
    duracao_audio = 0.0
    ts_path = pasta_projeto / "03-timestamps.json"
    if ts_path.exists():
        ts_data = json.loads(ts_path.read_text(encoding="utf-8"))
        duracao_audio = float(ts_data.get("duracao_total") or 0.0)
        for seg in ts_data.get("segmentos") or []:
            for w in seg.get("palavras") or []:
                txt = str(w.get("palavra", "")).strip()
                if txt:
                    palavras_ts.append(
                        {
                            "palavra": txt,
                            "inicio": float(w.get("inicio", 0.0)),
                            "fim": float(w.get("fim", 0.0)),
                        }
                    )

    # Fallback de texto de narração se não houver 03-timestamps.json
    nar_path = pasta_projeto / "02-narracao.txt"
    narracao_palavras = (
        nar_path.read_text(encoding="utf-8").strip().split()
        if nar_path.exists()
        else []
    )

    tem_timestamps_no_txt = all(re.match(r"^\[\d{2}:\d{2}\]", l) for l in linhas_brutas)
    inicios: list[float] = []
    if tem_timestamps_no_txt:
        inicios = [_parsear_mm_ss(l) for l in linhas_brutas]
        if inicios:
            inicios[0] = 0.0
        # Garante estrita monotonicidade se houver algum empate
        for i in range(1, len(inicios)):
            if inicios[i] <= inicios[i - 1]:
                inicios[i] = round(inicios[i - 1] + 1.5, 2)
    else:
        dur_base = duracao_audio if duracao_audio > 0 else len(linhas_brutas) * 2.0
        passo = dur_base / len(linhas_brutas)
        inicios = [round(i * passo, 2) for i in range(len(linhas_brutas))]

    duracao_total = round(
        max(duracao_audio, (inicios[-1] + 2.0) if inicios else 0.0),
        2,
    )

    efeitos_alternados = ["zoom-in", "zoom-out", "impact-pop"]
    cenas_json_lista: list[dict[str, Any]] = []
    palavra_cursor = 0

    for idx, linha in enumerate(linhas_brutas, start=1):
        inicio = round(inicios[idx - 1], 2)
        fim = round(inicios[idx], 2) if idx < len(inicios) else duracao_total
        if fim <= inicio:
            fim = round(inicio + 1.5, 2)

        prompt_limpo = limpar_prefixo_timestamp(linha)
        efeito = efeitos_alternados[(idx - 1) % len(efeitos_alternados)]

        palavras_cena: list[dict[str, Any]] = []
        eh_ultima_cena = idx == len(linhas_brutas)
        while palavra_cursor < len(palavras_ts):
            w = palavras_ts[palavra_cursor]
            meio = (w["inicio"] + w["fim"]) / 2.0
            if eh_ultima_cena or meio < fim:
                palavras_cena.append(w)
                palavra_cursor += 1
            else:
                break

        if palavras_cena:
            fala = " ".join(w["palavra"] for w in palavras_cena).strip()
            legendas = _gerar_blocos_legenda(fala, inicio, fim, palavras_cena)
        elif narracao_palavras:
            p_ini = (len(narracao_palavras) * (idx - 1)) // len(linhas_brutas)
            p_fim = (len(narracao_palavras) * idx) // len(linhas_brutas)
            fala = " ".join(narracao_palavras[p_ini:p_fim]).strip()
            legendas = _gerar_blocos_legenda(fala, inicio, fim) if fala else []
        else:
            fala = ""
            legendas = []

        cenas_json_lista.append(
            {
                "arquivo": f"assets_atual/cenas/cena_{idx:02d}.png",
                "inicio": inicio,
                "fim": fim,
                "efeito": efeito,
                "texto": fala,
                "narracao": fala,
                "legendas": legendas,
                "prompt": prompt_limpo,
                "escala": 1.0,
            }
        )

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

    return {
        "ok": True,
        "fonte": fonte_usada,
        "formato": formato,
        "duracao_total": duracao_total,
        "qtd_cenas": len(cenas_json_lista),
        "cenas": cenas_payload,
    }
