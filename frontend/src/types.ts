export type AbaId = "roteiro" | "audio" | "storyboard" | "imagens" | "thumb-render";

export type ProjetoTipo = "longo" | "short";

export type EfeitoCena =
  | "pop-in"
  | "zoom-in"
  | "zoom-out"
  | "slide-up"
  | "shake"
  | "cut";

export type PersonagemTipo = "pose" | "sprite" | "none";

export type PersonagemPosicao =
  | "center"
  | "left"
  | "right"
  | "bottom-corner"
  | "bottom-left";

export type PersonagemAnimacao =
  | "pop-in"
  | "slide-in-left"
  | "slide-in-right"
  | "float"
  | "bounce"
  | "shake"
  | "none";

export interface PersonagemSpriteConfig {
  frames: number;
  quadro: number;
  fps: number;
}

export interface CenaFundo {
  arquivo: string;
  prompt?: string;
}

export interface CenaPersonagem {
  tipo: PersonagemTipo;
  fonte?: string;
  asset?: string;
  posicao?: PersonagemPosicao;
  x?: number;
  y?: number;
  escala?: number;
  flip?: boolean;
  animacao?: PersonagemAnimacao;
  tags?: string[];
  sprite?: PersonagemSpriteConfig;
  arquivo?: string;
  prompt?: string;
}

export interface BibliotecaPasta {
  fonte: string;
  pasta: string;
  modo: "poses" | "sprite";
  modo_inferido: boolean;
  frames: number;
  quadro: number;
  fps: number;
  tags_pasta: string[];
  qtd_assets: number;
}

export interface BibliotecaAsset {
  id: string;
  fonte: string;
  pasta: string;
  arquivo: string;
  tipo: "pose" | "sprite";
  frames: number;
  quadro: number;
  fps: number;
  tags: string[];
  tags_proprias: string[];
}

export interface BibliotecaPersonagem {
  pastas: BibliotecaPasta[];
  assets: BibliotecaAsset[];
}

export interface ProjetoResumo {
  nome: string;
  tipo: ProjetoTipo;
  atualizado_em: number;
  tem_narracao: boolean;
  tem_timestamps: boolean;
  tem_storyboard: boolean;
  tem_cenas_json: boolean;
  tem_audio: boolean;
  tem_prompts_flow: boolean;
  qtd_imagens_cenas: number;
  qtd_imagens_raw: number;
  qtd_cenas_json: number;
  duracao_total: number | null;
  formato: "16:9" | "9:16" | string;
}

export interface ProjetoMeta {
  tipo: ProjetoTipo;
  formato: "16:9" | "9:16";
  titulo_thumb?: string;
  duracao_thumb?: string;
  legenda_short?: string;
  hashtags_short?: string;
}

export interface PalavraTimestamp {
  palavra: string;
  inicio: number;
  fim: number;
}

export interface SegmentoTimestamp {
  marca: string;
  inicio: number;
  fim: number;
  texto: string;
  palavras?: PalavraTimestamp[];
}

export interface TimestampsData {
  projeto: string;
  duracao_total: number;
  segmentos: SegmentoTimestamp[];
}

export interface CenaItem {
  arquivo: string;
  inicio: number;
  fim: number;
  efeito: EfeitoCena | string;
  texto: string;
  narracao?: string;
  prompt?: string;
  prompt_fundo?: string;
  prompt_personagem?: string;
  escala: number;
  fundo?: CenaFundo;
  personagem?: CenaPersonagem;
}

export interface CenasConfig {
  projeto: string;
  formato: "16:9" | "9:16" | string;
  fps: number;
  duracao_total: number;
  audio: string;
  versao_schema?: number;
  mostrar_legendas?: boolean;
  cenas: CenaItem[];
}

export interface ComfyStatus {
  online: boolean;
  url: string;
  dispositivo: string | null;
  vram_total_mb: number | null;
  vram_free_mb: number | null;
  checkpoints: string[];
  checkpoint_padrao: string | null;
  erro: string | null;
}

export interface ComfyJobStatus {
  status: "idle" | "running" | "done" | "error" | "canceled";
  projeto: string;
  outro_projeto_gerando: string | null;
  checkpoint: string | null;
  total_cenas: number;
  concluidas: number;
  cena_indice_atual: number | null;
  ultima_cena_salva: string | null;
  logs: string[];
  erro: string | null;
}

export interface ComfyGerarPayload {
  apenas_faltantes?: boolean;
  indice_cena?: number;
  checkpoint?: string;
  steps?: number;
  cfg?: number;
  sampler_name?: string;
  scheduler?: string;
  largura?: number;
  altura?: number;
  seed?: number;
  negativo_extra?: string;
  workflow_api?: Record<string, unknown>;
}

export interface GeminiStatus {
  configurado: boolean;
  modelo_padrao: string;
  modelos_fallback: string[];
  mensagem: string | null;
}

export interface SeoThumbDados {
  titulo_principal: string;
  motivo_titulo: string;
  titulos_alternativos: string[];
  texto_na_thumb: string;
  prompt_thumb_16_9: string;
  prompt_thumb_sem_texto_16_9: string;
  descricao_youtube: string;
  tags_youtube: string[];
  legenda_short: string;
  hashtags_short: string;
  comentario_fixado: string;
}
