import { useState, type FormEvent } from "react";
import {
  FolderPlus,
  FolderOpen,
  Film,
  Smartphone,
  RefreshCw,
  Loader2,
  Trash2,
  AlertTriangle,
  Pencil,
  Check,
  X,
  PanelLeftClose,
} from "lucide-react";
import type { ProjetoResumo, ProjetoTipo } from "../types";

interface Props {
  projetos: ProjetoResumo[];
  projetoAtivo: string | null;
  carregando: boolean;
  onSelecionar: (nome: string) => void;
  onCriar: (nome: string, tipo: ProjetoTipo) => Promise<void>;
  onRenomear: (nomeAntigo: string, novoNome: string) => Promise<void>;
  onExcluir: (nome: string) => Promise<void>;
  onRecarregar: () => void;
  onFechar?: () => void;
}

export function SidebarProjetos({
  projetos,
  projetoAtivo,
  carregando,
  onSelecionar,
  onCriar,
  onRenomear,
  onExcluir,
  onRecarregar,
  onFechar,
}: Props) {
  const [criando, setCriando] = useState(false);
  const [novoNome, setNovoNome] = useState("");
  const [novoTipo, setNovoTipo] = useState<ProjetoTipo>("longo");
  const [filtroTipo, setFiltroTipo] = useState<"todos" | ProjetoTipo>("todos");
  const [submitting, setSubmitting] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [confirmandoExclusao, setConfirmandoExclusao] = useState<string | null>(null);
  const [excluindo, setExcluindo] = useState(false);
  const [erroExclusao, setErroExclusao] = useState<string | null>(null);
  const [editandoNome, setEditandoNome] = useState<string | null>(null);
  const [nomeEditDraft, setNomeEditDraft] = useState("");
  const [renomeando, setRenomeando] = useState(false);

  const hojeSlug = (tipo: ProjetoTipo) => {
    const d = new Date();
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    return tipo === "short"
      ? `${yyyy}-${mm}-short-novo`
      : `${yyyy}-${mm}-novo-video`;
  };

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!novoNome.trim()) return;
    setSubmitting(true);
    setErro(null);
    try {
      await onCriar(novoNome.trim(), novoTipo);
      setNovoNome("");
      setCriando(false);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Erro ao criar projeto");
    } finally {
      setSubmitting(false);
    }
  }

  const projetosFiltrados = projetos.filter((p) =>
    filtroTipo === "todos" ? true : p.tipo === filtroTipo
  );

  const totalLongos = projetos.filter((p) => p.tipo === "longo").length;
  const totalShorts = projetos.filter((p) => p.tipo === "short").length;

  async function confirmarExcluir() {
    if (!confirmandoExclusao) return;
    setExcluindo(true);
    setErroExclusao(null);
    try {
      await onExcluir(confirmandoExclusao);
      setConfirmandoExclusao(null);
    } catch (err) {
      setErroExclusao(
        err instanceof Error ? err.message : "Erro ao excluir projeto"
      );
    } finally {
      setExcluindo(false);
    }
  }

  return (
    <aside className="w-76 shrink-0 border-r border-slate-800/80 bg-[#10131a] flex flex-col h-full">
      {/* Brand */}
      <div className="px-4 py-4 border-b border-slate-800/80 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-[#ffc928] text-black flex items-center justify-center font-black text-sm shadow-sm">
            SR
          </div>
          <div>
            <h1 className="text-sm font-bold text-slate-100 leading-tight">
              Só um Rabisco
            </h1>
            <p className="text-[11px] text-slate-400">Studio Local v1.1</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={onRecarregar}
            title="Atualizar lista de projetos"
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800/70 transition cursor-pointer"
          >
            <RefreshCw className={`w-4 h-4 ${carregando ? "animate-spin" : ""}`} />
          </button>
          {onFechar && (
            <button
              type="button"
              onClick={onFechar}
              title="Recolher menu lateral"
              className="p-1.5 rounded-lg text-slate-400 hover:text-[#ffc928] hover:bg-slate-800/70 transition cursor-pointer"
            >
              <PanelLeftClose className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Create Action */}
      <div className="p-3 border-b border-slate-800/60">
        {!criando ? (
          <button
            type="button"
            onClick={() => {
              setNovoTipo("longo");
              setNovoNome(hojeSlug("longo"));
              setCriando(true);
              setErro(null);
            }}
            className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-[#ffc928] hover:bg-[#ffd452] text-black font-semibold text-xs transition cursor-pointer shadow-sm"
          >
            <FolderPlus className="w-4 h-4" />
            Novo Projeto
          </button>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-2.5">
            {/* Tipo do Projeto */}
            <div className="grid grid-cols-2 gap-1 bg-[#0b0d12] p-1 rounded-lg border border-slate-800">
              <button
                type="button"
                onClick={() => {
                  setNovoTipo("longo");
                  if (novoNome === hojeSlug("short")) {
                    setNovoNome(hojeSlug("longo"));
                  }
                }}
                className={`flex items-center justify-center gap-1 py-1.5 rounded text-[11px] font-semibold cursor-pointer transition ${
                  novoTipo === "longo"
                    ? "bg-[#ffc928] text-black"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Film className="w-3 h-3" /> Longo (16:9)
              </button>
              <button
                type="button"
                onClick={() => {
                  setNovoTipo("short");
                  if (novoNome === hojeSlug("longo")) {
                    setNovoNome(hojeSlug("short"));
                  }
                }}
                className={`flex items-center justify-center gap-1 py-1.5 rounded text-[11px] font-semibold cursor-pointer transition ${
                  novoTipo === "short"
                    ? "bg-purple-500 text-white"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Smartphone className="w-3 h-3" /> Short (9:16)
              </button>
            </div>

            <input
              type="text"
              value={novoNome}
              onChange={(e) => setNovoNome(e.target.value)}
              placeholder="Ex: 2026-11-tema-video"
              autoFocus
              className="w-full bg-[#0b0d12] border border-slate-700 focus:border-[#ffc928] rounded-lg px-2.5 py-1.5 text-xs text-slate-100 outline-none"
            />
            {erro && <p className="text-[11px] text-rose-400">{erro}</p>}
            <div className="flex gap-1.5">
              <button
                type="submit"
                disabled={submitting || !novoNome.trim()}
                className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-[#ffc928] hover:bg-[#ffd452] disabled:opacity-50 text-black font-semibold text-xs cursor-pointer"
              >
                {submitting && <Loader2 className="w-3 h-3 animate-spin" />}
                Criar
              </button>
              <button
                type="button"
                onClick={() => setCriando(false)}
                className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs cursor-pointer"
              >
                Cancelar
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Filtro Longos vs Shorts */}
      <div className="px-3 pt-2.5 pb-1">
        <div className="grid grid-cols-3 gap-1 bg-[#0b0d12] p-1 rounded-lg border border-slate-800/80 text-[11px] font-semibold">
          <button
            type="button"
            onClick={() => setFiltroTipo("todos")}
            className={`py-1 rounded transition cursor-pointer ${
              filtroTipo === "todos"
                ? "bg-slate-800 text-slate-100"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Todos ({projetos.length})
          </button>
          <button
            type="button"
            onClick={() => setFiltroTipo("longo")}
            className={`py-1 rounded transition cursor-pointer ${
              filtroTipo === "longo"
                ? "bg-[#ffc928]/20 text-[#ffc928]"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Longos ({totalLongos})
          </button>
          <button
            type="button"
            onClick={() => setFiltroTipo("short")}
            className={`py-1 rounded transition cursor-pointer ${
              filtroTipo === "short"
                ? "bg-purple-500/20 text-purple-300"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Shorts ({totalShorts})
          </button>
        </div>
      </div>

      {/* Project List */}
      <div className="flex-1 overflow-y-auto p-2.5 space-y-1.5">
        {projetosFiltrados.length === 0 && !carregando && (
          <div className="px-3 py-6 text-center text-xs text-slate-500">
            Nenhum projeto{" "}
            {filtroTipo === "longo"
              ? "longo"
              : filtroTipo === "short"
              ? "short"
              : ""}{" "}
            encontrado.
          </div>
        )}

        {projetosFiltrados.map((p) => {
          const ativo = p.nome === projetoAtivo;
          const isShort = p.tipo === "short";
          return (
            <div key={p.nome}>
            <div
              className={`group relative flex items-stretch rounded-xl border transition ${
                ativo
                  ? isShort
                    ? "bg-[#1a1829] border-purple-500/60 shadow-sm"
                    : "bg-[#1a1f2b] border-[#ffc928]/60 shadow-sm"
                  : "bg-transparent border-transparent hover:bg-slate-800/40 hover:border-slate-800"
              }`}
            >
              <button
                type="button"
                onClick={() => onSelecionar(p.nome)}
                className="flex-1 min-w-0 text-left p-2.5 pr-1 cursor-pointer"
              >
                <div className="flex items-start gap-2">
                  {ativo ? (
                    <FolderOpen
                      className={`w-4 h-4 shrink-0 mt-0.5 ${
                        isShort ? "text-purple-400" : "text-[#ffc928]"
                      }`}
                    />
                  ) : isShort ? (
                    <Smartphone className="w-4 h-4 text-purple-400/70 shrink-0 mt-0.5" />
                  ) : (
                    <Film className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                  )}
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-1.5">
                      <div
                        className={`text-xs font-semibold truncate ${
                          ativo ? "text-slate-100" : "text-slate-300"
                        }`}
                        title={p.nome}
                      >
                        {p.nome}
                      </div>
                      <span
                        className={`shrink-0 text-[9px] font-bold px-1.5 py-0.5 rounded uppercase ${
                          isShort
                            ? "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                            : "bg-[#ffc928]/15 text-[#ffc928] border border-[#ffc928]/30"
                        }`}
                      >
                        {isShort ? "9:16" : "16:9"}
                      </span>
                    </div>
                    <div className="mt-1.5 flex flex-wrap gap-1">
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                          p.tem_narracao
                            ? "bg-emerald-500/15 text-emerald-400"
                            : "bg-slate-800 text-slate-500"
                        }`}
                      >
                        Txt
                      </span>
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                          p.tem_audio
                            ? "bg-sky-500/15 text-sky-400"
                            : "bg-slate-800 text-slate-500"
                        }`}
                      >
                        Áudio
                      </span>
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                          p.tem_cenas_json
                            ? "bg-[#ffc928]/15 text-[#ffc928]"
                            : "bg-slate-800 text-slate-500"
                        }`}
                      >
                        {p.qtd_cenas_json > 0 ? `${p.qtd_cenas_json} cenas` : "JSON"}
                      </span>
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                          p.qtd_imagens_cenas > 0
                            ? "bg-purple-500/15 text-purple-300"
                            : "bg-slate-800 text-slate-500"
                        }`}
                      >
                        {p.qtd_imagens_cenas} png
                      </span>
                    </div>
                  </div>
                </div>
              </button>
              <button
                type="button"
                onClick={() => {
                  setEditandoNome(p.nome);
                  setNomeEditDraft(p.nome);
                  setErro(null);
                }}
                title={`Renomear projeto "${p.nome}"`}
                className="px-1.5 flex items-center justify-center text-slate-500 hover:text-[#ffc928] hover:bg-slate-800/70 opacity-60 group-hover:opacity-100 transition cursor-pointer shrink-0"
              >
                <Pencil className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={() => {
                  setErroExclusao(null);
                  setConfirmandoExclusao(p.nome);
                }}
                title={`Excluir projeto "${p.nome}"`}
                className="px-2 flex items-center justify-center text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-r-xl opacity-60 group-hover:opacity-100 transition cursor-pointer shrink-0"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
            {editandoNome === p.nome && (
              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  if (!nomeEditDraft.trim()) return;
                  setRenomeando(true);
                  setErro(null);
                  try {
                    await onRenomear(p.nome, nomeEditDraft);
                    setEditandoNome(null);
                  } catch (err) {
                    setErro(err instanceof Error ? err.message : "Erro ao renomear");
                  } finally {
                    setRenomeando(false);
                  }
                }}
                className="mt-1 mb-1 px-2 flex items-center gap-1"
              >
                <input
                  type="text"
                  value={nomeEditDraft}
                  onChange={(e) => setNomeEditDraft(e.target.value)}
                  autoFocus
                  disabled={renomeando}
                  className="flex-1 min-w-0 bg-[#0b0d12] border border-[#ffc928] rounded px-2 py-1 text-[11px] text-slate-100 outline-none"
                />
                <button
                  type="submit"
                  disabled={renomeando}
                  className="p-1 rounded bg-[#ffc928] text-black cursor-pointer"
                  title="Salvar"
                >
                  <Check className="w-3 h-3" />
                </button>
                <button
                  type="button"
                  disabled={renomeando}
                  onClick={() => setEditandoNome(null)}
                  className="p-1 rounded bg-slate-800 text-slate-300 cursor-pointer"
                  title="Cancelar"
                >
                  <X className="w-3 h-3" />
                </button>
              </form>
            )}
            </div>
          );
        })}
      </div>

      {confirmandoExclusao && (
        <div
          className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={(e) => {
            if (!excluindo && e.target === e.currentTarget) {
              setConfirmandoExclusao(null);
            }
          }}
        >
          <div className="bg-[#141821] border border-slate-700 rounded-2xl w-full max-w-md p-5 space-y-4 shadow-2xl">
            <div className="flex items-start gap-3">
              <div className="w-9 h-9 rounded-xl bg-rose-500/15 border border-rose-500/30 flex items-center justify-center shrink-0">
                <AlertTriangle className="w-5 h-5 text-rose-400" />
              </div>
              <div className="space-y-1 min-w-0">
                <h3 className="text-sm font-bold text-slate-100">
                  Excluir projeto
                </h3>
                <p className="text-xs text-slate-300 leading-relaxed">
                  Tem certeza que deseja excluir o projeto{" "}
                  <strong className="text-white break-all">
                    &ldquo;{confirmandoExclusao}&rdquo;
                  </strong>
                  ?
                </p>
                <p className="text-[11px] text-rose-300/90 leading-relaxed">
                  Esta ação apaga permanentemente a pasta do projeto e todos os
                  seus arquivos (roteiro, áudio, imagens e vídeo renderizado).
                </p>
              </div>
            </div>

            {erroExclusao && (
              <div className="px-3 py-2 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
                {erroExclusao}
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-1">
              <button
                type="button"
                disabled={excluindo}
                onClick={() => setConfirmandoExclusao(null)}
                className="px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-xs font-medium cursor-pointer"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={excluindo}
                onClick={() => void confirmarExcluir()}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white text-xs font-semibold cursor-pointer"
              >
                {excluindo ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Trash2 className="w-3.5 h-3.5" />
                )}
                Excluir definitivamente
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
