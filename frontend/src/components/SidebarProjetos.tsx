import { useState, type FormEvent } from "react";
import { FolderPlus, FolderOpen, Film, RefreshCw, Loader2 } from "lucide-react";
import type { ProjetoResumo } from "../types";

interface Props {
  projetos: ProjetoResumo[];
  projetoAtivo: string | null;
  carregando: boolean;
  onSelecionar: (nome: string) => void;
  onCriar: (nome: string) => Promise<void>;
  onRecarregar: () => void;
}

export function SidebarProjetos({
  projetos,
  projetoAtivo,
  carregando,
  onSelecionar,
  onCriar,
  onRecarregar,
}: Props) {
  const [criando, setCriando] = useState(false);
  const [novoNome, setNovoNome] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const hojeSlug = () => {
    const d = new Date();
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    return `${yyyy}-${mm}-novo-video`;
  };

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!novoNome.trim()) return;
    setSubmitting(true);
    setErro(null);
    try {
      await onCriar(novoNome.trim());
      setNovoNome("");
      setCriando(false);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Erro ao criar projeto");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <aside className="w-72 shrink-0 border-r border-slate-800/80 bg-[#10131a] flex flex-col h-full">
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
            <p className="text-[11px] text-slate-400">Studio Local v1.0</p>
          </div>
        </div>
        <button
          type="button"
          onClick={onRecarregar}
          title="Atualizar lista de projetos"
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800/70 transition cursor-pointer"
        >
          <RefreshCw className={`w-4 h-4 ${carregando ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Create Action */}
      <div className="p-3 border-b border-slate-800/60">
        {!criando ? (
          <button
            type="button"
            onClick={() => {
              setNovoNome(hojeSlug());
              setCriando(true);
              setErro(null);
            }}
            className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-[#ffc928] hover:bg-[#ffd452] text-black font-semibold text-xs transition cursor-pointer shadow-sm"
          >
            <FolderPlus className="w-4 h-4" />
            Novo Projeto
          </button>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-2">
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

      {/* Project List */}
      <div className="flex-1 overflow-y-auto p-2.5 space-y-1.5">
        <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          Projetos ({projetos.length})
        </div>

        {projetos.length === 0 && !carregando && (
          <div className="px-3 py-6 text-center text-xs text-slate-500">
            Nenhum projeto encontrado em <code className="text-slate-400">projetos/</code>.
          </div>
        )}

        {projetos.map((p) => {
          const ativo = p.nome === projetoAtivo;
          return (
            <button
              key={p.nome}
              type="button"
              onClick={() => onSelecionar(p.nome)}
              className={`w-full text-left p-2.5 rounded-xl border transition cursor-pointer ${
                ativo
                  ? "bg-[#1a1f2b] border-[#ffc928]/60 shadow-sm"
                  : "bg-transparent border-transparent hover:bg-slate-800/40 hover:border-slate-800"
              }`}
            >
              <div className="flex items-start gap-2">
                {ativo ? (
                  <FolderOpen className="w-4 h-4 text-[#ffc928] shrink-0 mt-0.5" />
                ) : (
                  <Film className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                )}
                <div className="min-w-0 flex-1">
                  <div
                    className={`text-xs font-semibold truncate ${
                      ativo ? "text-slate-100" : "text-slate-300"
                    }`}
                    title={p.nome}
                  >
                    {p.nome}
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
          );
        })}
      </div>
    </aside>
  );
}
