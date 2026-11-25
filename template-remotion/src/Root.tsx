import React from "react";
import { Composition, staticFile } from "remotion";
import { MainVideo, type MainVideoProps } from "./Composition";
import type { CenasData } from "./types";

const DADOS_INICIAIS: CenasData = {
  projeto: "padrao",
  formato: "16:9",
  fps: 30,
  duracao_total: 10,
  audio: "",
  tem_audio: false,
  mostrar_legendas: true,
  cenas: [],
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="MainVideo"
      component={MainVideo}
      durationInFrames={300}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{ dados: DADOS_INICIAIS } satisfies MainVideoProps}
      calculateMetadata={async () => {
        try {
          const resp = await fetch(staticFile("cenas.json"));
          if (resp.ok) {
            const dados = (await resp.json()) as CenasData;
            const fps = Math.max(1, Number(dados.fps) || 30);
            const duracao = Math.max(0.5, Number(dados.duracao_total) || 10);
            const ehHorizontal = (dados.formato || "9:16") === "16:9";
            return {
              durationInFrames: Math.max(1, Math.ceil(duracao * fps)),
              fps,
              width: ehHorizontal ? 1920 : 1080,
              height: ehHorizontal ? 1080 : 1920,
              props: { dados },
            };
          }
        } catch {
          // Fallback para props iniciais caso cenas.json ainda não exista
        }
        return {
          durationInFrames: 300,
          fps: 30,
          width: 1920,
          height: 1080,
          props: { dados: DADOS_INICIAIS },
        };
      }}
    />
  );
};
