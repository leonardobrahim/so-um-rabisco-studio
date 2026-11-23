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

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.pipeline import (
    gerar_cenas_de_prompts_salvos,
    gerar_storyboard_automatico,
    inferir_tipo_projeto,
    ler_ou_criar_meta_projeto,
    montar_pacote_chat,
    salvar_meta_projeto,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
PROJETOS_DIR = ROOT_DIR / "projetos"
SCRIPTS_DIR = ROOT_DIR / "scripts"
TEMPLATE_DIR = ROOT_DIR / "template-hyperframes"

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
    arquivo = pasta / "04-storyboard-e-prompts.md"
    if not arquivo.exists():
        raise HTTPException(
            status_code=404,
            detail="Arquivo 04-storyboard-e-prompts.md não encontrado neste projeto.",
        )
    conteudo = arquivo.read_text(encoding="utf-8")
    qtd_prompts = _sincronizar_prompts_imagens(conteudo)
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


@app.post("/api/projetos/{nome}/gerar-storyboard")
def gerar_storyboard_endpoint(nome: str, tipo: str | None = None) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    try:
        resultado = gerar_storyboard_automatico(pasta, tipo_forcado=tipo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return resultado


@app.post("/api/projetos/{nome}/gerar-cenas-prompts")
def gerar_cenas_prompts_endpoint(nome: str, tipo: str | None = None) -> dict[str, Any]:
    pasta = _resolver_projeto(nome)
    try:
        return gerar_cenas_de_prompts_salvos(pasta, tipo_forcado=tipo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    if gerar_storyboard and timestamps is not None:
        try:
            res_sb = gerar_storyboard_automatico(pasta)
            storyboard_info = {
                "qtd_cenas": res_sb["qtd_cenas"],
                "formato": res_sb["formato"],
                "origem": res_sb["origem"],
            }
        except Exception:
            storyboard_info = None

    return {
        "ok": True,
        "arquivo_salvo": "midia/audio.wav",
        "tamanho_bytes": len(conteudo),
        "log": resultado_script["stdout"],
        "timestamps": timestamps,
        "storyboard_gerado": storyboard_info,
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

    base_ts = time.time()
    salvos: list[str] = []

    for idx, arquivo in enumerate(arquivos_validos, start=1):
        nome_seguro = Path(arquivo.filename or f"imagem_{idx:02d}.png").name
        destino = raw_dir / f"{idx:03d}_{nome_seguro}"
        dados = await arquivo.read()
        destino.write_bytes(dados)
        # Garante ordem determinística por mtime conforme esperado pelo limpar_imagens.py
        ts = base_ts + idx * 0.01
        os.utime(destino, (ts, ts))
        salvos.append(destino.name)

    meta = ler_ou_criar_meta_projeto(pasta)
    args_limpeza = [str(raw_dir), str(cenas_dir)]
    if meta.get("tipo") == "longo":
        args_limpeza.append("--manter-fundo")

    resultado_script = _executar_script(
        "limpar_imagens.py",
        args_limpeza,
        timeout_sec=300,
    )

    cenas_geradas = sorted([f.name for f in cenas_dir.iterdir() if f.is_file() and f.suffix.lower() == ".png"])

    return {
        "ok": True,
        "enviados": salvos,
        "cenas_geradas": cenas_geradas,
        "log": resultado_script["stdout"],
    }


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
    "log_linhas": [],
    "erro": None,
    "atualizado_em": 0.0,
}


def _rodar_hyperframes_render(
    nome_projeto: str,
    arquivo_saida: Path,
    qualidade: str,
) -> None:
    npx_cmd = shutil.which("npx.cmd") or shutil.which("npx") or "npx"
    cmd = [
        npx_cmd,
        "hyperframes",
        "render",
        ".",
        "-o",
        str(arquivo_saida),
        "-q",
        qualidade,
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
                linhas = list(_RENDER_ESTADO.get("log_linhas") or [])
                linhas.append(limpa)
                _RENDER_ESTADO["log_linhas"] = linhas[-30:]
                _RENDER_ESTADO["atualizado_em"] = time.time()

        codigo = proc.wait()
        with _RENDER_LOCK:
            if codigo == 0 and arquivo_saida.is_file():
                _RENDER_ESTADO["status"] = "done"
                _RENDER_ESTADO["erro"] = None
            else:
                ultimas = " | ".join((_RENDER_ESTADO.get("log_linhas") or [])[-3:])
                _RENDER_ESTADO["status"] = "error"
                _RENDER_ESTADO["erro"] = (
                    f"HyperFrames encerrou com código {codigo}. {ultimas}".strip()
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
                "log_linhas": [f"Iniciando HyperFrames ({qualidade})..."],
                "erro": None,
                "atualizado_em": time.time(),
            }
        )

    t = threading.Thread(
        target=_rodar_hyperframes_render,
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
        erro = _RENDER_ESTADO.get("erro") if mesmo_projeto else None

    return {
        "status": status,
        "projeto": pasta.name,
        "outro_projeto_renderizando": outro_rodando,
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
