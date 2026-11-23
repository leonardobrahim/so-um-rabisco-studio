import { useEffect, useRef, useState, type DragEvent } from "react";
import {
  Smartphone,
  Rocket,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Image as ImageIcon,
  Sun,
  Moon,
  Copy,
  Check,
  Heart,
  MessageCircle,
  Share2,
  Film,
  Download,
} from "lucide-react";
import { api } from "../api";
import type { ProjetoResumo } from "../types";

interface Props {
  projeto: ProjetoResumo;
  onAtualizado: () => void;
}

function formatarDuracao(segundos: number | null): string {
  if (!segundos || segundos <= 0) return "07:42";
  const min = Math.floor(segundos / 60);
  const seg = Math.round(segundos % 60);
  return `${String(min).padStart(2, "0")}:${String(seg).padStart(2, "0")}`;
}

function tocarSomConclusao(sucesso: boolean) {
  try {
    const AudioCtx =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext })
        .webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const agora = ctx.currentTime;
    const notas = sucesso ? [523.25, 659.25, 783.99] : [330, 261.63];

    notas.forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, agora + i * 0.11);

      gain.gain.setValueAtTime(0.001, agora + i * 0.11);
      gain.gain.exponentialRampToValueAtTime(0.18, agora + i * 0.11 + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.001, agora + i * 0.11 + 0.32);

      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(agora + i * 0.11);
      osc.stop(agora + i * 0.11 + 0.34);
    });
  } catch {
    // Ignora caso o navegador bloqueie áudio automático
  }
}

function notificarConclusao(nomeProjeto: string, sucesso: boolean) {
  tocarSomConclusao(sucesso);

  const tituloOriginal = document.title;
  document.title = sucesso
    ? `✅ Vídeo pronto! - ${nomeProjeto}`
    : `❌ Erro no render - ${nomeProjeto}`;
  const restaurarTitulo = () => {
    document.title = tituloOriginal;
    window.removeEventListener("focus", restaurarTitulo);
  };
  window.addEventListener("focus", restaurarTitulo);
  setTimeout(restaurarTitulo, 10000);

  if ("Notification" in window && Notification.permission === "granted") {
    try {
      new Notification(
        sucesso ? "Vídeo pronto! — Só um Rabisco" : "Erro ao gerar vídeo",
        {
          body: sucesso
            ? `O vídeo "${nomeProjeto}" terminou de ser gerado no HyperFrames.`
            : `Falha ao renderizar "${nomeProjeto}". Confira os detalhes no Studio.`,
        }
      );
    } catch {
      // Ignora erro de notificação em contextos restritos
    }
  }
}

export function TabThumbRender({ projeto, onAtualizado }: Props) {
  const isShort = projeto.tipo === "short";
  const tituloPadrao =
    projeto.nome
      .replace(/^\d{4}-\d{2}-(short-)?/, "")
      .replace(/-/g, " ") ||
    "Por Que Você Sempre Fica Sem Dinheiro Todo Mês";

  const [thumbDataUrl, setThumbDataUrl] = useState<string | null>(null);
  const [titulo, setTitulo] = useState(tituloPadrao);
  const [duracao, setDuracao] = useState(() =>
    formatarDuracao(projeto.duracao_total)
  );
  const [metaTexto, setMetaTexto] = useState("18 mil visualizações • há 4 horas");
  const [hashtags, setHashtags] = useState(
    "#psicologia #animacao #soumrabisco #shorts"
  );
  const [temaPhone, setTemaPhone] = useState<"dark" | "light">("dark");
  const [dragOver, setDragOver] = useState(false);
  const [cortouNoCelular, setCortouNoCelular] = useState(false);
  const [copiadoPromptThumb, setCopiadoPromptThumb] = useState(false);

  const [preparando, setPreparando] = useState(false);
  const [comLegenda, setComLegenda] = useState(true);
  const [qualidade, setQualidade] = useState<"draft" | "looks" | "delivery">("looks");
  const [renderStatus, setRenderStatus] = useState<"idle" | "running" | "done" | "error">("idle");
  const [ultimaLinhaRender, setUltimaLinhaRender] = useState<string | null>(null);
  const [existeVideo, setExisteVideo] = useState(false);
  const [tamanhoVideoBytes, setTamanhoVideoBytes] = useState<number | null>(null);
  const [caminhoVideo, setCaminhoVideo] = useState<string | null>(null);
  const [videoCacheBust, setVideoCacheBust] = useState<number>(() => Date.now());
  const [renderLog, setRenderLog] = useState<string | null>(null);
  const [renderErro, setRenderErro] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const titlePreviewRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let ativo = true;
    setRenderLog(null);
    setRenderErro(null);
    setDuracao(formatarDuracao(projeto.duracao_total));
    setTitulo(tituloPadrao);

    api
      .lerMeta(projeto.nome)
      .then((res) => {
        if (!ativo) return;
        if (res.meta.titulo_thumb) setTitulo(res.meta.titulo_thumb);
        if (res.meta.duracao_thumb) setDuracao(res.meta.duracao_thumb);
        if (res.meta.hashtags_short) setHashtags(res.meta.hashtags_short);
      })
      .catch(() => {});

    api
      .statusRenderVideo(projeto.nome)
      .then((st) => {
        if (!ativo) return;
        setRenderStatus(st.status);
        setUltimaLinhaRender(st.ultima_linha);
        setExisteVideo(st.existe_video);
        setTamanhoVideoBytes(st.tamanho_bytes);
        setCaminhoVideo(st.caminho_video);
        if (st.erro) setRenderErro(st.erro);
      })
      .catch(() => {});

    return () => {
      ativo = false;
    };
  }, [projeto.nome, projeto.duracao_total]);

  useEffect(() => {
    if (renderStatus !== "running") return;
    let ativo = true;
    const timer = setInterval(() => {
      api
        .statusRenderVideo(projeto.nome)
        .then((st) => {
          if (!ativo) return;
          setRenderStatus(st.status);
          setUltimaLinhaRender(st.ultima_linha);
          setExisteVideo(st.existe_video);
          setTamanhoVideoBytes(st.tamanho_bytes);
          setCaminhoVideo(st.caminho_video);
          if (st.status === "done") {
            setVideoCacheBust(Date.now());
            setRenderLog("Vídeo MP4 gerado com sucesso pelo HyperFrames!");
            setRenderErro(null);
            notificarConclusao(projeto.nome, true);
            onAtualizado();
          } else if (st.status === "error") {
            setRenderErro(st.erro || "Erro ao renderizar vídeo no HyperFrames.");
            notificarConclusao(projeto.nome, false);
          }
        })
        .catch(() => {});
    }, 2000);
    return () => {
      ativo = false;
      clearInterval(timer);
    };
  }, [renderStatus, projeto.nome, onAtualizado]);

  function carregarImagem(file: File | undefined | null) {
    if (!file || !file.type.startsWith("image/")) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      if (typeof e.target?.result === "string") {
        setThumbDataUrl(e.target.result);
      }
    };
    reader.readAsDataURL(file);
  }

  useEffect(() => {
    const onPaste = (e: ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;
      for (const item of items) {
        if (item.type.startsWith("image/")) {
          carregarImagem(item.getAsFile());
          break;
        }
      }
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, []);

  useEffect(() => {
    const id = requestAnimationFrame(() => {
      const el = titlePreviewRef.current;
      if (!el) return;
      setCortouNoCelular(el.scrollHeight > el.clientHeight + 1);
    });
    return () => cancelAnimationFrame(id);
  }, [titulo, isShort]);

  function salvarMetaSilencioso(patch: Record<string, string>) {
    void api.atualizarMeta(projeto.nome, patch).catch(() => {});
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
    carregarImagem(e.dataTransfer.files[0]);
  }

  async function handlePrepararRender() {
    setPreparando(true);
    setRenderErro(null);
    setRenderLog(null);
    try {
      const res = await api.prepararRender(projeto.nome, comLegenda);
      setRenderLog(
        (res.log || "Template preparado com sucesso!") +
          ` (${comLegenda ? "Com legendas" : "Sem legendas"})`
      );
      onAtualizado();
    } catch (err) {
      setRenderErro(
        err instanceof Error ? err.message : "Erro ao preparar render"
      );
    } finally {
      setPreparando(false);
    }
  }

  const promptThumbPaperBillions = `Dramatic 2D graphic novel cartoon YouTube thumbnail about "${titulo.trim()}". Close-up on the left of a minimalist cartoon character with a large rounded pale-white head, messy spiky black hair, wearing a vibrant yellow hoodie (#FFC928), extreme shocked and panicked expression with wide eyes, small pupils and sweat drops. On the right, a glowing symbolic object casting intense neon rim light onto the character's hair and hoodie. Detailed dark navy atmospheric background (#050811) with subtle blur, thick black outlines, cel-shading, dramatic lighting, 16:9 aspect ratio.`;

  async function copiarPromptThumb() {
    await navigator.clipboard.writeText(promptThumbPaperBillions);
    setCopiadoPromptThumb(true);
    setTimeout(() => setCopiadoPromptThumb(false), 1800);
  }

  const textoLimpo = titulo.trim();
  const palavras = textoLimpo
    ? textoLimpo.split(/\s+/).filter(Boolean).length
    : 0;
  const caracteres = textoLimpo.length;

  const classePalavras = isShort
    ? palavras >= 3 && palavras <= 7
      ? "bg-emerald-500/15 text-emerald-400"
      : "bg-amber-500/15 text-amber-300"
    : palavras >= 7 && palavras <= 8
    ? "bg-emerald-500/15 text-emerald-400"
    : palavras >= 5 && palavras <= 10
    ? "bg-amber-500/15 text-amber-300"
    : "bg-rose-500/15 text-rose-400";

  const classeCaracteres = isShort
    ? caracteres <= 55
      ? "bg-emerald-500/15 text-emerald-400"
      : "bg-rose-500/15 text-rose-400"
    : caracteres >= 45 && caracteres <= 55
    ? "bg-emerald-500/15 text-emerald-400"
    : caracteres <= 65
    ? "bg-amber-500/15 text-amber-300"
    : "bg-rose-500/15 text-rose-400";

  const isDarkPhone = temaPhone === "dark";

  return (
    <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
      {/* Coluna Esquerda: Preparar Render + Controles */}
      <div className="xl:col-span-7 flex flex-col gap-5">
        {/* Card Preparar Render */}
        <div className="bg-[#141821] border border-slate-800 rounded-2xl p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <Rocket className="w-4 h-4 text-[#ffc928]" />
                Preparar Render (
                {isShort ? "1080×1920 • 9:16 Short" : "1920×1080 • 16:9 Longo"})
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Copia <code>cenas.json</code>, áudio e PNGs recortados para{" "}
                <code>template-hyperframes/</code> via{" "}
                <code>scripts/preparar_render.py</code>.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2.5">
              <div className="flex items-center bg-[#0b0d12] p-0.5 rounded-xl border border-slate-800 text-xs font-semibold">
                <button
                  type="button"
                  onClick={() => setComLegenda(true)}
                  className={`px-3 py-2 rounded-lg transition cursor-pointer ${
                    comLegenda
                      ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Com Legenda
                </button>
                <button
                  type="button"
                  onClick={() => setComLegenda(false)}
                  className={`px-3 py-2 rounded-lg transition cursor-pointer ${
                    !comLegenda
                      ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Sem Legenda
                </button>
              </div>
              <select
                value={qualidade}
                onChange={(e) =>
                  setQualidade(e.target.value as "draft" | "looks" | "delivery")
                }
                disabled={renderStatus === "running"}
                className="bg-[#0b0d12] border border-slate-800 rounded-xl px-2.5 py-2 text-xs text-slate-200 outline-none cursor-pointer"
                title="Qualidade do render HyperFrames"
              >
                <option value="draft">Rápido (draft)</option>
                <option value="looks">Padrão (looks)</option>
                <option value="delivery">Máxima (delivery)</option>
              </select>
              <button
                type="button"
                onClick={() => void handlePrepararRender()}
                disabled={preparando || renderStatus === "running" || !projeto.tem_cenas_json}
                className="flex items-center gap-2 px-3.5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-45 text-slate-100 font-semibold text-xs transition cursor-pointer"
              >
                {preparando ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Rocket className="w-4 h-4 text-[#ffc928]" />
                )}
                Só Preparar
              </button>
              <button
                type="button"
                onClick={async () => {
                  setRenderErro(null);
                  setRenderLog(null);
                  if ("Notification" in window && Notification.permission === "default") {
                    void Notification.requestPermission().catch(() => {});
                  }
                  try {
                    await api.renderizarVideo(projeto.nome, comLegenda, qualidade);
                    setRenderStatus("running");
                    setUltimaLinhaRender("Preparando projeto e iniciando HyperFrames...");
                  } catch (err) {
                    setRenderErro(
                      err instanceof Error ? err.message : "Erro ao iniciar renderização"
                    );
                  }
                }}
                disabled={preparando || renderStatus === "running" || !projeto.tem_cenas_json}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#ffc928] hover:bg-[#ffd452] disabled:opacity-45 text-black font-bold text-xs transition cursor-pointer shadow-sm"
              >
                {renderStatus === "running" ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Film className="w-4 h-4" />
                )}
                {renderStatus === "running" ? "Renderizando..." : "Gerar Vídeo (MP4)"}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2.5 text-xs">
            <div className="bg-[#0e1117] border border-slate-800 rounded-xl px-3 py-2.5 flex items-center gap-2">
              {projeto.tem_cenas_json ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              )}
              <div>
                <div className="font-semibold text-slate-200">cenas.json</div>
                <div className="text-[11px] text-slate-400">
                  {projeto.tem_cenas_json
                    ? `${projeto.qtd_cenas_json} cenas (${projeto.formato})`
                    : "Pendente"}
                </div>
              </div>
            </div>

            <div className="bg-[#0e1117] border border-slate-800 rounded-xl px-3 py-2.5 flex items-center gap-2">
              {projeto.tem_audio ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
              )}
              <div>
                <div className="font-semibold text-slate-200">Áudio</div>
                <div className="text-[11px] text-slate-400">
                  {projeto.tem_audio ? "audio.wav pronto" : "Não enviado"}
                </div>
              </div>
            </div>

            <div className="bg-[#0e1117] border border-slate-800 rounded-xl px-3 py-2.5 flex items-center gap-2">
              {projeto.qtd_imagens_cenas > 0 ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
              )}
              <div>
                <div className="font-semibold text-slate-200">Cenas PNG</div>
                <div className="text-[11px] text-slate-400">
                  {projeto.qtd_imagens_cenas} arquivo(s)
                </div>
              </div>
            </div>
          </div>

          {renderStatus === "running" && (
            <div className="px-3.5 py-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs flex items-center gap-2.5">
              <Loader2 className="w-4 h-4 animate-spin shrink-0 text-[#ffc928]" />
              <div className="min-w-0">
                <div className="font-semibold">Renderizando vídeo MP4 com HyperFrames...</div>
                {ultimaLinhaRender && (
                  <div className="text-[11px] text-amber-300/80 truncate">
                    {ultimaLinhaRender}
                  </div>
                )}
              </div>
            </div>
          )}

          {renderErro && (
            <div className="px-3.5 py-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
              {renderErro}
            </div>
          )}

          {renderLog && (
            <div className="px-3.5 py-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{renderLog}</span>
            </div>
          )}

          {existeVideo && (
            <div className="bg-[#0e1117] border border-slate-800 rounded-xl p-3.5 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="text-xs font-bold text-emerald-400 flex items-center gap-1.5">
                    <Film className="w-4 h-4" /> Vídeo Final Pronto (MP4)
                  </div>
                  <div className="text-[11px] text-slate-400">
                    {tamanhoVideoBytes
                      ? `${(tamanhoVideoBytes / (1024 * 1024)).toFixed(2)} MB • `
                      : ""}
                    {caminhoVideo || "midia/video_final.mp4"}
                  </div>
                </div>
                <a
                  href={api.videoFinalUrl(projeto.nome, videoCacheBust)}
                  download={`${projeto.nome}.mp4`}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/40 text-emerald-300 text-xs font-semibold transition"
                >
                  <Download className="w-3.5 h-3.5" /> Baixar MP4
                </a>
              </div>
              <video
                key={videoCacheBust}
                src={api.videoFinalUrl(projeto.nome, videoCacheBust)}
                controls
                className="w-full max-h-72 rounded-lg bg-black"
              />
            </div>
          )}
        </div>

        {/* Card Controles do Preview */}
        <div className="bg-[#141821] border border-slate-800 rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <Smartphone className="w-4 h-4 text-[#ffc928]" />
              {isShort
                ? "Preview Vertical (Shorts / Reels / TikTok 9:16)"
                : "Preview de Clique Mobile (YouTube 16:9)"}
            </h3>
            <span
              className={`text-[11px] font-bold px-2 py-0.5 rounded uppercase ${
                isShort
                  ? "bg-purple-500 text-white"
                  : "bg-[#ffc928] text-black"
              }`}
            >
              {isShort ? "Short 9:16" : "Longo 16:9"}
            </span>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-400">
              1. {isShort ? "Capa / Frame Vertical (9:16)" : "Thumbnail (16:9)"}
            </label>
            <div
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition ${
                dragOver
                  ? "border-[#ffc928] bg-[#ffc928]/5"
                  : "border-slate-700 hover:border-[#ffc928]/60 bg-[#0e1117]"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                hidden
                onChange={(e) => carregarImagem(e.target.files?.[0])}
              />
              <div className="flex items-center justify-center gap-2 text-xs text-slate-300">
                <ImageIcon className="w-4 h-4 text-[#ffc928]" />
                <span>
                  Clique, arraste ou aperte{" "}
                  <strong className="text-[#ffc928]">Ctrl + V</strong> em qualquer
                  lugar
                </span>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-400">
              2. {isShort ? "Título / Gancho do Short" : "Título do Vídeo (Regra: 7 a 8 palavras)"}
            </label>
            <textarea
              value={titulo}
              onChange={(e) => {
                setTitulo(e.target.value);
                salvarMetaSilencioso({ titulo_thumb: e.target.value });
              }}
              rows={2}
              placeholder="Digite o título para testar no celular..."
              className="w-full bg-[#0e1117] border border-slate-700 focus:border-[#ffc928] rounded-xl p-3 text-sm text-slate-100 outline-none resize-y"
            />
            <div className="flex flex-wrap gap-2">
              <span
                className={`text-xs font-semibold px-2.5 py-1 rounded-lg ${classePalavras}`}
              >
                {palavras} {palavras === 1 ? "palavra" : "palavras"}
              </span>
              <span
                className={`text-xs font-semibold px-2.5 py-1 rounded-lg ${classeCaracteres}`}
              >
                {caracteres} caracteres
              </span>
              <span
                className={`text-xs font-semibold px-2.5 py-1 rounded-lg ${
                  cortouNoCelular
                    ? "bg-rose-500/15 text-rose-400"
                    : "bg-emerald-500/15 text-emerald-400"
                }`}
              >
                {cortouNoCelular
                  ? "Cortou com '...' no celular"
                  : "Cabe inteiro no celular"}
              </span>
            </div>
          </div>

          {isShort ? (
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-400">
                Hashtags do Short
              </label>
              <input
                type="text"
                value={hashtags}
                onChange={(e) => {
                  setHashtags(e.target.value);
                  salvarMetaSilencioso({ hashtags_short: e.target.value });
                }}
                className="w-full bg-[#0e1117] border border-slate-700 focus:border-[#ffc928] rounded-xl px-3 py-2 text-xs text-slate-100 outline-none"
              />
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-400">
                    Duração
                  </label>
                  <input
                    type="text"
                    value={duracao}
                    onChange={(e) => {
                      setDuracao(e.target.value);
                      salvarMetaSilencioso({ duracao_thumb: e.target.value });
                    }}
                    className="w-full bg-[#0e1117] border border-slate-700 focus:border-[#ffc928] rounded-xl px-3 py-2 text-xs text-slate-100 outline-none"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-400">
                    Views e Tempo
                  </label>
                  <input
                    type="text"
                    value={metaTexto}
                    onChange={(e) => setMetaTexto(e.target.value)}
                    className="w-full bg-[#0e1117] border border-slate-700 focus:border-[#ffc928] rounded-xl px-3 py-2 text-xs text-slate-100 outline-none"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-400">
                  Tema do App no Celular
                </label>
                <div className="grid grid-cols-2 gap-1 bg-[#0e1117] p-1 rounded-xl border border-slate-800">
                  <button
                    type="button"
                    onClick={() => setTemaPhone("dark")}
                    className={`flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold transition cursor-pointer ${
                      isDarkPhone
                        ? "bg-slate-800 text-white"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <Moon className="w-3.5 h-3.5" /> Modo Escuro
                  </button>
                  <button
                    type="button"
                    onClick={() => setTemaPhone("light")}
                    className={`flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold transition cursor-pointer ${
                      !isDarkPhone
                        ? "bg-slate-800 text-white"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <Sun className="w-3.5 h-3.5" /> Modo Claro
                  </button>
                </div>
              </div>

              {/* Prompt de Thumb Paper Billions automático */}
              <div className="bg-[#0e1117] border border-slate-800 rounded-xl p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    Prompt de Thumbnail (Paper Billions 16:9)
                  </span>
                  <button
                    type="button"
                    onClick={() => void copiarPromptThumb()}
                    className="flex items-center gap-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[11px] text-slate-200 font-medium cursor-pointer"
                  >
                    {copiadoPromptThumb ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-400" /> Copiado
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3 text-[#ffc928]" /> Copiar Prompt
                      </>
                    )}
                  </button>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  {promptThumbPaperBillions}
                </p>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Coluna Direita: Simulador Mobile (16:9 Feed ou 9:16 Shorts) */}
      <div className="xl:col-span-5 flex justify-center">
        {isShort ? (
          /* Simulador Short 9:16 com Safe Zones */
          <div className="w-[340px] h-[640px] rounded-[38px] border-[9px] border-[#262a34] bg-[#0b0d12] shadow-2xl overflow-hidden relative flex flex-col shrink-0">
            {thumbDataUrl ? (
              <img
                src={thumbDataUrl}
                alt="Preview Short 9:16"
                className="w-full h-full object-cover"
              />
            ) : (
              <div
                className="w-full h-full flex flex-col items-center justify-center text-white text-center p-6"
                style={{
                  background:
                    "radial-gradient(circle at 50% 40%, #2a183b 0%, #050811 80%)",
                }}
              >
                <span className="font-black text-lg tracking-wide">
                  CAPA / FRAME 9:16
                </span>
                <small className="text-[#ffc928] mt-1.5 text-xs">
                  Aperte Ctrl+V para testar a área segura
                </small>
              </div>
            )}

            {/* Top Safe Zone */}
            <div className="absolute top-3 inset-x-4 flex justify-between items-center text-[11px] font-semibold text-white/90 drop-shadow">
              <span>Shorts</span>
              <span className="px-2 py-0.5 rounded bg-black/40">9:16</span>
            </div>

            {/* Right Action Rail (Safe Zone) */}
            <div className="absolute right-3 bottom-24 flex flex-col items-center gap-4 text-white drop-shadow">
              <div className="flex flex-col items-center gap-0.5">
                <div className="w-9 h-9 rounded-full bg-black/40 flex items-center justify-center">
                  <Heart className="w-4 h-4" />
                </div>
                <span className="text-[10px]">12 mil</span>
              </div>
              <div className="flex flex-col items-center gap-0.5">
                <div className="w-9 h-9 rounded-full bg-black/40 flex items-center justify-center">
                  <MessageCircle className="w-4 h-4" />
                </div>
                <span className="text-[10px]">340</span>
              </div>
              <div className="flex flex-col items-center gap-0.5">
                <div className="w-9 h-9 rounded-full bg-black/40 flex items-center justify-center">
                  <Share2 className="w-4 h-4" />
                </div>
                <span className="text-[10px]">Enviar</span>
              </div>
            </div>

            {/* Bottom Caption Safe Zone */}
            <div className="absolute inset-x-0 bottom-0 p-4 pt-12 bg-gradient-to-t from-black/90 via-black/50 to-transparent text-white pr-14">
              <div className="flex items-center gap-2 mb-1.5">
                <div className="w-6 h-6 rounded-full bg-[#ffc928] text-black font-black text-[10px] flex items-center justify-center">
                  SR
                </div>
                <span className="text-xs font-bold">@soumrabisco</span>
              </div>
              <div
                ref={titlePreviewRef}
                className="text-[13px] font-medium leading-snug line-clamp-2 break-words"
              >
                {textoLimpo || "Título do Short..."}
              </div>
              <div className="text-[11px] text-slate-300 mt-1 truncate">
                {hashtags}
              </div>
            </div>
          </div>
        ) : (
          /* Simulador YouTube Feed Mobile 16:9 */
          <div
            className={`w-[360px] h-[680px] rounded-[38px] border-[9px] border-[#262a34] shadow-2xl overflow-hidden flex flex-col shrink-0 transition-colors ${
              isDarkPhone
                ? "bg-[#0f0f0f] text-[#f1f1f1]"
                : "bg-white text-[#0f0f0f]"
            }`}
          >
            <div className="flex justify-between px-5 pt-2.5 pb-1.5 text-[11px] font-semibold">
              <span>21:42</span>
              <span>5G • 84%</span>
            </div>

            <div className="flex items-center justify-between px-3.5 py-2">
              <div className="flex items-center gap-1.5 font-extrabold text-base tracking-tight">
                <div className="w-6 h-4 bg-[#ff0000] rounded flex items-center justify-center">
                  <div className="w-0 h-0 border-y-[3.5px] border-y-transparent border-l-[6px] border-l-white ml-0.5" />
                </div>
                <span>YouTube</span>
              </div>
              <div className="flex gap-3 text-xs opacity-75">
                <span>Cast</span>
                <span>Sino</span>
                <span>Busca</span>
              </div>
            </div>

            <div
              className={`flex gap-2 px-3 pt-1.5 pb-2.5 overflow-hidden border-b ${
                isDarkPhone ? "border-[#272727]" : "border-[#e5e5e5]"
              }`}
            >
              <span
                className={`px-2.5 py-1 rounded-lg text-[11px] font-medium whitespace-nowrap ${
                  isDarkPhone
                    ? "bg-[#f1f1f1] text-[#0f0f0f]"
                    : "bg-[#0f0f0f] text-white"
                }`}
              >
                Tudo
              </span>
              {["Psicologia", "Animação", "Recentes"].map((chip) => (
                <span
                  key={chip}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-medium whitespace-nowrap ${
                    isDarkPhone ? "bg-[#272727]" : "bg-[#f2f2f2]"
                  }`}
                >
                  {chip}
                </span>
              ))}
            </div>

            <div className="flex-1 overflow-y-auto">
              <div className="mb-4">
                <div className="relative w-full aspect-video bg-[#1c1f26] overflow-hidden">
                  {thumbDataUrl ? (
                    <img
                      src={thumbDataUrl}
                      alt="Thumbnail preview"
                      className="w-full h-full object-cover block"
                    />
                  ) : (
                    <div
                      className="w-full h-full flex flex-col items-center justify-center text-white text-center p-4"
                      style={{
                        background:
                          "radial-gradient(circle at 75% 50%, #2a183b 0%, #050811 75%)",
                      }}
                    >
                      <span className="font-black text-lg tracking-wide drop-shadow">
                        COLE SUA THUMB (CTRL+V)
                      </span>
                      <small className="text-[#ffc928] mt-1 text-[11px]">
                        Padrão Só um Rabisco 16:9
                      </small>
                    </div>
                  )}
                  <div className="absolute right-2 bottom-2 bg-black/80 text-white text-[11px] font-semibold px-1.5 py-0.5 rounded">
                    {duracao || "00:00"}
                  </div>
                </div>

                <div className="flex gap-3 px-3 pt-3 pb-1 items-start">
                  <div className="w-9 h-9 rounded-full shrink-0 overflow-hidden bg-[#1b1f2a]">
                    <svg width="36" height="36" viewBox="0 0 36 36">
                      <rect width="36" height="36" fill="#232938" />
                      <path
                        d="M8 36 C8 27, 28 27, 28 36 Z"
                        fill="#FFC928"
                        stroke="#000"
                        strokeWidth="1.8"
                      />
                      <circle
                        cx="18"
                        cy="17"
                        r="9.5"
                        fill="#F8FAFC"
                        stroke="#000"
                        strokeWidth="1.8"
                      />
                      <path
                        d="M9 14 L7 9 L12 11 L15 6 L19 10 L23 6 L25 11 L29 10 L27 15 Z"
                        fill="#111"
                      />
                      <ellipse cx="15" cy="17" rx="1.3" ry="2" fill="#111" />
                      <ellipse cx="21" cy="17" rx="1.3" ry="2" fill="#111" />
                    </svg>
                  </div>

                  <div className="flex-1 min-w-0">
                    <div
                      ref={titlePreviewRef}
                      className="text-[14px] font-medium leading-[19px] line-clamp-2 break-words"
                    >
                      {textoLimpo || "Título do vídeo..."}
                    </div>
                    <div
                      className={`text-[12px] mt-1 leading-4 ${
                        isDarkPhone ? "text-[#aaaaaa]" : "text-[#606060]"
                      }`}
                    >
                      Só um rabisco • {metaTexto}
                    </div>
                  </div>
                  <div
                    className={`text-base px-0.5 ${
                      isDarkPhone ? "text-[#aaaaaa]" : "text-[#606060]"
                    }`}
                  >
                    ⋮
                  </div>
                </div>
              </div>

              <div className="opacity-45 mb-4">
                <div
                  className="relative w-full aspect-video flex items-center justify-center text-[#8da9c4] text-xs font-semibold"
                  style={{
                    background: "linear-gradient(135deg, #1f3a52, #0d1b2a)",
                  }}
                >
                  Vídeo concorrente no feed
                  <div className="absolute right-2 bottom-2 bg-black/80 text-white text-[11px] font-semibold px-1.5 py-0.5 rounded">
                    12:15
                  </div>
                </div>
                <div className="flex gap-3 px-3 pt-3 pb-1 items-start">
                  <div
                    className={`w-9 h-9 rounded-full shrink-0 ${
                      isDarkPhone ? "bg-[#272727]" : "bg-[#e5e5e5]"
                    }`}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="text-[14px] font-medium leading-[19px] line-clamp-2">
                      Como Organizar Sua Rotina Sem Perder Tempo
                    </div>
                    <div
                      className={`text-[12px] mt-1 ${
                        isDarkPhone ? "text-[#aaaaaa]" : "text-[#606060]"
                      }`}
                    >
                      Canal Exemplo • 94 mil visualizações • há 2 dias
                    </div>
                  </div>
                  <div
                    className={`text-base px-0.5 ${
                      isDarkPhone ? "text-[#aaaaaa]" : "text-[#606060]"
                    }`}
                  >
                    ⋮
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
