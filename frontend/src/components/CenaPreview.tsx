import { useRef, useState, type CSSProperties, type PointerEvent } from "react";
import { api } from "../api";
import type { BibliotecaAsset, CenaItem } from "../types";

export function extrairNomePng(arquivoPath: string | undefined): string {
  if (!arquivoPath) return "";
  const partes = arquivoPath.replace(/\\/g, "/").split("/");
  return partes[partes.length - 1] || "";
}

interface SpriteThumbProps {
  src: string;
  alt: string;
  frames: number;
  fps: number;
  flip?: boolean;
  className?: string;
}

export function SpriteThumb({
  src,
  alt,
  frames,
  fps,
  flip = false,
  className = "",
}: SpriteThumbProps) {
  const nFrames = Math.max(1, frames || 1);
  const duracao = nFrames / Math.max(1, fps || 8);
  const style = {
    width: `${nFrames * 100}%`,
    maxWidth: "none",
    "--sprite-frames": String(nFrames),
    "--sprite-duracao": `${duracao}s`,
  } as CSSProperties;

  return (
    <div
      className={`overflow-hidden w-full h-full ${flip ? "-scale-x-100" : ""} ${className}`}
    >
      <img
        src={src}
        alt={alt}
        style={style}
        className="h-full object-fill select-none pointer-events-none sprite-strip-anim"
        loading="lazy"
      />
    </div>
  );
}

interface CenaPreviewProps {
  projetoNome: string;
  formato: string;
  cena: CenaItem;
  temImagemFundo: boolean;
  assetsBiblioteca?: BibliotecaAsset[];
  tamanho?: "thumb" | "grande";
  cacheBust?: number;
  onMoverPersonagem?: (x: number, y: number) => void;
  onDropImagem?: (file: File) => void;
  onClick?: () => void;
  title?: string;
}

export function CenaPreview({
  projetoNome,
  formato,
  cena,
  temImagemFundo,
  assetsBiblioteca = [],
  tamanho = "thumb",
  cacheBust,
  onMoverPersonagem,
  onDropImagem,
  onClick,
  title,
}: CenaPreviewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const arrastandoRef = useRef(false);
  const [dragOverImg, setDragOverImg] = useState(false);
  const ehHorizontal = formato === "16:9";
  const nomePng = extrairNomePng(cena.fundo?.arquivo || cena.arquivo);
  const personagem = cena.personagem;
  const temPersonagem =
    Boolean(personagem) &&
    (personagem?.tipo === "pose" || personagem?.tipo === "sprite") &&
    Boolean(personagem?.asset);

  const fonte = personagem?.fonte || "protagonista";
  const assetMeta = temPersonagem
    ? assetsBiblioteca.find(
        (a) => a.id === personagem?.asset && a.fonte === fonte
      )
    : undefined;

  // Mesma proporção usada em template-hyperframes/app.js
  const alturaBasePct = ehHorizontal ? 52 : 34;
  const escalaP = Number(personagem?.escala) > 0 ? Number(personagem?.escala) : 1;
  const alturaPct = alturaBasePct * escalaP;
  const aspectRatio = ehHorizontal ? 16 / 9 : 9 / 16;
  const larguraPct = alturaPct / aspectRatio;
  const pos = personagem?.posicao || "center";
  const temPosLivre =
    typeof personagem?.x === "number" && typeof personagem?.y === "number";

  const posStyle: CSSProperties = {
    height: `${alturaPct}%`,
    width: `${larguraPct}%`,
  };
  if (temPosLivre) {
    posStyle.left = `${personagem?.x}%`;
    posStyle.top = `${personagem?.y}%`;
    posStyle.transform = "translate(-50%, -50%)";
  } else {
    posStyle.bottom = `${-alturaPct * 0.04}%`;
    if (pos === "left" || pos === "bottom-left") {
      posStyle.left = "3%";
    } else if (pos === "right" || pos === "bottom-corner") {
      posStyle.right = "3%";
    } else {
      posStyle.left = "50%";
      posStyle.transform = "translateX(-50%)";
    }
  }

  function calcularEAtualizar(e: PointerEvent<HTMLDivElement>) {
    if (!onMoverPersonagem || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const x = Math.max(0, Math.min(100, ((e.clientX - rect.left) / rect.width) * 100));
    const y = Math.max(0, Math.min(100, ((e.clientY - rect.top) / rect.height) * 100));
    onMoverPersonagem(Number(x.toFixed(1)), Number(y.toFixed(1)));
  }

  const assetUrl =
    temPersonagem && personagem?.asset
      ? api.personagemArquivoUrl(personagem.asset, undefined, fonte)
      : "";

  const isGrande = tamanho === "grande";
  const dimensaoClasse = isGrande
    ? ehHorizontal
      ? "w-full aspect-video"
      : "w-full max-w-[270px] mx-auto aspect-[9/16]"
    : ehHorizontal
    ? "w-36 h-20"
    : "w-20 h-36";

  const podeArrastar = Boolean(onMoverPersonagem && temPersonagem);
  const classBase = `relative overflow-hidden rounded border bg-white checkerboard-dark flex items-center justify-center shrink-0 transition ${dimensaoClasse} ${
    dragOverImg
      ? "border-[#ffc928] ring-2 ring-[#ffc928]/60"
      : "border-slate-700"
  } ${
    podeArrastar
      ? "cursor-grab active:cursor-grabbing select-none touch-none"
      : onClick
      ? "cursor-pointer hover:border-[#ffc928] group"
      : ""
  }`;

  const conteudo = (
    <>
      {/* Fundo */}
      {temImagemFundo ? (
        <div
          className={`absolute inset-0 flex justify-center ${
            !ehHorizontal && temPersonagem
              ? "items-start pt-[7%]"
              : "items-center"
          }`}
        >
          <img
            src={api.imagemCenaUrl(projetoNome, nomePng, cacheBust)}
            alt={nomePng}
            className={
              ehHorizontal
                ? "w-full h-full object-cover select-none pointer-events-none"
                : !ehHorizontal && temPersonagem
                ? "max-w-[84%] max-h-[56%] object-contain select-none pointer-events-none"
                : "max-w-[84%] max-h-[70%] object-contain select-none pointer-events-none"
            }
            loading="lazy"
          />
        </div>
      ) : (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-900/85 text-slate-400 px-2 text-center">
          <span className={isGrande ? "text-xs font-medium" : "text-[9px]"}>
            {isGrande ? "Sem fundo gerado (midia/cenas/)" : "---"}
          </span>
          {isGrande && nomePng && (
            <span className="text-[10px] font-mono text-slate-500 mt-1">
              {nomePng}
            </span>
          )}
        </div>
      )}

      {/* Personagem sobreposto */}
      {temPersonagem && assetUrl && (
        <div
          style={posStyle}
          className={`absolute pointer-events-none z-10 flex items-end justify-center ${
            podeArrastar ? "ring-1 ring-[#ffc928]/60 ring-dashed rounded" : ""
          }`}
        >
          {personagem?.tipo === "sprite" ? (
            <SpriteThumb
              src={assetUrl}
              alt={personagem.asset || "Sprite"}
              frames={personagem.sprite?.frames || assetMeta?.frames || 4}
              fps={personagem.sprite?.fps || assetMeta?.fps || 8}
              flip={Boolean(personagem.flip)}
            />
          ) : (
            <img
              src={assetUrl}
              alt={personagem?.asset || "Personagem"}
              className={`w-full h-full object-contain select-none ${
                personagem?.flip ? "-scale-x-100" : ""
              }`}
              loading="lazy"
            />
          )}
        </div>
      )}
    </>
  );

  const dropHandlers = onDropImagem
    ? {
        onDragOver: (e: React.DragEvent<HTMLElement>) => {
          e.preventDefault();
          setDragOverImg(true);
        },
        onDragLeave: () => setDragOverImg(false),
        onDrop: (e: React.DragEvent<HTMLElement>) => {
          e.preventDefault();
          setDragOverImg(false);
          const file = e.dataTransfer.files?.[0];
          if (file && file.type.startsWith("image/")) {
            onDropImagem(file);
          }
        },
      }
    : {};

  if (onClick && !podeArrastar) {
    return (
      <button type="button" onClick={onClick} title={title} className={classBase} {...dropHandlers}>
        {conteudo}
      </button>
    );
  }

  return (
    <div
      ref={containerRef}
      title={title}
      className={classBase}
      {...dropHandlers}
      onPointerDown={(e) => {
        if (!podeArrastar) return;
        arrastandoRef.current = true;
        e.currentTarget.setPointerCapture(e.pointerId);
        calcularEAtualizar(e);
      }}
      onPointerMove={(e) => {
        if (!arrastandoRef.current) return;
        calcularEAtualizar(e);
      }}
      onPointerUp={(e) => {
        if (!arrastandoRef.current) return;
        arrastandoRef.current = false;
        e.currentTarget.releasePointerCapture(e.pointerId);
      }}
    >
      {conteudo}
    </div>
  );
}
