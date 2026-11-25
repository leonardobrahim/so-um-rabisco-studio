"""Pipeline de geração 100% via Gemini Structured Outputs (roteiro, storyboard, cenas.json, personagem e SEO)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from backend.gemini_client import (
    ROOT_DIR,
    gerar_estruturado,
    ler_env_valor,
)
from backend.personagem import (
    FONTE_PADRAO,
    listar_biblioteca,
    personagem_vazio,
)

# Mantido para compatibilidade com backend/comfyui.py
_ler_env_valor = ler_env_valor

AGENT_RULES_DIR = ROOT_DIR / ".agent" / "rules"

DNA_ARTISTICO_OBRIGATORIO = (
    "Minimalist 2D cartoon doodle illustration, hand-drawn sketch aesthetic with thick clean black marker outlines "
    "and flat colors, slightly irregular hand-crafted lines, simple expressive composition. "
    "Strictly NO photorealism, NO 3D rendering, NO heavy gradients, NO realistic cast shadows, NO complex textures."
)
PROMPT_PREFIXO_PADRAO = DNA_ARTISTICO_OBRIGATORIO

SUFIXO_FUNDO_LONGO = (
    "No characters or people in the scene. "
    "Soft muted pastel colors only, no overly bright, saturated, or neon colors."
)

DESCRICAO_PROTAGONISTA = (
    "Compact cartoon character whose large rounded pale-white head with subtle light-blue shading on the left side "
    "takes up one-third of his height, messy irregular spiky black hair, simple oval black eyes, minimalist expressive face, "
    "wearing a bright yellow hoodie (#FFC928), dark navy blue pants, and low white sneakers with black details."
)

DESCRICAO_SECUNDARIA_BIA = (
    "Cartoon girl with brown hair tied in a ponytail, green tank top, black leggings, "
    "holding a small notebook, same 2D hand-drawn marker doodle style."
)

EfeitoCenaLiteral = Literal["pop-in", "zoom-in", "zoom-out", "slide-up", "shake", "cut"]
CorLegendaLiteral = Literal["branco", "canal", "alerta"]
PosicaoPersonagemLiteral = Literal["center", "left", "right", "bottom-corner", "bottom-left"]
AnimacaoPersonagemLiteral = Literal[
    "pop-in", "slide-in-left", "slide-in-right", "float", "bounce", "shake", "none"
]
PersonagemQuemLiteral = Literal["protagonista", "secundaria_bia"]
PersonagemEnquadramentoLiteral = Literal["close-up", "medium shot", "full body"]


# ---------------------------------------------------------------------------
# Schemas Pydantic para Structured Outputs (response_schema)
# ---------------------------------------------------------------------------


class LegendaIndiceSchema(BaseModel):
    texto: str = Field(description="Trecho exato das palavras da legenda (1 a 4 palavras, sem cortar números).")
    palavra_inicio: int = Field(description="Índice 0-based da primeira palavra deste bloco no trecho recebido.")
    palavra_fim: int = Field(description="Índice 0-based da última palavra deste bloco no trecho recebido.")
    cor: CorLegendaLiteral = Field(description="Destaque visual: 'branco', 'canal' (amarelo) ou 'alerta' (vermelho).")


class CenaTimestampsSchema(BaseModel):
    palavra_inicio: int = Field(description="Índice 0-based da primeira palavra da cena no array de palavras.")
    palavra_fim: int = Field(description="Índice 0-based da última palavra da cena no array de palavras.")
    efeito: EfeitoCenaLiteral = Field(description="Efeito de câmera variando o ritmo visual.")
    escala_fundo: float = Field(description="Escala inicial do fundo (entre 1.0 e 1.08).")
    fundo_descricao: str = Field(
        description=(
            "Descrição em INGLÊS do cenário/ambiente (sem pessoas e sem o protagonista, com espaço livre no centro/inferior). "
            "Para 16:9: cenário completo em tons pastéis/dessaturados ligado à fala. Para 9:16: fundo branco sólido limpo com no máximo 1 objeto simples."
        )
    )
    personagem_quem: PersonagemQuemLiteral = Field(
        description="Use 'protagonista' na maioria das cenas ou 'secundaria_bia' apenas quando a cena pedir outra pessoa."
    )
    personagem_enquadramento: PersonagemEnquadramentoLiteral = Field(
        description="Varie entre 'close-up', 'medium shot' e 'full body' conforme a emoção da fala."
    )
    personagem_acao_descricao: str = Field(
        description=(
            "Descrição em INGLÊS da ação física, expressão facial exagerada ou metáfora cômica traduzindo a fala exata desta cena "
            "(textos em placas/cadernos/etiquetas em Português do Brasil; sem repetir pose da cena anterior)."
        )
    )
    legendas: list[LegendaIndiceSchema] = Field(
        description="Micro-blocos de legenda cobrindo todas as palavras da cena em ordem."
    )
    personagem_asset_id: str = Field(
        description="ID exato do asset escolhido na biblioteca enviada, ou string vazia se nenhum asset existir."
    )
    personagem_posicao: PosicaoPersonagemLiteral
    personagem_escala: float = Field(description="Escala do personagem entre 0.75 e 1.15.")
    personagem_flip: bool = Field(description="Espelhamento horizontal orgânico para variar direção.")
    personagem_animacao: AnimacaoPersonagemLiteral
    tags: list[str] = Field(description="Tags curtas de emoção/ação em português escolhidas para a cena.")


class StoryboardTimestampsSchema(BaseModel):
    cenas: list[CenaTimestampsSchema]


class LegendaTextoSchema(BaseModel):
    texto: str = Field(description="Micro-bloco de 1 a 4 palavras mantendo números e sentido intactos.")
    cor: CorLegendaLiteral


class CenaNarracaoSchema(BaseModel):
    texto: str = Field(description="Trecho exato da narração falado nesta cena.")
    duracao_segundos: float = Field(description="Duração estimada da cena respeitando o formato (16:9 ou 9:16).")
    efeito: EfeitoCenaLiteral
    escala_fundo: float = Field(description="Escala entre 1.0 e 1.08.")
    fundo_descricao: str = Field(
        description=(
            "Descrição em INGLÊS do cenário/ambiente (sem pessoas e sem o protagonista, com espaço livre no centro/inferior). "
            "Para 16:9: cenário completo em tons pastéis/dessaturados ligado à fala. Para 9:16: fundo branco sólido limpo com no máximo 1 objeto simples."
        )
    )
    personagem_quem: PersonagemQuemLiteral
    personagem_enquadramento: PersonagemEnquadramentoLiteral
    personagem_acao_descricao: str
    legendas: list[LegendaTextoSchema]
    personagem_asset_id: str = Field(description="ID exato de um asset da biblioteca ou string vazia.")
    personagem_posicao: PosicaoPersonagemLiteral
    personagem_escala: float
    personagem_flip: bool
    personagem_animacao: AnimacaoPersonagemLiteral
    tags: list[str]


class StoryboardNarracaoSchema(BaseModel):
    cenas: list[CenaNarracaoSchema]


class SugestaoCenaPersonagemSchema(BaseModel):
    indice_cena: int = Field(description="Índice 0-based da cena na lista enviada.")
    personagem_asset_id: str = Field(description="ID exato de um asset da biblioteca enviada.")
    posicao: PosicaoPersonagemLiteral
    escala: float
    flip: bool
    animacao: AnimacaoPersonagemLiteral
    tags: list[str]


class SugestoesPersonagemSchema(BaseModel):
    sugestoes: list[SugestaoCenaPersonagemSchema]


class CenaDePromptSalvoSchema(BaseModel):
    indice_cena: int = Field(description="Índice 0-based da cena na ordem dos prompts recebidos.")
    texto: str = Field(description="Trecho exato da narração correspondente a esta cena.")
    efeito: EfeitoCenaLiteral
    escala_fundo: float
    personagem_quem: PersonagemQuemLiteral
    personagem_enquadramento: PersonagemEnquadramentoLiteral
    personagem_acao_descricao: str
    legendas: list[LegendaTextoSchema]
    personagem_asset_id: str
    personagem_posicao: PosicaoPersonagemLiteral
    personagem_escala: float
    personagem_flip: bool
    personagem_animacao: AnimacaoPersonagemLiteral
    tags: list[str]


class CenasDePromptsSchema(BaseModel):
    cenas: list[CenaDePromptSalvoSchema]


class AnguloIdeiaSchema(BaseModel):
    titulo_angulo: str
    gancho_inicial: str
    desenvolvimento_resumo: str
    fechamento_loop: str
    por_que_funciona: str


class IdeiasRoteiroSchema(BaseModel):
    diagnostico_premissa: str = Field(description="Crítica honesta da premissa original sem rodeios.")
    angulos: list[AnguloIdeiaSchema] = Field(description="Exatamente 3 ângulos específicos e identificáveis.")


class RoteiroNarracaoSchema(BaseModel):
    titulo_interno: str
    narracao_pura: str = Field(
        description=(
            "Texto puro falado na narração, em português natural do canal Só um Rabisco, "
            "zero colchetes, zero marcações de cena ou direção."
        )
    )
    resumo_gancho: str


class SeoThumbSchema(BaseModel):
    titulo_principal: str = Field(description="Título recomendado com 7 a 8 palavras (45 a 55 caracteres) para longo, ou curto para Short.")
    motivo_titulo: str
    titulos_alternativos: list[str] = Field(description="Exatamente 3 alternativas de título.")
    texto_na_thumb: str = Field(description="2 a 4 palavras em caixa alta para colocar no topo da thumb.")
    prompt_thumb_16_9: str = Field(description="Prompt completo em inglês 16:9 no estilo Paper Billions com objeto simbólico do vídeo.")
    prompt_thumb_sem_texto_16_9: str = Field(description="Variação em inglês 16:9 do prompt sem texto.")
    descricao_youtube: str
    tags_youtube: list[str]
    legenda_short: str
    hashtags_short: str
    comentario_fixado: str


# ---------------------------------------------------------------------------
# Utilitários básicos e metadados de projeto
# ---------------------------------------------------------------------------


def _ler_regra_agente(nome_arquivo: str) -> str:
    caminho = AGENT_RULES_DIR / nome_arquivo
    if caminho.exists():
        return caminho.read_text(encoding="utf-8", errors="replace").strip()
    return ""


def limpar_prefixo_timestamp(prompt: str) -> str:
    return re.sub(r"^\s*\[\d{1,2}:\d{2}(?::\d{2})?\]\s*", "", prompt or "").strip()


def formatar_mmss(segundos: float) -> str:
    seg_int = max(0, int(round(segundos)))
    return f"{seg_int // 60:02d}:{seg_int % 60:02d}"


def inferir_tipo_projeto(pasta_projeto: Path) -> Literal["longo", "short"]:
    meta_path = pasta_projeto / "projeto.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            tipo = str(meta.get("tipo", "")).lower()
            if tipo in ("longo", "short"):
                return tipo  # type: ignore[return-value]
        except (OSError, json.JSONDecodeError):
            pass

    cenas_path = pasta_projeto / "cenas.json"
    if cenas_path.exists():
        try:
            cenas_data = json.loads(cenas_path.read_text(encoding="utf-8"))
            if cenas_data.get("formato") == "9:16":
                return "short"
        except (OSError, json.JSONDecodeError):
            pass

    if "short" in pasta_projeto.name.lower():
        return "short"
    return "longo"


def ler_ou_criar_meta_projeto(pasta_projeto: Path) -> dict[str, Any]:
    meta_path = pasta_projeto / "projeto.json"
    tipo = inferir_tipo_projeto(pasta_projeto)
    meta: dict[str, Any] = {
        "tipo": tipo,
        "formato": "9:16" if tipo == "short" else "16:9",
    }
    if meta_path.exists():
        try:
            existente = json.loads(meta_path.read_text(encoding="utf-8"))
            if isinstance(existente, dict):
                meta.update(existente)
                t = str(meta.get("tipo", tipo)).lower()
                if t in ("longo", "short"):
                    meta["tipo"] = t
                    meta["formato"] = "9:16" if t == "short" else "16:9"
        except (OSError, json.JSONDecodeError):
            pass
    else:
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def salvar_meta_projeto(
    pasta_projeto: Path,
    tipo: str,
    extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tipo_norm: Literal["longo", "short"] = "short" if str(tipo).lower() == "short" else "longo"
    meta = ler_ou_criar_meta_projeto(pasta_projeto)
    meta["tipo"] = tipo_norm
    meta["formato"] = "9:16" if tipo_norm == "short" else "16:9"
    if extras:
        for k, v in extras.items():
            if v is not None:
                meta[k] = v
    (pasta_projeto / "projeto.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return meta


# ---------------------------------------------------------------------------
# Normalização estrita de prompts positivos e biblioteca de personagens
# ---------------------------------------------------------------------------


_RE_CLAUSULA_NEGATIVA = re.compile(
    r"(?:,\s*)?\b(?:no|without|avoid|free of|zero)\s+"
    r"(?:3d|photorealism|photorealistic|realism|realistic|people|person|persons|"
    r"character|characters|human|humans|crowd|crowds|hand|hands|finger|fingers|"
    r"body\s*parts?|faces?|silhouettes?|gradients?|shadows?|watermark|watermarks|"
    r"signatures?|text|letters?|words?|clutter|details?)\b[^,.;]*",
    flags=re.IGNORECASE,
)


def _limpar_dna_duplicado(texto: str) -> str:
    limpo = limpar_prefixo_timestamp(texto)
    for bloco in (
        DNA_ARTISTICO_OBRIGATORIO,
        SUFIXO_FUNDO_LONGO,
        DESCRICAO_PROTAGONISTA,
        DESCRICAO_SECUNDARIA_BIA,
    ):
        if bloco in limpo:
            limpo = limpo.replace(bloco, " ")
    # Remove caso o modelo tenha repetido trecho parcial da descrição fixa do protagonista no campo de ação
    limpo = re.sub(
        r"Compact cartoon character[^.]*?(?:black details|yellow hoodie\s*\(#FFC928\))[^,.]*[,.]?\s*",
        "",
        limpo,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s{2,}", " ", limpo).strip(" ,.;")


def normalizar_prompt_fundo(descricao: str, formato: str) -> str:
    """Monta o prompt da Camada 1 (fundo sem pessoas) com DNA artístico e sufixo do formato."""
    texto = _limpar_dna_duplicado(descricao)
    if not texto:
        texto = (
            "Simple uncluttered cozy room interior in warm beige (#EFECE6) and sage green (#DCE5DC) tones, open center foreground"
            if formato != "9:16"
            else "Minimalist single symbolic object centered on pure solid white background (#FFFFFF)"
        )
    if not texto.endswith((".", "!", "?")):
        texto = f"{texto}."

    if formato == "9:16":
        if "white background" not in texto.lower() and "#ffffff" not in texto.lower():
            texto = f"{texto} Pure solid white background (#FFFFFF)."
        return f"{DNA_ARTISTICO_OBRIGATORIO} {texto} 9:16 aspect ratio. No characters or people in the scene."

    return (
        f"{DNA_ARTISTICO_OBRIGATORIO} {texto} "
        f"Open uncluttered space in the center and lower foreground for character overlay. "
        f"16:9 aspect ratio. {SUFIXO_FUNDO_LONGO}"
    )


def normalizar_prompt_personagem(
    acao_descricao: str,
    quem: str = "protagonista",
    enquadramento: str = "medium shot",
    formato: str = "16:9",
) -> str:
    """Monta o prompt da Camada 2 (personagem isolado em fundo branco #FFFFFF) com DNA e descrição fixa."""
    acao = _limpar_dna_duplicado(acao_descricao)
    if not acao:
        acao = "reacting expressively to the narration with wide eyes and raised eyebrows"
    if not acao.endswith((".", "!", "?")):
        acao = f"{acao}."

    desc_base = (
        DESCRICAO_SECUNDARIA_BIA
        if quem == "secundaria_bia"
        else DESCRICAO_PROTAGONISTA
    )
    enq = enquadramento if enquadramento in ("close-up", "medium shot", "full body") else "medium shot"
    return (
        f"{DNA_ARTISTICO_OBRIGATORIO} {desc_base} "
        f"Framing: {enq} with ample free margin around head, hair, and hands so nothing is cropped. "
        f"Action and expression: {acao} "
        f"Isolated on pure solid white background (#FFFFFF), {formato} aspect ratio."
    )


def _montar_catalogo_assets() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], str]:
    bib = listar_biblioteca()
    assets: list[dict[str, Any]] = bib.get("assets", [])
    por_id: dict[str, dict[str, Any]] = {}
    linhas: list[str] = []
    for a in assets:
        aid = str(a.get("id", ""))
        if not aid:
            continue
        por_id[aid] = a
        # Também indexa pelo caminho sem fonte ou apenas nome caso o modelo abrevie
        por_id.setdefault(f"{a.get('pasta', '')}/{a.get('arquivo', '')}", a)
        tags_txt = ", ".join(a.get("tags") or []) or "neutro"
        extra_sprite = (
            f" | frames={a.get('frames')} fps={a.get('fps')}"
            if a.get("tipo") == "sprite"
            else ""
        )
        linhas.append(f"- id: `{aid}` | tipo: {a.get('tipo')} | fonte: {a.get('fonte')} | tags: [{tags_txt}]{extra_sprite}")
    catalogo_txt = "\n".join(linhas) if linhas else "(Nenhum asset cadastrado na biblioteca de personagens.)"
    return assets, por_id, catalogo_txt


def _resolver_personagem_cena(
    *,
    asset_id: str,
    posicao: str,
    escala: float,
    flip: bool,
    animacao: str,
    tags: list[str],
    assets: list[dict[str, Any]],
    assets_por_id: dict[str, dict[str, Any]],
    ultimo_asset_id: str | None,
    formato: str,
) -> tuple[dict[str, Any], str | None]:
    if not assets:
        return personagem_vazio(), None

    escolhido = assets_por_id.get((asset_id or "").strip())
    if escolhido is None and asset_id:
        alvo = asset_id.strip().lower()
        for a in assets:
            if str(a.get("id", "")).lower() == alvo or str(a.get("arquivo", "")).lower() == alvo:
                escolhido = a
                break

    if escolhido is None:
        # Escolhe o primeiro asset compatível pelas tags que não repita o anterior
        tags_low = {t.lower() for t in tags}
        candidatos = [a for a in assets if a.get("id") != ultimo_asset_id] or assets
        candidatos_ordenados = sorted(
            candidatos,
            key=lambda a: (
                1 if a.get("tipo") == "pose" else 0,
                len(tags_low & {t.lower() for t in (a.get("tags") or [])}),
            ),
            reverse=True,
        )
        escolhido = candidatos_ordenados[0]

    # Nunca repetir o mesmo asset em cenas seguidas quando há alternativas na biblioteca
    if ultimo_asset_id and escolhido.get("id") == ultimo_asset_id and len(assets) > 1:
        tags_low = {t.lower() for t in tags}
        alternativas = [a for a in assets if a.get("id") != ultimo_asset_id]
        alternativas.sort(
            key=lambda a: (
                1 if a.get("tipo") == "pose" else 0,
                len(tags_low & {t.lower() for t in (a.get("tags") or [])}),
            ),
            reverse=True,
        )
        escolhido = alternativas[0]

    pos_valida = posicao if posicao in ("center", "left", "right", "bottom-corner", "bottom-left") else (
        "center" if formato == "9:16" else "bottom-corner"
    )
    anim_valida = animacao if animacao in (
        "pop-in", "slide-in-left", "slide-in-right", "float", "bounce", "shake", "none"
    ) else "pop-in"

    escala_limpa = max(0.65, min(1.25, round(float(escala or 0.92), 2)))
    tipo_asset = "sprite" if escolhido.get("tipo") == "sprite" else "pose"

    personagem_obj: dict[str, Any] = {
        "tipo": tipo_asset,
        "fonte": escolhido.get("fonte", FONTE_PADRAO),
        "asset": escolhido["id"],
        "posicao": pos_valida,
        "escala": escala_limpa,
        "flip": bool(flip),
        "animacao": anim_valida,
        "tags": tags or list(escolhido.get("tags") or []),
    }
    if tipo_asset == "sprite":
        personagem_obj["sprite"] = {
            "frames": int(escolhido.get("frames") or 1),
            "quadro": int(escolhido.get("quadro") or 512),
            "fps": int(escolhido.get("fps") or 8),
        }
    return personagem_obj, str(escolhido["id"])


def _reconstruir_legendas_por_indices(
    legendas_schema: list[LegendaIndiceSchema],
    palavras_globais: list[dict[str, Any]],
    w_inicio: int,
    w_fim: int,
    cena_inicio: float,
    cena_fim: float,
) -> list[dict[str, Any]]:
    if w_fim < w_inicio or not palavras_globais:
        return []

    blocos: list[dict[str, Any]] = []
    cursor = w_inicio

    for idx_leg, leg in enumerate(legendas_schema):
        if cursor > w_fim:
            break
        li = max(cursor, min(leg.palavra_inicio, w_fim))
        lf = max(li, min(leg.palavra_fim, w_fim))
        # Garante que o último bloco feche exatamente todas as palavras restantes da cena
        if idx_leg == len(legendas_schema) - 1:
            lf = w_fim
        if li > cursor:
            li = cursor

        trecho = " ".join(str(p.get("palavra", "")).strip() for p in palavras_globais[li : lf + 1]).strip()
        if not trecho:
            cursor = lf + 1
            continue

        ini_t = round(max(cena_inicio, float(palavras_globais[li]["inicio"])), 2)
        fim_t = round(min(cena_fim, float(palavras_globais[lf]["fim"])), 2)
        if fim_t <= ini_t:
            fim_t = round(min(cena_fim, ini_t + 0.25), 2)

        cor = leg.cor if leg.cor in ("branco", "canal", "alerta") else "branco"
        blocos.append({"texto": trecho, "inicio": ini_t, "fim": fim_t, "cor": cor})
        cursor = lf + 1

    # Caso o modelo deixe palavras sobrando no final ou não retorne blocos, cobre o restante
    if cursor <= w_fim:
        restante = palavras_globais[cursor : w_fim + 1]
        for pos in range(0, len(restante), 3):
            fatia = restante[pos : pos + 3]
            txt = " ".join(str(p.get("palavra", "")).strip() for p in fatia).strip()
            if not txt:
                continue
            ini_t = round(max(cena_inicio, float(fatia[0]["inicio"])), 2)
            fim_t = round(min(cena_fim, float(fatia[-1]["fim"])), 2)
            if fim_t <= ini_t:
                fim_t = round(min(cena_fim, ini_t + 0.25), 2)
            blocos.append({"texto": txt, "inicio": ini_t, "fim": fim_t, "cor": "branco"})

    # Continuidade suave entre micro-blocos dentro da cena
    for idx in range(len(blocos)):
        if idx > 0 and blocos[idx]["inicio"] < blocos[idx - 1]["fim"]:
            blocos[idx]["inicio"] = blocos[idx - 1]["fim"]
        if blocos[idx]["fim"] <= blocos[idx]["inicio"]:
            blocos[idx]["fim"] = round(blocos[idx]["inicio"] + 0.15, 2)
    if blocos:
        blocos[-1]["fim"] = round(max(blocos[-1]["inicio"] + 0.15, cena_fim), 2)

    return blocos


def _distribuir_legendas_sem_timestamps(
    legendas_schema: list[LegendaTextoSchema],
    texto_fallback: str,
    cena_inicio: float,
    cena_fim: float,
) -> list[dict[str, Any]]:
    itens = [l for l in legendas_schema if l.texto.strip()]
    if not itens:
        palavras = texto_fallback.split()
        itens = [
            LegendaTextoSchema(texto=" ".join(palavras[i : i + 3]), cor="branco")
            for i in range(0, len(palavras), 3)
        ]
    if not itens:
        return []

    total_peso = sum(max(1, len(item.texto)) for item in itens)
    duracao = max(0.3, cena_fim - cena_inicio)
    blocos: list[dict[str, Any]] = []
    t = cena_inicio
    for i, item in enumerate(itens):
        if i == len(itens) - 1:
            fim = cena_fim
        else:
            frac = max(1, len(item.texto)) / total_peso
            fim = round(t + duracao * frac, 2)
        blocos.append(
            {
                "texto": item.texto.strip(),
                "inicio": round(t, 2),
                "fim": round(max(fim, t + 0.15), 2),
                "cor": item.cor if item.cor in ("branco", "canal", "alerta") else "branco",
            }
        )
        t = blocos[-1]["fim"]
    return blocos


def _extrair_palavras_globais(ts_data: dict[str, Any]) -> list[dict[str, Any]]:
    palavras: list[dict[str, Any]] = []
    for seg in ts_data.get("segmentos", []):
        pals = seg.get("palavras") or []
        if pals:
            for p in pals:
                txt = str(p.get("palavra", "")).strip()
                if txt:
                    palavras.append(
                        {
                            "palavra": txt,
                            "inicio": float(p.get("inicio", seg.get("inicio", 0.0))),
                            "fim": float(p.get("fim", seg.get("fim", 0.0))),
                        }
                    )
        else:
            # Segmento sem granularidade por palavra: interpola palavras do segmento
            seg_txt = str(seg.get("texto", "")).strip()
            toks = seg_txt.split()
            if not toks:
                continue
            ini = float(seg.get("inicio", 0.0))
            fim = max(ini + 0.2, float(seg.get("fim", ini + 0.5)))
            step = (fim - ini) / len(toks)
            for idx, tok in enumerate(toks):
                palavras.append(
                    {
                        "palavra": tok,
                        "inicio": round(ini + idx * step, 3),
                        "fim": round(ini + (idx + 1) * step, 3),
                    }
                )
    return palavras


def _dividir_janelas_palavras(
    palavras: list[dict[str, Any]], max_palavras: int = 450
) -> list[tuple[int, int]]:
    """Divide o array de palavras em janelas contínuas quebrando apenas em pontuação forte."""
    n = len(palavras)
    if n == 0:
        return []
    if n <= max_palavras:
        return [(0, n - 1)]

    janelas: list[tuple[int, int]] = []
    inicio = 0
    while inicio < n:
        alvo_fim = min(n - 1, inicio + max_palavras - 1)
        if alvo_fim >= n - 1:
            janelas.append((inicio, n - 1))
            break

        corte = alvo_fim
        # Procura o ponto final/interrogação/exclamação mais próximo para não partir frase entre chamadas
        for idx in range(alvo_fim, max(inicio + 120, alvo_fim - 90), -1):
            tok = str(palavras[idx].get("palavra", "")).strip()
            if tok.endswith((".", "!", "?", "...")):
                corte = idx
                break
        janelas.append((inicio, corte))
        inicio = corte + 1
    return janelas


def _construir_system_storyboard(formato: str, catalogo_assets: str) -> str:
    regra_visual = _ler_regra_agente("02-identidade-visual-e-prompts.md")
    alvo_duracao = "2.5s a 4.5s" if formato == "16:9" else "1.2s a 2.5s"
    regras_fundo = (
        "Para 16:9 (VÍDEO LONGO): NUNCA gere fundo branco! Crie um cenário completo e detalhado ligado à fala "
        "(quarto à noite, mesa de estudos bagunçada, corredor de mercado, sala de aula, parque, escritório etc.) "
        "usando OBRIGATORIAMENTE tons suaves, pastéis ou dessaturados (ex.: bege quente #EFECE6, azul-acinzentado #3A4659, "
        "verde-sálvia #DCE5DC, azul-céu claro #DCE8EE, lavanda suave #E6E4EE, areia #EDE6D8). "
        "Proibido cores vibrantes/neon (azulão, vermelhão, amarelão). "
        "Deixe espaço livre no centro/centro-inferior para o personagem."
        if formato == "16:9"
        else "Para 9:16 (SHORT): mantenha fundo branco sólido puro (#FFFFFF) limpo, com no máximo um objeto simples de apoio ligado à fala."
    )
    return f"""Você é o diretor visual e editor de storyboard do canal "Só um Rabisco".
Seu trabalho é transformar a narração (com timestamps exatos do Whisper quando fornecidos) em cenas com DUAS camadas independentes (`fundo_descricao` e `personagem_acao_descricao`), sem incluir `[MM:SS]` nem o DNA repetido nos campos.

REGRAS OBRIGATÓRIAS:
1. CORTES NATURAIS ({formato}):
   - Agrupe palavras respeitando pontuação e sentido completo.
   - Duração alvo por cena: {alvo_duracao}.
   - NUNCA corte números, valores ou frases no meio.
   - Cubra TODAS as palavras em ordem contínua sem pular índices.

2. CAMADA 1 — PROMPT DE FUNDO (`fundo_descricao`, EM INGLÊS):
   - ZERO PESSOAS: Nunca inclua personagens, silhuetas humanas ou o protagonista no fundo.
   - CADA cena deve descrever um cenário/objeto ÚNICO ligado à narração daquele trecho (zero repetição genérica).
   - {regras_fundo}
   - Textos internos em placas/relógios/cadernos devem estar em PORTUGUÊS DO BRASIL.

3. CAMADA 2 — PROMPT DE PERSONAGEM (`personagem_quem`, `personagem_enquadramento`, `personagem_acao_descricao`, EM INGLÊS):
   - O sistema adiciona automaticamente o DNA artístico, a descrição fixa do personagem e o fundo branco puro (#FFFFFF).
   - Em `personagem_acao_descricao`, traduza a fala exata daquele segundo em uma ação física, reação exagerada ou metáfora cômica.
   - Varie planos (`close-up`, `medium shot`, `full body`) e NUNCA repita a mesma pose em cenas seguidas.
   - Qualquer texto visível no personagem/objetos dele deve estar em PORTUGUÊS DO BRASIL.

4. SELEÇÃO DE ASSET DA BIBLIOTECA E RITMO VISUAL:
   - Escolha `personagem_asset_id` APENAS dentre os IDs reais da lista abaixo (priorize `pose`, use `sprite` só para movimento contínuo, nunca repita em cenas seguidas).
   - Varie `personagem_posicao`, `personagem_flip`, `efeito`, `personagem_animacao` e `legendas[].cor` (`branco`, `canal`, `alerta`).

BIBLIOTECA REAL DE PERSONAGENS DISPONÍVEL:
{catalogo_assets}

{regra_visual}""".strip()


def _salvar_arquivos_storyboard(
    pasta_projeto: Path,
    cenas_config: dict[str, Any],
    *,
    sincronizar_raiz: bool = True,
) -> dict[str, Any]:
    cenas = cenas_config.get("cenas", [])
    formato = cenas_config.get("formato", "16:9")

    md_linhas = [
        f"# Storyboard e Prompts ({formato}) - {pasta_projeto.name}",
        "",
        f"Total de cenas: **{len(cenas)}** | Duração total: **{cenas_config.get('duracao_total', 0):.2f}s**",
        "",
    ]
    prompts_linhas: list[str] = []
    prompts_personagens_linhas: list[str] = []
    tempos_linhas: list[str] = []
    flow_linhas: list[str] = []

    for idx, cena in enumerate(cenas, start=1):
        ini = float(cena.get("inicio", 0.0))
        fim = float(cena.get("fim", ini))
        marca = f"[{formatar_mmss(ini)}]"
        prompt_fundo_limpo = limpar_prefixo_timestamp(
            cena.get("prompt_fundo") or cena.get("fundo", {}).get("prompt", "")
        )
        pers = cena.get("personagem") or {}
        prompt_pers_limpo = limpar_prefixo_timestamp(
            cena.get("prompt_personagem") or pers.get("prompt", "")
        )
        prompt_marcado = f"{marca} {prompt_fundo_limpo}"

        md_linhas.append(f"## Cena {idx:02d} {marca} ({ini:.2f}s → {fim:.2f}s)")
        md_linhas.append(f"- **Fala:** {cena.get('narracao', cena.get('texto', ''))}")
        md_linhas.append(f"- **Efeito:** `{cena.get('efeito', 'cut')}`")
        md_linhas.append(
            f"- **Personagem (camada):** `{pers.get('asset', 'none')}` "
            f"(`{pers.get('tipo', 'none')}`, pos `{pers.get('posicao', 'center')}`, "
            f"anim `{pers.get('animacao', 'none')}`, flip `{pers.get('flip', False)}`)"
        )
        md_linhas.append(f"- **Prompt Fundo ({cena.get('arquivo', '')}):**")
        md_linhas.append(prompt_fundo_limpo)
        if prompt_pers_limpo:
            md_linhas.append("- **Prompt Personagem (isolado #FFFFFF):**")
            md_linhas.append(prompt_pers_limpo)
        md_linhas.append("")

        prompts_linhas.append(prompt_fundo_limpo)
        prompts_personagens_linhas.append(prompt_pers_limpo)
        tempos_linhas.append(f"{idx:02d}\t{ini:.2f}\t{fim:.2f}\t{marca}")
        flow_linhas.append(prompt_marcado)

    storyboard_md = "\n".join(md_linhas).strip() + "\n"
    (pasta_projeto / "04-storyboard-e-prompts.md").write_text(storyboard_md, encoding="utf-8")
    (pasta_projeto / "prompts_flow.txt").write_text("\n".join(flow_linhas) + ("\n" if flow_linhas else ""), encoding="utf-8")
    (pasta_projeto / "prompts_imagens.txt").write_text("\n".join(prompts_linhas) + ("\n" if prompts_linhas else ""), encoding="utf-8")
    (pasta_projeto / "prompts_personagens.txt").write_text(
        "\n".join(prompts_personagens_linhas) + ("\n" if prompts_personagens_linhas else ""),
        encoding="utf-8",
    )
    (pasta_projeto / "tempos_imagens.txt").write_text("\n".join(tempos_linhas) + ("\n" if tempos_linhas else ""), encoding="utf-8")
    (pasta_projeto / "cenas.json").write_text(
        json.dumps(cenas_config, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if sincronizar_raiz:
        (ROOT_DIR / "prompts_imagens.txt").write_text(
            "\n".join(prompts_linhas) + ("\n" if prompts_linhas else ""), encoding="utf-8"
        )
        (ROOT_DIR / "tempos_imagens.txt").write_text(
            "\n".join(tempos_linhas) + ("\n" if tempos_linhas else ""), encoding="utf-8"
        )

    return {
        "ok": True,
        "storyboard": storyboard_md,
        "qtd_cenas": len(cenas),
    }


def gerar_storyboard_automatico(
    pasta_projeto: Path,
    tipo_forcado: str | None = None,
    sincronizar_raiz: bool = True,
) -> dict[str, Any]:
    """Gera cenas.json e prompts completos exclusivamente via Gemini Structured Outputs."""
    tipo = (
        "short"
        if tipo_forcado == "short"
        else "longo"
        if tipo_forcado == "longo"
        else inferir_tipo_projeto(pasta_projeto)
    )
    formato: Literal["16:9", "9:16"] = "9:16" if tipo == "short" else "16:9"
    salvar_meta_projeto(pasta_projeto, tipo)

    narracao_path = pasta_projeto / "02-narracao.txt"
    narracao_texto = (
        narracao_path.read_text(encoding="utf-8", errors="replace").strip()
        if narracao_path.exists()
        else ""
    )

    ts_path = pasta_projeto / "03-timestamps.json"
    ts_data: dict[str, Any] | None = None
    if ts_path.exists():
        try:
            ts_data = json.loads(ts_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            ts_data = None

    assets, assets_por_id, catalogo_assets = _montar_catalogo_assets()
    system_prompt = _construir_system_storyboard(formato, catalogo_assets)

    cenas_montadas: list[dict[str, Any]] = []
    ultimo_asset_id: str | None = None
    modelo_usado = ""
    origem: Literal["timestamps", "narracao"] = "narracao"
    duracao_total = 0.0

    palavras_globais = _extrair_palavras_globais(ts_data) if ts_data else []

    if ts_data and palavras_globais:
        origem = "timestamps"
        duracao_total = round(
            float(ts_data.get("duracao_total") or palavras_globais[-1]["fim"]), 2
        )
        texto_completo = narracao_texto or " ".join(p["palavra"] for p in palavras_globais)
        janelas = _dividir_janelas_palavras(palavras_globais)
        prompts_anteriores: list[str] = []

        for j_idx, (j_ini, j_fim) in enumerate(janelas, start=1):
            palavras_bloco = [
                f"{idx}| {palavras_globais[idx]['palavra']} ({palavras_globais[idx]['inicio']:.2f}-{palavras_globais[idx]['fim']:.2f}s)"
                for idx in range(j_ini, j_fim + 1)
            ]
            contexto_anterior = ""
            if prompts_anteriores:
                contexto_anterior = (
                    f"\nÚLTIMO ASSET USADO NA CENA ANTERIOR (NÃO REPETIR NA PRÓXIMA): {ultimo_asset_id or 'nenhum'}\n"
                    f"ÚLTIMOS CENÁRIOS JÁ GERADOS (NÃO REPETIR): {'; '.join(prompts_anteriores[-5:])}\n"
                )

            user_prompt = (
                f"FORMATO DO VÍDEO: {formato} ({tipo})\n"
                f"BLOCO DE TRABALHO: parte {j_idx}/{len(janelas)} — cubra EXATAMENTE os índices de palavra {j_ini} até {j_fim}.\n"
                f"DURAÇÃO ALVO POR CENA: {'2.5s a 4.5s' if formato == '16:9' else '1.2s a 2.5s'}.\n"
                f"{contexto_anterior}\n"
                f"ROTEIRO COMPLETO (para contexto narrativo):\n{texto_completo}\n\n"
                f"PALAVRAS COM TIMESTAMPS DESTE TRECHO (índice | palavra (início-fim)):\n"
                + "\n".join(palavras_bloco)
            )

            resultado, modelo_usado = gerar_estruturado(
                ROOT_DIR,
                user_prompt,
                StoryboardTimestampsSchema,
                system_instruction=system_prompt,
                temperature=0.65,
            )

            if not resultado.cenas:
                raise RuntimeError("Gemini retornou lista de cenas vazia para o storyboard.")

            cursor_palavra = j_ini
            total_bloco = len(resultado.cenas)
            for idx_local, cena_ai in enumerate(resultado.cenas):
                if cursor_palavra > j_fim:
                    break
                w_start = cursor_palavra
                w_end = max(w_start, min(j_fim, cena_ai.palavra_fim))
                if idx_local == total_bloco - 1:
                    w_end = j_fim
                if w_end < w_start:
                    w_end = w_start

                fala = " ".join(
                    str(p.get("palavra", "")).strip()
                    for p in palavras_globais[w_start : w_end + 1]
                ).strip()

                t_ini = round(float(palavras_globais[w_start]["inicio"]), 2)
                t_fim = round(float(palavras_globais[w_end]["fim"]), 2)
                if not cenas_montadas:
                    t_ini = 0.0
                else:
                    t_ini = float(cenas_montadas[-1]["fim"])
                if t_fim <= t_ini:
                    t_fim = round(t_ini + 0.35, 2)

                legendas = _reconstruir_legendas_por_indices(
                    cena_ai.legendas,
                    palavras_globais,
                    w_start,
                    w_end,
                    t_ini,
                    t_fim,
                )

                num_cena = len(cenas_montadas) + 1
                arquivo_rel = f"assets_atual/cenas/cena_{num_cena:02d}.png"
                prompt_fundo = normalizar_prompt_fundo(cena_ai.fundo_descricao, formato)
                prompt_personagem = normalizar_prompt_personagem(
                    cena_ai.personagem_acao_descricao,
                    quem=cena_ai.personagem_quem,
                    enquadramento=cena_ai.personagem_enquadramento,
                    formato=formato,
                )
                pers_obj, ultimo_asset_id = _resolver_personagem_cena(
                    asset_id=cena_ai.personagem_asset_id,
                    posicao=cena_ai.personagem_posicao,
                    escala=cena_ai.personagem_escala,
                    flip=cena_ai.personagem_flip,
                    animacao=cena_ai.personagem_animacao,
                    tags=cena_ai.tags,
                    assets=assets,
                    assets_por_id=assets_por_id,
                    ultimo_asset_id=ultimo_asset_id,
                    formato=formato,
                )
                pers_obj["prompt"] = prompt_personagem

                cenas_montadas.append(
                    {
                        "arquivo": arquivo_rel,
                        "inicio": round(t_ini, 2),
                        "fim": round(t_fim, 2),
                        "efeito": cena_ai.efeito,
                        "texto": fala,
                        "narracao": fala,
                        "legendas": legendas,
                        "escala": max(1.0, min(1.1, round(float(cena_ai.escala_fundo or 1.03), 2))),
                        "prompt_fundo": prompt_fundo,
                        "prompt_personagem": prompt_personagem,
                        "fundo": {
                            "arquivo": arquivo_rel,
                            "prompt": prompt_fundo,
                        },
                        "personagem": pers_obj,
                    }
                )
                prompts_anteriores.append(cena_ai.fundo_descricao.strip())
                cursor_palavra = w_end + 1

        if cenas_montadas:
            cenas_montadas[-1]["fim"] = round(max(float(cenas_montadas[-1]["inicio"]) + 0.25, duracao_total), 2)
            if cenas_montadas[-1]["legendas"]:
                cenas_montadas[-1]["legendas"][-1]["fim"] = cenas_montadas[-1]["fim"]

    else:
        if not narracao_texto:
            raise ValueError(
                "Não encontrei nem 03-timestamps.json nem 02-narracao.txt neste projeto."
            )
        origem = "narracao"
        user_prompt = (
            f"FORMATO DO VÍDEO: {formato} ({tipo})\n"
            f"DURAÇÃO ALVO POR CENA: {'2.5s a 4.5s' if formato == '16:9' else '1.2s a 2.5s'}.\n"
            f"Ainda não há áudio gravado: divida a narração em cortes naturais e estime a duração realista em segundos de cada cena (aprox. 2.5 palavras/segundo).\n\n"
            f"NARRAÇÃO COMPLETA:\n{narracao_texto}"
        )
        resultado, modelo_usado = gerar_estruturado(
            ROOT_DIR,
            user_prompt,
            StoryboardNarracaoSchema,
            system_instruction=system_prompt,
            temperature=0.65,
        )
        if not resultado.cenas:
            raise RuntimeError("Gemini retornou lista de cenas vazia para a narração.")

        cursor_tempo = 0.0
        for idx, cena_ai in enumerate(resultado.cenas, start=1):
            dur = max(0.8, round(float(cena_ai.duracao_segundos or (2.0 if formato == "9:16" else 3.2)), 2))
            t_ini = round(cursor_tempo, 2)
            t_fim = round(t_ini + dur, 2)
            cursor_tempo = t_fim

            arquivo_rel = f"assets_atual/cenas/cena_{idx:02d}.png"
            prompt_fundo = normalizar_prompt_fundo(cena_ai.fundo_descricao, formato)
            prompt_personagem = normalizar_prompt_personagem(
                cena_ai.personagem_acao_descricao,
                quem=cena_ai.personagem_quem,
                enquadramento=cena_ai.personagem_enquadramento,
                formato=formato,
            )
            pers_obj, ultimo_asset_id = _resolver_personagem_cena(
                asset_id=cena_ai.personagem_asset_id,
                posicao=cena_ai.personagem_posicao,
                escala=cena_ai.personagem_escala,
                flip=cena_ai.personagem_flip,
                animacao=cena_ai.personagem_animacao,
                tags=cena_ai.tags,
                assets=assets,
                assets_por_id=assets_por_id,
                ultimo_asset_id=ultimo_asset_id,
                formato=formato,
            )
            pers_obj["prompt"] = prompt_personagem
            legendas = _distribuir_legendas_sem_timestamps(
                cena_ai.legendas,
                cena_ai.texto,
                t_ini,
                t_fim,
            )
            cenas_montadas.append(
                {
                    "arquivo": arquivo_rel,
                    "inicio": t_ini,
                    "fim": t_fim,
                    "efeito": cena_ai.efeito,
                    "texto": cena_ai.texto.strip(),
                    "narracao": cena_ai.texto.strip(),
                    "legendas": legendas,
                    "escala": max(1.0, min(1.1, round(float(cena_ai.escala_fundo or 1.03), 2))),
                    "prompt_fundo": prompt_fundo,
                    "prompt_personagem": prompt_personagem,
                    "fundo": {
                        "arquivo": arquivo_rel,
                        "prompt": prompt_fundo,
                    },
                    "personagem": pers_obj,
                }
            )
        duracao_total = round(cursor_tempo, 2)

    cenas_config: dict[str, Any] = {
        "projeto": pasta_projeto.name,
        "formato": formato,
        "fps": 30,
        "duracao_total": duracao_total,
        "audio": "assets_atual/audio.wav",
        "versao_schema": 2,
        "mostrar_legendas": True,
        "cenas": cenas_montadas,
    }
    salvo = _salvar_arquivos_storyboard(
        pasta_projeto,
        cenas_config,
        sincronizar_raiz=sincronizar_raiz,
    )
    return {
        "ok": True,
        "origem": origem,
        "tipo": tipo,
        "formato": formato,
        "duracao_total": duracao_total,
        "qtd_cenas": salvo["qtd_cenas"],
        "geracao_ia": "gemini",
        "modelo_ia": modelo_usado,
        "aviso_ia": None,
        "cenas": cenas_config,
        "storyboard": salvo["storyboard"],
    }


def sugerir_personagens(
    cenas_data: dict[str, Any],
    apenas_sem_personagem: bool = False,
    raiz: Path | None = None,
) -> int:
    """Sugere pose/sprite, posição, flip e animação para as cenas usando Gemini Structured Outputs."""
    cenas: list[dict[str, Any]] = cenas_data.get("cenas") or []
    if not cenas:
        return 0

    assets, assets_por_id, catalogo_assets = _montar_catalogo_assets()
    if not assets:
        return 0

    formato = str(cenas_data.get("formato") or "16:9")
    indices_alvo = [
        idx
        for idx, cena in enumerate(cenas)
        if not apenas_sem_personagem
        or not (isinstance(cena.get("personagem"), dict) and cena["personagem"].get("tipo", "none") != "none")
    ]
    if not indices_alvo:
        return 0

    resumo_cenas = "\n".join(
        f"[{idx}] fala=\"{cenas[idx].get('narracao') or cenas[idx].get('texto', '')}\" | "
        f"fundo=\"{limpar_prefixo_timestamp((cenas[idx].get('fundo') or {}).get('prompt', ''))}\""
        for idx in indices_alvo
    )

    prompt = (
        f"FORMATO DO VÍDEO: {formato}\n"
        f"Para cada índice de cena listado abaixo, selecione o melhor `personagem_asset_id` da biblioteca REAL,\n"
        f"priorizando `pose` estática por compatibilidade das tags e usando `sprite` somente se a ação exigir movimento contínuo.\n"
        f"NUNCA repita o mesmo `personagem_asset_id` em cenas consecutivas e varie posição, flip e animação organicamente.\n\n"
        f"BIBLIOTECA REAL DE ASSETS:\n{catalogo_assets}\n\n"
        f"CENAS:\n{resumo_cenas}"
    )

    res, _ = gerar_estruturado(
        raiz or ROOT_DIR,
        prompt,
        SugestoesPersonagemSchema,
        temperature=0.55,
    )
    mapa_sugestoes = {s.indice_cena: s for s in res.sugestoes}

    alteradas = 0
    ultimo_asset_id: str | None = None
    for idx, cena in enumerate(cenas):
        if idx not in indices_alvo:
            pers_atual = cena.get("personagem")
            if isinstance(pers_atual, dict) and pers_atual.get("asset"):
                ultimo_asset_id = str(pers_atual["asset"])
            continue
        sug = mapa_sugestoes.get(idx)
        pers_obj, ultimo_asset_id = _resolver_personagem_cena(
            asset_id=sug.personagem_asset_id if sug else "",
            posicao=sug.posicao if sug else ("center" if formato == "9:16" else "bottom-corner"),
            escala=sug.escala if sug else 0.92,
            flip=sug.flip if sug else False,
            animacao=sug.animacao if sug else "pop-in",
            tags=sug.tags if sug else [],
            assets=assets,
            assets_por_id=assets_por_id,
            ultimo_asset_id=ultimo_asset_id,
            formato=formato,
        )
        cena["personagem"] = pers_obj
        alteradas += 1
    return alteradas


def gerar_cenas_de_prompts_salvos(
    pasta_projeto: Path,
    tipo_forcado: str | None = None,
    sincronizar_raiz: bool = True,
) -> dict[str, Any]:
    """Monta cenas.json a partir de prompts salvos + tempos + narração usando Gemini Structured Outputs."""
    tipo = (
        "short"
        if tipo_forcado == "short"
        else "longo"
        if tipo_forcado == "longo"
        else inferir_tipo_projeto(pasta_projeto)
    )
    formato: Literal["16:9", "9:16"] = "9:16" if tipo == "short" else "16:9"

    prompts_path = pasta_projeto / "prompts_imagens.txt"
    tempos_path = pasta_projeto / "tempos_imagens.txt"
    if not prompts_path.exists():
        raise ValueError("Arquivo prompts_imagens.txt não encontrado neste projeto.")

    prompts = [
        limpar_prefixo_timestamp(l)
        for l in prompts_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if l.strip()
    ]
    if not prompts:
        raise ValueError("prompts_imagens.txt está vazio.")

    tempos: list[tuple[float, float]] = []
    if tempos_path.exists():
        for linha in tempos_path.read_text(encoding="utf-8", errors="replace").splitlines():
            partes = linha.strip().split("\t")
            if len(partes) >= 3:
                try:
                    tempos.append((float(partes[1]), float(partes[2])))
                except ValueError:
                    pass

    if len(tempos) != len(prompts):
        dur_padrao = 2.0 if formato == "9:16" else 3.2
        tempos = [(round(i * dur_padrao, 2), round((i + 1) * dur_padrao, 2)) for i in range(len(prompts))]

    narracao = (
        (pasta_projeto / "02-narracao.txt").read_text(encoding="utf-8", errors="replace").strip()
        if (pasta_projeto / "02-narracao.txt").exists()
        else ""
    )
    assets, assets_por_id, catalogo_assets = _montar_catalogo_assets()

    lista_prompts_txt = "\n".join(
        f"[{idx}] ({tempos[idx][0]:.2f}s-{tempos[idx][1]:.2f}s) {p}"
        for idx, p in enumerate(prompts)
    )
    user_prompt = (
        f"FORMATO: {formato} ({tipo})\n"
        f"Distribua a narração entre os {len(prompts)} prompts salvos abaixo, gerando legendas coloridas (`branco`, `canal`, `alerta`), "
        f"efeito de câmera variado e personagem da biblioteca (sem repetir asset consecutivo).\n\n"
        f"BIBLIOTECA DE ASSETS:\n{catalogo_assets}\n\n"
        f"NARRAÇÃO:\n{narracao or '(sem narração escrita)'}\n\n"
        f"PROMPTS SALVOS:\n{lista_prompts_txt}"
    )

    res, modelo_usado = gerar_estruturado(
        ROOT_DIR,
        user_prompt,
        CenasDePromptsSchema,
        temperature=0.55,
    )
    mapa_ai = {c.indice_cena: c for c in res.cenas}

    cenas_montadas: list[dict[str, Any]] = []
    ultimo_asset_id: str | None = None
    for idx, prompt_bruto in enumerate(prompts):
        t_ini, t_fim = tempos[idx]
        c_ai = mapa_ai.get(idx)
        texto_fala = c_ai.texto.strip() if c_ai and c_ai.texto.strip() else ""
        arquivo_rel = f"assets_atual/cenas/cena_{idx + 1:02d}.png"
        prompt_normalizado = normalizar_prompt_fundo(prompt_bruto, formato)
        prompt_personagem = normalizar_prompt_personagem(
            c_ai.personagem_acao_descricao if c_ai else "",
            quem=c_ai.personagem_quem if c_ai else "protagonista",
            enquadramento=c_ai.personagem_enquadramento if c_ai else "medium shot",
            formato=formato,
        )

        pers_obj, ultimo_asset_id = _resolver_personagem_cena(
            asset_id=c_ai.personagem_asset_id if c_ai else "",
            posicao=c_ai.personagem_posicao if c_ai else ("center" if formato == "9:16" else "bottom-corner"),
            escala=c_ai.personagem_escala if c_ai else 0.92,
            flip=c_ai.personagem_flip if c_ai else False,
            animacao=c_ai.personagem_animacao if c_ai else "pop-in",
            tags=c_ai.tags if c_ai else [],
            assets=assets,
            assets_por_id=assets_por_id,
            ultimo_asset_id=ultimo_asset_id,
            formato=formato,
        )
        pers_obj["prompt"] = prompt_personagem
        legendas = _distribuir_legendas_sem_timestamps(
            c_ai.legendas if c_ai else [],
            texto_fala,
            t_ini,
            t_fim,
        )
        cenas_montadas.append(
            {
                "arquivo": arquivo_rel,
                "inicio": round(t_ini, 2),
                "fim": round(t_fim, 2),
                "efeito": c_ai.efeito if c_ai else "cut",
                "texto": texto_fala,
                "narracao": texto_fala,
                "legendas": legendas,
                "escala": max(1.0, min(1.1, round(float(c_ai.escala_fundo if c_ai else 1.03), 2))),
                "prompt_fundo": prompt_normalizado,
                "prompt_personagem": prompt_personagem,
                "fundo": {"arquivo": arquivo_rel, "prompt": prompt_normalizado},
                "personagem": pers_obj,
            }
        )

    duracao_total = round(tempos[-1][1], 2)
    cenas_config: dict[str, Any] = {
        "projeto": pasta_projeto.name,
        "formato": formato,
        "fps": 30,
        "duracao_total": duracao_total,
        "audio": "assets_atual/audio.wav",
        "versao_schema": 2,
        "mostrar_legendas": True,
        "cenas": cenas_montadas,
    }
    _salvar_arquivos_storyboard(pasta_projeto, cenas_config, sincronizar_raiz=sincronizar_raiz)
    return {
        "ok": True,
        "fonte": "prompts_imagens.txt",
        "formato": formato,
        "duracao_total": duracao_total,
        "qtd_cenas": len(cenas_montadas),
        "modelo_ia": modelo_usado,
        "cenas": cenas_config,
    }


def gerar_ideias_ou_roteiro(
    pasta_projeto: Path,
    tema: str,
    modo: Literal["ideias", "roteiro"] = "roteiro",
    tipo_forcado: str | None = None,
    salvar: bool = True,
) -> dict[str, Any]:
    """Gera 3 ângulos críticos ou a narração pura completa usando regras editoriais do canal."""
    tema_limpo = tema.strip()
    if not tema_limpo:
        raise ValueError("Informe um tema ou premissa para o Gemini gerar o conteúdo.")

    tipo = (
        "short"
        if tipo_forcado == "short"
        else "longo"
        if tipo_forcado == "longo"
        else inferir_tipo_projeto(pasta_projeto)
    )
    regra_editorial = _ler_regra_agente("01-identidade-e-roteiro.md")

    if modo == "ideias":
        prompt = (
            f"FORMATO ALVO: {'Short (30-60s)' if tipo == 'short' else 'Vídeo Longo (5-8 min)'}\n"
            f"PREMISSA DO USUÁRIO: {tema_limpo}\n\n"
            f"Critique honestamente se a premissa for genérica e proponha 3 ângulos bem específicos e identificáveis."
        )
        res, modelo = gerar_estruturado(
            ROOT_DIR,
            prompt,
            IdeiasRoteiroSchema,
            system_instruction=regra_editorial,
            temperature=0.8,
        )
        linhas = [
            f"# Ideias e Ângulos - {pasta_projeto.name}",
            "",
            f"**Premissa:** {tema_limpo}",
            "",
            f"## Diagnóstico",
            res.diagnostico_premissa,
            "",
        ]
        for i, ang in enumerate(res.angulos, start=1):
            linhas.extend(
                [
                    f"## Ângulo {i}: {ang.titulo_angulo}",
                    f"- **Gancho inicial:** {ang.gancho_inicial}",
                    f"- **Escalada e descoberta:** {ang.desenvolvimento_resumo}",
                    f"- **Fechamento / Loop:** {ang.fechamento_loop}",
                    f"- **Por que funciona:** {ang.por_que_funciona}",
                    "",
                ]
            )
        md = "\n".join(linhas).strip() + "\n"
        if salvar:
            (pasta_projeto / "01-ideia-e-roteiro.md").write_text(md, encoding="utf-8")
        return {
            "ok": True,
            "modo": "ideias",
            "modelo_ia": modelo,
            "conteudo": md,
            "dados": res.model_dump(),
        }

    ideia_salva = ""
    ideia_path = pasta_projeto / "01-ideia-e-roteiro.md"
    if ideia_path.exists():
        ideia_salva = ideia_path.read_text(encoding="utf-8", errors="replace").strip()

    prompt = (
        f"FORMATO ALVO: {'Short de 30 a 60 segundos (aprox. 90-160 palavras) com loop final conectando ao início.' if tipo == 'short' else 'Vídeo Longo de 5 a 8 minutos (aprox. 750-1200 palavras).'}\n"
        f"TEMA / INSTRUÇÃO: {tema_limpo}\n\n"
        f"ANOTAÇÕES DO PROJETO:\n{ideia_salva or '(nenhuma)'}\n\n"
        f"Escreva APENAS o texto puro da narração em `narracao_pura`, pronto para gravar em voz alta. Zero colchetes ou rubricas."
    )
    res, modelo = gerar_estruturado(
        ROOT_DIR,
        prompt,
        RoteiroNarracaoSchema,
        system_instruction=regra_editorial,
        temperature=0.75,
    )
    narracao_limpa = res.narracao_pura.strip()
    if salvar:
        (pasta_projeto / "02-narracao.txt").write_text(narracao_limpa + "\n", encoding="utf-8")
    return {
        "ok": True,
        "modo": "roteiro",
        "modelo_ia": modelo,
        "conteudo": narracao_limpa,
        "palavras": len(narracao_limpa.split()),
        "dados": res.model_dump(),
    }


def gerar_seo_e_thumb(
    pasta_projeto: Path,
    tipo_forcado: str | None = None,
    salvar: bool = True,
) -> dict[str, Any]:
    """Gera títulos, SEO multiplataforma e prompt de thumbnail Paper Billions via Gemini."""
    tipo = (
        "short"
        if tipo_forcado == "short"
        else "longo"
        if tipo_forcado == "longo"
        else inferir_tipo_projeto(pasta_projeto)
    )
    regra_seo = _ler_regra_agente("03-thumbs-e-seo.md")
    narracao = (
        (pasta_projeto / "02-narracao.txt").read_text(encoding="utf-8", errors="replace").strip()
        if (pasta_projeto / "02-narracao.txt").exists()
        else ""
    )
    ideia = (
        (pasta_projeto / "01-ideia-e-roteiro.md").read_text(encoding="utf-8", errors="replace").strip()
        if (pasta_projeto / "01-ideia-e-roteiro.md").exists()
        else ""
    )
    if not narracao and not ideia:
        raise ValueError("Escreva primeiro a narração (02-narracao.txt) ou a ideia do vídeo para gerar SEO e Thumbnail.")

    prompt = (
        f"PROJETO: {pasta_projeto.name}\n"
        f"FORMATO: {'Short (9:16)' if tipo == 'short' else 'Vídeo Longo (16:9)'}\n\n"
        f"NARRAÇÃO DO VÍDEO:\n{narracao or ideia}\n\n"
        f"Gere título recomendado, 3 alternativas, prompt de thumbnail em inglês 16:9 estilo Paper Billions "
        f"(com objeto luminoso/MacGuffin exclusivo deste tema específico), descrição, tags, legenda de Short e comentário fixado."
    )
    res, modelo = gerar_estruturado(
        ROOT_DIR,
        prompt,
        SeoThumbSchema,
        system_instruction=regra_seo,
        temperature=0.7,
    )

    md_linhas = [
        f"# SEO e Thumbnail - {pasta_projeto.name}",
        "",
        "## Título Principal Recomendado",
        f"Motivo: {res.motivo_titulo}",
        "```text",
        res.titulo_principal,
        "```",
        "",
        "## Títulos Alternativos",
        *[f"- {alt}" for alt in res.titulos_alternativos],
        "",
        "## Texto na Thumbnail",
        "```text",
        res.texto_na_thumb,
        "```",
        "",
        "## Prompt da Thumbnail (Paper Billions 16:9)",
        "```text",
        res.prompt_thumb_16_9,
        "```",
        "",
        "## Prompt da Thumbnail Sem Texto (16:9)",
        "```text",
        res.prompt_thumb_sem_texto_16_9,
        "```",
        "",
        "## Descrição YouTube",
        "```text",
        res.descricao_youtube,
        "```",
        "",
        "## Tags YouTube",
        "```text",
        ", ".join(res.tags_youtube),
        "```",
        "",
        "## Legenda e Hashtags (Shorts / Reels / TikTok)",
        "```text",
        f"{res.legenda_short}\n\n{res.hashtags_short}",
        "```",
        "",
        "## Comentário Fixado",
        "```text",
        res.comentario_fixado,
        "```",
    ]
    md = "\n".join(md_linhas).strip() + "\n"

    if salvar:
        (pasta_projeto / "05-seo-e-thumb.md").write_text(md, encoding="utf-8")
        salvar_meta_projeto(
            pasta_projeto,
            tipo,
            extras={
                "titulo_thumb": res.titulo_principal,
                "legenda_short": res.legenda_short,
                "hashtags_short": res.hashtags_short,
            },
        )

    return {
        "ok": True,
        "modelo_ia": modelo,
        "markdown": md,
        "dados": res.model_dump(),
    }


def montar_pacote_chat(pasta_projeto: Path, tipo_forcado: str | None = None) -> dict[str, Any]:
    """Monta pacote textual de contexto caso o usuário queira inspecionar ou colar externamente."""
    tipo = (
        "short"
        if tipo_forcado == "short"
        else "longo"
        if tipo_forcado == "longo"
        else inferir_tipo_projeto(pasta_projeto)
    )
    formato = "9:16" if tipo == "short" else "16:9"
    narracao = (
        (pasta_projeto / "02-narracao.txt").read_text(encoding="utf-8", errors="replace").strip()
        if (pasta_projeto / "02-narracao.txt").exists()
        else ""
    )
    ts_path = pasta_projeto / "03-timestamps.json"
    duracao_total = 0.0
    segmentos: list[dict[str, Any]] = []
    if ts_path.exists():
        ts_data = json.loads(ts_path.read_text(encoding="utf-8"))
        duracao_total = float(ts_data.get("duracao_total", 0.0))
        segmentos = ts_data.get("segmentos", [])
    elif not narracao:
        raise ValueError("Projeto sem 03-timestamps.json nem 02-narracao.txt.")

    pacote = (
        f"PROJETO: {pasta_projeto.name} ({formato})\n"
        f"PREFIXO OBRIGATÓRIO DE FUNDO:\n{PROMPT_PREFIXO_PADRAO}\n"
        f"REGRA: zero palavras negativas após o prefixo.\n\n"
        f"NARRAÇÃO:\n{narracao}"
    )
    return {
        "ok": True,
        "projeto": pasta_projeto.name,
        "tipo": tipo,
        "formato": formato,
        "duracao_total": round(duracao_total, 2),
        "qtd_cortes": len(segmentos),
        "origem": "timestamps" if segmentos else "narracao",
        "pacote": pacote,
    }
