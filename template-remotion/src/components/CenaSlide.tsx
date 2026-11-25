import React from "react";
import { Easing, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import type { CenaItem } from "../types";
import { PersonagemCamada } from "./PersonagemCamada";

interface CenaSlideProps {
  cena: CenaItem;
  index: number;
  ehHorizontal: boolean;
  duracaoFrames: number;
  transicaoFrames: number;
  ehUltima: boolean;
}

type ModoCamera =
  | "zoom-in"
  | "zoom-out"
  | "ken-burns-right"
  | "ken-burns-left"
  | "ken-burns-up"
  | "impact-pop"
  | "slide-up"
  | "slide-left";

function escolherModoCamera(cena: CenaItem, index: number, ehGancho: boolean, ehHorizontal: boolean): ModoCamera {
  const efeito = (cena.efeito || "").toLowerCase();

  if (ehHorizontal) {
    if (efeito === "pop-in" || efeito === "impact-pop" || efeito === "shake") {
      return "impact-pop";
    }
    if (index > 0 && index % 5 === 0) {
      return index % 10 === 0 ? "slide-left" : "slide-up";
    }
    const cicloLongo: ModoCamera[] = [
      "zoom-in",
      "ken-burns-right",
      "zoom-out",
      "ken-burns-left",
      "zoom-in",
      "ken-burns-up",
    ];
    return cicloLongo[index % cicloLongo.length];
  }

  if (ehGancho) {
    const cicloGancho: ModoCamera[] = ["impact-pop", "slide-up", "impact-pop", "slide-left", "zoom-in"];
    return cicloGancho[index % cicloGancho.length];
  }

  if (index > 0 && index % 4 === 0) {
    return index % 8 === 0 ? "slide-left" : "slide-up";
  }

  if (efeito === "pop-in" || efeito === "impact-pop" || efeito === "shake") {
    return "impact-pop";
  }
  if (efeito === "zoom-in") return "zoom-in";
  if (efeito === "zoom-out") return "zoom-out";

  return index % 2 === 0 ? "zoom-in" : "zoom-out";
}

function normalizarCaminhoPublic(arquivo: string): string {
  return arquivo.replace(/^\/+/, "");
}

export const CenaSlide: React.FC<CenaSlideProps> = ({
  cena,
  index,
  ehHorizontal,
  duracaoFrames,
  transicaoFrames,
  ehUltima,
}) => {
  const frame = useCurrentFrame();
  const { fps, width: compW, height: compH } = useVideoConfig();

  const inicioSeg = Number(cena.inicio) || 0;
  const ehGancho = inicioSeg < 10.0;
  const modo = escolherModoCamera(cena, index, ehGancho, ehHorizontal);
  const escalaBase = Number(cena.escala) > 0 ? Number(cena.escala) : 1.0;

  const progress = interpolate(frame, [0, Math.max(1, duracaoFrames)], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.sin),
  });

  // Crossfade suave entre cenas sobrepostas (sem corte duro seco)
  const fadeIn =
    index === 0 || transicaoFrames <= 0
      ? 1
      : interpolate(frame, [0, transicaoFrames], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.out(Easing.cubic),
        });

  const fadeOut =
    ehUltima || transicaoFrames <= 0 || duracaoFrames <= transicaoFrames * 2
      ? 1
      : interpolate(frame, [duracaoFrames - transicaoFrames, duracaoFrames], [1, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.in(Easing.cubic),
        });

  const focos = ["50% 45%", "38% 45%", "62% 45%", "50% 38%"];
  const transformOrigin = ehHorizontal ? focos[index % focos.length] : "center center";

  let camScale = ehHorizontal ? escalaBase * 1.08 : escalaBase;
  let camX = 0;
  let camY = 0;
  let camRotate = 0;

  if (ehHorizontal) {
    const tilt = index % 2 === 0 ? 0.35 : -0.35;
    if (modo === "ken-burns-right") {
      camScale = interpolate(progress, [0, 1], [1.11, 1.16]) * escalaBase;
      camX = interpolate(progress, [0, 1], [-compW * 0.022, compW * 0.022]);
      camY = interpolate(progress, [0, 1], [compH * 0.005, -compH * 0.005]);
      camRotate = interpolate(progress, [0, 1], [0, tilt]);
    } else if (modo === "ken-burns-left") {
      camScale = interpolate(progress, [0, 1], [1.11, 1.16]) * escalaBase;
      camX = interpolate(progress, [0, 1], [compW * 0.022, -compW * 0.022]);
      camY = interpolate(progress, [0, 1], [-compH * 0.005, compH * 0.005]);
      camRotate = interpolate(progress, [0, 1], [0, -tilt]);
    } else if (modo === "ken-burns-up") {
      camScale = interpolate(progress, [0, 1], [1.10, 1.15]) * escalaBase;
      camY = interpolate(progress, [0, 1], [compH * 0.02, -compH * 0.02]);
      camX = interpolate(progress, [0, 1], [0, (index % 2 === 0 ? 1 : -1) * compW * 0.01]);
    } else if (modo === "slide-up") {
      const sp = spring({ frame, fps, config: { damping: 16, stiffness: 200, mass: 0.7 } });
      camY = interpolate(sp, [0, 1], [compH * 0.14, 0]);
      camScale = interpolate(progress, [0, 1], [1.09, 1.15]) * escalaBase;
      camX = interpolate(progress, [0, 1], [0, (index % 2 === 0 ? 1 : -1) * compW * 0.012]);
    } else if (modo === "slide-left") {
      const sp = spring({ frame, fps, config: { damping: 16, stiffness: 200, mass: 0.7 } });
      camX =
        interpolate(sp, [0, 1], [compW * 0.16, 0]) +
        interpolate(progress, [0, 1], [0, -compW * 0.012]);
      camScale = interpolate(progress, [0, 1], [1.09, 1.15]) * escalaBase;
    } else if (modo === "impact-pop") {
      const sp = spring({ frame, fps, config: { damping: 13, stiffness: 260, mass: 0.6 } });
      const pop = interpolate(sp, [0, 1], [1.20, 1.09]);
      const drift = interpolate(progress, [0, 1], [0, 0.04]);
      camScale = (pop + drift) * escalaBase;
      camX = interpolate(progress, [0, 1], [0, (index % 2 === 0 ? 1 : -1) * compW * 0.012]);
      camRotate = interpolate(sp, [0, 1], [-tilt, 0]);
    } else if (modo === "zoom-out") {
      camScale = interpolate(progress, [0, 1], [1.18, 1.07]) * escalaBase;
      camX = interpolate(progress, [0, 1], [-compW * 0.01, compW * 0.01]);
      camRotate = interpolate(progress, [0, 1], [tilt * 0.5, 0]);
    } else {
      camScale = interpolate(progress, [0, 1], [1.07, 1.17]) * escalaBase;
      camX = interpolate(progress, [0, 1], [0, (index % 2 === 0 ? 1 : -1) * compW * 0.012]);
      camY = interpolate(progress, [0, 1], [0, -compH * 0.008]);
      camRotate = interpolate(progress, [0, 1], [0, tilt * 0.5]);
    }
  } else {
    const driftX = index % 2 === 0 ? 16 : -16;
    const tilt = index % 2 === 0 ? 1.0 : -1.0;

    if (modo === "slide-up") {
      const sp = spring({ frame, fps, config: { damping: 15, stiffness: 230, mass: 0.65 } });
      camY = interpolate(sp, [0, 1], [compH * 0.16, 0]);
      camScale = interpolate(progress, [0, 1], [1.02, 1.10]) * escalaBase;
      camX = interpolate(progress, [0, 1], [0, driftX]);
      camRotate = interpolate(progress, [0, 1], [0, tilt]);
    } else if (modo === "slide-left") {
      const sp = spring({ frame, fps, config: { damping: 15, stiffness: 230, mass: 0.65 } });
      camX = interpolate(sp, [0, 1], [compW * 0.22, 0]) + interpolate(progress, [0, 1], [0, driftX * 0.5]);
      camScale = interpolate(progress, [0, 1], [1.02, 1.10]) * escalaBase;
      camRotate = interpolate(progress, [0, 1], [0, -tilt]);
    } else if (modo === "impact-pop") {
      const sp = spring({ frame, fps, config: { damping: 12, stiffness: 260, mass: 0.6 } });
      const pop = interpolate(sp, [0, 1], [ehGancho ? 1.18 : 1.14, 1.02]);
      const drift = interpolate(progress, [0, 1], [0, 0.07]);
      camScale = (pop + drift) * escalaBase;
      camX = interpolate(progress, [0, 1], [0, driftX * 0.7]);
      camRotate = interpolate(sp, [0, 1], [-tilt, 0]);
    } else if (modo === "zoom-out") {
      camScale = interpolate(progress, [0, 1], [1.12, 1.0]) * escalaBase;
      camX = interpolate(progress, [0, 1], [-driftX, driftX * 0.5]);
      camRotate = interpolate(progress, [0, 1], [tilt * 0.7, 0]);
    } else {
      camScale = interpolate(progress, [0, 1], [1.0, 1.11]) * escalaBase;
      camX = interpolate(progress, [0, 1], [0, driftX]);
      camRotate = interpolate(progress, [0, 1], [0, tilt]);
    }
  }

  // Tremor adicional se o efeito pedido for "shake"
  if ((cena.efeito || "").toLowerCase() === "shake" && frame < 14) {
    const decay = 1 - frame / 14;
    camX += Math.sin(frame * 2.2) * 10 * decay;
    camRotate += Math.sin(frame * 2.2) * 0.9 * decay;
  }

  const fundoArquivo = (cena.fundo && cena.fundo.arquivo) || cena.arquivo;
  const fundoSrc = staticFile(normalizarCaminhoPublic(fundoArquivo));
  const personagem = cena.personagem;
  const temPersonagem =
    Boolean(personagem) &&
    (personagem?.tipo === "pose" || personagem?.tipo === "sprite") &&
    Boolean(personagem?.arquivo);

  // Parallax 2.5D: o personagem desloca suavemente em contraponto/proporção ao fundo
  const parallaxX = ehHorizontal ? -camX * 0.35 : 0;
  const parallaxY = ehHorizontal ? -camY * 0.25 : 0;

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        width: "100%",
        height: "100%",
        opacity: fadeIn * fadeOut,
        overflow: "hidden",
      }}
    >
      {/* Camada de Fundo (ou imagem fechada caso não haja personagem em camada) */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: !ehHorizontal && temPersonagem ? "flex-start" : "center",
          justifyContent: "center",
          paddingTop: !ehHorizontal && temPersonagem ? "7%" : undefined,
          transformOrigin,
          transform: `translate3d(${camX}px, ${camY}px, 0) scale(${camScale}) rotate(${camRotate}deg)`,
        }}
      >
        <Img
          src={fundoSrc}
          style={
            ehHorizontal
              ? {
                  width: "100%",
                  height: "100%",
                  objectFit: "cover",
                  display: "block",
                }
              : {
                  maxWidth: "84%",
                  maxHeight: temPersonagem ? "56%" : "70%",
                  objectFit: "contain",
                  display: "block",
                }
          }
        />
      </div>

      {/* Vinheta cinematográfica ultra-suave nas bordas para vídeos 16:9 */}
      {ehHorizontal && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background:
              "radial-gradient(ellipse at center, rgba(0, 0, 0, 0) 62%, rgba(0, 0, 0, 0.10) 100%)",
            pointerEvents: "none",
          }}
        />
      )}

      {/* Camada independente do personagem (pose PNG ou sprite animado com parallax) */}
      {temPersonagem && personagem && (
        <PersonagemCamada
          personagem={personagem}
          ehHorizontal={ehHorizontal}
          duracaoFrames={duracaoFrames}
          parallaxX={parallaxX}
          parallaxY={parallaxY}
        />
      )}
    </div>
  );
};
