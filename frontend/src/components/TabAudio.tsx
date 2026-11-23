import { useEffect, useRef, useState, type DragEvent } from "react";
import {
  Upload,
  Loader2,
  Volume2,
  Clock,
  CheckCircle2,
  Search,
  Play,
} from "lucide-react";
import { api } from "../api";
import type { TimestampsData } from "../types";

interface Props {
  projeto: string;
  temAudio: boolean;
  onAtualizado: () => void;
}

export function TabAudio({ projeto, temAudio, onAtualizado }: Props) {
  const [timestamps, setTimestamps] = useState<TimestampsData | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [processando, setProcessando] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [busca, setBusca] = useState("");
  const [log, setLog] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [audioVersion, setAudioVersion] = useState(() => Date.now());
  const [audioDisponivel, setAudioDisponivel] = useState(temAudio);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    setAudioDisponivel(temAudio);
  }, [temAudio]);

  useEffect(() => {
    let ativo = true;
    setCarregando(true);
    setErro(null);
    setLog(null);
    api
      .lerTimestamps(projeto)
      .then((res) => {
        if (!ativo) return;
        setTimestamps(res.dados);
      })
      .catch((err) => {
        if (!ativo) return;
        setErro(err instanceof Error ? err.message : "Erro ao carregar timestamps");
      })
      .finally(() => {
        if (ativo) setCarregando(false);
      });
    return () => {
      ativo = false;
    };
  }, [projeto]);

  async function enviarAudio(file: File | undefined) {
    if (!file) return;
    setProcessando(true);
    setErro(null);
    setLog(null);
    try {
      const res = await api.uploadAudio(projeto, file);
      setTimestamps(res.timestamps);
      setAudioDisponivel(true);
      setAudioVersion(Date.now());
      setLog(res.log || "Áudio salvo e 03-timestamps.json gerado com sucesso!");
      onAtualizado();
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Erro ao processar áudio");
    } finally {
      setProcessando(false);
    }
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
    enviarAudio(e.dataTransfer.files[0]);
  }

  function tocarNoTempo(inicio: number) {
    const el = audioRef.current;
    if (!el) return;
    el.currentTime = inicio;
    void el.play();
  }

  const segmentosFiltrados = (timestamps?.segmentos || []).filter((seg) =>
    busca.trim()
      ? seg.texto.toLowerCase().includes(busca.toLowerCase()) ||
        seg.marca.includes(busca)
      : true
  );

  return (
    <div className="flex flex-col gap-5">
      {/* Upload + Player */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div
          onClick={() => !processando && fileInputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-xl p-6 text-center transition cursor-pointer flex flex-col items-center justify-center gap-2.5 ${
            dragOver
              ? "border-[#ffc928] bg-[#ffc928]/5"
              : "border-slate-700 hover:border-[#ffc928]/60 bg-[#12151d]"
          } ${processando ? "opacity-60 pointer-events-none" : ""}`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".wav,.mp3,.m4a,audio/*"
            hidden
            onChange={(e) => {
              void enviarAudio(e.target.files?.[0]);
              e.target.value = "";
            }}
          />
          {processando ? (
            <>
              <Loader2 className="w-8 h-8 text-[#ffc928] animate-spin" />
              <div className="text-sm font-semibold text-slate-200">
                Executando Whisper (scripts/extrair_tempos.py)...
              </div>
              <p className="text-xs text-slate-400">
                Isso pode levar alguns segundos dependendo da duração do áudio.
              </p>
            </>
          ) : (
            <>
              <Upload className="w-8 h-8 text-[#ffc928]" />
              <div className="text-sm font-semibold text-slate-200">
                Enviar <code className="text-[#ffc928]">audio.wav</code> e extrair tempos
              </div>
              <p className="text-xs text-slate-400">
                Arraste o arquivo aqui ou clique para selecionar. Salva em{" "}
                <code>midia/audio.wav</code> e gera <code>03-timestamps.json</code>.
              </p>
            </>
          )}
        </div>

        {/* Player & Resumo */}
        <div className="bg-[#141821] border border-slate-800 rounded-xl p-5 flex flex-col justify-between gap-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
              <Volume2 className="w-4 h-4 text-[#ffc928]" />
              <span>Player de Narração</span>
            </div>
            {timestamps && (
              <span className="text-xs px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-[#ffc928]" />
                Duração total: {timestamps.duracao_total}s
              </span>
            )}
          </div>

          {audioDisponivel ? (
            <audio
              ref={audioRef}
              controls
              src={api.audioUrl(projeto, audioVersion)}
              className="w-full"
            />
          ) : (
            <div className="py-4 text-center text-xs text-slate-500 border border-slate-800/70 rounded-lg bg-[#0e1117]">
              Nenhum áudio encontrado em <code>midia/audio.wav</code> ainda.
            </div>
          )}

          <div className="text-xs text-slate-400 flex items-center justify-between">
            <span>
              Segmentos detectados:{" "}
              <strong className="text-slate-200">
                {timestamps?.segmentos?.length ?? 0}
              </strong>
            </span>
            <span>Clique em um trecho abaixo para ouvir no player</span>
          </div>
        </div>
      </div>

      {erro && (
        <div className="px-4 py-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs whitespace-pre-wrap">
          {erro}
        </div>
      )}

      {log && (
        <div className="px-4 py-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-start gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5" />
          <pre className="whitespace-pre-wrap font-mono text-[11px]">{log}</pre>
        </div>
      )}

      {/* Timestamps Table */}
      <div className="bg-[#141821] border border-slate-800 rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-sm font-semibold text-slate-200">
            03-timestamps.json
          </h3>
          <div className="relative w-64">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Filtrar falas..."
              className="w-full bg-[#0e1117] border border-slate-700 focus:border-[#ffc928] rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-100 outline-none"
            />
          </div>
        </div>

        {carregando ? (
          <div className="p-8 flex items-center justify-center text-xs text-slate-400 gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-[#ffc928]" />
            Carregando timestamps...
          </div>
        ) : !timestamps ? (
          <div className="p-8 text-center text-xs text-slate-500">
            Envie um arquivo de áudio acima para gerar <code>03-timestamps.json</code>.
          </div>
        ) : (
          <div className="max-h-[420px] overflow-y-auto divide-y divide-slate-800/70">
            {segmentosFiltrados.map((seg, i) => (
              <div
                key={`${seg.inicio}-${i}`}
                onClick={() => audioDisponivel && tocarNoTempo(seg.inicio)}
                className={`px-4 py-2.5 flex items-start gap-3 text-xs transition ${
                  audioDisponivel
                    ? "hover:bg-slate-800/40 cursor-pointer"
                    : ""
                }`}
              >
                <span className="font-mono text-[#ffc928] shrink-0 mt-0.5">
                  {seg.marca}
                </span>
                <span className="font-mono text-slate-500 shrink-0 mt-0.5 w-28">
                  {seg.inicio.toFixed(2)}s → {seg.fim.toFixed(2)}s
                </span>
                <p className="text-slate-200 flex-1 leading-relaxed">{seg.texto}</p>
                {audioDisponivel && (
                  <Play className="w-3.5 h-3.5 text-slate-500 shrink-0 mt-0.5" />
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
