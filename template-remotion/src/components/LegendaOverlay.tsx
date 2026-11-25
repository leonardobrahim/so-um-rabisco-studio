import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { CenaItem, LegendaBloco } from "../types";

interface LegendaOverlayProps {
  cenas: CenaItem[];
  ehHorizontal: boolean;
  fontFamily: string;
}

const CORES_TEXTO: Record<string, string> = {
  branco: "#FFFFFF",
  canal: "#FFC928",
  alerta: "#FF3B30",
};

function dividirFalaCurtaFallback(fala: string, inicio: number, fim: number): LegendaBloco[] {
  const palavras = String(fala || "")
    .trim()
    .split(/\s+/)
    .filter(Boolean);
  if (!palavras.length) return [];

  const dur = Math.max(0.25, fim - inicio);
  const maxP = dur >= 1.2 ? 3 : 2;
  const grupos: string[][] = [];
  for (let i = 0; i < palavras.length; i += maxP) {
    grupos.push(palavras.slice(i, i + maxP));
  }

  let cursor = inicio;
  return grupos.map((g, idx) => {
    const bFim = idx === grupos.length - 1 ? fim : cursor + dur * (g.length / palavras.length);
    const cor = idx % 3 === 1 ? "canal" : "branco";
    const item: LegendaBloco = {
      texto: g.join(" "),
      inicio: cursor,
      fim: Math.max(cursor + 0.2, bFim),
      cor,
    };
    cursor = bFim;
    return item;
  });
}

export const LegendaOverlay: React.FC<LegendaOverlayProps> = ({
  cenas,
  ehHorizontal,
  fontFamily,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const blocos: LegendaBloco[] = [];
  for (const cena of cenas) {
    const inicioCena = Number(cena.inicio) || 0;
    const fimCena = Number(cena.fim) || inicioCena + 1.5;
    if (Array.isArray(cena.legendas) && cena.legendas.length > 0) {
      blocos.push(...cena.legendas);
    } else {
      const fallback = (cena.narracao || cena.texto || "").trim();
      if (fallback) {
        blocos.push(...dividirFalaCurtaFallback(fallback, inicioCena, fimCena));
      }
    }
  }

  // Encontra apenas o bloco ativo no frame exato (nunca sobrepõe duas legendas)
  const tempoAtual = frame / fps;
  let blocoAtivoIndex = -1;
  for (let i = 0; i < blocos.length; i++) {
    const b = blocos[i];
    if (tempoAtual >= b.inicio && tempoAtual < b.fim) {
      blocoAtivoIndex = i;
      break;
    }
  }

  if (blocoAtivoIndex === -1) return null;

  const bloco = blocos[blocoAtivoIndex];
  const texto = String(bloco.texto || "").trim();
  if (!texto) return null;

  const startFrame = Math.round(bloco.inicio * fps);
  const localFrame = Math.max(0, frame - startFrame);

  const sp = spring({
    frame: localFrame,
    fps,
    config: { damping: 14, stiffness: 320, mass: 0.55 },
  });

  const scale = interpolate(sp, [0, 1], [0.78, 1.0]);
  const translateY = interpolate(sp, [0, 1], [12, 0]);
  const opacity = interpolate(localFrame, [0, 2], [0.35, 1], {
    extrapolateRight: "clamp",
  });

  const corKey = bloco.cor || (blocoAtivoIndex % 3 === 1 ? "canal" : "branco");
  const color = CORES_TEXTO[corKey] || "#FFFFFF";

  return (
    <div
      style={{
        position: "absolute",
        left: ehHorizontal ? "10%" : "7.5%",
        right: ehHorizontal ? "10%" : "7.5%",
        top: ehHorizontal ? "74%" : "62%",
        width: ehHorizontal ? "80%" : "85%",
        pointerEvents: "none",
        zIndex: 25,
        display: "flex",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          width: "100%",
          padding: "4px 10px",
          color,
          fontFamily,
          fontWeight: 900,
          fontSize: ehHorizontal ? 64 : 62,
          lineHeight: 1.12,
          letterSpacing: "0.5px",
          textTransform: "uppercase",
          textAlign: "center",
          transformOrigin: "center center",
          transform: `translate3d(0, ${translateY}px, 0) scale(${scale})`,
          opacity,
          whiteSpace: "normal",
          wordWrap: "break-word",
          overflowWrap: "break-word",
          WebkitTextStroke: "3px #000000",
          paintOrder: "stroke fill",
          textShadow:
            "-3px -3px 0 #000000, 3px -3px 0 #000000, -3px 3px 0 #000000, 3px 3px 0 #000000, 0 8px 18px rgba(0, 0, 0, 0.65)",
        }}
      >
        {texto}
      </div>
    </div>
  );
};
