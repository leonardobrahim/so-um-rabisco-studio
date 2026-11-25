"""Integração direta com o ComfyUI local (API HTTP /prompt, /history, /view, /interrupt).

Envia prompts de fundo do cenas.json em fila, baixa os PNGs para midia/raw/
e processa cada cena diretamente para midia/cenas/ reaproveitando scripts/limpar_imagens.py.
"""
from __future__ import annotations

import copy
import json
import os
import random
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

from backend.pipeline import _ler_env_valor, limpar_prefixo_timestamp
from scripts.limpar_imagens import remover_fundo_externo

COMFYUI_URL_PADRAO = "http://127.0.0.1:8188"
NEGATIVO_FUNDO_PADRAO = (
    "person, people, human, character, boy, girl, man, woman, face, hands, fingers, "
    "silhouette, crowd, 3d, realistic, photorealistic, blurry, watermark, signature, text"
)


def obter_comfyui_url(raiz: Path) -> str:
    url = _ler_env_valor(raiz, "COMFYUI_URL") or COMFYUI_URL_PADRAO
    return url.rstrip("/")


def _http_json(url: str, data: dict[str, Any] | None = None, timeout: float = 5.0) -> dict[str, Any]:
    body = json.dumps(data).encode("utf-8") if data is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(url, data=body, headers=headers, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        texto = resp.read().decode("utf-8", errors="replace")
        return json.loads(texto) if texto.strip() else {}


def _http_bytes(url: str, timeout: float = 30.0) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read()


def preset_por_checkpoint(checkpoint: str, formato: str) -> dict[str, Any]:
    low = (checkpoint or "").lower()
    eh_horizontal = formato != "9:16"
    if "lightning" in low:
        return {
            "steps": 5,
            "cfg": 2.0,
            "sampler_name": "dpmpp_sde",
            "scheduler": "karras",
            "largura": 1024 if eh_horizontal else 576,
            "altura": 576 if eh_horizontal else 1024,
        }
    if "xl" in low:
        return {
            "steps": 20,
            "cfg": 6.5,
            "sampler_name": "dpmpp_2m",
            "scheduler": "karras",
            "largura": 1024 if eh_horizontal else 576,
            "altura": 576 if eh_horizontal else 1024,
        }
    return {
        "steps": 22,
        "cfg": 7.0,
        "sampler_name": "dpmpp_2m",
        "scheduler": "karras",
        "largura": 912 if eh_horizontal else 512,
        "altura": 512 if eh_horizontal else 912,
    }


def status_comfyui(raiz: Path) -> dict[str, Any]:
    url = obter_comfyui_url(raiz)
    try:
        stats = _http_json(f"{url}/system_stats", timeout=2.5)
    except Exception as exc:
        return {
            "online": False,
            "url": url,
            "dispositivo": None,
            "vram_total_mb": None,
            "vram_free_mb": None,
            "checkpoints": [],
            "checkpoint_padrao": None,
            "erro": f"ComfyUI não respondeu em {url} ({exc})",
        }

    devices = stats.get("devices") or []
    dev0 = devices[0] if devices else {}
    vram_total = dev0.get("vram_total")
    vram_free = dev0.get("vram_free")

    checkpoints: list[str] = []
    try:
        obj = _http_json(f"{url}/object_info/CheckpointLoaderSimple", timeout=3.0)
        checkpoints = list(
            obj.get("CheckpointLoaderSimple", {})
            .get("input", {})
            .get("required", {})
            .get("ckpt_name", [[]])[0]
        )
    except Exception:
        checkpoints = []

    padrao = None
    for ckpt in checkpoints:
        if "lightning" in ckpt.lower():
            padrao = ckpt
            break
    if padrao is None and checkpoints:
        padrao = checkpoints[0]

    return {
        "online": True,
        "url": url,
        "dispositivo": dev0.get("name"),
        "vram_total_mb": round(vram_total / (1024 * 1024)) if vram_total else None,
        "vram_free_mb": round(vram_free / (1024 * 1024)) if vram_free else None,
        "checkpoints": checkpoints,
        "checkpoint_padrao": padrao,
        "erro": None,
    }


def montar_workflow_api(
    prompt_positivo: str,
    prompt_negativo: str,
    checkpoint: str,
    largura: int,
    altura: int,
    steps: int,
    cfg: float,
    sampler_name: str,
    scheduler: str,
    seed: int,
    filename_prefix: str = "rabisco_fundo",
    workflow_base: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Monta um workflow API Format padrão ou injeta os parâmetros num workflow API customizado."""
    if workflow_base:
        wf = copy.deepcopy(workflow_base)
        ksampler_node = None
        for node in wf.values():
            if not isinstance(node, dict):
                continue
            ctype = node.get("class_type", "")
            inputs = node.setdefault("inputs", {})
            if ctype == "CheckpointLoaderSimple" and checkpoint:
                inputs["ckpt_name"] = checkpoint
            elif ctype in ("EmptyLatentImage", "EmptySD3LatentImage"):
                inputs["width"] = int(largura)
                inputs["height"] = int(altura)
            elif ctype in ("KSampler", "KSamplerAdvanced"):
                ksampler_node = inputs
                inputs["seed"] = int(seed)
                inputs["steps"] = int(steps)
                inputs["cfg"] = float(cfg)
                inputs["sampler_name"] = sampler_name
                inputs["scheduler"] = scheduler
            elif ctype == "SaveImage":
                inputs["filename_prefix"] = filename_prefix

        # Liga positivo/negativo pelos ids referenciados no KSampler quando houver
        pos_id = None
        neg_id = None
        if ksampler_node:
            if isinstance(ksampler_node.get("positive"), list) and ksampler_node["positive"]:
                pos_id = str(ksampler_node["positive"][0])
            if isinstance(ksampler_node.get("negative"), list) and ksampler_node["negative"]:
                neg_id = str(ksampler_node["negative"][0])

        if pos_id and pos_id in wf and isinstance(wf[pos_id], dict):
            wf[pos_id].setdefault("inputs", {})["text"] = prompt_positivo
        if neg_id and neg_id in wf and isinstance(wf[neg_id], dict):
            wf[neg_id].setdefault("inputs", {})["text"] = prompt_negativo
        if not pos_id:
            clip_nodes = [n for n in wf.values() if isinstance(n, dict) and n.get("class_type") == "CLIPTextEncode"]
            if clip_nodes:
                clip_nodes[0].setdefault("inputs", {})["text"] = prompt_positivo
            if len(clip_nodes) > 1:
                clip_nodes[1].setdefault("inputs", {})["text"] = prompt_negativo
        return wf

    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": int(seed),
                "steps": int(steps),
                "cfg": float(cfg),
                "sampler_name": sampler_name,
                "scheduler": scheduler,
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": int(largura), "height": int(altura), "batch_size": 1},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt_positivo, "clip": ["4", 1]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt_negativo, "clip": ["4", 1]},
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": filename_prefix, "images": ["8", 0]},
        },
    }


def limpar_e_salvar_imagem_cena(
    caminho_raw: Path,
    caminho_destino: Path,
    manter_fundo: bool,
) -> None:
    caminho_destino.parent.mkdir(parents=True, exist_ok=True)
    if manter_fundo:
        with Image.open(caminho_raw) as img_raw:
            img_corrigida = ImageOps.exif_transpose(img_raw)
            if img_corrigida.mode not in ("RGB", "RGBA"):
                img_corrigida = img_corrigida.convert("RGB")
            img_corrigida.save(caminho_destino, "PNG")
    else:
        img_limpa = remover_fundo_externo(caminho_raw)
        img_limpa.save(caminho_destino, "PNG")


def _extrair_erro_history(status_obj: dict[str, Any]) -> str:
    for msg in status_obj.get("messages") or []:
        if isinstance(msg, list) and len(msg) >= 2 and msg[0] == "execution_error":
            detalhe = msg[1] if isinstance(msg[1], dict) else {}
            ex_msg = detalhe.get("exception_message") or ""
            node_type = detalhe.get("node_type") or ""
            return f"{node_type}: {ex_msg}".strip(": ") or "Erro de execução no ComfyUI"
    return "Execução falhou no ComfyUI."


def _executar_prompt_unico(
    url: str,
    workflow: dict[str, Any],
    cancel_event: threading.Event,
    timeout_sec: int = 300,
) -> tuple[bytes, str]:
    client_id = str(uuid.uuid4())
    try:
        res = _http_json(f"{url}/prompt", data={"prompt": workflow, "client_id": client_id}, timeout=15.0)
    except urllib.error.HTTPError as exc:
        detalhe = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"ComfyUI recusou o workflow (HTTP {exc.code}): {detalhe}") from exc

    prompt_id = res.get("prompt_id")
    if not prompt_id:
        raise RuntimeError(f"Resposta inesperada do ComfyUI: {res}")

    inicio = time.time()
    while time.time() - inicio < timeout_sec:
        if cancel_event.is_set():
            try:
                _http_json(f"{url}/interrupt", data={}, timeout=3.0)
            except Exception:
                pass
            raise InterruptedError("Geração cancelada pelo usuário.")

        try:
            hist = _http_json(f"{url}/history/{urllib.parse.quote(str(prompt_id))}", timeout=5.0)
        except Exception:
            time.sleep(1.0)
            continue

        item = hist.get(prompt_id)
        if item:
            status_obj = item.get("status") or {}
            if status_obj.get("status_str") == "error":
                raise RuntimeError(_extrair_erro_history(status_obj))

            outputs = item.get("outputs") or {}
            for node_out in outputs.values():
                imagens = node_out.get("images") or []
                if imagens:
                    img_info = imagens[0]
                    qs = urllib.parse.urlencode(
                        {
                            "filename": img_info["filename"],
                            "subfolder": img_info.get("subfolder", ""),
                            "type": img_info.get("type", "output"),
                        }
                    )
                    dados = _http_bytes(f"{url}/view?{qs}", timeout=30.0)
                    return dados, str(img_info["filename"])

            if status_obj.get("completed"):
                raise RuntimeError("ComfyUI concluiu a execução, mas nenhuma imagem foi gerada (verifique o nó SaveImage).")

        time.sleep(0.9)

    raise TimeoutError(f"Tempo limite ({timeout_sec}s) aguardando o ComfyUI concluir a cena.")


_COMFY_LOCK = threading.Lock()
_COMFY_CANCEL = threading.Event()
_COMFY_ESTADO: dict[str, Any] = {
    "status": "idle",  # idle | running | done | error | canceled
    "projeto": None,
    "checkpoint": None,
    "total_cenas": 0,
    "concluidas": 0,
    "cena_indice_atual": None,
    "ultima_cena_salva": None,
    "logs": [],
    "erro": None,
    "atualizado_em": 0.0,
}


def _registrar_log(msg: str) -> None:
    with _COMFY_LOCK:
        logs = list(_COMFY_ESTADO.get("logs") or [])
        logs.append(msg)
        _COMFY_ESTADO["logs"] = logs[-30:]
        _COMFY_ESTADO["atualizado_em"] = time.time()


def obter_status_job(nome_projeto: str) -> dict[str, Any]:
    with _COMFY_LOCK:
        mesmo = _COMFY_ESTADO.get("projeto") == nome_projeto
        outro = (
            _COMFY_ESTADO.get("projeto")
            if not mesmo and _COMFY_ESTADO.get("status") == "running"
            else None
        )
        return {
            "status": _COMFY_ESTADO["status"] if mesmo else "idle",
            "projeto": nome_projeto,
            "outro_projeto_gerando": outro,
            "checkpoint": _COMFY_ESTADO.get("checkpoint") if mesmo else None,
            "total_cenas": _COMFY_ESTADO.get("total_cenas", 0) if mesmo else 0,
            "concluidas": _COMFY_ESTADO.get("concluidas", 0) if mesmo else 0,
            "cena_indice_atual": _COMFY_ESTADO.get("cena_indice_atual") if mesmo else None,
            "ultima_cena_salva": _COMFY_ESTADO.get("ultima_cena_salva") if mesmo else None,
            "logs": list(_COMFY_ESTADO.get("logs") or []) if mesmo else [],
            "erro": _COMFY_ESTADO.get("erro") if mesmo else None,
        }


def cancelar_job(raiz: Path) -> dict[str, Any]:
    _COMFY_CANCEL.set()
    url = obter_comfyui_url(raiz)
    try:
        _http_json(f"{url}/interrupt", data={}, timeout=3.0)
    except Exception:
        pass
    return {"ok": True}


def _rodar_lote_comfyui(
    raiz: Path,
    pasta_projeto: Path,
    url: str,
    alvos: list[dict[str, Any]],
    manter_fundo: bool,
    params: dict[str, Any],
    workflow_base: dict[str, Any] | None,
) -> None:
    raw_dir = pasta_projeto / "midia" / "raw"
    cenas_dir = pasta_projeto / "midia" / "cenas"
    raw_dir.mkdir(parents=True, exist_ok=True)
    cenas_dir.mkdir(parents=True, exist_ok=True)

    negativo = NEGATIVO_FUNDO_PADRAO
    if params.get("negativo_extra"):
        negativo = f"{negativo}, {str(params['negativo_extra']).strip()}"

    base_seed = params.get("seed")
    try:
        for pos, item in enumerate(alvos):
            if _COMFY_CANCEL.is_set():
                raise InterruptedError("Geração cancelada pelo usuário.")

            idx_cena = int(item["indice"])
            nome_png = str(item["nome_png"])
            prompt_txt = str(item["prompt"])
            seed = (
                int(base_seed) + (idx_cena - 1)
                if base_seed is not None and int(base_seed) >= 0
                else random.randint(1, 2**31 - 1)
            )

            with _COMFY_LOCK:
                _COMFY_ESTADO["cena_indice_atual"] = idx_cena
                _COMFY_ESTADO["atualizado_em"] = time.time()

            _registrar_log(f"Cena {idx_cena:02d}/{len(alvos)}: enviando para ComfyUI...")
            wf = montar_workflow_api(
                prompt_positivo=prompt_txt,
                prompt_negativo=negativo,
                checkpoint=params["checkpoint"],
                largura=params["largura"],
                altura=params["altura"],
                steps=params["steps"],
                cfg=params["cfg"],
                sampler_name=params["sampler_name"],
                scheduler=params["scheduler"],
                seed=seed,
                filename_prefix=f"rabisco_{pasta_projeto.name[:24]}_c{idx_cena:02d}",
                workflow_base=workflow_base,
            )

            img_bytes, nome_comfy = _executar_prompt_unico(url, wf, _COMFY_CANCEL)

            # Remove eventual raw antigo desse mesmo índice antes de gravar o novo
            prefixo_raw = f"{idx_cena:03d}_"
            for antigo in raw_dir.iterdir():
                if antigo.is_file() and antigo.name.startswith(prefixo_raw):
                    antigo.unlink()

            raw_path = raw_dir / f"{idx_cena:03d}_comfy_{nome_png}"
            raw_path.write_bytes(img_bytes)
            ts = time.time() + idx_cena * 0.01
            os.utime(raw_path, (ts, ts))

            destino_cena = cenas_dir / nome_png
            limpar_e_salvar_imagem_cena(raw_path, destino_cena, manter_fundo=manter_fundo)

            with _COMFY_LOCK:
                _COMFY_ESTADO["concluidas"] = pos + 1
                _COMFY_ESTADO["ultima_cena_salva"] = nome_png
                _COMFY_ESTADO["atualizado_em"] = time.time()
            _registrar_log(f"Cena {idx_cena:02d} salva -> {nome_png} ({nome_comfy})")

        with _COMFY_LOCK:
            _COMFY_ESTADO["status"] = "done"
            _COMFY_ESTADO["cena_indice_atual"] = None
            _COMFY_ESTADO["erro"] = None
            _COMFY_ESTADO["atualizado_em"] = time.time()
    except InterruptedError as exc:
        with _COMFY_LOCK:
            _COMFY_ESTADO["status"] = "canceled"
            _COMFY_ESTADO["erro"] = str(exc)
            _COMFY_ESTADO["atualizado_em"] = time.time()
    except Exception as exc:
        _registrar_log(f"ERRO: {exc}")
        with _COMFY_LOCK:
            _COMFY_ESTADO["status"] = "error"
            _COMFY_ESTADO["erro"] = str(exc)
            _COMFY_ESTADO["atualizado_em"] = time.time()


def iniciar_geracao_comfyui(
    raiz: Path,
    pasta_projeto: Path,
    formato: str,
    manter_fundo: bool,
    apenas_faltantes: bool = False,
    indice_cena: int | None = None,
    checkpoint: str | None = None,
    steps: int | None = None,
    cfg: float | None = None,
    sampler_name: str | None = None,
    scheduler: str | None = None,
    largura: int | None = None,
    altura: int | None = None,
    seed: int | None = None,
    negativo_extra: str | None = None,
    workflow_api: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cenas_path = pasta_projeto / "cenas.json"
    if not cenas_path.exists():
        raise ValueError("O arquivo cenas.json ainda não existe neste projeto. Gere o Storyboard antes.")

    cenas_data = json.loads(cenas_path.read_text(encoding="utf-8"))
    cenas = cenas_data.get("cenas") or []
    if not cenas:
        raise ValueError("Não há cenas em cenas.json para gerar.")

    st = status_comfyui(raiz)
    if not st["online"]:
        raise ConnectionError(st["erro"] or "ComfyUI offline.")

    ckpt = checkpoint or st["checkpoint_padrao"]
    if not ckpt:
        raise ValueError("Nenhum checkpoint encontrado no ComfyUI (models/checkpoints).")

    preset = preset_por_checkpoint(ckpt, formato)
    params = {
        "checkpoint": ckpt,
        "steps": int(steps) if steps is not None else preset["steps"],
        "cfg": float(cfg) if cfg is not None else preset["cfg"],
        "sampler_name": sampler_name or preset["sampler_name"],
        "scheduler": scheduler or preset["scheduler"],
        "largura": int(largura) if largura is not None else preset["largura"],
        "altura": int(altura) if altura is not None else preset["altura"],
        "seed": seed,
        "negativo_extra": negativo_extra,
    }

    cenas_dir = pasta_projeto / "midia" / "cenas"
    alvos: list[dict[str, Any]] = []
    sem_prompt: list[int] = []

    for idx, cena in enumerate(cenas, start=1):
        if indice_cena is not None and idx != indice_cena:
            continue
        arquivo_cena = str((cena.get("fundo") or {}).get("arquivo") or cena.get("arquivo") or f"cena_{idx:02d}.png")
        nome_png = Path(arquivo_cena.replace("\\", "/")).name or f"cena_{idx:02d}.png"
        if apenas_faltantes and indice_cena is None and (cenas_dir / nome_png).is_file():
            continue

        prompt_raw = str((cena.get("fundo") or {}).get("prompt") or cena.get("prompt") or "").strip()
        prompt_limpo = limpar_prefixo_timestamp(prompt_raw)
        if not prompt_limpo:
            sem_prompt.append(idx)
            continue
        alvos.append({"indice": idx, "nome_png": nome_png, "prompt": prompt_limpo})

    if indice_cena is not None and not alvos and not sem_prompt:
        raise ValueError(f"Cena {indice_cena} não encontrada em cenas.json.")
    if sem_prompt and not alvos:
        raise ValueError(
            f"Cena(s) {sem_prompt} não possuem prompt salvo em cenas.json. Gere o Storyboard primeiro."
        )
    if not alvos:
        return {
            "ok": True,
            "status": "done",
            "total_cenas": 0,
            "checkpoint": ckpt,
            "mensagem": "Todas as cenas já possuem PNG em midia/cenas/.",
        }

    with _COMFY_LOCK:
        if _COMFY_ESTADO["status"] == "running":
            raise RuntimeError(
                f"Já existe uma geração ComfyUI em andamento para '{_COMFY_ESTADO['projeto']}'."
            )
        _COMFY_CANCEL.clear()
        _COMFY_ESTADO.update(
            {
                "status": "running",
                "projeto": pasta_projeto.name,
                "checkpoint": ckpt,
                "total_cenas": len(alvos),
                "concluidas": 0,
                "cena_indice_atual": alvos[0]["indice"],
                "ultima_cena_salva": None,
                "logs": [
                    f"Iniciando {len(alvos)} cena(s) no ComfyUI ({ckpt}, {params['largura']}x{params['altura']}, {params['steps']} steps)..."
                ],
                "erro": None,
                "atualizado_em": time.time(),
            }
        )

    t = threading.Thread(
        target=_rodar_lote_comfyui,
        args=(raiz, pasta_projeto, st["url"], alvos, manter_fundo, params, workflow_api),
        daemon=True,
    )
    t.start()

    return {
        "ok": True,
        "status": "running",
        "total_cenas": len(alvos),
        "checkpoint": ckpt,
        "params": params,
    }
