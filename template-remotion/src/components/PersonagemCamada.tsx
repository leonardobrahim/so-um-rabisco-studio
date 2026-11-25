import React from "react";
import { Easing, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import type { PersonagemCena } from "../types";

interface PersonagemCamadaProps {
  personagem: PersonagemCena;
  ehHorizontal: boolean;
  duracaoFrames: number;
  parallaxX?: number;
  parallaxY?: number;
}

const ALTURA_PERSONAGEM = {
  horizontal: 0.52,
  vertical: 0.34,
};

function normalizarCaminhoPublic(arquivo: string): string {
  return arquivo.replace(/^\/+/, "");
}

export const PersonagemCamada: React.FC<PersonagemCamadaProps> = ({
  personagem,
  ehHorizontal,
  duracaoFrames,
  parallaxX = 0,
  parallaxY = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps, width: compW, height: compH } = useVideoConfig();

  if (!personagem.arquivo || (personagem.tipo !== "pose" && personagem.tipo !== "sprite")) {
    return null;
  }

  const escalaCfg = Number(personagem.escala) > 0 ? Number(personagem.escala) : 1;
  const lado = Math.round(
    compH * (ehHorizontal ? ALTURA_PERSONAGEM.horizontal : ALTURA_PERSONAGEM.vertical) * escalaCfg
  );
  const margem = Math.round(compW * 0.03);
  const posicao = personagem.posicao || "center";

  let left: number;
  if (posicao === "left" || posicao === "bottom-left") {
    left = margem;
  } else if (posicao === "right" || posicao === "bottom-corner") {
    left = compW - lado - margem;
  } else {
    left = Math.round((compW - lado) / 2);
  }

  const posStyle: React.CSSProperties = {
    position: "absolute",
    width: lado,
    height: lado,
    transformOrigin: "50% 100%",
    pointerEvents: "none",
  };

  if (typeof personagem.x === "number" && typeof personagem.y === "number") {
    posStyle.left = Math.round((personagem.x / 100) * compW - lado / 2);
    posStyle.top = Math.round((personagem.y / 100) * compH - lado / 2);
  } else {
    posStyle.left = left;
    posStyle.bottom = -Math.round(lado * 0.04);
  }

  const animacao = String(personagem.animacao || "pop-in").toLowerCase();

  let entradaScale = 1;
  let entradaX = 0;
  let entradaY = 0;
  let entradaOpacity = 1;
  let entradaRotate = 0;

  if (animacao === "pop-in") {
    const sp = spring({
      frame,
      fps,
      config: { damping: 12, stiffness: 210, mass: 0.75 },
    });
    entradaScale = interpolate(sp, [0, 1], [0.55, 1]);
    entradaY = interpolate(sp, [0, 1], [36, 0]);
    entradaOpacity = interpolate(frame, [0, 4], [0, 1], { extrapolateRight: "clamp" });
  } else if (animacao === "slide-in-left") {
    const sp = spring({
      frame,
      fps,
      config: { damping: 15, stiffness: 170, mass: 0.8 },
    });
    entradaX = interpolate(sp, [0, 1], [-lado * 1.15, 0]);
    entradaRotate = interpolate(sp, [0, 1], [-4, 0]);
    entradaOpacity = interpolate(frame, [0, 3], [0, 1], { extrapolateRight: "clamp" });
  } else if (animacao === "slide-in-right") {
    const sp = spring({
      frame,
      fps,
      config: { damping: 15, stiffness: 170, mass: 0.8 },
    });
    entradaX = interpolate(sp, [0, 1], [lado * 1.15, 0]);
    entradaRotate = interpolate(sp, [0, 1], [4, 0]);
    entradaOpacity = interpolate(frame, [0, 3], [0, 1], { extrapolateRight: "clamp" });
  } else if (animacao === "bounce") {
    const sp = spring({
      frame,
      fps,
      config: { damping: 9, stiffness: 220, mass: 0.7 },
    });
    entradaY = interpolate(sp, [0, 1], [lado * 0.35, 0]);
    entradaScale = interpolate(sp, [0, 1], [0.85, 1]);
    entradaOpacity = interpolate(frame, [0, 4], [0, 1], { extrapolateRight: "clamp" });
  } else if (animacao === "float") {
    entradaOpacity = interpolate(frame, [0, 6], [0, 1], { extrapolateRight: "clamp" });
    entradaY = interpolate(frame, [0, 10], [18, 0], {
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.cubic),
    });
  } else if (animacao === "shake") {
    const sp = spring({
      frame,
      fps,
      config: { damping: 12, stiffness: 240, mass: 0.7 },
    });
    entradaScale = interpolate(sp, [0, 1], [0.65, 1]);
    entradaOpacity = interpolate(frame, [0, 3], [0, 1], { extrapolateRight: "clamp" });
    if (frame >= 3 && frame <= 16) {
      const decay = 1 - (frame - 3) / 13;
      entradaX = Math.sin((frame - 3) * 2.1) * 14 * decay;
      entradaRotate = Math.sin((frame - 3) * 2.1) * 2.4 * decay;
    }
  } else {
    entradaOpacity = interpolate(frame, [0, 3], [0, 1], { extrapolateRight: "clamp" });
  }

  // Vida contínua orgânica (respiração + leve balanço) para o personagem nunca parecer um recorte congelado
  const tSec = frame / fps;
  const cicloResp = Math.sin(tSec * 2.6);
  const vivoY = animacao === "float" ? Math.sin(tSec * 3.1) * 10 : cicloResp * 3.5;
  const vivoScaleY = 1 + Math.sin(tSec * 2.8) * 0.012;
  const vivoRotate = Math.sin(tSec * 1.9) * 0.65;

  // Pequeno fade-out nos últimos 3 frames apenas se a cena for longa o bastante
  const saidaOpacity =
    duracaoFrames > 12
      ? interpolate(frame, [duracaoFrames - 4, duracaoFrames], [1, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        })
      : 1;

  const src = staticFile(normalizarCaminhoPublic(personagem.arquivo));
  const ehSprite = personagem.tipo === "sprite";
  const cfgSprite = personagem.sprite || {};
  const totalFrames = Math.max(1, Number(cfgSprite.frames) || 1);
  const spriteFps = Math.max(1, Number(cfgSprite.fps) || 8);
  const quadroAtual = ehSprite ? Math.floor((frame * spriteFps) / fps) % totalFrames : 0;

  return (
    <div
      style={{
        ...posStyle,
        opacity: entradaOpacity * saidaOpacity,
        transform: `translate3d(${entradaX + parallaxX}px, ${entradaY + vivoY + parallaxY}px, 0) scale(${entradaScale}, ${entradaScale * vivoScaleY}) rotate(${entradaRotate + vivoRotate}deg)`,
      }}
    >
      {/* Sombra de contato sutil nos pés para integrar o personagem ao cenário 16:9 */}
      {ehHorizontal && (
        <div
          style={{
            position: "absolute",
            left: "24%",
            right: "24%",
            bottom: Math.round(lado * 0.045),
            height: Math.max(12, Math.round(lado * 0.045)),
            borderRadius: "50%",
            background: "radial-gradient(ellipse at center, rgba(0,0,0,0.20) 0%, rgba(0,0,0,0) 72%)",
            pointerEvents: "none",
          }}
        />
      )}

      <div
        style={{
          width: "100%",
          height: "100%",
          overflow: "hidden",
          transform: personagem.flip ? "scaleX(-1)" : undefined,
        }}
      >
        {ehSprite ? (
          <Img
            src={src}
            style={{
              width: totalFrames * lado,
              height: lado,
              maxWidth: "none",
              transform: `translateX(${-quadroAtual * lado}px)`,
              display: "block",
            }}
          />
        ) : (
          <Img
            src={src}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "contain",
              display: "block",
            }}
          />
        )}
      </div>
    </div>
  );
};
