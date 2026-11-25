"""Biblioteca de personagem para o sistema de camadas (fundo + personagem transparente).

Lê as saídas de scripts/cortar_sprites.py, lista poses (frame_XX.png) e sprite sheets
(strip.png) e escolhe o asset mais adequado para cada cena por pontuação de tags,
com rodízio anti-repetição.

Estrutura esperada em cada fonte:
    <fonte>/<pasta>/frame_01.png ... frame_NN.png
    <fonte>/<pasta>/strip.png
    <fonte>/<pasta>/meta.json   (opcional, gravado pelo cortar_sprites.py e editável no Studio)

Formato do meta.json:
    {"modo": "poses" | "sprite", "frames": 4, "quadro": 512, "fps": 8,
     "tags_pasta": ["andar"], "tags": {"frame_02.png": ["ansioso", "panico"]}}
"""
from __future__ import annotations

import json
import re
import struct
import unicodedata
from pathlib import Path
from typing import Any

RAIZ_DIR = Path(__file__).resolve().parent.parent

# O campo "fonte" do personagem na cena permite plugar outros personagens depois.
FONTES: dict[str, Path] = {
    "protagonista": RAIZ_DIR / "assets" / "personagem" / "sprites_output",
    "secundarios": RAIZ_DIR / "assets" / "secundarios",
}
FONTE_PADRAO = "protagonista"

QUADRO_PADRAO = 512
FPS_SPRITE_PADRAO = 8

TIPOS_PERSONAGEM = ("pose", "sprite", "none")
POSICOES = ("center", "left", "right", "bottom-corner", "bottom-left")
ANIMACOES = ("pop-in", "slide-in-left", "slide-in-right", "float", "bounce", "shake", "none")

POSICOES_CICLO: dict[str, list[str]] = {
    "16:9": ["right", "left", "center", "right", "bottom-corner", "left"],
    "9:16": ["center", "bottom-corner", "center", "bottom-left"],
}

ANIMACAO_POR_EFEITO: dict[str, str] = {
    "pop-in": "pop-in",
    "impact-pop": "pop-in",
    "shake": "shake",
    "slide-up": "bounce",
    "zoom-in": "float",
    "zoom-out": "float",
    "cut": "none",
}

NOMES_SPRITE = ("walk", "cycle", "run", "sprite", "anim", "loop")

_RE_MOVIMENTO = re.compile(
    r"\b(?:andar|andando|anda\b|caminh|corr(?:er|endo)\b|cheg|seguir|seguindo|segue\b|avanc|fugi|passo|jornada)"
)


def normalizar_ascii(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode("ascii")


def _limpar_tags(tags: Any) -> list[str]:
    if not isinstance(tags, (list, tuple)):
        return []
    vistas: set[str] = set()
    resultado: list[str] = []
    for tag in tags:
        limpa = str(tag).strip().lower()
        chave = normalizar_ascii(limpa)
        if len(chave) >= 2 and chave not in vistas:
            vistas.add(chave)
            resultado.append(limpa)
    return resultado


def _tags_casam(a: str, b: str) -> bool:
    if a == b:
        return True
    return min(len(a), len(b)) >= 4 and (a.startswith(b) or b.startswith(a))


def _dimensoes_png(caminho: Path) -> tuple[int, int] | None:
    try:
        with caminho.open("rb") as f:
            cabecalho = f.read(24)
    except OSError:
        return None
    if cabecalho[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    largura, altura = struct.unpack(">II", cabecalho[16:24])
    return largura, altura


def resolver_pasta(fonte: str, pasta: str) -> Path | None:
    raiz = FONTES.get(fonte)
    nome = Path(str(pasta or "")).name
    if raiz is None or not nome or nome in {".", ".."}:
        return None
    caminho = (raiz / nome).resolve()
    if caminho.parent != raiz.resolve() or not caminho.is_dir():
        return None
    return caminho


def resolver_asset(fonte: str, asset: str) -> Path | None:
    """Resolve '<pasta>/<arquivo>.png' dentro da fonte, garantindo que o caminho não escapa da raiz."""
    partes = str(asset or "").replace("\\", "/").split("/")
    if len(partes) != 2:
        return None
    pasta = resolver_pasta(fonte, partes[0])
    if pasta is None:
        return None
    caminho = (pasta / Path(partes[1]).name).resolve()
    if caminho.parent != pasta or not caminho.is_file() or caminho.suffix.lower() != ".png":
        return None
    return caminho


def _ler_meta(pasta: Path) -> dict[str, Any]:
    meta_path = pasta / "meta.json"
    if meta_path.is_file():
        try:
            dados = json.loads(meta_path.read_text(encoding="utf-8"))
            if isinstance(dados, dict):
                return dados
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def _inferir_modo(nome_pasta: str) -> str:
    nome = nome_pasta.lower()
    return "sprite" if any(k in nome for k in NOMES_SPRITE) else "poses"


def _descrever_pasta(fonte: str, pasta: Path) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
    frames = sorted(pasta.glob("frame_*.png"))
    strip = pasta / "strip.png"
    outros_pngs = sorted(
        p for p in pasta.glob("*.png") if p.name != "strip.png" and p not in frames
    )
    poses_pngs = frames + outros_pngs
    if not poses_pngs and not strip.is_file():
        return None

    meta = _ler_meta(pasta)
    modo = meta.get("modo") if meta.get("modo") in ("poses", "sprite") else _inferir_modo(pasta.name)

    quadro = int(meta.get("quadro") or 0)
    if quadro <= 0:
        dim = _dimensoes_png(poses_pngs[0]) if poses_pngs else None
        quadro = dim[1] if dim else QUADRO_PADRAO

    qtd_frames = len(poses_pngs)
    if strip.is_file():
        dim_strip = _dimensoes_png(strip)
        if dim_strip and quadro > 0:
            qtd_frames = max(1, dim_strip[0] // quadro)

    fps = int(meta.get("fps") or FPS_SPRITE_PADRAO)
    tags_pasta = _limpar_tags(meta.get("tags_pasta"))
    tags_por_arquivo = meta.get("tags") if isinstance(meta.get("tags"), dict) else {}

    def montar(arquivo: str, tipo: str, n_frames: int) -> dict[str, Any]:
        proprias = _limpar_tags(tags_por_arquivo.get(arquivo))
        return {
            "id": f"{pasta.name}/{arquivo}",
            "fonte": fonte,
            "pasta": pasta.name,
            "arquivo": arquivo,
            "tipo": tipo,
            "frames": n_frames,
            "quadro": quadro,
            "fps": fps,
            "tags": _limpar_tags([*tags_pasta, *proprias]),
            "tags_proprias": proprias,
        }

    assets: list[dict[str, Any]] = []
    if modo == "sprite" and strip.is_file():
        assets.append(montar("strip.png", "sprite", qtd_frames))
    elif poses_pngs:
        assets.extend(montar(f.name, "pose", 1) for f in poses_pngs)
    elif strip.is_file():
        assets.append(montar("strip.png", "sprite", qtd_frames))

    resumo = {
        "fonte": fonte,
        "pasta": pasta.name,
        "modo": modo,
        "modo_inferido": "modo" not in meta,
        "frames": qtd_frames,
        "quadro": quadro,
        "fps": fps,
        "tags_pasta": tags_pasta,
        "qtd_assets": len(assets),
    }
    return resumo, assets


def listar_biblioteca() -> dict[str, Any]:
    pastas: list[dict[str, Any]] = []
    assets: list[dict[str, Any]] = []
    for fonte, raiz in FONTES.items():
        if not raiz.is_dir():
            continue
        diretorios = sorted((p for p in raiz.iterdir() if p.is_dir()), key=lambda p: p.name.lower())
        for pasta in diretorios:
            descrito = _descrever_pasta(fonte, pasta)
            if descrito is None:
                continue
            resumo, itens = descrito
            pastas.append(resumo)
            assets.extend(itens)
    return {"pastas": pastas, "assets": assets}


def atualizar_meta_pasta(
    fonte: str,
    pasta_nome: str,
    modo: str | None = None,
    fps: int | None = None,
    tags_pasta: list[str] | None = None,
    tags: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    pasta = resolver_pasta(fonte, pasta_nome)
    if pasta is None:
        raise FileNotFoundError(f"Pasta de personagem '{pasta_nome}' não encontrada.")

    meta = _ler_meta(pasta)
    if meta.get("modo") not in ("poses", "sprite"):
        meta["modo"] = _inferir_modo(pasta.name)
    if modo in ("poses", "sprite"):
        meta["modo"] = modo
    if fps is not None and fps > 0:
        meta["fps"] = int(fps)
    if tags_pasta is not None:
        meta["tags_pasta"] = _limpar_tags(tags_pasta)
    if tags is not None:
        atuais = meta.get("tags") if isinstance(meta.get("tags"), dict) else {}
        for arquivo, lista in tags.items():
            nome = Path(arquivo).name
            if (pasta / nome).is_file():
                atuais[nome] = _limpar_tags(lista)
        meta["tags"] = atuais

    (pasta / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def personagem_vazio(fonte: str = FONTE_PADRAO, tags: list[str] | None = None) -> dict[str, Any]:
    return {"tipo": "none", "fonte": fonte, "tags": list(tags or [])}


class SeletorPersonagem:
    """Escolhe pose/sprite por cena: pontua tags e evita repetir o mesmo asset em sequência."""

    def __init__(
        self,
        formato: str = "16:9",
        assets: list[dict[str, Any]] | None = None,
        fonte: str = FONTE_PADRAO,
    ) -> None:
        todos = listar_biblioteca()["assets"] if assets is None else assets
        self.fonte = fonte
        self.assets = [a for a in todos if a["fonte"] == fonte]
        self.formato = formato
        self.historico: list[str] = []
        self.posicoes: list[str] = []
        self.usos: dict[str, int] = {}

    def tags_disponiveis(self) -> list[str]:
        return sorted({tag for a in self.assets for tag in a["tags"]}, key=normalizar_ascii)

    def registrar(self, personagem: dict[str, Any]) -> None:
        asset = str(personagem.get("asset") or "")
        self.historico.append(asset)
        self.posicoes.append(str(personagem.get("posicao") or ""))
        if asset:
            self.usos[asset] = self.usos.get(asset, 0) + 1

    def _pontuar(self, asset: dict[str, Any], texto_norm: str, desejadas: list[str]) -> float:
        pontos = 0.0
        for tag in asset["tags"]:
            chave = normalizar_ascii(tag).strip()
            if len(chave) < 2:
                continue
            if any(_tags_casam(chave, d) for d in desejadas):
                pontos += 3.0
            if re.search(r"\b" + re.escape(chave), texto_norm):
                pontos += 2.0
        if self.historico and self.historico[-1] == asset["id"]:
            pontos -= 5.0
        pontos -= 0.75 * self.historico[-4:].count(asset["id"])
        pontos -= 0.1 * self.usos.get(asset["id"], 0)
        return pontos

    def _proxima_posicao(self) -> str:
        ciclo = POSICOES_CICLO.get(self.formato, POSICOES_CICLO["16:9"])
        base = len(self.historico)
        for passo in range(len(ciclo)):
            candidata = ciclo[(base + passo) % len(ciclo)]
            if not self.posicoes or candidata != self.posicoes[-1]:
                return candidata
        return ciclo[0]

    def escolher(
        self,
        texto: str,
        efeito: str = "",
        tags_desejadas: list[str] | None = None,
        posicao: str | None = None,
        animacao: str | None = None,
    ) -> dict[str, Any]:
        tags = list(tags_desejadas or [])
        if not self.assets:
            vazio = personagem_vazio(self.fonte, tags)
            self.registrar(vazio)
            return vazio

        texto_norm = normalizar_ascii(texto or "")
        desejadas = [normalizar_ascii(t).strip() for t in tags if t]
        tipos_presentes = {a["tipo"] for a in self.assets}
        movimento = bool(_RE_MOVIMENTO.search(texto_norm))
        preferido = "sprite" if movimento and "sprite" in tipos_presentes else "pose"
        candidatos = [a for a in self.assets if a["tipo"] == preferido] or self.assets

        escolhido = max(
            candidatos,
            key=lambda a: (
                self._pontuar(a, texto_norm, desejadas),
                -self.usos.get(a["id"], 0),
                -candidatos.index(a),
            ),
        )

        posicao_final = posicao if posicao in POSICOES else self._proxima_posicao()
        if animacao in ANIMACOES:
            animacao_final = animacao
        elif escolhido["tipo"] == "sprite":
            animacao_final = "slide-in-right" if posicao_final in ("right", "bottom-corner") else "slide-in-left"
        else:
            animacao_final = ANIMACAO_POR_EFEITO.get((efeito or "").lower(), "pop-in")

        personagem: dict[str, Any] = {
            "tipo": escolhido["tipo"],
            "fonte": escolhido["fonte"],
            "asset": escolhido["id"],
            "posicao": posicao_final,
            "escala": 0.8 if posicao_final in ("bottom-corner", "bottom-left") else 1.0,
            "flip": False,
            "animacao": animacao_final,
            "tags": tags,
        }
        if escolhido["tipo"] == "sprite":
            personagem["sprite"] = {
                "frames": escolhido["frames"],
                "quadro": escolhido["quadro"],
                "fps": escolhido["fps"],
            }
        self.registrar(personagem)
        return personagem
