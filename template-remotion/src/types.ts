export interface LegendaBloco {
  texto: string;
  inicio: number;
  fim: number;
  cor?: "branco" | "canal" | "alerta" | string;
}

export interface SpriteConfig {
  frames?: number;
  quadro?: number;
  fps?: number;
}

export interface PersonagemCena {
  tipo: "pose" | "sprite" | "none";
  fonte?: string;
  asset?: string;
  arquivo?: string;
  posicao?: "center" | "left" | "right" | "bottom-corner" | "bottom-left" | string;
  x?: number;
  y?: number;
  escala?: number;
  flip?: boolean;
  animacao?: "pop-in" | "slide-in-left" | "slide-in-right" | "float" | "bounce" | "shake" | "none" | string;
  sprite?: SpriteConfig;
}

export interface CenaItem {
  arquivo: string;
  inicio: number;
  fim: number;
  efeito?: string;
  texto?: string;
  narracao?: string;
  escala?: number;
  legendas?: LegendaBloco[];
  fundo?: {
    arquivo?: string;
    prompt?: string;
  };
  personagem?: PersonagemCena;
}

export interface CenasData {
  projeto: string;
  formato: "16:9" | "9:16" | string;
  fps?: number;
  duracao_total: number;
  audio?: string;
  tem_audio?: boolean;
  mostrar_legendas?: boolean;
  cenas: CenaItem[];
}
