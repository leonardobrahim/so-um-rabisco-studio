import React from "react";
import { Audio, Sequence, staticFile, useVideoConfig } from "remotion";
import { loadFont } from "@remotion/google-fonts/Montserrat";
import type { CenasData } from "./types";
import { CenaSlide } from "./components/CenaSlide";
import { LegendaOverlay } from "./components/LegendaOverlay";

const { fontFamily } = loadFont("normal", {
  weights: ["700", "800", "900"],
  subsets: ["latin"],
});

export type MainVideoProps = {
  dados?: CenasData;
};

const TRANSICAO_FRAMES = 6; // ~0.20s a 30fps de sobreposição fluida entre cenas

export const MainVideo: React.FC<MainVideoProps> = ({ dados }) => {
  const { fps } = useVideoConfig();
  const cfg = dados ?? {
    projeto: "padrao",
    formato: "16:9",
    duracao_total: 10,
    cenas: [],
  };
  const ehHorizontal = (cfg.formato || "9:16") === "16:9";
  const cenas = cfg.cenas || [];
  const mostrarLegendas = cfg.mostrar_legendas !== false;
  const audioArquivo = (cfg.audio || "").replace(/^\/+/, "");

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        backgroundColor: "#FFFFFF",
        overflow: "hidden",
        fontFamily,
      }}
    >
      {audioArquivo && cfg.tem_audio !== false && (
        <Audio src={staticFile(audioArquivo)} />
      )}

      {cenas.map((cena, index) => {
        const inicio = Number(cena.inicio) || 0;
        const fim = Number(cena.fim) || inicio + 1.5;
        const startFrame = Math.max(0, Math.round(inicio * fps));
        const endFrame = Math.max(startFrame + 1, Math.round(fim * fps));
        const ehUltima = index === cenas.length - 1;
        const overlap = ehUltima ? 0 : TRANSICAO_FRAMES;
        const durationInFrames = Math.max(1, endFrame - startFrame + overlap);

        return (
          <Sequence
            key={`${cena.arquivo}-${index}`}
            from={startFrame}
            durationInFrames={durationInFrames}
            layout="none"
          >
            <CenaSlide
              cena={cena}
              index={index}
              ehHorizontal={ehHorizontal}
              duracaoFrames={durationInFrames}
              transicaoFrames={TRANSICAO_FRAMES}
              ehUltima={ehUltima}
            />
          </Sequence>
        );
      })}

      {mostrarLegendas && (
        <LegendaOverlay
          cenas={cenas}
          ehHorizontal={ehHorizontal}
          fontFamily={fontFamily}
        />
      )}
    </div>
  );
};
