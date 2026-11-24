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
  escala?: number;
  flip?: boolean;
  animacao?: PersonagemAnimacao;
  tags?: string[];
  sprite?: PersonagemSpriteConfig;
  arquivo?: string;
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
