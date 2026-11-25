"""Cliente oficial Google Gemini (`google-genai`) com Structured Outputs (Pydantic)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, TypeVar

from google import genai
from google.genai import errors, types
from pydantic import BaseModel

ROOT_DIR = Path(__file__).resolve().parent.parent
GEMINI_MODEL_PADRAO = "gemini-2.5-flash"
GEMINI_FALLBACK_MODELOS = (
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
    "gemini-3.5-flash-lite",
)

T = TypeVar("T", bound=BaseModel)


class GeminiConfigError(RuntimeError):
    """Erro quando a chave GEMINI_API_KEY não está configurada ou é inválida."""


class GeminiGenerationError(RuntimeError):
    """Erro na chamada ou validação de resposta estruturada do Gemini."""


def ler_env_valor(raiz: Path, chave: str) -> str:
    """Lê uma variável do ambiente ou do arquivo .env na raiz do projeto."""
    val = (os.environ.get(chave) or "").strip()
    if val:
        return val
    env_path = raiz / ".env"
    if not env_path.exists():
        return ""
    for linha in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        texto = linha.strip()
        if not texto or texto.startswith("#") or "=" not in texto:
            continue
        k, v = texto.split("=", 1)
        if k.strip() == chave:
            return v.strip().strip('"').strip("'")
    return ""


def status_gemini(raiz: Path | None = None) -> dict[str, Any]:
    """Retorna o status da configuração da API do Gemini sem expor a chave."""
    base = raiz or ROOT_DIR
    chave = ler_env_valor(base, "GEMINI_API_KEY")
    modelo = ler_env_valor(base, "GEMINI_MODEL") or GEMINI_MODEL_PADRAO
    configurado = bool(chave)
    mensagem = (
        None
        if configurado
        else "GEMINI_API_KEY não configurada no arquivo .env. Configure a chave para gerar roteiros, storyboards e SEO com IA."
    )
    return {
        "configurado": configurado,
        "modelo_padrao": modelo,
        "modelos_fallback": list(GEMINI_FALLBACK_MODELOS),
        "mensagem": mensagem,
    }


def _modelos_candidatos(raiz: Path) -> list[str]:
    modelo_cfg = ler_env_valor(raiz, "GEMINI_MODEL") or GEMINI_MODEL_PADRAO
    candidatos = [modelo_cfg]
    for alt in GEMINI_FALLBACK_MODELOS:
        if alt not in candidatos:
            candidatos.append(alt)
    return candidatos


def _eh_erro_modelo_indisponivel(exc: errors.APIError) -> bool:
    code = getattr(exc, "code", None)
    if code in (404, 429, 503):
        return True
    status = str(getattr(exc, "status", "") or "").upper()
    return status in ("NOT_FOUND", "RESOURCE_EXHAUSTED", "UNAVAILABLE")


def gerar_estruturado(
    raiz: Path,
    prompt: str,
    schema_cls: type[T],
    *,
    system_instruction: str | None = None,
    temperature: float = 0.6,
) -> tuple[T, str]:
    """Executa generate_content com response_schema Pydantic e retorna (objeto, modelo_usado)."""
    api_key = ler_env_valor(raiz, "GEMINI_API_KEY")
    if not api_key:
        raise GeminiConfigError(
            "GEMINI_API_KEY não configurada no arquivo .env. "
            "Adicione sua chave da API do Gemini no .env na raiz do projeto (veja .env.example)."
        )

    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
        response_mime_type="application/json",
        response_schema=schema_cls,
    )

    ultimo_erro: Exception | None = None
    for modelo in _modelos_candidatos(raiz):
        try:
            resp = client.models.generate_content(
                model=modelo,
                contents=prompt,
                config=config,
            )
            if isinstance(resp.parsed, schema_cls):
                return resp.parsed, modelo
            if resp.parsed is not None:
                return schema_cls.model_validate(resp.parsed), modelo
            if resp.text:
                return schema_cls.model_validate_json(resp.text), modelo
            ultimo_erro = GeminiGenerationError(
                f"Gemini ({modelo}) retornou resposta vazia para {schema_cls.__name__}."
            )
        except errors.APIError as exc:
            code = getattr(exc, "code", None)
            if code in (400, 401, 403):
                msg_low = str(exc).lower()
                if "api_key" in msg_low or "api key" in msg_low or code in (401, 403):
                    raise GeminiConfigError(f"Chave GEMINI_API_KEY inválida ou sem permissão ({code}): {exc}") from exc
            if _eh_erro_modelo_indisponivel(exc):
                ultimo_erro = exc
                continue
            raise GeminiGenerationError(f"Erro da API Gemini ({modelo}): {exc}") from exc
        except Exception as exc:
            ultimo_erro = exc
            raise GeminiGenerationError(
                f"Falha ao validar saída estruturada do Gemini ({modelo}): {exc}"
            ) from exc

    raise GeminiGenerationError(
        f"Nenhum modelo Gemini disponível respondeu com sucesso (último erro: {ultimo_erro})."
    )
