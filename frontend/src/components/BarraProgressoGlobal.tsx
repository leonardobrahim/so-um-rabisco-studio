import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { Loader2, ArrowUpRight } from "lucide-react";
import type { AbaId } from "../types";

export interface TarefaProgresso {
  id: string;
  titulo: string;
  etapa: string;
  progresso: number;
  projetoNome: string;
  aba?: AbaId;
}

interface IniciarEstimadoOpts {
  id: string;
  titulo: string;
  etapa: string;
  projetoNome: string;
  aba?: AbaId;
  duracaoEstimadaMs?: number;
}

interface ProgressoContextValue {
  tarefas: TarefaProgresso[];
  definirTarefa: (tarefa: TarefaProgresso) => void;
  removerTarefa: (id: string) => void;
  iniciarTarefaEstimada: (opts: IniciarEstimadoOpts) => () => void;
}

const ProgressoContext = createContext<ProgressoContextValue | null>(null);

export function ProgressoProvider({ children }: { children: ReactNode }) {
  const [tarefas, setTarefas] = useState<TarefaProgresso[]>([]);
  const timersRef = useRef<Record<string, number>>({});

  const limparTimer = useCallback((id: string) => {
    const t = timersRef.current[id];
    if (t) {
      window.clearInterval(t);
      delete timersRef.current[id];
    }
  }, []);

  const definirTarefa = useCallback((tarefa: TarefaProgresso) => {
    setTarefas((prev) => {
      const idx = prev.findIndex((item) => item.id === tarefa.id);
      const normalizada: TarefaProgresso = {
        ...tarefa,
        progresso: Math.max(0, Math.min(100, Math.round(tarefa.progresso))),
      };
      if (idx === -1) return [...prev, normalizada];
      const copia = [...prev];
      copia[idx] = normalizada;
      return copia;
    });
  }, []);

  const removerTarefa = useCallback(
    (id: string) => {
      limparTimer(id);
      setTarefas((prev) => prev.filter((item) => item.id !== id));
    },
    [limparTimer]
  );

  const iniciarTarefaEstimada = useCallback(
    ({
      id,
      titulo,
      etapa,
      projetoNome,
      aba,
      duracaoEstimadaMs = 15000,
    }: IniciarEstimadoOpts) => {
      limparTimer(id);
      const inicio = Date.now();
      definirTarefa({
        id,
        titulo,
        etapa,
        progresso: 5,
        projetoNome,
        aba,
      });

      const timer = window.setInterval(() => {
        const decorrido = Date.now() - inicio;
        // Curva assintótica suave até 92% para nunca travar nem ultrapassar antes da resposta real
        const fracao = 1 - Math.exp((-2.4 * decorrido) / Math.max(2000, duracaoEstimadaMs));
        const pct = Math.min(92, Math.max(5, Math.round(5 + fracao * 87)));
        definirTarefa({
          id,
          titulo,
          etapa,
          progresso: pct,
          projetoNome,
          aba,
        });
      }, 300);
      timersRef.current[id] = timer;

      return () => {
        limparTimer(id);
        setTarefas((prev) => prev.filter((item) => item.id !== id));
      };
    },
    [definirTarefa, limparTimer]
  );

  useEffect(() => {
    return () => {
      Object.values(timersRef.current).forEach((t) => window.clearInterval(t));
    };
  }, []);

  return (
    <ProgressoContext.Provider
      value={{ tarefas, definirTarefa, removerTarefa, iniciarTarefaEstimada }}
    >
      {children}
    </ProgressoContext.Provider>
  );
}

export function useProgresso() {
  const ctx = useContext(ProgressoContext);
  if (!ctx) {
    throw new Error("useProgresso deve ser usado dentro de ProgressoProvider");
  }
  return ctx;
}

export function BarraProgressoGlobal({
  onIrParaAba,
}: {
  onIrParaAba: (aba: AbaId) => void;
}) {
  const { tarefas } = useProgresso();
  if (tarefas.length === 0) return null;

  return (
    <div className="bg-[#121620] border-b border-slate-800 px-6 py-2.5 space-y-2 shrink-0">
      {tarefas.map((t) => (
        <div
          key={t.id}
          className="bg-[#0b0d12] border border-amber-500/30 rounded-lg px-3 py-2 flex flex-col gap-1.5"
        >
          <div className="flex items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2 min-w-0">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-[#ffc928] shrink-0" />
              <span className="font-semibold text-slate-100 truncate">
                {t.titulo}
              </span>
              <span className="text-[11px] text-slate-400 truncate hidden sm:inline">
                • {t.etapa}
              </span>
            </div>
            <div className="flex items-center gap-2.5 shrink-0">
              <span className="font-mono font-bold text-[#ffc928]">
                {t.progresso}%
              </span>
              {t.aba && (
                <button
                  type="button"
                  onClick={() => onIrParaAba(t.aba!)}
                  className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] text-slate-200 flex items-center gap-1 cursor-pointer"
                  title="Ir para a aba desta geração"
                >
                  Abrir <ArrowUpRight className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>
          <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-[#ffc928] transition-all duration-300"
              style={{ width: `${Math.max(3, Math.min(100, t.progresso))}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

export function BarraProgressoInline({
  titulo,
  etapa,
  progresso,
}: {
  titulo: string;
  etapa?: string;
  progresso: number;
}) {
  return (
    <div className="px-3.5 py-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs space-y-1.5">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0 text-[#ffc928]" />
          <span className="font-semibold truncate">{titulo}</span>
          {etapa && (
            <span className="text-[11px] text-amber-300/80 truncate hidden sm:inline">
              • {etapa}
            </span>
          )}
        </div>
        <span className="font-mono font-bold text-[#ffc928] shrink-0">
          {Math.max(0, Math.min(100, Math.round(progresso)))}%
        </span>
      </div>
      <div className="w-full h-1.5 bg-black/40 rounded-full overflow-hidden">
        <div
          className="h-full bg-[#ffc928] transition-all duration-300"
          style={{ width: `${Math.max(3, Math.min(100, progresso))}%` }}
        />
      </div>
    </div>
  );
}
