import { useMemo, useState } from "react";
import {
  X,
  Search,
  Sparkles,
  FlipHorizontal2,
  Tag,
  Check,
  Loader2,
  UserX,
  Film,
  Image as ImageIcon,
} from "lucide-react";
import { api } from "../api";
import type {
  BibliotecaAsset,
  BibliotecaPasta,
  BibliotecaPersonagem,
  CenaItem,
  CenaPersonagem,
  PersonagemAnimacao,
  PersonagemPosicao,
} from "../types";
import { CenaPreview, SpriteThumb } from "./CenaPreview";

export const POSICOES_PERSONAGEM: { value: PersonagemPosicao; label: string }[] = [
  { value: "center", label: "Centro" },
  { value: "left", label: "Esquerda" },
  { value: "right", label: "Direita" },
  { value: "bottom-corner", label: "Canto Dir." },
  { value: "bottom-left", label: "Canto Esq." },
];

export const ANIMACOES_PERSONAGEM: {
  value: PersonagemAnimacao;
  label: string;
}[] = [
  { value: "pop-in", label: "pop-in (salto)" },
  { value: "slide-in-left", label: "slide-in-left" },
  { value: "slide-in-right", label: "slide-in-right" },
  { value: "float", label: "float (flutuar)" },
  { value: "bounce", label: "bounce (quicar)" },
  { value: "shake", label: "shake (tremer)" },
  { value: "none", label: "none (parado)" },
];

interface Props {
  projetoNome: string;
  formato: string;
  indiceCena: number;
  cena: CenaItem;
  temImagemFundo: boolean;
  biblioteca: BibliotecaPersonagem;
  onAtualizarCena: (patch: Partial<CenaItem>) => void;
  onBibliotecaAtualizada: (nova: BibliotecaPersonagem) => void;
  onFechar: () => void;
}

export function PersonagemPicker({
  projetoNome,
  formato,
  indiceCena,
  cena,
  temImagemFundo,
  biblioteca,
  onAtualizarCena,
  onBibliotecaAtualizada,
  onFechar,
}: Props) {
  const [busca, setBusca] = useState("");
  const [filtroTipo, setFiltroTipo] = useState<"todos" | "pose" | "sprite">(
    "todos"
  );
  const [editandoTagsId, setEditandoTagsId] = useState<string | null>(null);
  const [tagsDraft, setTagsDraft] = useState("");
  const [editandoPasta, setEditandoPasta] = useState<BibliotecaPasta | null>(
    null
  );
  const [pastaTagsDraft, setPastaTagsDraft] = useState("");
  const [pastaFpsDraft, setPastaFpsDraft] = useState(8);
  const [pastaModoDraft, setPastaModoDraft] = useState<"poses" | "sprite">(
    "poses"
  );
  const [salvandoMeta, setSalvandoMeta] = useState(false);
  const [erroMeta, setErroMeta] = useState<string | null>(null);

  const personagemAtual: CenaPersonagem = cena.personagem ?? {
    tipo: "none",
    fonte: "protagonista",
  };

  function atualizarPersonagem(patch: Partial<CenaPersonagem>) {
    onAtualizarCena({
      personagem: {
        ...personagemAtual,
        ...patch,
      },
    });
  }

  function selecionarAsset(asset: BibliotecaAsset) {
    const proximo: CenaPersonagem = {
      tipo: asset.tipo,
      fonte: asset.fonte,
      asset: asset.id,
      posicao: personagemAtual.posicao || (formato === "16:9" ? "right" : "center"),
      escala: personagemAtual.escala ?? 1.0,
      flip: personagemAtual.flip ?? false,
      animacao:
        personagemAtual.animacao ||
        (asset.tipo === "sprite" ? "slide-in-left" : "pop-in"),
      tags: personagemAtual.tags ?? [],
    };
    if (asset.tipo === "sprite") {
      proximo.sprite = {
        frames: asset.frames,
        quadro: asset.quadro,
        fps: asset.fps,
      };
    }
    onAtualizarCena({ personagem: proximo });
  }

  function removerPersonagem() {
    onAtualizarCena({
      personagem: {
        tipo: "none",
        fonte: personagemAtual.fonte || "protagonista",
        tags: personagemAtual.tags ?? [],
      },
    });
  }

  const assetsFiltrados = useMemo(() => {
    const q = busca.trim().toLowerCase();
    return biblioteca.assets.filter((a) => {
      if (filtroTipo !== "todos" && a.tipo !== filtroTipo) return false;
      if (!q) return true;
      const texto = [a.id, a.pasta, a.arquivo, ...a.tags]
        .join(" ")
        .toLowerCase();
      return texto.includes(q);
    });
  }, [biblioteca.assets, busca, filtroTipo]);

  function abrirEdicaoTagsAsset(asset: BibliotecaAsset) {
    setErroMeta(null);
    setEditandoPasta(null);
    setEditandoTagsId(asset.id);
    setTagsDraft(asset.tags_proprias.join(", "));
  }

  async function salvarTagsAsset(asset: BibliotecaAsset) {
    setSalvandoMeta(true);
    setErroMeta(null);
    try {
      const lista = tagsDraft
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      const res = await api.atualizarBibliotecaPersonagem(
        asset.pasta,
        { tags: { [asset.arquivo]: lista } },
        asset.fonte
      );
      onBibliotecaAtualizada({ pastas: res.pastas, assets: res.assets });
      setEditandoTagsId(null);
    } catch (err) {
      setErroMeta(
        err instanceof Error ? err.message : "Erro ao salvar tags do asset"
      );
    } finally {
      setSalvandoMeta(false);
    }
  }

  function abrirEdicaoPasta(pasta: BibliotecaPasta) {
    setErroMeta(null);
    setEditandoTagsId(null);
    setEditandoPasta(pasta);
    setPastaTagsDraft(pasta.tags_pasta.join(", "));
    setPastaFpsDraft(pasta.fps);
    setPastaModoDraft(pasta.modo);
  }

  async function salvarPasta() {
    if (!editandoPasta) return;
    setSalvandoMeta(true);
    setErroMeta(null);
    try {
      const tagsPasta = pastaTagsDraft
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
      const res = await api.atualizarBibliotecaPersonagem(
        editandoPasta.pasta,
        {
          modo: pastaModoDraft,
          fps: Number(pastaFpsDraft) || 8,
          tags_pasta: tagsPasta,
        },
        editandoPasta.fonte
      );
      onBibliotecaAtualizada({ pastas: res.pastas, assets: res.assets });
      setEditandoPasta(null);
    } catch (err) {
      setErroMeta(
        err instanceof Error ? err.message : "Erro ao salvar pasta da biblioteca"
      );
    } finally {
      setSalvandoMeta(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onFechar();
      }}
    >
      <div className="bg-[#141821] border border-slate-700 rounded-2xl w-full max-w-6xl max-h-[92vh] flex flex-col overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-slate-800 flex items-center justify-between gap-3 bg-[#0e1117]">
          <div className="min-w-0">
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#ffc928]" />
              Cena {String(indiceCena + 1).padStart(2, "0")} — Camada do
              Personagem ({formato})
            </h3>
            {cena.texto && (
              <p className="text-xs text-slate-400 truncate mt-0.5">
                Fala: &ldquo;{cena.texto}&rdquo;
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onFechar}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto grid grid-cols-1 lg:grid-cols-12 gap-5 p-5">
          {/* Coluna Esquerda: Preview Composto + Ajustes */}
          <div className="lg:col-span-5 flex flex-col gap-4">
            <div className="bg-[#0e1117] border border-slate-800 rounded-xl p-3">
              <CenaPreview
                projetoNome={projetoNome}
                formato={formato}
                cena={cena}
                temImagemFundo={temImagemFundo}
                assetsBiblioteca={biblioteca.assets}
                tamanho="grande"
              />
            </div>

            <div className="bg-[#0e1117] border border-slate-800 rounded-xl p-4 space-y-3 text-xs">
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold text-slate-200">
                  Camada atual:{" "}
                  <span className="text-[#ffc928] font-mono">
                    {personagemAtual.tipo === "none"
                      ? "Sem personagem (só fundo)"
                      : personagemAtual.asset || "nenhum"}
                  </span>
                </span>
                {personagemAtual.tipo !== "none" && (
                  <button
                    type="button"
                    onClick={removerPersonagem}
                    className="flex items-center gap-1 px-2 py-1 rounded bg-rose-500/15 border border-rose-500/30 text-rose-300 hover:bg-rose-500/25 cursor-pointer text-[11px]"
                  >
                    <UserX className="w-3 h-3" />
                    Remover
                  </button>
                )}
              </div>

              {personagemAtual.tipo !== "none" && (
                <>
                  {/* Posição */}
                  <div className="space-y-1.5">
                    <span className="text-[11px] text-slate-400 block">
                      Posição na tela
                    </span>
                    <div className="grid grid-cols-5 gap-1">
                      {POSICOES_PERSONAGEM.map((p) => {
                        const ativo =
                          (personagemAtual.posicao || "center") === p.value;
                        return (
                          <button
                            key={p.value}
                            type="button"
                            onClick={() =>
                              atualizarPersonagem({ posicao: p.value })
                            }
                            className={`px-1.5 py-1.5 rounded-lg border text-[11px] font-medium transition cursor-pointer ${
                              ativo
                                ? "bg-[#ffc928] border-[#ffc928] text-black font-semibold"
                                : "bg-[#141821] border-slate-800 text-slate-300 hover:border-slate-600"
                            }`}
                          >
                            {p.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Escala + Flip */}
                  <div className="grid grid-cols-12 gap-3 items-center">
                    <label className="col-span-8 space-y-1">
                      <span className="text-[11px] text-slate-400 flex justify-between">
                        <span>Escala do personagem</span>
                        <strong className="text-slate-200 font-mono">
                          {(personagemAtual.escala ?? 1).toFixed(2)}x
                        </strong>
                      </span>
                      <input
                        type="range"
                        min={0.4}
                        max={1.6}
                        step={0.05}
                        value={personagemAtual.escala ?? 1}
                        onChange={(e) =>
                          atualizarPersonagem({
                            escala: Number(e.target.value) || 1,
                          })
                        }
                        className="w-full accent-[#ffc928]"
                      />
                    </label>
                    <div className="col-span-4 flex justify-end pt-3">
                      <button
                        type="button"
                        onClick={() =>
                          atualizarPersonagem({ flip: !personagemAtual.flip })
                        }
                        className={`w-full flex items-center justify-center gap-1.5 px-2.5 py-2 rounded-lg border text-xs font-medium cursor-pointer ${
                          personagemAtual.flip
                            ? "bg-[#ffc928]/15 border-[#ffc928]/60 text-[#ffc928]"
                            : "bg-[#141821] border-slate-800 text-slate-300 hover:border-slate-600"
                        }`}
                      >
                        <FlipHorizontal2 className="w-3.5 h-3.5" />
                        Espelhar
                      </button>
                    </div>
                  </div>

                  {/* Animação GSAP */}
                  <label className="block space-y-1">
                    <span className="text-[11px] text-slate-400">
                      Animação do personagem (GSAP)
                    </span>
                    <select
                      value={personagemAtual.animacao || "pop-in"}
                      onChange={(e) =>
                        atualizarPersonagem({
                          animacao: e.target.value as PersonagemAnimacao,
                        })
                      }
                      className="w-full bg-[#141821] border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 outline-none focus:border-[#ffc928]"
                    >
                      {ANIMACOES_PERSONAGEM.map((a) => (
                        <option key={a.value} value={a.value}>
                          {a.label}
                        </option>
                      ))}
                    </select>
                  </label>

                  {/* FPS do sprite, quando aplicável */}
                  {personagemAtual.tipo === "sprite" && (
                    <label className="block space-y-1">
                      <span className="text-[11px] text-slate-400">
                        Velocidade do sprite nesta cena (FPS)
                      </span>
                      <input
                        type="number"
                        min={1}
                        max={30}
                        value={personagemAtual.sprite?.fps ?? 8}
                        onChange={(e) =>
                          atualizarPersonagem({
                            sprite: {
                              frames: personagemAtual.sprite?.frames ?? 4,
                              quadro: personagemAtual.sprite?.quadro ?? 512,
                              fps: Math.max(1, Number(e.target.value) || 8),
                            },
                          })
                        }
                        className="w-24 bg-[#141821] border border-slate-700 rounded-lg px-2.5 py-1.5 font-mono text-slate-200 outline-none focus:border-[#ffc928]"
                      />
                    </label>
                  )}
                </>
              )}

              {(cena.fundo?.prompt || cena.prompt) && (
                <div className="pt-2 border-t border-slate-800 space-y-1">
                  <span className="text-[10px] uppercase tracking-wider text-slate-500">
                    Prompt do fundo
                  </span>
                  <p className="text-[11px] text-slate-400 leading-relaxed max-h-24 overflow-y-auto">
                    {cena.fundo?.prompt || cena.prompt}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Coluna Direita: Biblioteca de Poses / Sprites + Editor de Tags */}
          <div className="lg:col-span-7 flex flex-col gap-3">
            {/* Barra de busca e filtro */}
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative flex-1 min-w-[180px]">
                <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={busca}
                  onChange={(e) => setBusca(e.target.value)}
                  placeholder="Filtrar por tag (ansioso, feliz, andar...) ou pasta"
                  className="w-full bg-[#0e1117] border border-slate-800 focus:border-[#ffc928] rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 outline-none"
                />
              </div>

              <div className="flex items-center bg-[#0e1117] border border-slate-800 rounded-lg p-0.5 text-xs">
                {(
                  [
                    { id: "todos", label: "Todos" },
                    { id: "pose", label: "Poses" },
                    { id: "sprite", label: "Sprites" },
                  ] as const
                ).map((f) => (
                  <button
                    key={f.id}
                    type="button"
                    onClick={() => setFiltroTipo(f.id)}
                    className={`px-2.5 py-1 rounded-md font-medium cursor-pointer transition ${
                      filtroTipo === f.id
                        ? "bg-[#ffc928] text-black font-semibold"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Pastas da biblioteca (tags de pasta / modo / fps) */}
            {biblioteca.pastas.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                <span className="text-slate-500 mr-1">Pastas (meta.json):</span>
                {biblioteca.pastas.map((p) => (
                  <button
                    key={`${p.fonte}:${p.pasta}`}
                    type="button"
                    onClick={() => abrirEdicaoPasta(p)}
                    className="px-2 py-0.5 rounded bg-[#0e1117] border border-slate-800 hover:border-[#ffc928]/60 text-slate-300 flex items-center gap-1 cursor-pointer"
                    title="Editar modo, FPS e tags da pasta"
                  >
                    {p.modo === "sprite" ? (
                      <Film className="w-3 h-3 text-purple-300" />
                    ) : (
                      <ImageIcon className="w-3 h-3 text-emerald-300" />
                    )}
                    <span className="truncate max-w-[160px]">{p.pasta}</span>
                    {p.tags_pasta.length > 0 && (
                      <span className="text-slate-500">
                        ({p.tags_pasta.length})
                      </span>
                    )}
                  </button>
                ))}
              </div>
            )}

            {editandoPasta && (
              <div className="bg-[#0e1117] border border-[#ffc928]/40 rounded-xl p-3 space-y-2.5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-200">
                    Configurar pasta:{" "}
                    <code className="text-[#ffc928]">{editandoPasta.pasta}</code>
                  </span>
                  <button
                    type="button"
                    onClick={() => setEditandoPasta(null)}
                    className="text-slate-400 hover:text-slate-200 cursor-pointer"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-12 gap-2">
                  <label className="sm:col-span-3 space-y-1">
                    <span className="text-[11px] text-slate-400">Modo</span>
                    <select
                      value={pastaModoDraft}
                      onChange={(e) =>
                        setPastaModoDraft(e.target.value as "poses" | "sprite")
                      }
                      className="w-full bg-[#141821] border border-slate-700 rounded px-2 py-1 text-slate-200"
                    >
                      <option value="poses">poses (frames)</option>
                      <option value="sprite">sprite (strip)</option>
                    </select>
                  </label>
                  <label className="sm:col-span-2 space-y-1">
                    <span className="text-[11px] text-slate-400">FPS</span>
                    <input
                      type="number"
                      min={1}
                      max={30}
                      value={pastaFpsDraft}
                      onChange={(e) =>
                        setPastaFpsDraft(Number(e.target.value) || 8)
                      }
                      className="w-full bg-[#141821] border border-slate-700 rounded px-2 py-1 text-slate-200 font-mono"
                    />
                  </label>
                  <label className="sm:col-span-7 space-y-1">
                    <span className="text-[11px] text-slate-400">
                      Tags da pasta (separadas por vírgula)
                    </span>
                    <input
                      type="text"
                      value={pastaTagsDraft}
                      onChange={(e) => setPastaTagsDraft(e.target.value)}
                      placeholder="andar, caminhar, correr"
                      className="w-full bg-[#141821] border border-slate-700 rounded px-2 py-1 text-slate-200"
                    />
                  </label>
                </div>
                <div className="flex justify-end">
                  <button
                    type="button"
                    disabled={salvandoMeta}
                    onClick={() => void salvarPasta()}
                    className="px-3 py-1 rounded bg-[#ffc928] hover:bg-[#ffd452] disabled:opacity-50 text-black font-semibold flex items-center gap-1 cursor-pointer"
                  >
                    {salvandoMeta ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <Check className="w-3 h-3" />
                    )}
                    Salvar meta.json
                  </button>
                </div>
              </div>
            )}

            {erroMeta && (
              <div className="px-3 py-2 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
                {erroMeta}
              </div>
            )}

            {/* Grade da biblioteca */}
            {assetsFiltrados.length === 0 ? (
              <div className="bg-[#0e1117] border border-slate-800 rounded-xl p-8 text-center text-xs text-slate-400 space-y-2">
                <p>
                  Nenhum asset encontrado em{" "}
                  <code>assets/personagem/sprites_output/</code>.
                </p>
                <p className="text-[11px] text-slate-500">
                  Coloque suas grades 2×2 em{" "}
                  <code>assets/personagem/grades_input/</code> e rode{" "}
                  <code>python scripts/cortar_sprites.py --poses</code>.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 max-h-[460px] overflow-y-auto pr-1">
                {assetsFiltrados.map((asset) => {
                  const selecionado =
                    personagemAtual.tipo !== "none" &&
                    personagemAtual.asset === asset.id &&
                    (personagemAtual.fonte || "protagonista") === asset.fonte;
                  const assetUrl = api.personagemArquivoUrl(
                    asset.pasta,
                    asset.arquivo,
                    asset.fonte
                  );
                  const editandoEste = editandoTagsId === asset.id;

                  return (
                    <div
                      key={`${asset.fonte}:${asset.id}`}
                      className={`rounded-xl border overflow-hidden flex flex-col bg-[#0e1117] transition ${
                        selecionado
                          ? "border-[#ffc928] ring-1 ring-[#ffc928]/60"
                          : "border-slate-800 hover:border-slate-600"
                      }`}
                    >
                      <button
                        type="button"
                        onClick={() => selecionarAsset(asset)}
                        className="relative aspect-square checkerboard-dark p-2 flex items-center justify-center cursor-pointer"
                        title={`Selecionar ${asset.id}`}
                      >
                        {asset.tipo === "sprite" ? (
                          <SpriteThumb
                            src={assetUrl}
                            alt={asset.id}
                            frames={asset.frames}
                            fps={asset.fps}
                          />
                        ) : (
                          <img
                            src={assetUrl}
                            alt={asset.id}
                            className="w-full h-full object-contain select-none"
                            loading="lazy"
                          />
                        )}
                        <span
                          className={`absolute top-1.5 left-1.5 px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${
                            asset.tipo === "sprite"
                              ? "bg-purple-500/80 text-white"
                              : "bg-slate-900/85 text-slate-200 border border-slate-700"
                          }`}
                        >
                          {asset.tipo === "sprite"
                            ? `sprite ${asset.frames}f`
                            : "pose"}
                        </span>
                        {selecionado && (
                          <span className="absolute top-1.5 right-1.5 w-5 h-5 rounded-full bg-[#ffc928] text-black flex items-center justify-center">
                            <Check className="w-3 h-3" />
                          </span>
                        )}
                      </button>

                      <div className="p-2 border-t border-slate-800/80 space-y-1.5 text-[11px]">
                        <div className="flex items-center justify-between gap-1">
                          <span
                            className="font-mono text-slate-300 truncate"
                            title={asset.id}
                          >
                            {asset.arquivo}
                          </span>
                          <button
                            type="button"
                            onClick={() =>
                              editandoEste
                                ? setEditandoTagsId(null)
                                : abrirEdicaoTagsAsset(asset)
                            }
                            title="Editar tags deste asset"
                            className="p-1 rounded text-slate-400 hover:text-[#ffc928] hover:bg-slate-800 shrink-0 cursor-pointer"
                          >
                            <Tag className="w-3 h-3" />
                          </button>
                        </div>
                        <div
                          className="text-[10px] text-slate-500 truncate"
                          title={asset.pasta}
                        >
                          {asset.pasta}
                        </div>

                        {editandoEste ? (
                          <div className="space-y-1.5 pt-1">
                            <input
                              type="text"
                              value={tagsDraft}
                              onChange={(e) => setTagsDraft(e.target.value)}
                              placeholder="ansioso, medo, choque"
                              className="w-full bg-[#141821] border border-slate-700 focus:border-[#ffc928] rounded px-1.5 py-1 text-[10px] text-slate-200 outline-none"
                            />
                            <div className="flex justify-end gap-1">
                              <button
                                type="button"
                                onClick={() => setEditandoTagsId(null)}
                                className="px-1.5 py-0.5 rounded text-[10px] text-slate-400 hover:text-slate-200 cursor-pointer"
                              >
                                Cancelar
                              </button>
                              <button
                                type="button"
                                disabled={salvandoMeta}
                                onClick={() => void salvarTagsAsset(asset)}
                                className="px-2 py-0.5 rounded bg-[#ffc928] text-black font-semibold text-[10px] cursor-pointer"
                              >
                                Salvar
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div className="flex flex-wrap gap-1 min-h-[18px]">
                            {asset.tags.length === 0 ? (
                              <span className="text-[10px] text-slate-600 italic">
                                sem tags
                              </span>
                            ) : (
                              asset.tags.slice(0, 4).map((t) => (
                                <span
                                  key={t}
                                  className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[9px]"
                                >
                                  {t}
                                </span>
                              ))
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-slate-800 bg-[#0e1117] flex items-center justify-between text-xs text-slate-400">
          <span>
            Lembre de salvar o <code>cenas.json</code> (Ctrl+S) após ajustar as
            cenas.
          </span>
          <button
            type="button"
            onClick={onFechar}
            className="px-4 py-1.5 rounded-lg bg-[#ffc928] hover:bg-[#ffd452] text-black font-semibold cursor-pointer"
          >
            Concluir
          </button>
        </div>
      </div>
    </div>
  );
}
