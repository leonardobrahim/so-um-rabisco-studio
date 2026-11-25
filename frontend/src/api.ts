import type {
  BibliotecaPersonagem,
  CenasConfig,
  ComfyGerarPayload,
  ComfyJobStatus,
  ComfyStatus,
  GeminiStatus,
  ProjetoMeta,
  ProjetoResumo,
  ProjetoTipo,
  SeoThumbDados,
  TimestampsData,
} from "./types";

export const API_BASE =
  import.meta.env.VITE_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    let message = `Erro HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) {
        message =
          typeof body.detail === "string"
            ? body.detail
            : JSON.stringify(body.detail);
      }
    } catch {
      // ignora parse de erro não-JSON
    }
    throw new Error(message);
  }
  return res.json() as Promise<T>;
}

export const api = {
  geminiStatus: () => request<GeminiStatus>("/api/gemini/status"),

  listarProjetos: () => request<{ projetos: ProjetoResumo[] }>("/api/projetos"),

  criarProjeto: (nome: string, tipo: ProjetoTipo = "longo") =>
    request<{ projeto: ProjetoResumo }>("/api/projetos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nome, tipo }),
    }),

  excluirProjeto: (nome: string) =>
    request<{ ok: boolean; projeto: string }>(
      `/api/projetos/${encodeURIComponent(nome)}`,
      { method: "DELETE" }
    ),

  renomearProjeto: (nome: string, novoNome: string) =>
    request<{ ok: boolean; nome_antigo: string; projeto: ProjetoResumo }>(
      `/api/projetos/${encodeURIComponent(nome)}/renomear`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ novo_nome: novoNome }),
      }
    ),

  lerMeta: (nome: string) =>
    request<{ meta: ProjetoMeta }>(
      `/api/projetos/${encodeURIComponent(nome)}/meta`
    ),

  atualizarMeta: (nome: string, payload: Partial<ProjetoMeta>) =>
    request<{ ok: boolean; meta: ProjetoMeta; projeto: ProjetoResumo }>(
      `/api/projetos/${encodeURIComponent(nome)}/meta`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }
    ),

  lerNarracao: (nome: string) =>
    request<{ nome: string; conteudo: string; existe: boolean }>(
      `/api/projetos/${encodeURIComponent(nome)}/narracao`
    ),

  salvarNarracao: (nome: string, conteudo: string) =>
    request<{
      ok: boolean;
      arquivo: string;
      caracteres: number;
      palavras: number;
    }>(`/api/projetos/${encodeURIComponent(nome)}/narracao`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conteudo }),
    }),

  lerStoryboard: (nome: string) =>
    request<{ nome: string; conteudo: string; existe: boolean }>(
      `/api/projetos/${encodeURIComponent(nome)}/storyboard`
    ),

  salvarStoryboard: (nome: string, conteudo: string) =>
    request<{
      ok: boolean;
      arquivo: string;
      prompts_atualizados: number;
    }>(`/api/projetos/${encodeURIComponent(nome)}/storyboard`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conteudo }),
    }),

  gerarStoryboard: (nome: string, tipo?: ProjetoTipo) =>
    request<{
      ok: boolean;
      origem: "timestamps" | "narracao";
      tipo: ProjetoTipo;
      formato: "16:9" | "9:16";
      duracao_total: number;
      qtd_cenas: number;
      geracao_ia?: "gemini" | "fallback_local";
      modelo_ia?: string | null;
      aviso_ia?: string | null;
      cenas: CenasConfig;
      storyboard: string;
    }>(
      `/api/projetos/${encodeURIComponent(nome)}/gerar-storyboard${
        tipo ? `?tipo=${tipo}` : ""
      }`,
      { method: "POST" }
    ),

  gerarRoteiro: (
    nome: string,
    payload: {
      tema: string;
      modo: "ideias" | "roteiro";
      tipo?: ProjetoTipo;
      salvar?: boolean;
    }
  ) =>
    request<{
      ok: boolean;
      modo: "ideias" | "roteiro";
      modelo_ia: string;
      conteudo: string;
      palavras?: number;
      dados: Record<string, unknown>;
    }>(`/api/projetos/${encodeURIComponent(nome)}/gerar-roteiro`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),

  lerSeoThumb: (nome: string) =>
    request<{
      nome: string;
      existe: boolean;
      markdown: string;
      meta: ProjetoMeta;
    }>(`/api/projetos/${encodeURIComponent(nome)}/seo-thumb`),

  gerarSeoThumb: (nome: string, tipo?: ProjetoTipo) =>
    request<{
      ok: boolean;
      modelo_ia: string;
      markdown: string;
      dados: SeoThumbDados;
    }>(
      `/api/projetos/${encodeURIComponent(nome)}/gerar-seo-thumb${
        tipo ? `?tipo=${tipo}` : ""
      }`,
      { method: "POST" }
    ),

  gerarCenasDePrompts: (nome: string, tipo?: ProjetoTipo) =>
    request<{
      ok: boolean;
      fonte: string;
      formato: "16:9" | "9:16";
      duracao_total: number;
      qtd_cenas: number;
      cenas: CenasConfig;
    }>(
      `/api/projetos/${encodeURIComponent(nome)}/gerar-cenas-prompts${
        tipo ? `?tipo=${tipo}` : ""
      }`,
      { method: "POST" }
    ),

  exportarPrompts: (nome: string) =>
    request<{ ok: boolean; arquivo_destino: string; qtd_prompts: number }>(
      `/api/projetos/${encodeURIComponent(nome)}/exportar-prompts`,
      { method: "POST" }
    ),

  obterPacoteChat: (nome: string, tipo?: ProjetoTipo) =>
    request<{
      ok: boolean;
      projeto: string;
      tipo: ProjetoTipo;
      formato: "16:9" | "9:16";
      duracao_total: number;
      qtd_cortes: number;
      origem: "timestamps" | "narracao";
      pacote: string;
    }>(
      `/api/projetos/${encodeURIComponent(nome)}/pacote-chat${
        tipo ? `?tipo=${tipo}` : ""
      }`
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

  sugerirPersonagem: (
    nome: string,
    dados: CenasConfig,
    apenasSemPersonagem = false
  ) =>
    request<{ ok: boolean; alteradas: number; dados: CenasConfig }>(
      `/api/projetos/${encodeURIComponent(
        nome
      )}/cenas/sugerir-personagem?apenas_sem_personagem=${apenasSemPersonagem}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dados }),
      }
    ),

  listarBibliotecaPersonagem: () =>
    request<BibliotecaPersonagem>("/api/personagem/biblioteca"),

  personagemArquivoUrl: (
    assetOrPasta: string,
    arquivo?: string,
    fonte = "protagonista",
    cacheBust?: number
  ) => {
    let pasta = assetOrPasta;
    let nomeArquivo = arquivo ?? "";
    if (!arquivo && assetOrPasta.includes("/")) {
      const partes = assetOrPasta.split("/");
      pasta = partes[0] || "";
      nomeArquivo = partes[1] || "";
    }
    const qs = new URLSearchParams({ fonte });
    if (cacheBust) qs.set("t", String(cacheBust));
    return `${API_BASE}/api/personagem/arquivo/${encodeURIComponent(
      pasta
    )}/${encodeURIComponent(nomeArquivo)}?${qs.toString()}`;
  },

  atualizarBibliotecaPersonagem: (
    pasta: string,
    payload: {
      modo?: "poses" | "sprite";
      fps?: number;
      tags_pasta?: string[];
      tags?: Record<string, string[]>;
    },
    fonte = "protagonista"
  ) =>
    request<{ ok: boolean } & BibliotecaPersonagem>(
      `/api/personagem/biblioteca/${encodeURIComponent(
        pasta
      )}?fonte=${encodeURIComponent(fonte)}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }
    ),

  uploadPersonagemAsset: (
    file: File,
    opcoes?: {
      pasta?: string;
      modo?: "auto" | "poses" | "sprite";
      fps?: number;
      frames?: number;
      removerFundo?: boolean;
    }
  ) => {
    const form = new FormData();
    form.append("file", file);
    form.append("pasta", opcoes?.pasta || "custom");
    form.append("modo", opcoes?.modo || "auto");
    form.append("fps", String(opcoes?.fps ?? 8));
    form.append("frames", String(opcoes?.frames ?? 1));
    form.append("remover_fundo", String(opcoes?.removerFundo ?? true));
    return request<{ ok: boolean; asset_id: string; tipo: "pose" | "sprite" } & BibliotecaPersonagem>(
      "/api/personagem/upload",
      { method: "POST", body: form }
    );
  },

  excluirPersonagemAsset: (asset: string, fonte = "protagonista") =>
    request<{ ok: boolean } & BibliotecaPersonagem>(
      `/api/personagem/asset?asset=${encodeURIComponent(asset)}&fonte=${encodeURIComponent(fonte)}`,
      { method: "DELETE" }
    ),

  uploadImagemCena: (nome: string, arquivoAlvo: string, file: File) => {
    const form = new FormData();
    form.append("arquivo_alvo", arquivoAlvo);
    form.append("file", file);
    return request<{ ok: boolean; arquivo: string; cenas_geradas: string[] }>(
      `/api/projetos/${encodeURIComponent(nome)}/imagens/cena`,
      { method: "POST", body: form }
    );
  },

  reordenarImagens: (nome: string, ordem: string[]) =>
    request<{ ok: boolean; cenas_geradas: string[] }>(
      `/api/projetos/${encodeURIComponent(nome)}/imagens/reordenar`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ordem }),
      }
    ),

  excluirImagemCena: (nome: string, arquivo: string) =>
    request<{ ok: boolean; cenas_geradas: string[] }>(
      `/api/projetos/${encodeURIComponent(nome)}/imagens/cena/${encodeURIComponent(arquivo)}`,
      { method: "DELETE" }
    ),

  uploadAudio: (nome: string, file: File, gerarStoryboard = true) => {
    const form = new FormData();
    form.append("file", file);
    return request<{
      ok: boolean;
      arquivo_salvo: string;
      tamanho_bytes: number;
      log: string;
      timestamps: TimestampsData | null;
      storyboard_gerado: {
        qtd_cenas: number;
        formato: string;
        origem: string;
      } | null;
      storyboard_erro?: string | null;
    }>(
      `/api/projetos/${encodeURIComponent(
        nome
      )}/audio?gerar_storyboard=${gerarStoryboard}`,
      {
        method: "POST",
        body: form,
      }
    );
  },

  audioUrl: (nome: string, cacheBust?: number) =>
    `${API_BASE}/api/projetos/${encodeURIComponent(nome)}/audio${
      cacheBust ? `?t=${cacheBust}` : ""
    }`,

  listarImagens: (nome: string) =>
    request<{ raw: string[]; cenas: string[] }>(
      `/api/projetos/${encodeURIComponent(nome)}/imagens`
    ),

  reprocessarImagens: (nome: string) =>
    request<{ ok: boolean; cenas_geradas: string[]; log: string }>(
      `/api/projetos/${encodeURIComponent(nome)}/imagens/reprocessar`,
      { method: "POST" }
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
      `/api/projetos/${encodeURIComponent(
        nome
      )}/imagens?limpar_anteriores=${limparAnteriores}`,
      {
        method: "POST",
        body: form,
      }
    );
  },

  imagemCenaUrl: (nome: string, arquivo: string, cacheBust?: number) =>
    `${API_BASE}/api/projetos/${encodeURIComponent(
      nome
    )}/midia/cenas/${encodeURIComponent(arquivo)}${
      cacheBust ? `?t=${cacheBust}` : ""
    }`,

  comfyuiStatus: () => request<ComfyStatus>("/api/comfyui/status"),

  comfyuiGerar: (nome: string, payload: ComfyGerarPayload) =>
    request<{
      ok: boolean;
      status: string;
      total_cenas: number;
      checkpoint: string;
      mensagem?: string;
    }>(`/api/projetos/${encodeURIComponent(nome)}/comfyui/gerar`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),

  comfyuiJobStatus: (nome: string) =>
    request<ComfyJobStatus>(
      `/api/projetos/${encodeURIComponent(nome)}/comfyui/status`
    ),

  comfyuiCancelar: () =>
    request<{ ok: boolean }>("/api/comfyui/cancelar", { method: "POST" }),

  prepararRender: (nome: string, comLegenda = true) =>
    request<{
      ok: boolean;
      projeto: string;
      com_legenda: boolean;
      template_dir: string;
      log: string;
    }>(
      `/api/projetos/${encodeURIComponent(
        nome
      )}/preparar-render?com_legenda=${comLegenda}`,
      {
        method: "POST",
      }
    ),

  renderizarVideo: (
    nome: string,
    comLegenda = true,
    qualidade: "draft" | "looks" | "delivery" = "looks"
  ) =>
    request<{
      ok: boolean;
      status: string;
      projeto: string;
      arquivo_saida: string;
    }>(
      `/api/projetos/${encodeURIComponent(
        nome
      )}/renderizar-video?com_legenda=${comLegenda}&qualidade=${qualidade}`,
      {
        method: "POST",
      }
    ),

  statusRenderVideo: (nome: string) =>
    request<{
      status: "idle" | "running" | "done" | "error";
      projeto: string;
      outro_projeto_renderizando: string | null;
      progresso: number;
      etapa: string;
      existe_video: boolean;
      tamanho_bytes: number | null;
      caminho_video: string;
      log_linhas: string[];
      ultima_linha: string | null;
      erro: string | null;
    }>(`/api/projetos/${encodeURIComponent(nome)}/renderizar-status`),

  videoFinalUrl: (nome: string, cacheBust?: number) =>
    `${API_BASE}/api/projetos/${encodeURIComponent(nome)}/video${
      cacheBust ? `?t=${cacheBust}` : ""
    }`,
};
