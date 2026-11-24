import json
import math
import os
import re
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .personagem import ANIMACOES, POSICOES, SeletorPersonagem

SCHEMA_VERSAO = 2

# O prompt de imagem descreve APENAS o fundo/objeto: o personagem entra depois, em camada (PNG transparente).
ESTILO_FUNDO_BASE = (
    "empty scene, no people, no characters, minimalist 2d cartoon background, "
    "thick black ink outlines, flat colors"
)

STYLE_SUFFIX_SHORT_TEMPLATE = (
    "Single highlighted object or icon centered in the frame, "
    + ESTILO_FUNDO_BASE
    + ", hand-drawn doodle and marker aesthetic, slightly irregular lines, "
    "pure solid white background (#FFFFFF), no hands, no body parts, no photorealism, "
    "no 3D, no heavy gradients, no realistic shadows, no excessive detail, {aspect} aspect ratio."
)

STYLE_SUFFIX_LONGO_TEMPLATE = (
    ESTILO_FUNDO_BASE
    + ", hand-drawn doodle and marker aesthetic, slightly irregular lines, "
    "full illustrated background with soft muted pastel or desaturated colors, "
    "subtle scenery and objects matching the scene, uncluttered lower foreground, "
    "strictly avoid overly saturated or harsh bright primary background colors "
    "(no loud neon blue, bright red, or harsh yellow walls/skies), no hands, no body parts, "
    "no photorealism, no 3D, no heavy gradients, no realistic shadows, no excessive detail, "
    "{aspect} aspect ratio."
)


def _obter_sufixo_estilo(tipo: str, formato: str) -> str:
    template = STYLE_SUFFIX_SHORT_TEMPLATE if tipo == "short" else STYLE_SUFFIX_LONGO_TEMPLATE
    return template.format(aspect=formato)

# Regras semânticas PT-BR -> fundo/objeto em inglês (SEM pessoas) + efeito de câmera + tags de pose do personagem
# Usado apenas como fallback local quando não há Gemini API; usa match por palavra inteira e bloqueio global.
REGRAS_VISUAIS: list[tuple[tuple[str, ...], str, str, tuple[str, ...]]] = [
    (
        ("ansioso", "ansiedade", "estressado", "estresse", "panico", "surto", "desespero", "nervoso", "medo"),
        "Jagged dark stress scribbles and tiny lightning doodles scattered over a plain pastel wall",
        "shake",
        ("ansioso", "panico", "medo"),
    ),
    (
        ("celular", "smartphone", "telefone", "notificacao", "notificacoes", "instagram", "tiktok", "mensagem"),
        "A glowing smartphone floating in the center with notification bubble doodles popping around it",
        "pop-in",
        ("celular", "surpreso", "olhando"),
    ),
    (
        ("dinheiro", "salario", "boleto", "rico", "loteria", "pagar", "comprar", "gastar", "banco", "carteira"),
        "An open empty wallet with floating coin doodles and a few cobwebs",
        "pop-in",
        ("preocupado", "duvida", "dinheiro"),
    ),
    (
        ("relogio", "calendario", "semana", "mes", "meses", "cronometro"),
        "A minimalist wall calendar and a big ticking clock doodle with floating motion lines",
        "zoom-in",
        ("olhando", "pensativo", "relogio"),
    ),
    (
        ("trabalho", "emprego", "chefe", "reuniao", "escritorio", "computador", "notebook", "tarefa", "meta", "produtivo"),
        "A minimalist desk with an open laptop and tall stacks of paper piled around it",
        "slide-up",
        ("cansado", "trabalho", "sentado"),
    ),
    (
        ("prova", "estudar", "estudo", "livro", "livros", "faculdade", "escola"),
        "A pile of exam papers, books and a pencil on a minimalist desk",
        "zoom-in",
        ("nervoso", "estudando", "suor"),
    ),
    (
        ("cerebro", "mente", "dopamina", "evolucao", "ancestral", "habito", "vicio"),
        "A glowing cartoon brain doodle with lightning sparks floating over a plain pastel wall",
        "pop-in",
        ("pensativo", "ideia", "duvida"),
    ),
    (
        ("feliz", "alegria", "conseguiu", "vitoria", "trofeu", "sucesso", "comemorar", "sorrir"),
        "Confetti, stars and a golden trophy doodle on a plain pastel wall",
        "pop-in",
        ("feliz", "comemorando", "animado"),
    ),
    (
        ("dormir", "sono", "cansado", "exausto", "descansar", "cama", "travesseiro", "madrugada", "acordar"),
        "A minimalist bed with a crumpled blanket and floating Zzz doodles under a crescent moon",
        "zoom-out",
        ("cansado", "dormindo", "exausto"),
    ),
    (
        ("espelho", "reflexo"),
        "A minimalist standing mirror in an otherwise empty room",
        "zoom-in",
        ("apontando", "olhando", "duvida"),
    ),
    (
        ("procrastinar", "procrastinacao", "preguica", "sofa", "despertador"),
        "A cozy sofa with a loudly ringing alarm clock doodle floating nearby",
        "slide-up",
        ("preguica", "deitado", "relaxado"),
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


def _contem_palavra(texto_norm: str, termo: str) -> bool:
    """Casamento por palavra inteira (evita falsos positivos como 'apagar' bater em 'pagar')."""
    termo_norm = _normalizar_ascii(termo).strip()
    if not termo_norm:
        return False
    return bool(re.search(r"\b" + re.escape(termo_norm) + r"\b", texto_norm))


def _tags_pose_por_fala(fala: str) -> list[str]:
    """Tags de emoção/pose desejadas para o personagem, derivadas da fala do corte."""
    norm = _normalizar_ascii(fala)
    for keywords, _fundo, _efeito, tags in REGRAS_VISUAIS:
        if any(_contem_palavra(norm, k) for k in keywords):
            return list(tags)
    if "?" in fala:
        return ["duvida", "confuso", "curioso"]
    if "!" in fala:
        return ["surpreso", "chocado", "animado"]
    if any(_contem_palavra(norm, k) for k in ("nao", "nunca", "mas", "porem", "errado", "problema")):
        return ["cetico", "negando", "bravo"]
    return []


_FUNDOS_NEUTROS_FALLBACK = [
    "A plain soft pastel living room wall with a simple framed picture and floating thought doodles",
    "A clean pastel minimalist room corner with a small wooden table and a simple lamp",
    "An uncluttered soft sky-blue doodle backdrop with subtle clouds and floating comic lines",
    "A cozy quiet room interior with soft pastel curtains and a window showing tiny stars",
    "A minimal desk surface with a blank notebook and a floating question bubble doodle",
    "An empty hallway with two closed doors and subtle perspective sketch lines",
]


def _escolher_fundo_efeito_tags(
    fala: str,
    indice: int,
    fundos_usados: set[str] | None = None,
) -> tuple[str, str, list[str]]:
    norm = _normalizar_ascii(fala)
    usados = fundos_usados if fundos_usados is not None else set()

    for keywords, fundo, efeito, tags in REGRAS_VISUAIS:
        if any(_contem_palavra(norm, k) for k in keywords) and fundo not in usados:
            usados.add(fundo)
            return fundo, efeito, list(tags)

    base = _FUNDOS_NEUTROS_FALLBACK[(indice - 1) % len(_FUNDOS_NEUTROS_FALLBACK)]
    if "?" in fala:
        fundo = f"{base}, with a bold hand-drawn question mark doodle floating in the upper area"
        efeito = "pop-in"
    elif "!" in fala:
        fundo = f"{base}, with sharp hand-drawn exclamation burst lines"
        efeito = "shake"
    elif any(_contem_palavra(norm, k) for k in ("nao", "nunca", "mas", "porem", "errado", "problema")):
        fundo = f"{base}, with a subtle red hand-drawn X doodle floating on the side"
        efeito = "slide-up"
    else:
        fundo = base
        efeito = "zoom-in" if indice % 2 == 1 else "zoom-out"

    if fundo in usados:
        fundo = f"{fundo}, scene angle {indice}"
    usados.add(fundo)
    return fundo, efeito, _tags_pose_por_fala(fala)


def _ler_env_valor(raiz: Path, chave_nome: str) -> str | None:
    valor_env = os.environ.get(chave_nome, "").strip()
    if valor_env:
        return valor_env

    env_path = raiz / ".env"
    if env_path.exists():
        for linha in env_path.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            if linha.startswith(f"{chave_nome}="):
                valor = linha.split("=", 1)[1].strip().strip('"').strip("'")
                if valor:
                    return valor
    return None


def _obter_gemini_api_key(raiz: Path) -> str | None:
    return _ler_env_valor(raiz, "GEMINI_API_KEY")


GEMINI_MODELOS_PADRAO = [
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
]


def _obter_gemini_modelos(raiz: Path) -> list[str]:
    custom = _ler_env_valor(raiz, "GEMINI_MODEL")
    if custom:
        return [custom, *[m for m in GEMINI_MODELOS_PADRAO if m != custom]]
    return list(GEMINI_MODELOS_PADRAO)


def _carregar_regras_visuais(raiz: Path) -> str:
    regra_path = raiz / ".agent" / "rules" / "02-identidade-visual-e-prompts.md"
    if regra_path.exists():
        return regra_path.read_text(encoding="utf-8").strip()
    return ""


def _frases_contexto_por_bloco(blocos: list[dict[str, Any]]) -> list[str]:
    """Agrupa cortes quebrados na mesma sentença para dar contexto completo ao LLM."""
    contextos: list[str] = [""] * len(blocos)
    grupo_idxs: list[int] = []
    textos_grupo: list[str] = []

    for idx, b in enumerate(blocos):
        txt = str(b.get("texto", "")).strip()
        grupo_idxs.append(idx)
        if txt:
            textos_grupo.append(txt)
        termina_frase = txt.endswith((".", "?", "!"))
        if termina_frase or idx == len(blocos) - 1:
            frase = " ".join(textos_grupo).strip()
            for g_i in grupo_idxs:
                contextos[g_i] = frase
            grupo_idxs = []
            textos_grupo = []
    return contextos


def _gerar_fundos_via_gemini(
    roteiro_completo: str,
    blocos: list[dict[str, Any]],
    formato: str,
    regras_visuais: str,
    api_key: str,
    tags_disponiveis: list[str],
    modelos: list[str] | None = None,
) -> tuple[list[dict[str, Any]] | None, str | None, str | None]:
    frases_ctx = _frases_contexto_por_bloco(blocos)
    lista_cortes = "\n".join(
        f"{idx}. {_formatar_mm_ss(float(b['inicio']))} ({b['inicio']}s -> {b['fim']}s) | "
        f"Fala do corte: \"{b['texto']}\" | Frase completa: \"{frases_ctx[idx - 1]}\""
        for idx, b in enumerate(blocos, start=1)
    )

    if formato == "9:16":
        instrucao_fundo = (
            "- Descreva UM único objeto/ícone concreto em destaque, centralizado, sobre fundo branco sólido (#FFFFFF), "
            "sem cenário complexo."
        )
    else:
        instrucao_fundo = (
            "- Descreva um cenário/ambiente/objetos de fundo em 2D minimalista coerentes com a fala exata, usando cores "
            "suaves/pastel/dessaturadas (nunca cores muito fortes ou saturadas) e deixando o terço inferior do quadro livre."
        )

    tags_txt = ", ".join(tags_disponiveis) if tags_disponiveis else "(nenhuma tag cadastrada)"

    prompt_sistema = (
        "Você é o diretor de storyboard do canal 'Só um Rabisco'.\n"
        "O vídeo é montado em CAMADAS: você descreve apenas o FUNDO (cenário vazio ou objeto em destaque); "
        "o protagonista é um PNG transparente adicionado depois por cima, reagindo à fala.\n"
        f"Existem EXATAMENTE {len(blocos)} cortes sequenciais. Para CADA corte, gere em INGLÊS uma descrição visual "
        "100% fiel e específica ao que está sendo falado naquele momento exato, usando a 'Frase completa' quando o corte "
        "estiver no meio de uma frase.\n\n"
        "REGRAS OBRIGATÓRIAS (cumpra todas sem exceção):\n"
        "- ZERO REPETIÇÃO NO VÍDEO INTEIRO: todos os cenários/objetos principais das cenas DEVEM ser diferentes entre si! "
        "NUNCA repita o mesmo cômodo, espelho, cérebro ou relógio várias vezes ao longo do vídeo.\n"
        "- Quando uma frase for dividida em 2 ou 3 cortes seguidos, crie visuais COMPLEMENTARES da mesma ideia sem repetir o mesmo objeto "
        "(ex.: corte sobre 'encosta a' -> quarto à noite com janela e lua na parede; corte seguinte sobre 'cabeça no travesseiro' -> "
        "close-up de um travesseiro branco macio sobre lençol pastel amassado).\n"
        "- Traduza literalmente ou metaforicamente os substantivos e ações reais da fala (ex.: chave perdida em gancho vazio, crachá de nome em branco, "
        "interruptor de luz desligado no escuro, pasta de arquivo brilhando, calçada vazia com placa de tchau, etc.).\n"
        "- NUNCA use cenários genéricos desconectados da fala.\n"
        "- O fundo NUNCA pode conter pessoas, personagens, rostos, mãos ou partes do corpo (empty scene, no people, no characters).\n"
        "- NÃO inclua descrição do protagonista nem o sufixo de estilo (isso será concatenado depois).\n"
        f"{instrucao_fundo}\n"
        "- Se houver texto escrito dentro da ilustração (ex: placa, papel, tela, arquivo), coloque esse texto em PORTUGUÊS DO BRASIL entre aspas simples.\n"
        f"- Formato do vídeo: {formato}.\n"
        "- efeito (câmera do fundo): escolha entre pop-in, zoom-in, zoom-out, slide-up, shake, cut.\n"
        f"- tags_pose: de 1 a 3 tags da lista de tags disponíveis que descrevam a emoção/pose ideal do personagem reagindo à fala: [{tags_txt}]. Use lista vazia se nenhuma servir.\n"
        f"- posicao: onde o personagem fica na tela sem tapar o elemento principal do fundo, entre: {', '.join(POSICOES)}.\n"
        f"- animacao: entrada/movimento do personagem, entre: {', '.join(ANIMACOES)}.\n"
        f"- Retorne EXCLUSIVAMENTE um JSON array com EXATAMENTE {len(blocos)} objetos no formato "
        "{\"indice\": int, \"fundo\": string, \"efeito\": string, \"tags_pose\": [string], \"posicao\": string, \"animacao\": string}, "
        "na mesma ordem dos cortes.\n\n"
        f"REGRAS VISUAIS:\n{regras_visuais}\n\n"
        f"ROTEIRO COMPLETO:\n{roteiro_completo}\n\n"
        f"CORTES DECUPADOS:\n{lista_cortes}"
    )

    body = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt_sistema}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.7},
        }
    ).encode("utf-8")

    efeitos_validos = {"pop-in", "zoom-in", "zoom-out", "slide-up", "shake", "cut"}
    ultimo_erro: str | None = None
    candidatos_modelo = modelos or GEMINI_MODELOS_PADRAO

    for modelo in candidatos_modelo:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            texto_json = payload["candidates"][0]["content"]["parts"][0]["text"]
            itens = json.loads(texto_json)
            if not isinstance(itens, list) or len(itens) != len(blocos):
                ultimo_erro = (
                    f"{modelo}: retornou {len(itens) if isinstance(itens, list) else type(itens).__name__} "
                    f"itens (esperado {len(blocos)})."
                )
                continue

            resultado: list[dict[str, Any]] = []
            valido = True
            for item in itens:
                fundo = str(item.get("fundo") or item.get("acao") or "").strip().rstrip(".")
                if not fundo:
                    valido = False
                    break
                efeito = str(item.get("efeito", "pop-in")).strip().lower()
                if efeito not in efeitos_validos:
                    efeito = "pop-in"
                tags_brutas = item.get("tags_pose") or []
                tags = [str(t).strip() for t in tags_brutas if str(t).strip()][:3]
                posicao = str(item.get("posicao", "")).strip().lower()
                animacao = str(item.get("animacao", "")).strip().lower()
                resultado.append(
                    {
                        "fundo": fundo,
                        "efeito": efeito,
                        "tags_pose": tags,
                        "posicao": posicao if posicao in POSICOES else None,
                        "animacao": animacao if animacao in ANIMACOES else None,
                    }
                )
            if valido:
                return resultado, modelo, None
            ultimo_erro = f"{modelo}: retorno com campo 'fundo' vazio."
        except urllib.error.HTTPError as exc:
            detalhe = ""
            try:
                err_json = json.loads(exc.read().decode("utf-8", errors="replace"))
                detalhe = str(err_json.get("error", {}).get("message") or "")[:180]
            except Exception:
                detalhe = ""
            ultimo_erro = f"{modelo}: HTTP {exc.code}" + (f" ({detalhe})" if detalhe else "")
            if exc.code in (404, 429, 500, 502, 503, 504):
                continue
            break
        except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError, TimeoutError, AttributeError, TypeError) as exc:
            ultimo_erro = f"{modelo}: {type(exc).__name__}: {exc}"
            continue

    return None, None, ultimo_erro or "Falha desconhecida ao chamar API do Gemini."


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
        "um único objeto/ícone em destaque, centralizado, sobre fundo #FFFFFF, sem pessoas."
        if tipo == "short"
        else "cenário ilustrado completo e vazio (sem pessoas) em tons suaves/dessaturados, sem cores fortes."
    )

    pacote = "\n".join(
        [
            f"# PACOTE PARA GERAR PROMPTS — {pasta_projeto.name}",
            f"Formato: {formato} ({'Short / Reels' if tipo == 'short' else 'Vídeo Longo'}) | Duração: {duracao_total:.2f}s | Cortes: {len(blocos)} | Origem: {origem}",
            "",
            "## 1. REGRAS DE ESTILO E RITMO",
            regras or f"Cortes dinâmicos de 1,5s a 3,0s; prompts em inglês; textos na imagem em PT-BR; {regra_fallback_fundo}",
            "",
            "O vídeo é montado em CAMADAS: o prompt descreve APENAS o fundo (cenário vazio ou objeto em destaque). "
            "O personagem NÃO entra no prompt: ele é adicionado depois como PNG transparente por cima.",
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
            "Gere 1 linha por timestamp no formato `[MM:SS] <cenário vazio ou objeto em destaque em inglês, sem pessoas ou personagens, ilustrando a fala do corte>. <sufixo obrigatório>`, sem repetir o mesmo cenário/objeto em sequência.",
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


def _descrever_personagem(personagem: dict[str, Any]) -> str:
    if personagem.get("tipo") not in ("pose", "sprite"):
        return "nenhum"
    return (
        f"{personagem['tipo']} `{personagem.get('asset', '')}` | "
        f"{personagem.get('posicao', 'center')} | {personagem.get('animacao', 'none')}"
    )


def _montar_cena(
    inicio: float,
    fim: float,
    efeito: str,
    fala: str,
    legendas: list[dict[str, Any]],
    arquivo: str,
    prompt_fundo: str,
    seletor: SeletorPersonagem,
    tags_pose: list[str],
    posicao: str | None = None,
    animacao: str | None = None,
) -> dict[str, Any]:
    """Monta uma cena em camadas: `fundo` (imagem gerada) + `personagem` (PNG transparente da biblioteca)."""
    personagem = seletor.escolher(
        fala,
        efeito=efeito,
        tags_desejadas=tags_pose,
        posicao=posicao,
        animacao=animacao,
    )
    return {
        "arquivo": arquivo,
        "inicio": inicio,
        "fim": fim,
        "efeito": efeito,
        "texto": fala,
        "narracao": fala,
        "legendas": legendas,
        "escala": 1.0,
        "fundo": {"arquivo": arquivo, "prompt": prompt_fundo},
        "personagem": personagem,
    }


def sugerir_personagens(cenas_data: dict[str, Any], apenas_sem_personagem: bool = False) -> int:
    """Escolhe pose/sprite da biblioteca para cada cena de um cenas.json existente (sem tocar nos fundos)."""
    seletor = SeletorPersonagem(formato=str(cenas_data.get("formato") or "16:9"))
    alteradas = 0
    for cena in cenas_data.get("cenas", []):
        atual = cena.get("personagem") if isinstance(cena.get("personagem"), dict) else None
        if apenas_sem_personagem and atual and atual.get("tipo") in ("pose", "sprite"):
            seletor.registrar(atual)
            continue
        fala = str(cena.get("narracao") or cena.get("texto") or "")
        tags = (atual or {}).get("tags") or _tags_pose_por_fala(fala)
        cena["personagem"] = seletor.escolher(
            fala,
            efeito=str(cena.get("efeito") or ""),
            tags_desejadas=list(tags),
        )
        alteradas += 1
    cenas_data["versao_schema"] = SCHEMA_VERSAO
    return alteradas


def gerar_storyboard_automatico(
    pasta_projeto: Path,
    tipo_forcado: str | None = None,
    sincronizar_raiz: bool = True,
) -> dict[str, Any]:
    """
    Gera automaticamente cenas.json (fundo + personagem em camadas), 04-storyboard-e-prompts.md,
    prompts_flow.txt e (opcionalmente) prompts_imagens.txt na raiz a partir de 03-timestamps.json
    ou 02-narracao.txt. Os prompts de imagem descrevem apenas o fundo/objeto; o personagem vem
    da biblioteca de assets (assets/personagem/sprites_output).
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

    seletor = SeletorPersonagem(formato=formato)

    fundos_gemini: list[dict[str, Any]] | None = None
    modelo_ia: str | None = None
    aviso_ia: str | None = None
    api_key = _obter_gemini_api_key(raiz)
    if api_key:
        fundos_gemini, modelo_ia, erro_ia = _gerar_fundos_via_gemini(
            roteiro_completo=roteiro_completo,
            blocos=blocos,
            formato=formato,
            regras_visuais=regras_visuais,
            api_key=api_key,
            tags_disponiveis=seletor.tags_disponiveis(),
            modelos=_obter_gemini_modelos(raiz),
        )
        if not fundos_gemini and erro_ia:
            aviso_ia = f"Gemini falhou ({erro_ia}); usando fallback local."
    else:
        aviso_ia = "GEMINI_API_KEY não configurada no .env; usando fallback local."

    geracao_ia = "gemini" if fundos_gemini else "fallback_local"
    rotulo_geracao = (
        f"Gemini API ({modelo_ia})"
        if fundos_gemini
        else f"Fallback local ({aviso_ia or 'sem IA'})"
    )

    cenas_json_lista: list[dict[str, Any]] = []
    linhas_md: list[str] = [
        f"# Storyboard e Prompts - {pasta_projeto.name}",
        "",
        f"- **Formato:** `{formato}` ({'Short / Reels' if tipo == 'short' else 'YouTube Longo'})",
        f"- **Origem da decupagem:** `{'03-timestamps.json' if origem == 'timestamps' else '02-narracao.txt (estimado)'}`",
        f"- **Geração de cenas:** `{rotulo_geracao}`",
        f"- **Camadas:** fundo gerado no ComfyUI + personagem da biblioteca (`{len(seletor.assets)}` assets)",
        f"- **Duração total:** `{duracao_total:.2f}s`",
        f"- **Total de cenas:** `{len(blocos)}`",
        "",
        "---",
        "",
    ]
    prompts_txt_lista: list[str] = []
    tempos_txt_lista: list[str] = []

    sufixo = _obter_sufixo_estilo(tipo, formato)
    fundos_usados: set[str] = set()

    for idx, bloco in enumerate(blocos, start=1):
        fala = bloco["texto"]
        inicio = float(bloco["inicio"])
        fim = float(bloco["fim"])
        marca = _formatar_mm_ss(inicio)

        posicao: str | None = None
        animacao: str | None = None
        if fundos_gemini:
            item = fundos_gemini[idx - 1]
            fundo = item["fundo"]
            efeito = item["efeito"]
            tags_pose = item["tags_pose"] or _tags_pose_por_fala(fala)
            posicao = item["posicao"]
            animacao = item["animacao"]
        else:
            fundo, efeito, tags_pose = _escolher_fundo_efeito_tags(fala, idx, fundos_usados)

        legendas = _gerar_blocos_legenda(fala, inicio, fim, bloco.get("palavras"))
        prompt_completo = f"{marca} {fundo}. {sufixo}"

        cena = _montar_cena(
            inicio=inicio,
            fim=fim,
            efeito=efeito,
            fala=fala,
            legendas=legendas,
            arquivo=f"assets_atual/cenas/cena_{idx:02d}.png",
            prompt_fundo=limpar_prefixo_timestamp(prompt_completo),
            seletor=seletor,
            tags_pose=tags_pose,
            posicao=posicao,
            animacao=animacao,
        )
        cenas_json_lista.append(cena)

        linhas_md.append(
            f"### Cena {idx:03d} — {marca} (`{inicio:.2f}s` → `{fim:.2f}s` | Efeito: `{efeito}`)"
        )
        linhas_md.append(f'> *"{fala}"*')
        linhas_md.append("")
        linhas_md.append(prompt_completo)
        linhas_md.append("")
        linhas_md.append(f"> Personagem (camada): {_descrever_personagem(cena['personagem'])}")
        linhas_md.append("")

        prompts_txt_lista.append(limpar_prefixo_timestamp(prompt_completo))
        tempos_txt_lista.append(marca)

    cenas_payload = {
        "projeto": pasta_projeto.name,
        "formato": formato,
        "fps": 30,
        "duracao_total": duracao_total,
        "audio": "assets_atual/audio.wav",
        "versao_schema": SCHEMA_VERSAO,
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
        "geracao_ia": geracao_ia,
        "modelo_ia": modelo_ia,
        "aviso_ia": aviso_ia,
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
    seletor = SeletorPersonagem(formato=formato)
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
            _montar_cena(
                inicio=inicio,
                fim=fim,
                efeito=efeito,
                fala=fala,
                legendas=legendas,
                arquivo=f"assets_atual/cenas/cena_{idx:02d}.png",
                prompt_fundo=prompt_limpo,
                seletor=seletor,
                tags_pose=_tags_pose_por_fala(fala),
            )
        )

    cenas_payload = {
        "projeto": pasta_projeto.name,
        "formato": formato,
        "versao_schema": SCHEMA_VERSAO,
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
