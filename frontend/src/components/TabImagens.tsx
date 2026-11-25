import { useEffect, useRef, useState, type DragEvent } from "react";
import {
  ImagePlus,
  Loader2,
  Sparkles,
  CheckCircle2,
  Trash2,
  Images,
  ArrowLeft,
  ArrowRight,
  Copy,
  Check,
  Cpu,
  Play,
  Square,
  RefreshCw,
  SlidersHorizontal,
  Upload,
} from "lucide-react";
import { api } from "../api";
import type {
  AbaId,
  CenaItem,
  ComfyJobStatus,
  ComfyStatus,
  ProjetoResumo,
} from "../types";
import { useProgresso } from "./BarraProgressoGlobal";

interface Props {
  projeto: ProjetoResumo;
  onAtualizado: () => void;
  onIrParaAba: (aba: AbaId) => void;
}

export function TabImagens({ projeto, onAtualizado, onIrParaAba }: Props) {
  const { iniciarTarefaEstimada } = useProgresso();
  const [fila, setFila] = useState<File[]>([]);
  const [cenasProntas, setCenasProntas] = useState<string[]>([]);
  const [rawArquivos, setRawArquivos] = useState<string[]>([]);
  const [promptsCount, setPromptsCount] = useState(0);
  const [promptsTexto, setPromptsTexto] = useState("");
  const [copiado, setCopiado] = useState(false);
  const [limparAnteriores, setLimparAnteriores] = useState(true);
  const [carregando, setCarregando] = useState(true);
  const [processando, setProcessando] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [cacheBust, setCacheBust] = useState(() => Date.now());
  const [log, setLog] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  // Integração ComfyUI
  const [comfyStatus, setComfyStatus] = useState<ComfyStatus | null>(null);
  const [comfyJob, setComfyJob] = useState<ComfyJobStatus | null>(null);
  const [ckptSelecionado, setCkptSelecionado] = useState("");
  const [steps, setSteps] = useState(5);
  const [cfg, setCfg] = useState(2.0);
  const [resolucao, setResolucao] = useState("1024x576");
  const [samplerName, setSamplerName] = useState("dpmpp_sde");
  const [scheduler, setScheduler] = useState("karras");
  const [negativoExtra, setNegativoExtra] = useState("");
  const [seedInput, setSeedInput] = useState("");
  const [workflowJsonTexto, setWorkflowJsonTexto] = useState("");
  const [mostrarAvancadoComfy, setMostrarAvancadoComfy] = useState(false);
  const [mostrarComfyui, setMostrarComfyui] = useState(false);
  const [verificandoComfy, setVerificandoComfy] = useState(false);
  const [cenasStoryboard, setCenasStoryboard] = useState<CenaItem[]>([]);
  const [substituindoCena, setSubstituindoCena] = useState<string | null>(null);
  const [dragCardNome, setDragCardNome] = useState<string | null>(null);
  const [cardArrastadoOrdem, setCardArrastadoOrdem] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const ultimasConcluidasRef = useRef<number>(0);
  const cardHoverNomeRef = useRef<string | null>(null);
  const [previewsFila, setPreviewsFila] = useState<string[]>([]);

  useEffect(() => {
    const urls = fila.map((f) => URL.createObjectURL(f));
    setPreviewsFila(urls);
    return () => {
      urls.forEach((u) => URL.revokeObjectURL(u));
    };
  }, [fila]);

  const isShort = projeto.tipo === "short";

  function aplicarPresetCheckpoint(ckpt: string, shortMode: boolean) {
    const low = ckpt.toLowerCase();
    if (low.includes("lightning")) {
      setSteps(5);
      setCfg(2.0);
      setSamplerName("dpmpp_sde");
      setScheduler("karras");
      setResolucao(shortMode ? "576x1024" : "1024x576");
    } else if (low.includes("xl")) {
      setSteps(20);
      setCfg(6.5);
      setSamplerName("dpmpp_2m");
      setScheduler("karras");
      setResolucao(shortMode ? "576x1024" : "1024x576");
    } else {
      setSteps(22);
      setCfg(7.0);
      setSamplerName("dpmpp_2m");
      setScheduler("karras");
      setResolucao(shortMode ? "512x912" : "912x512");
    }
  }

  async function verificarComfyui() {
    setVerificandoComfy(true);
    try {
      const st = await api.comfyuiStatus();
      setComfyStatus(st);
      if (st.online && st.checkpoint_padrao) {
        setCkptSelecionado((atual) => {
          const escolhido =
            atual && st.checkpoints.includes(atual) ? atual : st.checkpoint_padrao || "";
          if (!atual && escolhido) {
            aplicarPresetCheckpoint(escolhido, isShort);
          }
          return escolhido;
        });
      }
    } catch {
      setComfyStatus(null);
    } finally {
      setVerificandoComfy(false);
    }
  }

  async function carregarDados() {
    setCarregando(true);
    try {
      const [imgRes, sbRes, cenasRes] = await Promise.all([
        api.listarImagens(projeto.nome),
        api.lerStoryboard(projeto.nome),
        api.lerCenas(projeto.nome).catch(() => null),
      ]);
      setCenasProntas(imgRes.cenas);
      setRawArquivos(imgRes.raw);
      setCenasStoryboard(cenasRes?.dados?.cenas || []);
      const linhas = sbRes.conteudo
        .split(/\r?\n/)
        .filter((l) => /^\[\d{2}:\d{2}\]/.test(l.trim()));
      setPromptsCount(linhas.length);
      setPromptsTexto(linhas.join("\n\n"));
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Erro ao listar imagens");
    } finally {
      setCarregando(false);
    }
  }

  async function substituirImagemCena(nomePng: string, file: File | undefined) {
    if (!file || !file.type.startsWith("image/")) return;
    setSubstituindoCena(nomePng);
    setErro(null);
    try {
      const res = await api.uploadImagemCena(projeto.nome, nomePng, file);
      setCenasProntas(res.cenas_geradas);
      setCacheBust(Date.now());
      setLog(`Imagem '${res.arquivo}' atualizada diretamente em midia/cenas/.`);
      onAtualizado();
    } catch (err) {
      setErro(
        err instanceof Error ? err.message : `Erro ao enviar ${nomePng}`
      );
    } finally {
      setSubstituindoCena(null);
    }
  }

  async function reordenarCenaPara(nomeOrigem: string, novaPosicaoIdx: number) {
    const listaAtual = [...cenasProntas];
    const idxAtual = listaAtual.indexOf(nomeOrigem);
    if (idxAtual < 0 || novaPosicaoIdx < 0 || novaPosicaoIdx >= listaAtual.length || idxAtual === novaPosicaoIdx) {
      return;
    }
    const [removido] = listaAtual.splice(idxAtual, 1);
    listaAtual.splice(novaPosicaoIdx, 0, removido);
    setErro(null);
    try {
      const res = await api.reordenarImagens(projeto.nome, listaAtual);
      setCenasProntas(res.cenas_geradas);
      setCacheBust(Date.now());
      setLog("Ordem das cenas atualizada e arquivos renomeados.");
      onAtualizado();
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Erro ao reordenar cenas");
    }
  }

  async function handleExcluirCena(nomePng: string) {
    if (!window.confirm(`Excluir a cena "${nomePng}" e renumerar as seguintes?`)) {
      return;
    }
    setErro(null);
    try {
      const res = await api.excluirImagemCena(projeto.nome, nomePng);
      setCenasProntas(res.cenas_geradas);
      setCacheBust(Date.now());
      await carregarDados();
      setLog(`Cena '${nomePng}' excluída e sequência atualizada.`);
      onAtualizado();
    } catch (err) {
      setErro(err instanceof Error ? err.message : `Erro ao excluir ${nomePng}`);
    }
  }

  useEffect(() => {
    setFila([]);
    setLog(null);
    setErro(null);
    ultimasConcluidasRef.current = 0;
    void carregarDados();
    void verificarComfyui();
    void api
      .comfyuiJobStatus(projeto.nome)
      .then((j) => setComfyJob(j))
      .catch(() => {});
  }, [projeto.nome, projeto.tipo]);

  useEffect(() => {
    if (!comfyJob || comfyJob.status !== "running") return;
    const timer = window.setInterval(async () => {
      try {
        const j = await api.comfyuiJobStatus(projeto.nome);
        setComfyJob(j);
        if (j.concluidas > ultimasConcluidasRef.current || j.status !== "running") {
          ultimasConcluidasRef.current = j.concluidas;
          setCacheBust(Date.now());
          const imgRes = await api.listarImagens(projeto.nome);
          setCenasProntas(imgRes.cenas);
          setRawArquivos(imgRes.raw);
          if (j.status === "done") {
            onAtualizado();
          }
        }
      } catch {
        // ignora falha pontual de polling
      }
    }, 1200);
    return () => window.clearInterval(timer);
  }, [comfyJob?.status, projeto.nome]);

  async function dispararComfyui(opcoes: {
    apenasFaltantes?: boolean;
    indiceCena?: number;
  }) {
    setErro(null);
    setLog(null);
    let workflowApi: Record<string, unknown> | undefined;
    if (workflowJsonTexto.trim()) {
      try {
        workflowApi = JSON.parse(workflowJsonTexto) as Record<string, unknown>;
      } catch {
        setErro("O JSON do Workflow API customizado é inválido.");
        return;
      }
    }

    const [wStr, hStr] = resolucao.split("x");
    const largura = Number(wStr) || (isShort ? 576 : 1024);
    const altura = Number(hStr) || (isShort ? 1024 : 576);
    const seedNum = seedInput.trim() ? Number(seedInput.trim()) : undefined;

    try {
      ultimasConcluidasRef.current = 0;
      const res = await api.comfyuiGerar(projeto.nome, {
        apenas_faltantes: opcoes.apenasFaltantes ?? false,
        indice_cena: opcoes.indiceCena,
        checkpoint: ckptSelecionado || undefined,
        steps,
        cfg,
        sampler_name: samplerName,
        scheduler,
        largura,
        altura,
        seed: Number.isFinite(seedNum) ? seedNum : undefined,
        negativo_extra: negativoExtra.trim() || undefined,
        workflow_api: workflowApi,
      });
      if (res.total_cenas === 0 && res.mensagem) {
        setLog(res.mensagem);
        return;
      }
      const st = await api.comfyuiJobStatus(projeto.nome);
      setComfyJob(st);
    } catch (err) {
      setErro(
        err instanceof Error ? err.message : "Erro ao iniciar geração no ComfyUI"
      );
    }
  }

  function adicionarArquivos(fileList: FileList | File[] | null) {
    if (!fileList) return;
    const validos = Array.from(fileList).filter(
      (f) => /\.(png|jpe?g|webp)$/i.test(f.name) || f.type.startsWith("image/")
    );
    if (validos.length > 0) {
      setFila((prev) =>
        [...prev, ...validos].sort((a, b) =>
          a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: "base" })
        )
      );
    }
  }

  useEffect(() => {
    const onPaste = (e: ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;
      const imagens: File[] = [];
      let idx = 1;
      for (const item of items) {
        if (item.type.startsWith("image/")) {
          const blob = item.getAsFile();
          if (blob) {
            const ext = blob.type.split("/")[1]?.replace("jpeg", "jpg") || "png";
            const nomeArq =
              blob.name && blob.name !== "image.png"
                ? blob.name
                : `colada_${Date.now()}_${idx}.${ext}`;
            imagens.push(new File([blob], nomeArq, { type: blob.type || "image/png" }));
            idx += 1;
          }
        }
      }
      if (imagens.length === 0) return;

      e.preventDefault();
      if (cardHoverNomeRef.current) {
        void substituirImagemCena(cardHoverNomeRef.current, imagens[0]);
      } else {
        adicionarArquivos(imagens);
        setLog(`${imagens.length} imagem(ns) colada(s) na fila de envio (Ctrl+V).`);
      }
    };

    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  });

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
    adicionarArquivos(e.dataTransfer.files);
  }

  async function handleEnviarEProcessar() {
    if (fila.length === 0) return;
    setProcessando(true);
    setErro(null);
    setLog(null);
    const finalizar = iniciarTarefaEstimada({
      id: `imagens-${projeto.nome}`,
      titulo: `Processando ${fila.length} imagem(ns) (${projeto.nome})`,
      etapa: "Salvando e preparando PNGs em midia/cenas/",
      projetoNome: projeto.nome,
      aba: "imagens",
      duracaoEstimadaMs: Math.max(4000, fila.length * 1200),
    });
    try {
      const res = await api.uploadImagens(projeto.nome, fila, limparAnteriores);
      setCenasProntas(res.cenas_geradas);
      setFila([]);
      setCacheBust(Date.now());
      setLog(
        res.log ||
          `${res.cenas_geradas.length} imagens processadas em midia/cenas/.`
      );
      await carregarDados();
      onAtualizado();
    } catch (err) {
      setErro(
        err instanceof Error ? err.message : "Erro ao processar imagens"
      );
    } finally {
      finalizar();
      setProcessando(false);
    }
  }

  async function handleReprocessarRaw() {
    setProcessando(true);
    setErro(null);
    setLog(null);
    const finalizar = iniciarTarefaEstimada({
      id: `imagens-reproc-${projeto.nome}`,
      titulo: `Reprocessando Imagens (${projeto.nome})`,
      etapa: "Recortando/convertendo midia/raw/ → midia/cenas/",
      projetoNome: projeto.nome,
      aba: "imagens",
      duracaoEstimadaMs: 10000,
    });
    try {
      const res = await api.reprocessarImagens(projeto.nome);
      setCenasProntas(res.cenas_geradas);
      setCacheBust(Date.now());
      setLog(
        res.log ||
          `${res.cenas_geradas.length} imagens reprocessadas a partir de midia/raw/.`
      );
      await carregarDados();
      onAtualizado();
    } catch (err) {
      setErro(
        err instanceof Error ? err.message : "Erro ao reprocessar imagens"
      );
    } finally {
      finalizar();
      setProcessando(false);
    }
  }

  async function handleCopiarPrompts() {
    if (!promptsTexto) return;
    await navigator.clipboard.writeText(promptsTexto);
    setCopiado(true);
    setTimeout(() => setCopiado(false), 1800);
  }

  const esperadas = projeto.qtd_cenas_json || promptsCount;
  const comfyRodando = comfyJob?.status === "running";
  const faltantesEstimadas = Math.max(0, esperadas - cenasProntas.length);
  const opcoesResolucao = isShort
    ? [
        { value: "576x1024", label: "576×1024 (9:16 • Rápido 8GB)" },
        { value: "688x1216", label: "688×1216 (9:16 • Médio)" },
        { value: "768x1344", label: "768×1344 (9:16 • Alto)" },
        { value: "512x912", label: "512×912 (9:16 • SD 1.5)" },
      ]
    : [
        { value: "1024x576", label: "1024×576 (16:9 • Rápido 8GB)" },
        { value: "1216x688", label: "1216×688 (16:9 • Médio)" },
        { value: "1280x720", label: "1280×720 (16:9 • HD)" },
        { value: "1344x768", label: "1344×768 (16:9 • Alto)" },
        { value: "912x512", label: "912×512 (16:9 • SD 1.5)" },
      ];

  return (
    <div className="flex flex-col gap-5">
      {/* Barra de status interligado com Storyboard */}
      <div className="bg-[#141821] border border-slate-800 rounded-xl px-4 py-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3 text-xs">
          <span className="px-2.5 py-1 rounded-lg bg-slate-800 text-slate-200 font-semibold">
            Proporção esperada:{" "}
            <strong className={isShort ? "text-purple-300" : "text-[#ffc928]"}>
              {isShort ? "9:16 (Short Vertical)" : "16:9 (Longo Horizontal)"}
            </strong>
          </span>
          <span className="text-slate-300">
            Cenas no Storyboard: <strong>{esperadas}</strong> • PNGs prontos:{" "}
            <strong
              className={
                esperadas > 0 && cenasProntas.length >= esperadas
                  ? "text-emerald-400"
                  : "text-amber-300"
              }
            >
              {cenasProntas.length}
            </strong>
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {rawArquivos.length > 0 && (
            <button
              type="button"
              disabled={processando}
              onClick={() => void handleReprocessarRaw()}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#ffc928]/15 border border-[#ffc928]/40 hover:bg-[#ffc928]/25 disabled:opacity-50 text-[#ffc928] text-xs font-semibold cursor-pointer"
            >
              {processando ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Sparkles className="w-3.5 h-3.5" />
              )}
              {isShort
                ? `Reprocessar raw/ (${rawArquivos.length})`
                : `Reprocessar raw/ (Manter Fundo - ${rawArquivos.length})`}
            </button>
          )}
          {promptsTexto && (
            <button
              type="button"
              onClick={() => void handleCopiarPrompts()}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-700 bg-[#0e1117] hover:border-[#ffc928]/60 text-slate-200 text-xs font-medium cursor-pointer"
            >
              {copiado ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400" /> Copiados!
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5 text-[#ffc928]" /> Copiar Prompts ({promptsCount})
                </>
              )}
            </button>
          )}
          <button
            type="button"
            onClick={() => onIrParaAba("thumb-render")}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-700 hover:border-[#ffc928]/60 text-slate-200 text-xs font-medium cursor-pointer"
          >
            Thumb / Render <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Card ComfyUI Direto (Opcional / Segundo Plano) */}
      <div className="bg-[#141821] border border-slate-800/80 rounded-xl p-4 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => setMostrarComfyui((v) => !v)}
            className="flex items-center gap-2 text-left cursor-pointer"
          >
            <Cpu className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-semibold text-slate-300">
              ComfyUI Local (Opcional / Segundo Plano)
            </span>
            <span className="text-[11px] text-slate-500">
              {mostrarComfyui ? "— clique para recolher" : "— clique para expandir"}
            </span>
          </button>
          <span className="text-[11px] text-slate-500">
            {comfyStatus?.online ? "Online" : "Em segundo plano"}
          </span>
        </div>

        {mostrarComfyui && (
          <div className="space-y-4 pt-2 border-t border-slate-800/70">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="space-y-0.5">
                <div className="flex flex-wrap items-center gap-2">
                  <Cpu className="w-4 h-4 text-[#ffc928]" />
                  <h3 className="text-sm font-bold text-slate-100">
                    Gerar Fundos direto no ComfyUI Local
                  </h3>
                  {comfyStatus?.online ? (
                    <span className="px-2 py-0.5 rounded-full bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 text-[11px] font-semibold">
                      Online •{" "}
                      {comfyStatus.vram_free_mb
                        ? `${(comfyStatus.vram_free_mb / 1024).toFixed(1)} GB VRAM livre`
                        : comfyStatus.url}
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 rounded-full bg-rose-500/15 border border-rose-500/40 text-rose-300 text-[11px] font-semibold">
                      Offline (127.0.0.1:8188)
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-400">
                  Envia os prompts do <code>cenas.json</code> em lote para o ComfyUI, salva em{" "}
                  <code>midia/raw/</code> e prepara automaticamente em <code>midia/cenas/</code>.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => void verificarComfyui()}
                  disabled={verificandoComfy}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-slate-700 bg-[#0e1117] hover:border-slate-500 text-slate-300 text-xs cursor-pointer"
                  title="Verificar conexão com o ComfyUI"
                >
                  <RefreshCw
                    className={`w-3.5 h-3.5 ${verificandoComfy ? "animate-spin" : ""}`}
              />
              Status
            </button>

            <button
              type="button"
              onClick={() => setMostrarAvancadoComfy((v) => !v)}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs cursor-pointer ${
                mostrarAvancadoComfy
                  ? "bg-[#ffc928]/15 border-[#ffc928]/50 text-[#ffc928]"
                  : "bg-[#0e1117] border-slate-700 text-slate-300 hover:border-slate-500"
              }`}
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              Avançado
            </button>

            {comfyRodando ? (
              <button
                type="button"
                onClick={() => void api.comfyuiCancelar()}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-rose-500/20 border border-rose-500/50 hover:bg-rose-500/30 text-rose-200 text-xs font-semibold cursor-pointer"
              >
                <Square className="w-3.5 h-3.5" />
                Cancelar
              </button>
            ) : (
              <>
                {faltantesEstimadas > 0 && cenasProntas.length > 0 && (
                  <button
                    type="button"
                    disabled={!comfyStatus?.online || !projeto.tem_cenas_json}
                    onClick={() => void dispararComfyui({ apenasFaltantes: true })}
                    className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-emerald-500/20 border border-emerald-500/40 hover:bg-emerald-500/30 disabled:opacity-40 text-emerald-200 text-xs font-semibold cursor-pointer"
                  >
                    <Play className="w-3.5 h-3.5" />
                    Gerar Faltantes ({faltantesEstimadas})
                  </button>
                )}
                <button
                  type="button"
                  disabled={!comfyStatus?.online || !projeto.tem_cenas_json}
                  onClick={() => void dispararComfyui({ apenasFaltantes: false })}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#ffc928] hover:bg-[#ffd452] disabled:opacity-40 text-black text-xs font-bold cursor-pointer"
                >
                  <Play className="w-3.5 h-3.5" />
                  Gerar Todas ({esperadas})
                </button>
              </>
            )}
          </div>
        </div>

        {comfyStatus?.online ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-12 gap-3 text-xs">
            <label className="lg:col-span-5 space-y-1">
              <span className="text-[11px] text-slate-400">Checkpoint</span>
              <select
                value={ckptSelecionado}
                onChange={(e) => {
                  setCkptSelecionado(e.target.value);
                  aplicarPresetCheckpoint(e.target.value, isShort);
                }}
                disabled={comfyRodando}
                className="w-full bg-[#0e1117] border border-slate-700 focus:border-[#ffc928] rounded-lg px-2.5 py-1.5 text-slate-200 outline-none"
              >
                {comfyStatus.checkpoints.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </label>

            <label className="lg:col-span-3 space-y-1">
              <span className="text-[11px] text-slate-400">Resolução</span>
              <select
                value={resolucao}
                onChange={(e) => setResolucao(e.target.value)}
                disabled={comfyRodando}
                className="w-full bg-[#0e1117] border border-slate-700 focus:border-[#ffc928] rounded-lg px-2.5 py-1.5 text-slate-200 outline-none"
              >
                {opcoesResolucao.map((op) => (
                  <option key={op.value} value={op.value}>
                    {op.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="lg:col-span-2 space-y-1">
              <span className="text-[11px] text-slate-400">Steps</span>
              <input
                type="number"
                min={1}
                max={60}
                value={steps}
                disabled={comfyRodando}
                onChange={(e) => setSteps(Number(e.target.value) || 5)}
                className="w-full bg-[#0e1117] border border-slate-700 focus:border-[#ffc928] rounded-lg px-2.5 py-1.5 font-mono text-slate-200 outline-none"
              />
            </label>

            <label className="lg:col-span-2 space-y-1">
              <span className="text-[11px] text-slate-400">CFG</span>
              <input
                type="number"
                step="0.5"
                min={1}
                max={20}
                value={cfg}
                disabled={comfyRodando}
                onChange={(e) => setCfg(Number(e.target.value) || 2)}
                className="w-full bg-[#0e1117] border border-slate-700 focus:border-[#ffc928] rounded-lg px-2.5 py-1.5 font-mono text-slate-200 outline-none"
              />
            </label>
          </div>
        ) : (
          <div className="text-xs text-slate-400 bg-[#0e1117] border border-slate-800 rounded-lg px-3 py-2.5">
            Abra o ComfyUI em <code>C:\ComfyUI-Zluda\comfyui-user.bat</code> e clique em{" "}
            <strong>Status</strong> para habilitar a geração automática de cenas.
          </div>
        )}

        {mostrarAvancadoComfy && (
          <div className="bg-[#0e1117] border border-slate-800 rounded-lg p-3 space-y-3 text-xs">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <label className="space-y-1">
                <span className="text-[11px] text-slate-400">Sampler</span>
                <input
                  type="text"
                  value={samplerName}
                  onChange={(e) => setSamplerName(e.target.value)}
                  className="w-full bg-[#141821] border border-slate-700 rounded px-2 py-1 font-mono text-slate-200"
                />
              </label>
              <label className="space-y-1">
                <span className="text-[11px] text-slate-400">Scheduler</span>
                <input
                  type="text"
                  value={scheduler}
                  onChange={(e) => setScheduler(e.target.value)}
                  className="w-full bg-[#141821] border border-slate-700 rounded px-2 py-1 font-mono text-slate-200"
                />
              </label>
              <label className="space-y-1">
                <span className="text-[11px] text-slate-400">
                  Seed fixa (vazio = aleatória)
                </span>
                <input
                  type="number"
                  value={seedInput}
                  onChange={(e) => setSeedInput(e.target.value)}
                  placeholder="Aleatória"
                  className="w-full bg-[#141821] border border-slate-700 rounded px-2 py-1 font-mono text-slate-200"
                />
              </label>
            </div>
            <label className="block space-y-1">
              <span className="text-[11px] text-slate-400">
                Negativo extra (opcional, somado ao bloqueio de pessoas)
              </span>
              <input
                type="text"
                value={negativoExtra}
                onChange={(e) => setNegativoExtra(e.target.value)}
                placeholder="ex.: dark shadows, noisy background"
                className="w-full bg-[#141821] border border-slate-700 rounded px-2 py-1 text-slate-200"
              />
            </label>
            <label className="block space-y-1">
              <span className="text-[11px] text-slate-400">
                Workflow API Format customizado (JSON opcional — deixe vazio para usar o padrão)
              </span>
              <textarea
                rows={3}
                value={workflowJsonTexto}
                onChange={(e) => setWorkflowJsonTexto(e.target.value)}
                placeholder='Cole aqui o JSON exportado via "Save (API Format)" no ComfyUI...'
                className="w-full bg-[#141821] border border-slate-700 rounded p-2 font-mono text-[11px] text-slate-200 resize-y"
              />
            </label>
          </div>
        )}

        {comfyJob && comfyJob.status !== "idle" && (
          <div
            className={`rounded-lg border px-3 py-2.5 text-xs space-y-1.5 ${
              comfyJob.status === "running"
                ? "bg-amber-500/10 border-amber-500/30 text-amber-200"
                : comfyJob.status === "done"
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                : "bg-rose-500/10 border-rose-500/30 text-rose-300"
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 font-semibold">
                {comfyJob.status === "running" && (
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-[#ffc928]" />
                )}
                <span>
                  {comfyJob.status === "running"
                    ? `Gerando cena ${comfyJob.cena_indice_atual ?? ""} (${comfyJob.concluidas}/${comfyJob.total_cenas})...`
                    : comfyJob.status === "done"
                    ? `Concluído: ${comfyJob.concluidas}/${comfyJob.total_cenas} cena(s) gerada(s)!`
                    : comfyJob.erro || `Status: ${comfyJob.status}`}
                </span>
              </div>
              {comfyJob.total_cenas > 0 && (
                <span className="font-mono text-[11px]">
                  {Math.round((comfyJob.concluidas / comfyJob.total_cenas) * 100)}%
                </span>
              )}
            </div>
            {comfyJob.total_cenas > 0 && (
              <div className="w-full h-1.5 bg-black/30 rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#ffc928] transition-all"
                  style={{
                    width: `${Math.min(
                      100,
                      Math.round((comfyJob.concluidas / comfyJob.total_cenas) * 100)
                    )}%`,
                  }}
                />
              </div>
            )}
            {comfyJob.logs.length > 0 && (
              <div className="text-[11px] opacity-80 truncate">
                {comfyJob.logs[comfyJob.logs.length - 1]}
              </div>
            )}
          </div>
        )}
          </div>
        )}
      </div>

      {/* Batch Upload Zone */}
      <div className="bg-[#141821] border border-slate-800 rounded-xl p-5 space-y-4">
        <div
          onClick={() => !processando && fileInputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-xl p-8 text-center transition cursor-pointer flex flex-col items-center justify-center gap-2 ${
            dragOver
              ? "border-[#ffc928] bg-[#ffc928]/5"
              : "border-slate-700 hover:border-[#ffc928]/60 bg-[#0e1117]"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".png,.jpg,.jpeg,.webp,image/*"
            hidden
            onChange={(e) => {
              adicionarArquivos(e.target.files);
              e.target.value = "";
            }}
          />
          <ImagePlus className="w-8 h-8 text-[#ffc928]" />
          <div className="text-sm font-semibold text-slate-200">
            Upload em lote de fundos/objetos {isShort ? "9:16" : "16:9"} (<code>midia/raw/</code>)
          </div>
          <p className="text-xs text-slate-400">
            Arraste os fundos/objetos, clique para selecionar ou aperte{" "}
            <strong className="text-[#ffc928]">Ctrl + V</strong> (passe o mouse sobre um card e aperte Ctrl + V para colar direto na cena).
          </p>
        </div>

        {/* Queue */}
        {fila.length > 0 && (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="text-xs text-slate-300 font-medium">
                {fila.length} arquivo(s) na fila para envio
              </div>
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={limparAnteriores}
                    onChange={(e) => setLimparAnteriores(e.target.checked)}
                    className="accent-[#ffc928]"
                  />
                  Substituir imagens anteriores do projeto
                </label>
                <button
                  type="button"
                  onClick={() => setFila([])}
                  className="text-xs text-slate-400 hover:text-rose-400 cursor-pointer"
                >
                  Limpar fila
                </button>
                <button
                  type="button"
                  onClick={() => void handleEnviarEProcessar()}
                  disabled={processando}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#ffc928] hover:bg-[#ffd452] disabled:opacity-50 text-black font-semibold text-xs transition cursor-pointer"
                >
                  {processando ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Sparkles className="w-4 h-4" />
                  )}
                  {isShort
                    ? "Enviar e Limpar Fundo (limpar_imagens.py)"
                    : "Enviar e Padronizar Cenas (Manter Fundo)"}
                </button>
              </div>
            </div>

            <div className="max-h-64 overflow-y-auto grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-2.5 pr-1">
              {fila.map((f, idx) => (
                <div
                  key={`${f.name}-${idx}`}
                  className="bg-[#0e1117] border border-slate-800 rounded-lg overflow-hidden flex flex-col"
                >
                  <div
                    className={`${
                      isShort ? "aspect-[9/16]" : "aspect-video"
                    } checkerboard-dark flex items-center justify-center p-1.5 relative`}
                  >
                    {previewsFila[idx] ? (
                      <img
                        src={previewsFila[idx]}
                        alt={f.name}
                        className="max-h-full max-w-full object-contain"
                      />
                    ) : null}
                    <span className="absolute top-1 left-1 px-1.5 py-0.5 rounded bg-black/70 text-[10px] font-mono font-bold text-[#ffc928]">
                      #{idx + 1}
                    </span>
                  </div>
                  <div className="px-2 py-1.5 flex items-center justify-between gap-1 text-[10px] border-t border-slate-800/80">
                    <span className="truncate text-slate-300" title={f.name}>
                      {f.name}
                    </span>
                    <button
                      type="button"
                      onClick={() =>
                        setFila((prev) => prev.filter((_, i) => i !== idx))
                      }
                      title="Remover da fila"
                      className="text-slate-500 hover:text-rose-400 shrink-0 cursor-pointer"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {erro && (
        <div className="px-4 py-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
          {erro}
        </div>
      )}

      {log && (
        <div className="px-4 py-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-start gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
          <pre className="whitespace-pre-wrap font-mono text-[11px] max-h-40 overflow-y-auto">
            {log}
          </pre>
        </div>
      )}

      {/* Gallery of processed PNGs */}
      <div className="bg-[#141821] border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
            <Images className="w-4 h-4 text-[#ffc928]" />
            <span>
              Cenas Recortadas (<code>midia/cenas/</code>)
            </span>
          </div>
          <span className="text-xs text-slate-400">
            {cenasProntas.length} PNG(s) com fundo removido • {rawArquivos.length} em raw/
          </span>
        </div>

        {carregando ? (
          <div className="py-10 flex items-center justify-center gap-2 text-xs text-slate-400">
            <Loader2 className="w-4 h-4 animate-spin text-[#ffc928]" />
            Carregando galeria...
          </div>
        ) : cenasStoryboard.length === 0 && cenasProntas.length === 0 ? (
          <div className="py-10 text-center text-xs text-slate-500 border border-slate-800/70 rounded-xl bg-[#0e1117]">
            Nenhuma cena ou imagem em <code>midia/cenas/</code> ainda.
          </div>
        ) : (
          <div
            className={`grid gap-3 ${
              isShort
                ? "grid-cols-2 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6"
                : "grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5"
            }`}
          >
            {(cenasStoryboard.length > 0
              ? cenasStoryboard.map((c, idx) => {
                  const partes = (c.fundo?.arquivo || c.arquivo || "").replace(/\\/g, "/").split("/");
                  const nomePng = partes[partes.length - 1] || `cena_${String(idx + 1).padStart(2, "0")}.png`;
                  return {
                    nome: nomePng,
                    fala: c.narracao || c.texto || "",
                    temImagem: cenasProntas.includes(nomePng),
                  };
                })
              : cenasProntas.map((nome) => ({
                  nome,
                  fala: "",
                  temImagem: true,
                }))
            ).map((item, idx) => {
              const nome = item.nome;
              const emUpload = substituindoCena === nome;
              const arrastando = dragCardNome === nome;
              const idxEmProntas = cenasProntas.indexOf(nome);
              return (
                <div
                  key={`${nome}-${idx}`}
                  onMouseEnter={() => {
                    cardHoverNomeRef.current = nome;
                  }}
                  onMouseLeave={() => {
                    if (cardHoverNomeRef.current === nome) {
                      cardHoverNomeRef.current = null;
                    }
                  }}
                  draggable={item.temImagem}
                  onDragStart={() => setCardArrastadoOrdem(nome)}
                  onDragEnd={() => setCardArrastadoOrdem(null)}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragCardNome(nome);
                  }}
                  onDragLeave={() => setDragCardNome(null)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDragCardNome(null);
                    const file = e.dataTransfer.files?.[0];
                    if (file) {
                      void substituirImagemCena(nome, file);
                      return;
                    }
                    if (cardArrastadoOrdem && cardArrastadoOrdem !== nome && idxEmProntas >= 0) {
                      void reordenarCenaPara(cardArrastadoOrdem, idxEmProntas);
                      setCardArrastadoOrdem(null);
                    }
                  }}
                  className={`bg-[#0e1117] border rounded-xl overflow-hidden flex flex-col transition ${
                    arrastando ? "border-[#ffc928] ring-2 ring-[#ffc928]/30" : "border-slate-800"
                  }`}
                >
                  <div
                    className={`${
                      isShort ? "aspect-[9/16]" : "aspect-video"
                    } checkerboard-dark flex items-center justify-center p-2 relative`}
                  >
                    {item.temImagem ? (
                      <img
                        src={api.imagemCenaUrl(projeto.nome, nome, cacheBust)}
                        alt={nome}
                        className="max-h-full max-w-full object-contain pointer-events-none"
                        loading="lazy"
                      />
                    ) : (
                      <div className="text-center px-2 text-[11px] text-slate-500">
                        Arraste a imagem aqui ou clique abaixo
                      </div>
                    )}
                    {emUpload && (
                      <div className="absolute inset-0 bg-black/70 flex items-center justify-center">
                        <Loader2 className="w-5 h-5 animate-spin text-[#ffc928]" />
                      </div>
                    )}
                  </div>
                  {item.fala && (
                    <p
                      title={item.fala}
                      className="px-2.5 pt-1.5 text-[10px] text-slate-400 truncate"
                    >
                      {item.fala}
                    </p>
                  )}
                  <div className="px-2 py-1.5 border-t border-slate-800/80 flex items-center justify-between gap-1 text-[11px] font-mono text-slate-300 mt-auto">
                    <span className="truncate" title={nome}>{nome}</span>
                    <div className="flex items-center gap-1 shrink-0">
                      {item.temImagem && idxEmProntas > 0 && (
                        <button
                          type="button"
                          onClick={() => void reordenarCenaPara(nome, idxEmProntas - 1)}
                          title="Mover para cena anterior"
                          className="p-1 rounded bg-slate-800/80 hover:bg-slate-700 text-slate-300 cursor-pointer"
                        >
                          <ArrowLeft className="w-3 h-3" />
                        </button>
                      )}
                      {item.temImagem && idxEmProntas >= 0 && idxEmProntas < cenasProntas.length - 1 && (
                        <button
                          type="button"
                          onClick={() => void reordenarCenaPara(nome, idxEmProntas + 1)}
                          title="Mover para próxima cena"
                          className="p-1 rounded bg-slate-800/80 hover:bg-slate-700 text-slate-300 cursor-pointer"
                        >
                          <ArrowRight className="w-3 h-3" />
                        </button>
                      )}
                      <label
                        className="px-1.5 py-0.5 rounded bg-slate-800 hover:bg-[#ffc928] hover:text-black text-[10px] font-sans font-semibold text-slate-200 flex items-center gap-1 cursor-pointer transition"
                        title={`Adicionar ou substituir ${nome}`}
                      >
                        <Upload className="w-3 h-3" />
                        {item.temImagem ? "Trocar" : "Enviar"}
                        <input
                          type="file"
                          accept="image/*"
                          hidden
                          disabled={emUpload}
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            e.target.value = "";
                            void substituirImagemCena(nome, file);
                          }}
                        />
                      </label>
                      <button
                        type="button"
                        onClick={() => void handleExcluirCena(nome)}
                        title={`Excluir ${nome}`}
                        className="p-1 rounded text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 cursor-pointer"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
