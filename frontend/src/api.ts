import type { CenasConfig, ProjetoResumo, TimestampsData } from "./types";

export const API_BASE =
  import.meta.env.VITE_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    let message = `Erro HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) {
        message = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      // ignora parse de erro não-JSON
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listarProjetos: () => request<{ projetos: ProjetoResumo[] }>("/api/projetos"),

  criarProjeto: (nome: string) =>
    request<{ projeto: ProjetoResumo }>("/api/projetos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nome }),
    }),

  lerNarracao: (nome: string) =>
    request<{ nome: string; conteudo: string; existe: boolean }>(
      `/api/projetos/${encodeURIComponent(nome)}/narracao`
    ),

  salvarNarracao: (nome: string, conteudo: string) =>
    request<{ ok: boolean; arquivo: string; caracteres: number; palavras: number }>(
      `/api/projetos/${encodeURIComponent(nome)}/narracao`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conteudo }),
      }
    ),

  lerStoryboard: (nome: string) =>
    request<{ nome: string; conteudo: string; existe: boolean }>(
      `/api/projetos/${encodeURIComponent(nome)}/storyboard`
    ),

  salvarStoryboard: (nome: string, conteudo: string) =>
    request<{ ok: boolean; arquivo: string; prompts_atualizados: number }>(
      `/api/projetos/${encodeURIComponent(nome)}/storyboard`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conteudo }),
      }
    ),

  exportarPrompts: (nome: string) =>
    request<{ ok: boolean; arquivo_destino: string; qtd_prompts: number }>(
      `/api/projetos/${encodeURIComponent(nome)}/exportar-prompts`,
      { method: "POST" }
    ),

  lerTimestamps: (nome: string) =>
    request<{ existe: boolean; dados: TimestampsData | null }>(
      `/api/projetos/${encodeURIComponent(nome)}/timestamps`
    ),

  lerCenas: (nome: string) =>
    request<{ existe: boolean; dados: CenasConfig }>(
      `/api/projetos/${encodeURIComponent(nome)}/cenas`
    ),

  salvarCenas: (nome: string, dados: CenasConfig) =>
    request<{ ok: boolean; arquivo: string; qtd_cenas: number }>(
      `/api/projetos/${encodeURIComponent(nome)}/cenas`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dados }),
      }
    ),

  uploadAudio: (nome: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<{
      ok: boolean;
      arquivo_salvo: string;
      tamanho_bytes: number;
      log: string;
      timestamps: TimestampsData | null;
    }>(`/api/projetos/${encodeURIComponent(nome)}/audio`, {
      method: "POST",
      body: form,
    });
  },

  audioUrl: (nome: string, cacheBust?: number) =>
    `${API_BASE}/api/projetos/${encodeURIComponent(nome)}/audio${
      cacheBust ? `?t=${cacheBust}` : ""
    }`,

  listarImagens: (nome: string) =>
    request<{ raw: string[]; cenas: string[] }>(
      `/api/projetos/${encodeURIComponent(nome)}/imagens`
    ),

  uploadImagens: (nome: string, files: File[], limparAnteriores = true) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    return request<{
      ok: boolean;
      enviados: string[];
      cenas_geradas: string[];
      log: string;
    }>(
      `/api/projetos/${encodeURIComponent(nome)}/imagens?limpar_anteriores=${limparAnteriores}`,
      {
        method: "POST",
        body: form,
      }
    );
  },

  imagemCenaUrl: (nome: string, arquivo: string, cacheBust?: number) =>
    `${API_BASE}/api/projetos/${encodeURIComponent(nome)}/midia/cenas/${encodeURIComponent(
      arquivo
    )}${cacheBust ? `?t=${cacheBust}` : ""}`,

  prepararRender: (nome: string) =>
    request<{
      ok: boolean;
      projeto: string;
      template_dir: string;
      log: string;
    }>(`/api/projetos/${encodeURIComponent(nome)}/preparar-render`, {
      method: "POST",
    }),
};
