import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from PIL import Image
from pydantic import BaseModel

from scripts.cortar_sprites import (
    detectar_grade_2x2,
    garantir_pose_sem_fundo,
    processar_grade,
    processar_pose_solo,
)
from scripts.limpar_imagens import remover_fundo_externo

from backend.comfyui import (
    cancelar_job as comfy_cancelar_job,
    iniciar_geracao_comfyui,
    obter_status_job as comfy_status_job,
    status_comfyui,
)
from backend.gemini_client import (
    GeminiConfigError,
    GeminiGenerationError,
    status_gemini,
)
from backend.personagem import (
    FONTE_PADRAO,
    atualizar_meta_pasta,
    listar_biblioteca,
    resolver_asset,
)
from backend.pipeline import (
    gerar_cenas_de_prompts_salvos,
    gerar_ideias_ou_roteiro,
    gerar_seo_e_thumb,
    gerar_storyboard_automatico,
    inferir_tipo_projeto,
    ler_ou_criar_meta_projeto,
    montar_pacote_chat,
    salvar_meta_projeto,
    sugerir_personagens,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
PROJETOS_DIR = ROOT_DIR / "projetos"
SCRIPTS_DIR = ROOT_DIR / "scripts"
TEMPLATE_DIR = ROOT_DIR / "template-remotion"

PROJETOS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Só um Rabisco Studio API",
    version="1.0.0",
    description="API local para gerenciar produção de vídeos do canal Só um Rabisco",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CriarProjetoPayload(BaseModel):
    nome: str
    tipo: Literal["longo", "short"] = "longo"


class RenomearProjetoPayload(BaseModel):
    novo_nome: str


class AtualizarMetaPayload(BaseModel):
    tipo: Literal["longo", "short"] | None = None
    titulo_thumb: str | None = None
    duracao_thumb: str | None = None
    legenda_short: str | None = None
    hashtags_short: str | None = None


class TextoPayload(BaseModel):
    conteudo: str


class CenasPayload(BaseModel):
    dados: dict[str, Any]


class GerarRoteiroPayload(BaseModel):
    tema: str
    modo: Literal["ideias", "roteiro"] = "roteiro"
    tipo: Literal["longo", "short"] | None = None
    salvar: bool = True


class ReordenarImagensPayload(BaseModel):
    ordem: list[str]


class PersonagemMetaPayload(BaseModel):
    modo: Literal["poses", "sprite"] | None = None
    fps: int | None = None
    tags_pasta: list[str] | None = None
    tags: dict[str, list[str]] | None = None


class ComfyGerarPayload(BaseModel):
    apenas_faltantes: bool = False
    indice_cena: int | None = None
    checkpoint: str | None = None
    steps: int | None = None
    cfg: float | None = None
    sampler_name: str | None = None
    scheduler: str | None = None
    largura: int | None = None
    altura: int | None = None
    seed: int | None = None
    negativo_extra: str | None = None
    workflow_api: dict[str, Any] | None = None


def _validar_nome_projeto(nome: str) -> str:
    nome_limpo = nome.strip()
    if not nome_limpo or nome_limpo in {".", ".."}:
        raise HTTPException(status_code=400, detail="Nome de projeto inválido.")
    if any(sep in nome_limpo for sep in ("/", "\\", "\x00")) or ".." in nome_limpo:
        raise HTTPException(status_code=400, detail="Nome de projeto contém caracteres inválidos.")
    if re.search(r'[<>:"|?*]', nome_limpo):
        raise HTTPException(status_code=400, detail="Nome de projeto contém caracteres não permitidos no Windows.")
    return nome_limpo


def _resolver_projeto(nome: str, exigir_existente: bool = True) -> Path:
    nome_limpo = _validar_nome_projeto(nome)
    caminho = (PROJETOS_DIR / nome_limpo).resolve()
    if caminho.parent != PROJETOS_DIR.resolve():
        raise HTTPException(status_code=400, detail="Caminho de projeto inválido.")
    if exigir_existente and not caminho.is_dir():
        raise HTTPException(status_code=404, detail=f"Projeto '{nome_limpo}' não encontrado.")
    return caminho


def _executar_script(script_nome: str, args: list[str], timeout_sec: int = 600) -> dict[str, Any]:
    script_path = SCRIPTS_DIR / script_nome
    if not script_path.exists():
        raise HTTPException(status_code=500, detail=f"Script '{script_nome}' não encontrado.")

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        proc = subprocess.run(
            [sys.executable, str(script_path), *args],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(
            status_code=504,
            detail=f"Tempo limite excedido ao executar {script_nome}.",
        ) from exc

    if proc.returncode != 0:
        erro = (proc.stderr or proc.stdout or "Erro desconhecido").strip()
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao executar {script_nome}: {erro}",
        )

    return {
        "ok": True,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def _resumo_projeto(pasta: Path) -> dict[str, Any]:
    midia_dir = pasta / "midia"
    cenas_dir = midia_dir / "cenas"
    raw_dir = midia_dir / "raw"

    tem_narracao = (pasta / "02-narracao.txt").exists()
    tem_timestamps = (pasta / "03-timestamps.json").exists()
    tem_storyboard = (pasta / "04-storyboard-e-prompts.md").exists()
    tem_cenas_json = (pasta / "cenas.json").exists()
    tem_audio = any((midia_dir / ext).exists() for ext in ("audio.wav", "audio.mp3", "audio.m4a"))

    qtd_imagens_cenas = (
        len([f for f in cenas_dir.iterdir() if f.is_file() and f.suffix.lower() == ".png"])
        if cenas_dir.is_dir()
        else 0
    )
    qtd_imagens_raw = (
        len([f for f in raw_dir.iterdir() if f.is_file()])
        if raw_dir.is_dir()
        else 0
    )

    duracao_total = None
    qtd_cenas_json = 0
    tipo = inferir_tipo_projeto(pasta)
    formato = "9:16" if tipo == "short" else "16:9"

    if tem_cenas_json:
        try:
            cenas_data = json.loads((pasta / "cenas.json").read_text(encoding="utf-8"))
            duracao_total = cenas_data.get("duracao_total")
            qtd_cenas_json = len(cenas_data.get("cenas", []))
            formato = cenas_data.get("formato", formato)
            if formato == "9:16":
                tipo = "short"
        except Exception:
            pass

    if duracao_total is None and tem_timestamps:
        try:
            ts_data = json.loads((pasta / "03-timestamps.json").read_text(encoding="utf-8"))
            duracao_total = ts_data.get("duracao_total")
        except Exception:
            pass

    return {
        "nome": pasta.name,
        "tipo": tipo,
        "atualizado_em": pasta.stat().st_mtime,
        "tem_narracao": tem_narracao,
        "tem_timestamps": tem_timestamps,
        "tem_storyboard": tem_storyboard,
        "tem_cenas_json": tem_cenas_json,
        "tem_audio": tem_audio,
        "tem_prompts_flow": (pasta / "prompts_flow.txt").exists(),
        "qtd_imagens_cenas": qtd_imagens_cenas,
        "qtd_imagens_raw": qtd_imagens_raw,
        "qtd_cenas_json": qtd_cenas_json,
        "duracao_total": duracao_total,
        "formato": formato,
    }


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "studio": "Só um Rabisco"}


@app.get("/api/gemini/status")
def obter_status_gemini() -> dict[str, Any]:
    return status_gemini(ROOT_DIR)


@app.get("/api/projetos")
def listar_projetos() -> dict[str, Any]:
    if not PROJETOS_DIR.exists():
        return {"projetos": []}

    pastas = [p for p in PROJETOS_DIR.iterdir() if p.is_dir()]
    pastas.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return {"projetos": [_resumo_projeto(p) for p in pastas]}


@app.post("/api/projetos", status_code=201)
def criar_projeto(payload: CriarProjetoPayload) -> dict[str, Any]:
    pasta = _resolver_projeto(payload.nome, exigir_existente=False)
    if pasta.exists():
        raise HTTPException(status_code=409, detail=f"Já existe um projeto chamado '{pasta.name}'.")

    (pasta / "midia" / "raw").mkdir(parents=True, exist_ok=True)
    (pasta / "midia" / "cenas").mkdir(parents=True, exist_ok=True)

    (pasta / "01-ideia-e-roteiro.md").write_text(f"# {pasta.name}\n\n", encoding="utf-8")
    (pasta / "02-narracao.txt").write_text("", encoding="utf-8")
    (pasta / "04-storyboard-e-prompts.md").write_text(
        f"# Storyboard e Prompts - {pasta.name}\n\n", encoding="utf-8"
    )
    (pasta / "05-seo-e-thumb.md").write_text(f"# SEO e Thumb - {pasta.name}\n\n", encoding="utf-8")
    salvar_meta_projeto(pasta, payload.tipo)

    return {"projeto": _resumo_projeto(pasta)}


@app.delete("/api/projetos/{nome}")
def excluir_projeto(nome: str) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    with _RENDER_LOCK:
        if _RENDER_ESTADO["status"] == "running" and _RENDER_ESTADO.get("projeto") == pasta.name:
            raise HTTPException(
                status_code=409,
                detail="Este projeto está sendo renderizado no momento. Aguarde concluir antes de excluir.",
            )
    if comfy_status_job(pasta.name).get("status") == "running":
        raise HTTPException(
            status_code=409,
            detail="Este projeto está gerando imagens no ComfyUI. Cancele antes de excluir.",
        )

    shutil.rmtree(pasta)
    return {"ok": True, "projeto": pasta.name}


@app.patch("/api/projetos/{nome}/renomear")
def renomear_projeto(nome: str, payload: RenomearProjetoPayload) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    novo_nome = _validar_nome_projeto(payload.novo_nome)
    if novo_nome == pasta.name:
        return {"ok": True, "nome_antigo": pasta.name, "projeto": _resumo_projeto(pasta)}

    with _RENDER_LOCK:
        if _RENDER_ESTADO["status"] == "running" and _RENDER_ESTADO.get("projeto") == pasta.name:
            raise HTTPException(
                status_code=409,
                detail="Este projeto está sendo renderizado no momento. Aguarde concluir antes de renomear.",
            )
    if comfy_status_job(pasta.name).get("status") == "running":
        raise HTTPException(
            status_code=409,
            detail="Este projeto está gerando imagens no ComfyUI. Cancele antes de renomear.",
        )

    destino = (PROJETOS_DIR / novo_nome).resolve()
    if destino.parent != PROJETOS_DIR.resolve():
        raise HTTPException(status_code=400, detail="Nome de projeto inválido.")
    if destino.exists():
        raise HTTPException(status_code=409, detail=f"Já existe um projeto chamado '{novo_nome}'.")

    nome_antigo = pasta.name
    pasta.rename(destino)

    cenas_path = destino / "cenas.json"
    if cenas_path.exists():
        try:
            cenas_data = json.loads(cenas_path.read_text(encoding="utf-8"))
            cenas_data["projeto"] = destino.name
            cenas_path.write_text(json.dumps(cenas_data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    return {"ok": True, "nome_antigo": nome_antigo, "projeto": _resumo_projeto(destino)}


@app.get("/api/projetos/{nome}/meta")
def ler_meta(nome: str) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    return {"meta": ler_ou_criar_meta_projeto(pasta)}


@app.patch("/api/projetos/{nome}/meta")
def atualizar_meta(nome: str, payload: AtualizarMetaPayload) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    meta_atual = ler_ou_criar_meta_projeto(pasta)
    novo_tipo = payload.tipo or meta_atual.get("tipo", "longo")

    extras: dict[str, Any] = {}
    if payload.titulo_thumb is not None:
        extras["titulo_thumb"] = payload.titulo_thumb
    if payload.duracao_thumb is not None:
        extras["duracao_thumb"] = payload.duracao_thumb
    if payload.legenda_short is not None:
        extras["legenda_short"] = payload.legenda_short
    if payload.hashtags_short is not None:
        extras["hashtags_short"] = payload.hashtags_short

    meta_salva = salvar_meta_projeto(pasta, novo_tipo, extras=extras)

    # Sincroniza formato dentro de cenas.json caso exista e o tipo tenha mudado
    cenas_path = pasta / "cenas.json"
    if payload.tipo and cenas_path.exists():
        try:
            cenas_data = json.loads(cenas_path.read_text(encoding="utf-8"))
            cenas_data["formato"] = meta_salva["formato"]
            cenas_path.write_text(
                json.dumps(cenas_data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    return {"ok": True, "meta": meta_salva, "projeto": _resumo_projeto(pasta)}


@app.get("/api/projetos/{nome}/narracao")
def ler_narracao(nome: str) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    arquivo = pasta / "02-narracao.txt"
    conteudo = arquivo.read_text(encoding="utf-8") if arquivo.exists() else ""
    return {"nome": pasta.name, "conteudo": conteudo, "existe": arquivo.exists()}


@app.put("/api/projetos/{nome}/narracao")
def salvar_narracao(nome: str, payload: TextoPayload) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    arquivo = pasta / "02-narracao.txt"
    arquivo.write_text(payload.conteudo, encoding="utf-8")
    return {
        "ok": True,
        "arquivo": "02-narracao.txt",
        "caracteres": len(payload.conteudo),
        "palavras": len(payload.conteudo.split()),
    }


@app.get("/api/projetos/{nome}/storyboard")
def ler_storyboard(nome: str) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    arquivo = pasta / "04-storyboard-e-prompts.md"
    conteudo = arquivo.read_text(encoding="utf-8") if arquivo.exists() else ""
    return {"nome": pasta.name, "conteudo": conteudo, "existe": arquivo.exists()}


def _sincronizar_prompts_imagens(conteudo_storyboard: str) -> int:
    prompts: list[str] = []
    tempos: list[str] = []
    for linha in conteudo_storyboard.splitlines():
        texto_linha = linha.strip()
        m = re.match(r"^(\[\d{2}:\d{2}\])\s*(.*)$", texto_linha)
        if m:
            tempos.append(m.group(1))
            prompts.append(m.group(2))

    destino = ROOT_DIR / "prompts_imagens.txt"
    destino.write_text("\n\n".join(prompts) + ("\n" if prompts else ""), encoding="utf-8")

    destino_tempos = ROOT_DIR / "tempos_imagens.txt"
    destino_tempos.write_text("\n\n".join(tempos) + ("\n" if tempos else ""), encoding="utf-8")
    return len(prompts)


@app.put("/api/projetos/{nome}/storyboard")
def salvar_storyboard(nome: str, payload: TextoPayload) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    arquivo = pasta / "04-storyboard-e-prompts.md"
    arquivo.write_text(payload.conteudo, encoding="utf-8")
    qtd_prompts = _sincronizar_prompts_imagens(payload.conteudo)
    return {
        "ok": True,
        "arquivo": "04-storyboard-e-prompts.md",
        "prompts_atualizados": qtd_prompts,
    }


@app.post("/api/projetos/{nome}/exportar-prompts")
def exportar_prompts_imagens(nome: str) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    cenas_path = pasta / "cenas.json"
    prompts_todos: list[str] = []
    prompts_fundo: list[str] = []
    prompts_pers: list[str] = []
    tempos_linhas: list[str] = []

    if cenas_path.exists():
        try:
            cenas_data = json.loads(cenas_path.read_text(encoding="utf-8"))
            for idx, c in enumerate(cenas_data.get("cenas", []), start=1):
                pf = str(c.get("prompt_fundo") or (c.get("fundo") or {}).get("prompt") or "").strip()
                pp = str(c.get("prompt_personagem") or (c.get("personagem") or {}).get("prompt") or "").strip()
                if pf:
                    prompts_fundo.append(pf)
                    prompts_todos.append(pf)
                if pp:
                    prompts_pers.append(pp)
                    prompts_todos.append(pp)
                ini = float(c.get("inicio") or 0.0)
                fim = float(c.get("fim") or ini)
                seg_i = max(0, int(round(ini)))
                tempos_linhas.append(f"{idx:02d}\t{ini:.2f}\t{fim:.2f}\t[{seg_i // 60:02d}:{seg_i % 60:02d}]")
        except Exception:
            prompts_todos = []

    if prompts_todos:
        conteudo_txt = "\n\n".join(prompts_todos) + "\n"
        (pasta / "prompts_imagens.txt").write_text(conteudo_txt, encoding="utf-8")
        (ROOT_DIR / "prompts_imagens.txt").write_text(conteudo_txt, encoding="utf-8")
        if prompts_pers:
            (pasta / "prompts_personagens.txt").write_text(
                "\n\n".join(prompts_pers) + "\n", encoding="utf-8"
            )
        if tempos_linhas:
            tempos_txt = "\n".join(tempos_linhas) + "\n"
            (pasta / "tempos_imagens.txt").write_text(tempos_txt, encoding="utf-8")
            (ROOT_DIR / "tempos_imagens.txt").write_text(tempos_txt, encoding="utf-8")
        return {
            "ok": True,
            "arquivo_destino": "prompts_imagens.txt",
            "qtd_prompts": len(prompts_todos),
        }

    arquivo = pasta / "04-storyboard-e-prompts.md"
    if not arquivo.exists():
        raise HTTPException(
            status_code=404,
            detail="Nenhum cenas.json nem 04-storyboard-e-prompts.md encontrado neste projeto.",
        )
    conteudo = arquivo.read_text(encoding="utf-8")
    qtd_prompts = _sincronizar_prompts_imagens(conteudo)
    if qtd_prompts == 0:
        # Fallback caso o markdown tenha prompts sem prefixo [MM:SS]
        linhas_prompts = [
            l.strip()
            for l in conteudo.splitlines()
            if l.strip() and not l.strip().startswith(("#", "- "))
        ]
        if linhas_prompts:
            txt = "\n\n".join(linhas_prompts) + "\n"
            (pasta / "prompts_imagens.txt").write_text(txt, encoding="utf-8")
            (ROOT_DIR / "prompts_imagens.txt").write_text(txt, encoding="utf-8")
            qtd_prompts = len(linhas_prompts)
    return {
        "ok": True,
        "arquivo_destino": "prompts_imagens.txt",
        "qtd_prompts": qtd_prompts,
    }


@app.get("/api/projetos/{nome}/timestamps")
def ler_timestamps(nome: str) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    arquivo = pasta / "03-timestamps.json"
    if not arquivo.exists():
        return {"existe": False, "dados": None}
    try:
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"03-timestamps.json inválido: {exc}") from exc
    return {"existe": True, "dados": dados}


@app.post("/api/projetos/{nome}/gerar-roteiro")
def gerar_roteiro_endpoint(nome: str, payload: GerarRoteiroPayload) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    try:
        return gerar_ideias_ou_roteiro(
            pasta,
            payload.tema,
            modo=payload.modo,
            tipo_forcado=payload.tipo,
            salvar=payload.salvar,
        )
    except (ValueError, GeminiConfigError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GeminiGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/projetos/{nome}/seo-thumb")
def ler_seo_thumb(nome: str) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    arquivo = pasta / "05-seo-e-thumb.md"
    markdown = arquivo.read_text(encoding="utf-8") if arquivo.exists() else ""
    return {
        "nome": pasta.name,
        "existe": arquivo.exists(),
        "markdown": markdown,
        "meta": ler_ou_criar_meta_projeto(pasta),
    }


@app.post("/api/projetos/{nome}/gerar-seo-thumb")
def gerar_seo_thumb_endpoint(nome: str, tipo: str | None = None) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    try:
        return gerar_seo_e_thumb(pasta, tipo_forcado=tipo, salvar=True)
    except (ValueError, GeminiConfigError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GeminiGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/projetos/{nome}/gerar-storyboard")
def gerar_storyboard_endpoint(nome: str, tipo: str | None = None) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    try:
        resultado = gerar_storyboard_automatico(pasta, tipo_forcado=tipo)
    except (ValueError, GeminiConfigError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GeminiGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return resultado


@app.post("/api/projetos/{nome}/gerar-cenas-prompts")
def gerar_cenas_prompts_endpoint(nome: str, tipo: str | None = None) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    try:
        return gerar_cenas_de_prompts_salvos(pasta, tipo_forcado=tipo)
    except (ValueError, GeminiConfigError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GeminiGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/projetos/{nome}/pacote-chat")
def obter_pacote_chat(nome: str, tipo: str | None = None) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    try:
        return montar_pacote_chat(pasta, tipo_forcado=tipo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/projetos/{nome}/cenas")
def ler_cenas(nome: str) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    arquivo = pasta / "cenas.json"
    tipo = inferir_tipo_projeto(pasta)
    formato_padrao = "9:16" if tipo == "short" else "16:9"
    if not arquivo.exists():
        return {
            "existe": False,
            "dados": {
                "projeto": pasta.name,
                "formato": formato_padrao,
                "fps": 30,
                "duracao_total": 0,
                "audio": "assets_atual/audio.wav",
                "cenas": [],
            },
        }
    try:
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"cenas.json inválido: {exc}") from exc
    return {"existe": True, "dados": dados}


@app.put("/api/projetos/{nome}/cenas")
def salvar_cenas(nome: str, payload: CenasPayload) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    arquivo = pasta / "cenas.json"
    arquivo.write_text(json.dumps(payload.dados, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "arquivo": "cenas.json",
        "qtd_cenas": len(payload.dados.get("cenas", [])),
    }


@app.post("/api/projetos/{nome}/cenas/sugerir-personagem")
def sugerir_personagem_cenas(
    nome: str,
    payload: CenasPayload,
    apenas_sem_personagem: bool = False,
) -> dict[str, Any]:
    """Sugere pose/sprite da biblioteca para cada cena do cenas.json enviado via Gemini, sem gravar em disco."""
    _resolver_projeto(nome)
    try:
        alteradas = sugerir_personagens(payload.dados, apenas_sem_personagem=apenas_sem_personagem)
    except (ValueError, GeminiConfigError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GeminiGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"ok": True, "alteradas": alteradas, "dados": payload.dados}


@app.get("/api/personagem/biblioteca")
def obter_biblioteca_personagem() -> dict[str, Any]:
    return listar_biblioteca()


@app.get("/api/personagem/arquivo/{pasta}/{arquivo}")
def obter_arquivo_personagem(pasta: str, arquivo: str, fonte: str = FONTE_PADRAO) -> FileResponse:
    caminho = resolver_asset(fonte, f"{pasta}/{arquivo}")
    if caminho is None:
        raise HTTPException(status_code=404, detail="Asset de personagem não encontrado.")
    if caminho.name != "strip.png" and not caminho.name.startswith("frame_"):
        garantir_pose_sem_fundo(caminho)
    return FileResponse(caminho)


@app.put("/api/personagem/biblioteca/{pasta}")
def atualizar_biblioteca_personagem(
    pasta: str,
    payload: PersonagemMetaPayload,
    fonte: str = FONTE_PADRAO,
) -> dict[str, Any]:
    try:
        atualizar_meta_pasta(
            fonte,
            pasta,
            modo=payload.modo,
            fps=payload.fps,
            tags_pasta=payload.tags_pasta,
            tags=payload.tags,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True, **listar_biblioteca()}


@app.post("/api/personagem/upload")
async def upload_asset_personagem(
    file: UploadFile = File(...),
    pasta: str = Form("custom"),
    modo: Literal["auto", "poses", "sprite"] = Form("auto"),
    fps: int = Form(8),
    frames: int = Form(1),
    remover_fundo: bool = Form(True),
) -> dict[str, Any]:
    """Faz upload de pose solo (remove fundo) ou sprite 2x2 (remove fundo, corta 4 quadros e gera strip.png animado)."""
    import tempfile

    pasta_limpa = re.sub(r"[^A-Za-z0-9_-]+", "_", pasta.strip()) or "custom"
    nome_arq = Path(file.filename or "pose.png").stem
    nome_limpo = re.sub(r"[^A-Za-z0-9_-]+", "_", nome_arq).strip("_") or f"asset_{int(time.time())}"
    sprites_root = (ROOT_DIR / "assets" / "personagem" / "sprites_output").resolve()
    sprites_root.mkdir(parents=True, exist_ok=True)

    dados = await file.read()
    if not dados:
        raise HTTPException(status_code=400, detail="Arquivo de imagem vazio.")

    ext = Path(file.filename or "img.png").suffix.lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp"):
        ext = ".png"

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_img = Path(tmp_dir) / f"{nome_limpo}{ext}"
        tmp_img.write_bytes(dados)

        eh_sprite = modo == "sprite" or (modo == "auto" and detectar_grade_2x2(tmp_img))
        if eh_sprite:
            processar_grade(tmp_img, mesma_escala=True, pasta_saida=sprites_root)
            pasta_sprite = sprites_root / nome_limpo
            meta_path = pasta_sprite / "meta.json"
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                    meta["fps"] = max(1, min(30, int(fps)))
                    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception:
                    pass
            asset_id = f"{nome_limpo}/strip.png"
            tipo_retorno: Literal["pose", "sprite"] = "sprite"
        else:
            destino_dir = sprites_root / pasta_limpa
            destino_dir.mkdir(parents=True, exist_ok=True)
            destino_png = destino_dir / f"{nome_limpo}.png"
            if remover_fundo:
                processar_pose_solo(tmp_img, destino_png)
            else:
                from io import BytesIO
                Image.open(BytesIO(dados)).convert("RGBA").save(destino_png, format="PNG")

            meta_path = destino_dir / "meta.json"
            meta: dict[str, Any] = {}
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except Exception:
                    meta = {}
            meta["modo"] = "poses"
            meta.setdefault("tags_pasta", [])
            meta.setdefault("tags", {})
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            asset_id = f"{pasta_limpa}/{destino_png.name}"
            tipo_retorno = "pose"

    return {
        "ok": True,
        "asset_id": asset_id,
        "tipo": tipo_retorno,
        **listar_biblioteca(),
    }


@app.delete("/api/personagem/asset")
def excluir_asset_personagem(asset: str, fonte: str = FONTE_PADRAO) -> dict[str, Any]:
    """Exclui uma pose solo ou pasta de sprite da biblioteca de personagens."""
    caminho = resolver_asset(fonte, asset)
    if caminho is None:
        raise HTTPException(status_code=404, detail="Pose/sprite não encontrado na biblioteca.")

    pasta_asset = caminho.parent
    if caminho.name == "strip.png":
        shutil.rmtree(pasta_asset)
    else:
        caminho.unlink()
        restantes = [p for p in pasta_asset.glob("*.png") if p.is_file()]
        if not restantes:
            shutil.rmtree(pasta_asset)

    return {"ok": True, **listar_biblioteca()}


@app.post("/api/projetos/{nome}/audio")
async def upload_audio(
    nome: str,
    file: UploadFile = File(...),
    gerar_storyboard: bool = True,
) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    midia_dir = pasta / "midia"
    midia_dir.mkdir(parents=True, exist_ok=True)

    destino = midia_dir / "audio.wav"
    conteudo = await file.read()
    if not conteudo:
        raise HTTPException(status_code=400, detail="Arquivo de áudio vazio.")

    destino.write_bytes(conteudo)

    resultado_script = _executar_script("extrair_tempos.py", [str(pasta)], timeout_sec=900)

    timestamps_path = pasta / "03-timestamps.json"
    timestamps = None
    if timestamps_path.exists():
        timestamps = json.loads(timestamps_path.read_text(encoding="utf-8"))

    storyboard_info = None
    storyboard_erro = None
    if gerar_storyboard and timestamps is not None:
        try:
            res_sb = gerar_storyboard_automatico(pasta)
            storyboard_info = {
                "qtd_cenas": res_sb["qtd_cenas"],
                "formato": res_sb["formato"],
                "origem": res_sb["origem"],
            }
        except (GeminiConfigError, GeminiGenerationError, ValueError, RuntimeError) as exc:
            storyboard_info = None
            storyboard_erro = str(exc)

    return {
        "ok": True,
        "arquivo_salvo": "midia/audio.wav",
        "tamanho_bytes": len(conteudo),
        "log": resultado_script["stdout"],
        "timestamps": timestamps,
        "storyboard_gerado": storyboard_info,
        "storyboard_erro": storyboard_erro,
    }


@app.get("/api/projetos/{nome}/audio")
def obter_audio(nome: str) -> FileResponse:
    pasta = _resolver_projeto(nome)
    midia_dir = pasta / "midia"
    for ext in ("audio.wav", "audio.mp3", "audio.m4a"):
        candidato = midia_dir / ext
        if candidato.exists():
            return FileResponse(candidato)
    raise HTTPException(status_code=404, detail="Áudio não encontrado neste projeto.")


@app.post("/api/projetos/{nome}/imagens")
async def upload_imagens_em_lote(
    nome: str,
    files: list[UploadFile] = File(...),
    limpar_anteriores: bool = True,
) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    raw_dir = pasta / "midia" / "raw"
    cenas_dir = pasta / "midia" / "cenas"
    raw_dir.mkdir(parents=True, exist_ok=True)
    cenas_dir.mkdir(parents=True, exist_ok=True)

    extensoes_validas = {".png", ".jpg", ".jpeg", ".webp"}
    arquivos_validos = sorted(
        [f for f in files if f.filename and Path(f.filename).suffix.lower() in extensoes_validas],
        key=lambda f: (f.filename or "").lower(),
    )
    if not arquivos_validos:
        raise HTTPException(
            status_code=400,
            detail="Nenhuma imagem válida (.png, .jpg, .jpeg, .webp) enviada.",
        )

    if limpar_anteriores:
        for antigo in raw_dir.iterdir():
            if antigo.is_file():
                antigo.unlink()
        for antigo in cenas_dir.iterdir():
            if antigo.is_file():
                antigo.unlink()

    cenas_existentes = sorted([f for f in cenas_dir.iterdir() if f.is_file() and f.suffix.lower() == ".png"])
    max_raw = 0
    for f in raw_dir.iterdir():
        if f.is_file():
            m = re.match(r"^(\d+)_", f.name)
            if m:
                max_raw = max(max_raw, int(m.group(1)))
    max_cena = 0
    for f in cenas_existentes:
        m = re.match(r"^cena_(\d+)\.png$", f.name, re.IGNORECASE)
        if m:
            max_cena = max(max_cena, int(m.group(1)))
    proximo_raw = max(max_raw, max_cena) + 1

    base_ts = time.time()
    salvos: list[str] = []
    destinos_raw: list[Path] = []

    for idx, arquivo in enumerate(arquivos_validos):
        nome_seguro = Path(arquivo.filename or f"imagem_{idx + 1:02d}.png").name
        destino = raw_dir / f"{proximo_raw + idx:03d}_{nome_seguro}"
        dados = await arquivo.read()
        destino.write_bytes(dados)
        ts = base_ts + idx * 0.01
        os.utime(destino, (ts, ts))
        salvos.append(destino.name)
        destinos_raw.append(destino)

    meta = ler_ou_criar_meta_projeto(pasta)
    manter_fundo = meta.get("tipo") == "longo"

    if not limpar_anteriores and cenas_existentes:
        # Adiciona apenas as novas imagens ao final sem reordenar nem sobrescrever as existentes
        from PIL import ImageOps
        logs_append: list[str] = []
        proximo_cena = max_cena + 1
        for offset, raw_arq in enumerate(destinos_raw):
            nome_saida = f"cena_{proximo_cena + offset:02d}.png"
            caminho_saida = cenas_dir / nome_saida
            if manter_fundo:
                with Image.open(raw_arq) as img_raw:
                    img_corrigida = ImageOps.exif_transpose(img_raw)
                    if img_corrigida.mode not in ("RGB", "RGBA"):
                        img_corrigida = img_corrigida.convert("RGB")
                    img_corrigida.save(caminho_saida, "PNG")
            else:
                img_limpa = remover_fundo_externo(raw_arq)
                img_limpa.save(caminho_saida, "PNG")
            logs_append.append(f"[OK] {raw_arq.name} -> {nome_saida}")
        stdout_log = "\n".join(logs_append)
    else:
        args_limpeza = [str(raw_dir), str(cenas_dir)]
        if manter_fundo:
            args_limpeza.append("--manter-fundo")
        resultado_script = _executar_script(
            "limpar_imagens.py",
            args_limpeza,
            timeout_sec=300,
        )
        stdout_log = resultado_script["stdout"]

    cenas_geradas = sorted([f.name for f in cenas_dir.iterdir() if f.is_file() and f.suffix.lower() == ".png"])

    return {
        "ok": True,
        "enviados": salvos,
        "cenas_geradas": cenas_geradas,
        "log": stdout_log,
    }


@app.post("/api/projetos/{nome}/imagens/cena")
async def upload_imagem_cena_individual(
    nome: str,
    arquivo_alvo: str = Form(...),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Adiciona ou substitui diretamente a imagem de fundo de uma cena específica em midia/cenas/."""
    pasta = _resolver_projeto(nome)
    cenas_dir = pasta / "midia" / "cenas"
    cenas_dir.mkdir(parents=True, exist_ok=True)

    nome_png = Path(arquivo_alvo.replace("\\", "/")).name
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.png", nome_png):
        raise HTTPException(status_code=400, detail="Nome de arquivo PNG inválido para a cena.")

    dados = await file.read()
    if not dados:
        raise HTTPException(status_code=400, detail="Arquivo de imagem vazio.")

    from io import BytesIO
    img = Image.open(BytesIO(dados)).convert("RGBA")
    destino = cenas_dir / nome_png
    img.save(destino, format="PNG")
    meta = ler_ou_criar_meta_projeto(pasta)
    if meta.get("tipo") == "short":
        img_limpa = remover_fundo_externo(destino)
        img_limpa.save(destino, format="PNG")

    cenas_geradas = sorted([f.name for f in cenas_dir.iterdir() if f.is_file() and f.suffix.lower() == ".png"])
    return {
        "ok": True,
        "arquivo": nome_png,
        "cenas_geradas": cenas_geradas,
    }


@app.put("/api/projetos/{nome}/imagens/reordenar")
def reordenar_imagens_cenas(nome: str, payload: ReordenarImagensPayload) -> dict[str, Any]:
    """Reordena os PNGs de midia/cenas/ e renomeia cada um para cena_XX.png conforme a nova posição."""
    pasta = _resolver_projeto(nome)
    cenas_dir = pasta / "midia" / "cenas"
    if not cenas_dir.is_dir():
        raise HTTPException(status_code=404, detail="Pasta midia/cenas não encontrada.")

    existentes = sorted([f.name for f in cenas_dir.iterdir() if f.is_file() and f.suffix.lower() == ".png"])
    ordem_limpa: list[str] = []
    vistos: set[str] = set()
    for item in payload.ordem:
        nome_png = Path(item.replace("\\", "/")).name
        if nome_png in existentes and nome_png not in vistos:
            ordem_limpa.append(nome_png)
            vistos.add(nome_png)
    # Mantém ao final quaisquer arquivos extras não listados
    for ext in existentes:
        if ext not in vistos:
            ordem_limpa.append(ext)

    if not ordem_limpa:
        return {"ok": True, "cenas_geradas": []}

    temps: list[tuple[Path, str]] = []
    for idx, nome_orig in enumerate(ordem_limpa, start=1):
        orig_path = cenas_dir / nome_orig
        tmp_path = cenas_dir / f"__reord_{idx:04d}_{nome_orig}"
        orig_path.rename(tmp_path)
        temps.append((tmp_path, f"cena_{idx:02d}.png"))

    for tmp_path, nome_final in temps:
        tmp_path.rename(cenas_dir / nome_final)

    cenas_geradas = sorted([f.name for f in cenas_dir.iterdir() if f.is_file() and f.suffix.lower() == ".png"])
    return {"ok": True, "cenas_geradas": cenas_geradas}


@app.delete("/api/projetos/{nome}/imagens/cena/{arquivo}")
def excluir_imagem_cena(
    nome: str,
    arquivo: str,
    remover_do_storyboard: bool = True,
) -> dict[str, Any]:
    """Exclui uma cena (PNG e opcionalmente entrada em cenas.json) e renumera as restantes em sequência."""
    pasta = _resolver_projeto(nome)
    cenas_dir = pasta / "midia" / "cenas"
    nome_png = Path(arquivo.replace("\\", "/")).name
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.png", nome_png):
        raise HTTPException(status_code=400, detail="Nome de arquivo PNG inválido.")

    alvo_path = cenas_dir / nome_png
    if alvo_path.exists():
        alvo_path.unlink()

    if cenas_dir.is_dir():
        restantes = sorted([f for f in cenas_dir.iterdir() if f.is_file() and f.suffix.lower() == ".png"])
        temps: list[tuple[Path, str]] = []
        for idx, arq in enumerate(restantes, start=1):
            tmp_path = cenas_dir / f"__del_{idx:04d}_{arq.name}"
            arq.rename(tmp_path)
            temps.append((tmp_path, f"cena_{idx:02d}.png"))
        for tmp_path, nome_final in temps:
            tmp_path.rename(cenas_dir / nome_final)

    cenas_path = pasta / "cenas.json"
    if remover_do_storyboard and cenas_path.exists():
        try:
            cenas_data = json.loads(cenas_path.read_text(encoding="utf-8"))
            lista = cenas_data.get("cenas") or []
            nova_lista = [
                c
                for c in lista
                if Path(str((c.get("fundo") or {}).get("arquivo") or c.get("arquivo") or "").replace("\\", "/")).name != nome_png
            ]
            for idx, c in enumerate(nova_lista, start=1):
                novo_rel = f"assets_atual/cenas/cena_{idx:02d}.png"
                c["arquivo"] = novo_rel
                if isinstance(c.get("fundo"), dict):
                    c["fundo"]["arquivo"] = novo_rel
            cenas_data["cenas"] = nova_lista
            cenas_path.write_text(json.dumps(cenas_data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    cenas_geradas = (
        sorted([f.name for f in cenas_dir.iterdir() if f.is_file() and f.suffix.lower() == ".png"])
        if cenas_dir.is_dir()
        else []
    )
    return {"ok": True, "cenas_geradas": cenas_geradas}


@app.post("/api/projetos/{nome}/imagens/reprocessar")
def reprocessar_imagens(nome: str) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    raw_dir = pasta / "midia" / "raw"
    cenas_dir = pasta / "midia" / "cenas"

    if not raw_dir.is_dir() or not any(f.is_file() for f in raw_dir.iterdir()):
        raise HTTPException(
            status_code=400,
            detail="Nenhuma imagem encontrada em midia/raw/ para reprocessar.",
        )

    cenas_dir.mkdir(parents=True, exist_ok=True)
    for antigo in cenas_dir.iterdir():
        if antigo.is_file():
            antigo.unlink()

    meta = ler_ou_criar_meta_projeto(pasta)
    args_limpeza = [str(raw_dir), str(cenas_dir)]
    if meta.get("tipo") == "longo":
        args_limpeza.append("--manter-fundo")

    resultado_script = _executar_script(
        "limpar_imagens.py",
        args_limpeza,
        timeout_sec=300,
    )
    cenas_geradas = sorted(
        [f.name for f in cenas_dir.iterdir() if f.is_file() and f.suffix.lower() == ".png"]
    )
    return {
        "ok": True,
        "cenas_geradas": cenas_geradas,
        "log": resultado_script["stdout"],
    }


@app.get("/api/comfyui/status")
def obter_status_comfyui() -> dict[str, Any]:
    return status_comfyui(ROOT_DIR)


@app.post("/api/comfyui/cancelar")
def cancelar_comfyui() -> dict[str, Any]:
    return comfy_cancelar_job(ROOT_DIR)


@app.post("/api/projetos/{nome}/comfyui/gerar")
def gerar_imagens_comfyui(nome: str, payload: ComfyGerarPayload) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    meta = ler_ou_criar_meta_projeto(pasta)
    formato = str(meta.get("formato") or ("9:16" if meta.get("tipo") == "short" else "16:9"))
    manter_fundo = meta.get("tipo") == "longo"
    try:
        return iniciar_geracao_comfyui(
            raiz=ROOT_DIR,
            pasta_projeto=pasta,
            formato=formato,
            manter_fundo=manter_fundo,
            apenas_faltantes=payload.apenas_faltantes,
            indice_cena=payload.indice_cena,
            checkpoint=payload.checkpoint,
            steps=payload.steps,
            cfg=payload.cfg,
            sampler_name=payload.sampler_name,
            scheduler=payload.scheduler,
            largura=payload.largura,
            altura=payload.altura,
            seed=payload.seed,
            negativo_extra=payload.negativo_extra,
            workflow_api=payload.workflow_api,
        )
    except ConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/projetos/{nome}/comfyui/status")
def status_geracao_comfyui(nome: str) -> dict[str, Any]:
    _resolver_projeto(nome)
    return comfy_status_job(nome)


@app.get("/api/projetos/{nome}/imagens")
def listar_imagens(nome: str) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    raw_dir = pasta / "midia" / "raw"
    cenas_dir = pasta / "midia" / "cenas"

    raw = (
        sorted([f.name for f in raw_dir.iterdir() if f.is_file()])
        if raw_dir.is_dir()
        else []
    )
    cenas = (
        sorted([f.name for f in cenas_dir.iterdir() if f.is_file() and f.suffix.lower() == ".png"])
        if cenas_dir.is_dir()
        else []
    )
    return {"raw": raw, "cenas": cenas}


@app.get("/api/projetos/{nome}/midia/cenas/{arquivo}")
def obter_imagem_cena(nome: str, arquivo: str) -> FileResponse:
    pasta = _resolver_projeto(nome)
    nome_seguro = Path(arquivo).name
    caminho = (pasta / "midia" / "cenas" / nome_seguro).resolve()
    cenas_dir = (pasta / "midia" / "cenas").resolve()
    if caminho.parent != cenas_dir or not caminho.is_file():
        raise HTTPException(status_code=404, detail="Imagem de cena não encontrada.")
    return FileResponse(caminho)


@app.post("/api/projetos/{nome}/preparar-render")
def preparar_render(nome: str, com_legenda: bool = True) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    cenas_path = pasta / "cenas.json"
    if not cenas_path.exists():
        raise HTTPException(
            status_code=400,
            detail="O arquivo cenas.json ainda não existe neste projeto. Salve o Storyboard antes de preparar o render.",
        )

    flag = "--com-legenda" if com_legenda else "--sem-legenda"
    resultado_script = _executar_script("preparar_render.py", [str(pasta), flag], timeout_sec=120)
    return {
        "ok": True,
        "projeto": pasta.name,
        "com_legenda": com_legenda,
        "template_dir": str(TEMPLATE_DIR),
        "log": resultado_script["stdout"],
    }


_RENDER_LOCK = threading.Lock()
_RENDER_ESTADO: dict[str, Any] = {
    "status": "idle",  # idle | running | done | error
    "projeto": None,
    "arquivo_saida": None,
    "qualidade": "looks",
    "com_legenda": True,
    "progresso": 0,
    "etapa": "",
    "log_linhas": [],
    "erro": None,
    "atualizado_em": 0.0,
}

_MAPA_CRF_REMOTION = {
    "draft": 26,
    "looks": 18,
    "delivery": 12,
}


def _atualizar_progresso_remotion(linha: str) -> None:
    low = linha.lower()
    if "bundling" in low:
        _RENDER_ESTADO["progresso"] = max(_RENDER_ESTADO.get("progresso", 0), 5)
        _RENDER_ESTADO["etapa"] = "Empacotando composição Remotion"
        return
    if "rendered" in low or "rendering frames" in low:
        m_frac = re.search(r"(\d+)\s*/\s*(\d+)", linha)
        if m_frac:
            done = int(m_frac.group(1))
            total = max(1, int(m_frac.group(2)))
            pct = 10 + int(round((done / total) * 75))
            _RENDER_ESTADO["progresso"] = max(_RENDER_ESTADO.get("progresso", 0), min(85, pct))
            _RENDER_ESTADO["etapa"] = f"Renderizando quadros ({done}/{total})"
            return
    if "encoding" in low or "stitching" in low or "encoded" in low:
        m_frac = re.search(r"(\d+)\s*/\s*(\d+)", linha)
        if m_frac:
            done = int(m_frac.group(1))
            total = max(1, int(m_frac.group(2)))
            pct = 85 + int(round((done / total) * 14))
            _RENDER_ESTADO["progresso"] = max(_RENDER_ESTADO.get("progresso", 0), min(99, pct))
            _RENDER_ESTADO["etapa"] = f"Codificando vídeo ({done}/{total})"
            return
        _RENDER_ESTADO["progresso"] = max(_RENDER_ESTADO.get("progresso", 0), 88)
        _RENDER_ESTADO["etapa"] = "Codificando vídeo final"
        return
    m_pct = re.search(r"(\d{1,3})%", linha)
    if m_pct:
        pct = max(0, min(99, int(m_pct.group(1))))
        _RENDER_ESTADO["progresso"] = max(_RENDER_ESTADO.get("progresso", 0), pct)


def _rodar_remotion_render(
    nome_projeto: str,
    arquivo_saida: Path,
    qualidade: str,
) -> None:
    npx_cmd = shutil.which("npx.cmd") or shutil.which("npx") or "npx"
    crf = _MAPA_CRF_REMOTION.get(qualidade, 18)
    cmd = [
        npx_cmd,
        "remotion",
        "render",
        "src/index.ts",
        "MainVideo",
        str(arquivo_saida),
        f"--crf={crf}",
        "--log=info",
    ]
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(TEMPLATE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        assert proc.stdout is not None
        for linha in proc.stdout:
            limpa = linha.strip()
            if not limpa:
                continue
            with _RENDER_LOCK:
                _atualizar_progresso_remotion(limpa)
                linhas = list(_RENDER_ESTADO.get("log_linhas") or [])
                linhas.append(limpa)
                _RENDER_ESTADO["log_linhas"] = linhas[-30:]
                _RENDER_ESTADO["atualizado_em"] = time.time()

        codigo = proc.wait()
        with _RENDER_LOCK:
            if codigo == 0 and arquivo_saida.is_file():
                _RENDER_ESTADO["status"] = "done"
                _RENDER_ESTADO["progresso"] = 100
                _RENDER_ESTADO["etapa"] = "Render concluído"
                _RENDER_ESTADO["erro"] = None
            else:
                ultimas = " | ".join((_RENDER_ESTADO.get("log_linhas") or [])[-3:])
                _RENDER_ESTADO["status"] = "error"
                _RENDER_ESTADO["erro"] = (
                    f"Remotion encerrou com código {codigo}. {ultimas}".strip()
                )
            _RENDER_ESTADO["atualizado_em"] = time.time()
    except Exception as exc:
        with _RENDER_LOCK:
            _RENDER_ESTADO["status"] = "error"
            _RENDER_ESTADO["erro"] = str(exc)
            _RENDER_ESTADO["atualizado_em"] = time.time()


@app.post("/api/projetos/{nome}/renderizar-video")
def renderizar_video(
    nome: str,
    com_legenda: bool = True,
    qualidade: Literal["draft", "looks", "delivery"] = "looks",
) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    cenas_path = pasta / "cenas.json"
    if not cenas_path.exists():
        raise HTTPException(
            status_code=400,
            detail="O arquivo cenas.json ainda não existe neste projeto. Salve o Storyboard antes de renderizar.",
        )

    with _RENDER_LOCK:
        if _RENDER_ESTADO["status"] == "running":
            raise HTTPException(
                status_code=409,
                detail=f"Já existe uma renderização em andamento para '{_RENDER_ESTADO['projeto']}'. Aguarde concluir.",
            )

    flag = "--com-legenda" if com_legenda else "--sem-legenda"
    _executar_script("preparar_render.py", [str(pasta), flag], timeout_sec=120)

    midia_dir = pasta / "midia"
    midia_dir.mkdir(parents=True, exist_ok=True)
    arquivo_saida = midia_dir / "video_final.mp4"

    with _RENDER_LOCK:
        _RENDER_ESTADO.update(
            {
                "status": "running",
                "projeto": pasta.name,
                "arquivo_saida": str(arquivo_saida),
                "qualidade": qualidade,
                "com_legenda": com_legenda,
                "progresso": 2,
                "etapa": "Preparando assets e iniciando Remotion...",
                "log_linhas": [f"Iniciando Remotion ({qualidade})..."],
                "erro": None,
                "atualizado_em": time.time(),
            }
        )

    t = threading.Thread(
        target=_rodar_remotion_render,
        args=(pasta.name, arquivo_saida, qualidade),
        daemon=True,
    )
    t.start()

    return {
        "ok": True,
        "status": "running",
        "projeto": pasta.name,
        "arquivo_saida": str(arquivo_saida),
    }


@app.get("/api/projetos/{nome}/renderizar-status")
def status_render_video(nome: str) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    video_path = pasta / "midia" / "video_final.mp4"
    existe_video = video_path.is_file()
    tamanho_bytes = video_path.stat().st_size if existe_video else None

    with _RENDER_LOCK:
        mesmo_projeto = _RENDER_ESTADO.get("projeto") == pasta.name
        status = _RENDER_ESTADO["status"] if mesmo_projeto else "idle"
        outro_rodando = (
            _RENDER_ESTADO.get("projeto")
            if not mesmo_projeto and _RENDER_ESTADO["status"] == "running"
            else None
        )
        log_linhas = list(_RENDER_ESTADO.get("log_linhas") or []) if mesmo_projeto else []
        progresso = int(_RENDER_ESTADO.get("progresso") or 0) if mesmo_projeto else 0
        etapa = str(_RENDER_ESTADO.get("etapa") or "") if mesmo_projeto else ""
        erro = _RENDER_ESTADO.get("erro") if mesmo_projeto else None

    return {
        "status": status,
        "projeto": pasta.name,
        "outro_projeto_renderizando": outro_rodando,
        "progresso": progresso,
        "etapa": etapa,
        "existe_video": existe_video,
        "tamanho_bytes": tamanho_bytes,
        "caminho_video": str(video_path),
        "log_linhas": log_linhas,
        "ultima_linha": log_linhas[-1] if log_linhas else None,
        "erro": erro,
    }


@app.get("/api/projetos/{nome}/video")
def obter_video_final(nome: str) -> FileResponse:
    pasta = _resolver_projeto(nome)
    video_path = pasta / "midia" / "video_final.mp4"
    if not video_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="O vídeo final ainda não foi renderizado para este projeto.",
        )
    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"{pasta.name}.mp4",
    )
