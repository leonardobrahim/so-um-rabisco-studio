import { useEffect, useState } from "react";
import {
  Save,
  Plus,
  Trash2,
  Loader2,
  CheckCircle2,
  Code2,
  Layers,
  FileText,
  Copy,
  Check,
  Wand2,
  ArrowRight,
} from "lucide-react";
import { api } from "../api";
import type { AbaId, CenaItem, CenasConfig, EfeitoCena, ProjetoResumo } from "../types";

interface Props {
  projeto: ProjetoResumo;
  onAtualizado: () => void;
  onIrParaAba: (aba: AbaId) => void;
}

const EFEITOS: EfeitoCena[] = [
  "pop-in",
  "zoom-in",
  "zoom-out",
  "slide-up",
  "shake",
  "cut",
];

function extrairNomePng(arquivoPath: string | undefined): string {
  if (!arquivoPath) return "";
  const partes = arquivoPath.split("/");
  return partes[partes.length - 1] || "";
}

export function TabStoryboard({ projeto, onAtualizado, onIrParaAba }: Props) {
  const [config, setConfig] = useState<CenasConfig | null>(null);
  const [storyboardMd, setStoryboardMd] = useState("");
  const [imagensCenas, setImagensCenas] = useState<Set<string>>(new Set());
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [gerando, setGerando] = useState(false);
  const [modoJson, setModoJson] = useState(false);
  const [jsonTexto, setJsonTexto] = useState("");
  const [mostrarPrompts, setMostrarPrompts] = useState(false);
  const [copiadoIdx, setCopiadoIdx] = useState<number | null>(null);
  const [copiadoTodos, setCopiadoTodos] = useState(false);
  const [mensagem, setMensagem] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    let ativo = true;
    setCarregando(true);
    setMensagem(null);
    setErro(null);

    Promise.all([
      api.lerCenas(projeto.nome),
      api.lerStoryboard(projeto.nome),
      api.listarImagens(projeto.nome),
    ])
      .then(([cenasRes, sbRes, imgRes]) => {
        if (!ativo) return;
        setConfig(cenasRes.dados);
        setJsonTexto(JSON.stringify(cenasRes.dados, null, 2));
        setStoryboardMd(sbRes.conteudo);
        setImagensCenas(new Set(imgRes.cenas));
      })
      .catch((err) => {
        if (!ativo) return;
        setErro(
          err instanceof Error ? err.message : "Erro ao carregar storyboard"
        );
      })
      .finally(() => {
        if (ativo) setCarregando(false);
      });

    return () => {
      ativo = false;
    };
  }, [projeto.nome, projeto.tipo]);

  function atualizarConfig(nova: CenasConfig) {
    setConfig(nova);
    setJsonTexto(JSON.stringify(nova, null, 2));
  }

  function atualizarCena(idx: number, patch: Partial<CenaItem>) {
    if (!config) return;
    const cenas = config.cenas.map((c, i) =>
      i === idx ? { ...c, ...patch } : c
    );
    atualizarConfig({ ...config, cenas });
  }

  function adicionarCena() {
    if (!config) return;
    const ultimoFim =
      config.cenas.length > 0
        ? Number(config.cenas[config.cenas.length - 1].fim) || 0
        : 0;
    const num = String(config.cenas.length + 1).padStart(2, "0");
    const nova: CenaItem = {
      arquivo: `assets_atual/cenas/cena_${num}.png`,
      inicio: Number(ultimoFim.toFixed(2)),
      fim: Number((ultimoFim + 2.0).toFixed(2)),
      efeito: "pop-in",
      texto: "",
      escala: 1.0,
    };
    atualizarConfig({ ...config, cenas: [...config.cenas, nova] });
  }

  function removerCena(idx: number) {
    if (!config) return;
    const cenas = config.cenas.filter((_, i) => i !== idx);
    atualizarConfig({ ...config, cenas });
  }

  async function handleGerarAutomatico() {
    setGerando(true);
    setErro(null);
    setMensagem(null);
    try {
      const res = await api.gerarStoryboard(projeto.nome, projeto.tipo);
      atualizarConfig(res.cenas);
      setStoryboardMd(res.storyboard);
      setModoJson(false);
      setMensagem(
        `Gerado automaticamente a partir de ${
          res.origem === "timestamps" ? "03-timestamps.json" : "02-narracao.txt"
        }: ${res.qtd_cenas} cenas (${res.formato}), prompts_imagens.txt e prompts_flow.txt atualizados!`
      );
      onAtualizado();
    } catch (err) {
      setErro(
        err instanceof Error
          ? err.message
          : "Erro ao gerar storyboard automático"
      );
    } finally {
      setGerando(false);
    }
  }

  async function handleSalvar() {
    if (!config) return;
    setSalvando(true);
    setErro(null);
    setMensagem(null);

    try {
      let dadosParaSalvar = config;
      if (modoJson) {
        dadosParaSalvar = JSON.parse(jsonTexto) as CenasConfig;
        setConfig(dadosParaSalvar);
      }
      const res = await api.salvarCenas(projeto.nome, dadosParaSalvar);
      setMensagem(`cenas.json salvo (${res.qtd_cenas} cenas).`);
      onAtualizado();
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Erro ao salvar cenas.json");
    } finally {
      setSalvando(false);
    }
  }

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
        e.preventDefault();
        void handleSalvar();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  });

  const promptsExtraidos = storyboardMd
    .split(/\r?\n/)
    .filter((line) => /^\[\d{2}:\d{2}\]/.test(line.trim()));

  async function copiarPrompt(texto: string, idx: number) {
    await navigator.clipboard.writeText(texto);
    setCopiadoIdx(idx);
    setTimeout(() => setCopiadoIdx(null), 1500);
  }

  async function copiarTodosPrompts() {
    const conteudo =
      promptsExtraidos.length > 0
        ? promptsExtraidos.join("\n\n")
        : storyboardMd.trim();
    if (!conteudo) return;
    await navigator.clipboard.writeText(conteudo);
    setCopiadoTodos(true);
    setTimeout(() => setCopiadoTodos(false), 2000);
  }

  async function sincronizarArquivoPrompts() {
    setErro(null);
    setMensagem(null);
    try {
      const res = await api.exportarPrompts(projeto.nome);
      setMensagem(
        `${res.arquivo_destino} atualizado com ${res.qtd_prompts} prompt(s) deste projeto.`
      );
    } catch (err) {
      setErro(
        err instanceof Error
          ? err.message
          : "Erro ao atualizar prompts_imagens.txt"
      );
    }
  }

  if (carregando || !config) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400 gap-2 text-sm">
        <Loader2 className="w-4 h-4 animate-spin text-[#ffc928]" />
        Carregando cenas.json...
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Top Config & Actions */}
      <div className="bg-[#141821] border border-slate-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-200 mr-2">
            <Layers className="w-4 h-4 text-[#ffc928]" />
            <span>cenas.json</span>
            <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300">
              {config.cenas.length} cenas
            </span>
          </div>

          <label className="flex items-center gap-1.5 text-xs text-slate-400">
            Formato:
            <select
              value={config.formato || projeto.formato}
              onChange={(e) =>
                atualizarConfig({ ...config, formato: e.target.value })
              }
              className="bg-[#0e1117] border border-slate-700 rounded-lg px-2 py-1 text-slate-100 outline-none focus:border-[#ffc928]"
            >
              <option value="16:9">16:9 (Longo)</option>
              <option value="9:16">9:16 (Short)</option>
            </select>
          </label>

          <label className="flex items-center gap-1.5 text-xs text-slate-400">
            FPS:
            <input
              type="number"
              value={config.fps}
              onChange={(e) =>
                atualizarConfig({ ...config, fps: Number(e.target.value) || 30 })
              }
              className="w-16 bg-[#0e1117] border border-slate-700 rounded-lg px-2 py-1 text-slate-100 outline-none focus:border-[#ffc928]"
            />
          </label>

          <label className="flex items-center gap-1.5 text-xs text-slate-400">
            Duração (s):
            <input
              type="number"
              step="0.01"
              value={config.duracao_total}
              onChange={(e) =>
                atualizarConfig({
                  ...config,
                  duracao_total: Number(e.target.value) || 0,
                })
              }
              className="w-24 bg-[#0e1117] border border-slate-700 rounded-lg px-2 py-1 text-slate-100 outline-none focus:border-[#ffc928]"
            />
          </label>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => void handleGerarAutomatico()}
            disabled={gerando}
            title="Gera cenas.json, prompts e storyboard automaticamente a partir do áudio ou roteiro salvo"
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-emerald-500/15 border border-emerald-500/40 hover:bg-emerald-500/25 disabled:opacity-50 text-emerald-300 text-xs font-semibold transition cursor-pointer"
          >
            {gerando ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Wand2 className="w-3.5 h-3.5" />
            )}
            Gerar do Áudio/Roteiro
          </button>

          <button
            type="button"
            onClick={() => setMostrarPrompts((v) => !v)}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-lg border text-xs font-medium transition cursor-pointer ${
              mostrarPrompts
                ? "bg-[#ffc928]/15 border-[#ffc928]/50 text-[#ffc928]"
                : "bg-[#0e1117] border-slate-700 text-slate-300 hover:border-slate-600"
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            Prompts ({promptsExtraidos.length})
          </button>

          {promptsExtraidos.length > 0 && (
            <>
              <button
                type="button"
                onClick={() => void copiarTodosPrompts()}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-slate-700 bg-[#0e1117] hover:border-[#ffc928]/60 text-slate-200 text-xs font-medium transition cursor-pointer"
              >
                {copiadoTodos ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                    Copiados!
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5 text-[#ffc928]" />
                    Copiar Todos
                  </>
                )}
              </button>
              <button
                type="button"
                onClick={() => void sincronizarArquivoPrompts()}
                title="Substitui o arquivo prompts_imagens.txt na raiz pelos prompts deste projeto"
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-slate-700 bg-[#0e1117] hover:border-[#ffc928]/60 text-slate-200 text-xs font-medium transition cursor-pointer"
              >
                <FileText className="w-3.5 h-3.5 text-[#ffc928]" />
                Atualizar prompts_imagens.txt
              </button>
            </>
          )}

          <button
            type="button"
            onClick={() => setModoJson((v) => !v)}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-lg border text-xs font-medium transition cursor-pointer ${
              modoJson
                ? "bg-[#ffc928]/15 border-[#ffc928]/50 text-[#ffc928]"
                : "bg-[#0e1117] border-slate-700 text-slate-300 hover:border-slate-600"
            }`}
          >
            <Code2 className="w-3.5 h-3.5" />
            {modoJson ? "Editor Visual" : "JSON Raw"}
          </button>

          {!modoJson && (
            <button
              type="button"
              onClick={adicionarCena}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-100 text-xs font-medium transition cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              Cena
            </button>
          )}

          <button
            type="button"
            onClick={() => void handleSalvar()}
            disabled={salvando}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#ffc928] hover:bg-[#ffd452] disabled:opacity-50 text-black text-xs font-semibold transition cursor-pointer"
          >
            {salvando ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Save className="w-3.5 h-3.5" />
            )}
            Salvar (Ctrl+S)
          </button>

          <button
            type="button"
            onClick={() => onIrParaAba("imagens")}
            className="flex items-center gap-1 px-3 py-2 rounded-lg border border-slate-700 hover:border-[#ffc928]/60 text-slate-200 text-xs font-medium transition cursor-pointer"
          >
            Imagens <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {erro && (
        <div className="px-4 py-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
          {erro}
        </div>
      )}

      {mensagem && (
        <div className="px-4 py-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{mensagem}</span>
        </div>
      )}

      {/* Prompts Drawer */}
      {mostrarPrompts && (
        <div className="bg-[#141821] border border-slate-800 rounded-xl p-4 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Prompts de 04-storyboard-e-prompts.md ({projeto.formato})
            </h4>
            <div className="flex items-center gap-3">
              <span className="text-[11px] text-slate-500">
                Clique para copiar individual ou todos de uma vez
              </span>
              {promptsExtraidos.length > 0 && (
                <button
                  type="button"
                  onClick={() => void copiarTodosPrompts()}
                  className="px-2.5 py-1 rounded bg-[#ffc928] hover:bg-[#ffd452] text-black font-semibold text-xs flex items-center gap-1.5 cursor-pointer transition"
                >
                  {copiadoTodos ? (
                    <>
                      <Check className="w-3.5 h-3.5" /> Copiados ({promptsExtraidos.length})
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" /> Copiar Todos ({promptsExtraidos.length})
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
          {promptsExtraidos.length === 0 ? (
            <pre className="max-h-56 overflow-y-auto text-xs text-slate-300 whitespace-pre-wrap bg-[#0e1117] p-3 rounded-lg border border-slate-800">
              {storyboardMd || "Arquivo 04-storyboard-e-prompts.md vazio."}
            </pre>
          ) : (
            <div className="max-h-60 overflow-y-auto space-y-2 pr-1">
              {promptsExtraidos.map((p, idx) => (
                <div
                  key={idx}
                  className="bg-[#0e1117] border border-slate-800 rounded-lg p-2.5 flex items-start justify-between gap-3 text-xs"
                >
                  <p className="text-slate-300 leading-relaxed line-clamp-2">{p}</p>
                  <button
                    type="button"
                    onClick={() => void copiarPrompt(p, idx)}
                    className="shrink-0 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 flex items-center gap-1 cursor-pointer"
                  >
                    {copiadoIdx === idx ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-400" /> Copiado
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" /> Copiar
                      </>
                    )}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Main Editor */}
      {modoJson ? (
        <textarea
          value={jsonTexto}
          onChange={(e) => setJsonTexto(e.target.value)}
          spellCheck={false}
          className="min-h-[520px] w-full bg-[#12151d] border border-slate-800 focus:border-[#ffc928] rounded-xl p-4 font-mono text-xs text-slate-200 outline-none resize-y"
        />
      ) : config.cenas.length === 0 ? (
        <div className="bg-[#141821] border border-slate-800 rounded-xl p-10 text-center space-y-4">
          <div className="space-y-1">
            <p className="text-sm font-semibold text-slate-200">
              Nenhuma cena gerada ainda para este projeto
            </p>
            <p className="text-xs text-slate-400">
              {projeto.tem_timestamps
                ? "O áudio já foi transcrito! Clique abaixo para decupar automaticamente em cenas e prompts."
                : projeto.tem_narracao
                ? "O roteiro já está salvo! Clique abaixo para gerar uma decupagem estimada ou envie o áudio na aba Áudio."
                : "Salve o roteiro na aba 1 ou envie o áudio na aba 2 para gerar tudo automaticamente."}
            </p>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-3">
            {(projeto.tem_timestamps || projeto.tem_narracao) && (
              <button
                type="button"
                onClick={() => void handleGerarAutomatico()}
                disabled={gerando}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#ffc928] hover:bg-[#ffd452] text-black text-xs font-bold cursor-pointer"
              >
                {gerando ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Wand2 className="w-4 h-4" />
                )}
                Gerar Cenas & Prompts Automaticamente ({projeto.formato})
              </button>
            )}
            <button
              type="button"
              onClick={adicionarCena}
              className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              Adicionar Cena Manual
            </button>
          </div>
        </div>
      ) : (
        <div className="bg-[#141821] border border-slate-800 rounded-xl overflow-hidden">
          <div className="overflow-x-auto max-h-[560px] overflow-y-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="bg-[#0e1117] text-slate-400 uppercase text-[10px] tracking-wider sticky top-0 z-10 border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3 w-10">#</th>
                  <th className="py-2.5 px-3 w-16">Preview</th>
                  <th className="py-2.5 px-3">Arquivo</th>
                  <th className="py-2.5 px-3 w-24">Início (s)</th>
                  <th className="py-2.5 px-3 w-24">Fim (s)</th>
                  <th className="py-2.5 px-3 w-20">Dur.</th>
                  <th className="py-2.5 px-3 w-32">Efeito</th>
                  <th className="py-2.5 px-3">Texto de Impacto</th>
                  <th className="py-2.5 px-3 w-20">Escala</th>
                  <th className="py-2.5 px-3 w-12"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/70">
                {config.cenas.map((cena, idx) => {
                  const nomePng = extrairNomePng(cena.arquivo);
                  const temImagem = imagensCenas.has(nomePng);
                  const inicio = Number(cena.inicio) || 0;
                  const fim = Number(cena.fim) || 0;
                  const dur = Math.max(0, fim - inicio);
                  const textoStr = cena.texto ?? "";
                  const qtdPalavras = textoStr.trim()
                    ? textoStr.trim().split(/\s+/).length
                    : 0;

                  return (
                    <tr
                      key={idx}
                      className="hover:bg-slate-800/30 transition-colors"
                    >
                      <td className="py-2 px-3 font-mono text-slate-500">
                        {String(idx + 1).padStart(2, "0")}
                      </td>
                      <td className="py-2 px-3">
                        <div
                          className={`${
                            projeto.tipo === "short" ? "w-8 h-12" : "w-12 h-8"
                          } rounded border border-slate-700 overflow-hidden checkerboard-dark flex items-center justify-center`}
                        >
                          {temImagem ? (
                            <img
                              src={api.imagemCenaUrl(projeto.nome, nomePng)}
                              alt={nomePng}
                              className="w-full h-full object-contain"
                              loading="lazy"
                            />
                          ) : (
                            <span className="text-[9px] text-slate-500">---</span>
                          )}
                        </div>
                      </td>
                      <td className="py-2 px-3">
                        <input
                          type="text"
                          value={cena.arquivo ?? ""}
                          onChange={(e) =>
                            atualizarCena(idx, { arquivo: e.target.value })
                          }
                          className="w-full min-w-[190px] bg-[#0e1117] border border-slate-800 focus:border-[#ffc928] rounded px-2 py-1 font-mono text-[11px] text-slate-200 outline-none"
                        />
                      </td>
                      <td className="py-2 px-3">
                        <input
                          type="number"
                          step="0.01"
                          value={inicio}
                          onChange={(e) =>
                            atualizarCena(idx, {
                              inicio: Number(e.target.value) || 0,
                            })
                          }
                          className="w-20 bg-[#0e1117] border border-slate-800 focus:border-[#ffc928] rounded px-2 py-1 font-mono text-slate-200 outline-none"
                        />
                      </td>
                      <td className="py-2 px-3">
                        <input
                          type="number"
                          step="0.01"
                          value={fim}
                          onChange={(e) =>
                            atualizarCena(idx, {
                              fim: Number(e.target.value) || 0,
                            })
                          }
                          className="w-20 bg-[#0e1117] border border-slate-800 focus:border-[#ffc928] rounded px-2 py-1 font-mono text-slate-200 outline-none"
                        />
                      </td>
                      <td className="py-2 px-3 font-mono text-slate-400">
                        {dur.toFixed(2)}s
                      </td>
                      <td className="py-2 px-3">
                        <select
                          value={cena.efeito || "pop-in"}
                          onChange={(e) =>
                            atualizarCena(idx, { efeito: e.target.value })
                          }
                          className="w-full bg-[#0e1117] border border-slate-800 focus:border-[#ffc928] rounded px-2 py-1 text-slate-200 outline-none"
                        >
                          {EFEITOS.map((ef) => (
                            <option key={ef} value={ef}>
                              {ef}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="py-2 px-3">
                        <input
                          type="text"
                          value={textoStr}
                          onChange={(e) =>
                            atualizarCena(idx, { texto: e.target.value })
                          }
                          placeholder="Opcional (máx 3 palavras)"
                          className={`w-full min-w-[150px] bg-[#0e1117] border rounded px-2 py-1 text-slate-200 outline-none ${
                            qtdPalavras > 3
                              ? "border-amber-500/60"
                              : "border-slate-800 focus:border-[#ffc928]"
                          }`}
                        />
                      </td>
                      <td className="py-2 px-3">
                        <input
                          type="number"
                          step="0.1"
                          value={cena.escala ?? 1}
                          onChange={(e) =>
                            atualizarCena(idx, {
                              escala: Number(e.target.value) || 1,
                            })
                          }
                          className="w-16 bg-[#0e1117] border border-slate-800 focus:border-[#ffc928] rounded px-2 py-1 font-mono text-slate-200 outline-none"
                        />
                      </td>
                      <td className="py-2 px-3 text-right">
                        <button
                          type="button"
                          onClick={() => removerCena(idx)}
                          title="Remover cena"
                          className="p-1.5 rounded text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 cursor-pointer"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
