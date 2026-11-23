export type AbaId = "roteiro" | "audio" | "storyboard" | "imagens" | "thumb-render";

export type EfeitoCena =
  | "pop-in"
  | "zoom-in"
  | "zoom-out"
  | "slide-up"
  | "shake"
  | "cut";

export interface ProjetoResumo {
  nome: string;
  atualizado_em: number;
  tem_narracao: boolean;
  tem_timestamps: boolean;
  tem_storyboard: boolean;
  tem_cenas_json: boolean;
  tem_audio: boolean;
  qtd_imagens_cenas: number;
  qtd_imagens_raw: number;
  qtd_cenas_json: number;
  duracao_total: number | null;
  formato: string;
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
  escala: number;
}

export interface CenasConfig {
  projeto: string;
  formato: "16:9" | "9:16" | string;
  fps: number;
  duracao_total: number;
  audio: string;
  cenas: CenaItem[];
}
