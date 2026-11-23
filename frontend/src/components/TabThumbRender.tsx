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

export function TabThumbRender({ projeto, onAtualizado }: Props) {
  const [thumbDataUrl, setThumbDataUrl] = useState<string | null>(null);
  const [titulo, setTitulo] = useState(
    projeto.nome.replace(/^\d{4}-\d{2}-/, "").replace(/-/g, " ") ||
      "Por Que Você Sempre Fica Sem Dinheiro Todo Mês"
  );
  const [duracao, setDuracao] = useState(() => formatarDuracao(projeto.duracao_total));
  const [metaTexto, setMetaTexto] = useState("18 mil visualizações • há 4 horas");
  const [temaPhone, setTemaPhone] = useState<"dark" | "light">("dark");
  const [dragOver, setDragOver] = useState(false);
  const [cortouNoCelular, setCortouNoCelular] = useState(false);

  const [preparando, setPreparando] = useState(false);
  const [renderLog, setRenderLog] = useState<string | null>(null);
  const [renderErro, setRenderErro] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const titlePreviewRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setDuracao(formatarDuracao(projeto.duracao_total));
    setRenderLog(null);
    setRenderErro(null);
  }, [projeto.nome, projeto.duracao_total]);

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

  // Suporte para Ctrl + V de imagem direto na tela
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

  // Verifica se o texto passou de 2 linhas no card mobile
  useEffect(() => {
    const id = requestAnimationFrame(() => {
      const el = titlePreviewRef.current;
      if (!el) return;
      setCortouNoCelular(el.scrollHeight > el.clientHeight + 1);
    });
    return () => cancelAnimationFrame(id);
  }, [titulo]);

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
      const res = await api.prepararRender(projeto.nome);
      setRenderLog(res.log || "Template preparado com sucesso!");
      onAtualizado();
    } catch (err) {
      setRenderErro(
        err instanceof Error ? err.message : "Erro ao preparar render"
      );
    } finally {
      setPreparando(false);
    }
  }

  const textoLimpo = titulo.trim();
  const palavras = textoLimpo ? textoLimpo.split(/\s+/).filter(Boolean).length : 0;
  const caracteres = textoLimpo.length;

  const classePalavras =
    palavras >= 7 && palavras <= 8
      ? "bg-emerald-500/15 text-emerald-400"
      : palavras >= 5 && palavras <= 10
      ? "bg-amber-500/15 text-amber-300"
      : "bg-rose-500/15 text-rose-400";

  const classeCaracteres =
    caracteres >= 45 && caracteres <= 55
      ? "bg-emerald-500/15 text-emerald-400"
      : caracteres <= 65
      ? "bg-amber-500/15 text-amber-300"
      : "bg-rose-500/15 text-rose-400";

  const isDarkPhone = temaPhone === "dark";

  return (
    <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
      {/* Coluna Esquerda: Controles de Thumb + Preparar Render */}
      <div className="xl:col-span-7 flex flex-col gap-5">
        {/* Card Preparar Render */}
        <div className="bg-[#141821] border border-slate-800 rounded-2xl p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <Rocket className="w-4 h-4 text-[#ffc928]" />
                Preparar Render (<code>template-hyperframes/</code>)
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Copia <code>cenas.json</code>, áudio e PNGs recortados para a pasta de renderização via{" "}
                <code>scripts/preparar_render.py</code>.
              </p>
            </div>
            <button
              type="button"
              onClick={handlePrepararRender}
              disabled={preparando || !projeto.tem_cenas_json}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#ffc928] hover:bg-[#ffd452] disabled:opacity-45 text-black font-bold text-xs transition cursor-pointer shadow-sm"
            >
              {preparando ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Rocket className="w-4 h-4" />
              )}
              Preparar Render Agora
            </button>
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
                    ? `${projeto.qtd_cenas_json} cenas`
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
        </div>

        {/* Card Controles do Preview Mobile */}
        <div className="bg-[#141821] border border-slate-800 rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <Smartphone className="w-4 h-4 text-[#ffc928]" />
              Preview de Clique Mobile
            </h3>
            <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-[#ffc928] text-black uppercase">
              Só um Rabisco
            </span>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-400">
              1. Thumbnail (16:9)
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
                  Clique, arraste ou aperte <strong className="text-[#ffc928]">Ctrl + V</strong> em qualquer lugar
                </span>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-400">
              2. Título do Vídeo (Regra: 7 a 8 palavras)
            </label>
            <textarea
              value={titulo}
              onChange={(e) => setTitulo(e.target.value)}
              rows={2}
              placeholder="Digite o título para testar no celular..."
              className="w-full bg-[#0e1117] border border-slate-700 focus:border-[#ffc928] rounded-xl p-3 text-sm text-slate-100 outline-none resize-y"
            />
            <div className="flex flex-wrap gap-2">
              <span className={`text-xs font-semibold px-2.5 py-1 rounded-lg ${classePalavras}`}>
                {palavras} {palavras === 1 ? "palavra" : "palavras"}
              </span>
              <span className={`text-xs font-semibold px-2.5 py-1 rounded-lg ${classeCaracteres}`}>
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

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-400">Duração</label>
              <input
                type="text"
                value={duracao}
                onChange={(e) => setDuracao(e.target.value)}
                className="w-full bg-[#0e1117] border border-slate-700 focus:border-[#ffc928] rounded-xl px-3 py-2 text-xs text-slate-100 outline-none"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-400">Views e Tempo</label>
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
        </div>
      </div>

      {/* Coluna Direita: Simulador Mobile YouTube */}
      <div className="xl:col-span-5 flex justify-center">
        <div
          className={`w-[360px] h-[680px] rounded-[38px] border-[9px] border-[#262a34] shadow-2xl overflow-hidden flex flex-col shrink-0 transition-colors ${
            isDarkPhone
              ? "bg-[#0f0f0f] text-[#f1f1f1]"
              : "bg-white text-[#0f0f0f]"
          }`}
        >
          {/* Status bar */}
          <div className="flex justify-between px-5 pt-2.5 pb-1.5 text-[11px] font-semibold">
            <span>21:42</span>
            <span>5G • 84%</span>
          </div>

          {/* YouTube Header */}
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

          {/* Chips */}
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

          {/* Feed */}
          <div className="flex-1 overflow-y-auto">
            {/* Seu Vídeo */}
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

            {/* Vídeo Concorrente no Feed */}
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
      </div>
    </div>
  );
}
