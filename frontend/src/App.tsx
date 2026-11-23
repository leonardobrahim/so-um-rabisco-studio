import { useCallback, useEffect, useState } from "react";
import {
  FileText,
  Mic,
  Clapperboard,
  Images,
  Smartphone,
  Film,
  AlertTriangle,
} from "lucide-react";
import { api } from "./api";
import type { AbaId, ProjetoResumo, ProjetoTipo } from "./types";
import { SidebarProjetos } from "./components/SidebarProjetos";
import { TabRoteiro } from "./components/TabRoteiro";
import { TabAudio } from "./components/TabAudio";
import { TabStoryboard } from "./components/TabStoryboard";
import { TabImagens } from "./components/TabImagens";
import { TabThumbRender } from "./components/TabThumbRender";

const ABAS: { id: AbaId; label: string; icon: typeof FileText }[] = [
  { id: "roteiro", label: "1. Roteiro", icon: FileText },
  { id: "audio", label: "2. Áudio", icon: Mic },
  { id: "storyboard", label: "3. Storyboard", icon: Clapperboard },
  { id: "imagens", label: "4. Imagens", icon: Images },
  { id: "thumb-render", label: "5. Thumb / Render", icon: Smartphone },
];

export function App() {
  const [projetos, setProjetos] = useState<ProjetoResumo[]>([]);
  const [projetoAtivoNome, setProjetoAtivoNome] = useState<string | null>(null);
  const [abaAtiva, setAbaAtiva] = useState<AbaId>("roteiro");
  const [carregando, setCarregando] = useState(true);
  const [trocandoTipo, setTrocandoTipo] = useState(false);
  const [erroApi, setErroApi] = useState<string | null>(null);

  const carregarProjetos = useCallback(async (selecionarNome?: string) => {
    setCarregando(true);
    setErroApi(null);
    try {
      const res = await api.listarProjetos();
      setProjetos(res.projetos);
      setProjetoAtivoNome((atual) => {
        if (selecionarNome) return selecionarNome;
        if (atual && res.projetos.some((p) => p.nome === atual)) return atual;
        return res.projetos[0]?.nome ?? null;
      });
    } catch (err) {
      setErroApi(
        err instanceof Error
          ? err.message
          : "Não foi possível conectar ao backend FastAPI (porta 8000)."
      );
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    void carregarProjetos();
  }, [carregarProjetos]);

  async function handleCriarProjeto(nome: string, tipo: ProjetoTipo) {
    const res = await api.criarProjeto(nome, tipo);
    await carregarProjetos(res.projeto.nome);
    setAbaAtiva("roteiro");
  }

  async function handleAlterarTipo(tipo: ProjetoTipo) {
    if (!projetoAtivo || projetoAtivo.tipo === tipo) return;
    setTrocandoTipo(true);
    try {
      await api.atualizarMeta(projetoAtivo.nome, { tipo });
      await carregarProjetos(projetoAtivo.nome);
    } catch (err) {
      setErroApi(
        err instanceof Error ? err.message : "Erro ao alterar tipo do projeto"
      );
    } finally {
      setTrocandoTipo(false);
    }
  }

  const projetoAtivo =
    projetos.find((p) => p.nome === projetoAtivoNome) ?? null;

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#0b0d12] text-slate-100">
      <SidebarProjetos
        projetos={projetos}
        projetoAtivo={projetoAtivoNome}
        carregando={carregando}
        onSelecionar={(nome) => setProjetoAtivoNome(nome)}
        onCriar={handleCriarProjeto}
        onRecarregar={() => void carregarProjetos()}
      />

      <main className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
        {/* Top Bar */}
        <header className="border-b border-slate-800/80 bg-[#10131a]/90 px-6 pt-4 pb-0 shrink-0">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
            <div className="min-w-0">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                Projeto Ativo
              </span>
              <h2 className="text-lg font-bold text-slate-100 truncate">
                {projetoAtivo ? projetoAtivo.nome : "Nenhum projeto selecionado"}
              </h2>
            </div>

            {projetoAtivo && (
              <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
                {/* Seletor Longo vs Short */}
                <div className="flex items-center bg-[#0b0d12] p-0.5 rounded-lg border border-slate-800">
                  <button
                    type="button"
                    disabled={trocandoTipo}
                    onClick={() => void handleAlterarTipo("longo")}
                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold transition cursor-pointer ${
                      projetoAtivo.tipo === "longo"
                        ? "bg-[#ffc928] text-black"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <Film className="w-3.5 h-3.5" />
                    Vídeo Longo (16:9)
                  </button>
                  <button
                    type="button"
                    disabled={trocandoTipo}
                    onClick={() => void handleAlterarTipo("short")}
                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold transition cursor-pointer ${
                      projetoAtivo.tipo === "short"
                        ? "bg-purple-500 text-white"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <Smartphone className="w-3.5 h-3.5" />
                    Short (9:16)
                  </button>
                </div>

                {projetoAtivo.duracao_total ? (
                  <span className="px-2.5 py-1.5 rounded-lg bg-[#181d27] border border-slate-800">
                    Duração:{" "}
                    <strong className="text-slate-200">
                      {projetoAtivo.duracao_total}s
                    </strong>
                  </span>
                ) : null}
              </div>
            )}
          </div>

          {/* 5 Abas */}
          <nav className="flex gap-1 overflow-x-auto">
            {ABAS.map((aba) => {
              const Icon = aba.icon;
              const ativa = aba.id === abaAtiva;
              return (
                <button
                  key={aba.id}
                  type="button"
                  disabled={!projetoAtivo}
                  onClick={() => setAbaAtiva(aba.id)}
                  className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition whitespace-nowrap cursor-pointer disabled:opacity-40 ${
                    ativa
                      ? "border-[#ffc928] text-[#ffc928] bg-[#ffc928]/5 rounded-t-lg"
                      : "border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/30 rounded-t-lg"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {aba.label}
                </button>
              );
            })}
          </nav>
        </header>

        {/* Workspace Content */}
        <section className="flex-1 overflow-y-auto p-6">
          {erroApi && (
            <div className="mb-5 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 shrink-0 text-rose-400" />
              <div>
                <div className="font-semibold">Erro de conexão com o backend</div>
                <div className="text-rose-300/80 mt-0.5">
                  {erroApi} — Verifique se o servidor FastAPI está rodando em{" "}
                  <code>http://localhost:8000</code>.
                </div>
              </div>
            </div>
          )}

          {!projetoAtivo ? (
            <div className="h-full flex items-center justify-center text-center">
              <div className="max-w-md space-y-2">
                <p className="text-sm font-semibold text-slate-300">
                  Selecione ou crie um projeto na barra lateral
                </p>
                <p className="text-xs text-slate-500">
                  Separe vídeos longos (16:9) de Shorts (9:16) e conecte roteiro,
                  áudio, storyboard, imagens e preview automaticamente.
                </p>
              </div>
            </div>
          ) : (
            <>
              {abaAtiva === "roteiro" && (
                <TabRoteiro
                  projeto={projetoAtivo}
                  onAtualizado={() => void carregarProjetos(projetoAtivo.nome)}
                  onIrParaAba={setAbaAtiva}
                />
              )}
              {abaAtiva === "audio" && (
                <TabAudio
                  projeto={projetoAtivo}
                  onAtualizado={() => void carregarProjetos(projetoAtivo.nome)}
                  onIrParaAba={setAbaAtiva}
                />
              )}
              {abaAtiva === "storyboard" && (
                <TabStoryboard
                  projeto={projetoAtivo}
                  onAtualizado={() => void carregarProjetos(projetoAtivo.nome)}
                  onIrParaAba={setAbaAtiva}
                />
              )}
              {abaAtiva === "imagens" && (
                <TabImagens
                  projeto={projetoAtivo}
                  onAtualizado={() => void carregarProjetos(projetoAtivo.nome)}
                  onIrParaAba={setAbaAtiva}
                />
              )}
              {abaAtiva === "thumb-render" && (
                <TabThumbRender
                  projeto={projetoAtivo}
                  onAtualizado={() => void carregarProjetos(projetoAtivo.nome)}
                />
              )}
            </>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
