import { useEffect, useState } from "react";
import {
  Save,
  Loader2,
  CheckCircle2,
  FileText,
  Clock,
  Wand2,
  ArrowRight,
} from "lucide-react";
import { api } from "../api";
import type { AbaId, ProjetoResumo } from "../types";

interface Props {
  projeto: ProjetoResumo;
  onAtualizado: () => void;
  onIrParaAba: (aba: AbaId) => void;
}

export function TabRoteiro({ projeto, onAtualizado, onIrParaAba }: Props) {
  const [conteudo, setConteudo] = useState("");
  const [original, setOriginal] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [gerando, setGerando] = useState(false);
  const [mensagem, setMensagem] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    let ativo = true;
    setCarregando(true);
    setMensagem(null);
    setErro(null);
    api
      .lerNarracao(projeto.nome)
      .then((res) => {
        if (!ativo) return;
        setConteudo(res.conteudo);
        setOriginal(res.conteudo);
      })
      .catch((err) => {
        if (!ativo) return;
        setErro(
          err instanceof Error ? err.message : "Erro ao carregar narração"
        );
      })
      .finally(() => {
        if (ativo) setCarregando(false);
      });
    return () => {
      ativo = false;
    };
  }, [projeto.nome]);

  async function handleSalvar(): Promise<boolean> {
    setSalvando(true);
    setErro(null);
    setMensagem(null);
    try {
      const res = await api.salvarNarracao(projeto.nome, conteudo);
      setOriginal(conteudo);
      setMensagem(`Salvo em 02-narracao.txt (${res.palavras} palavras).`);
      onAtualizado();
      return true;
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Erro ao salvar narração");
      return false;
    } finally {
      setSalvando(false);
    }
  }

  async function handleGerarStoryboardDoRoteiro() {
    if (!conteudo.trim()) {
      setErro("Escreva ou cole o roteiro antes de gerar o storyboard.");
      return;
    }
    setGerando(true);
    setErro(null);
    setMensagem(null);
    try {
      if (conteudo !== original) {
        await api.salvarNarracao(projeto.nome, conteudo);
        setOriginal(conteudo);
      }
      const res = await api.gerarStoryboard(projeto.nome, projeto.tipo);
      setMensagem(
        `Storyboard gerado automaticamente (${res.qtd_cenas} cenas em ${res.formato}, origem: ${
          res.origem === "timestamps" ? "03-timestamps.json" : "02-narracao.txt"
        }).`
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

  const palavras = conteudo.trim()
    ? conteudo.trim().split(/\s+/).filter(Boolean).length
    : 0;
  const caracteres = conteudo.length;
  const minutosEstimados = palavras / 145;
  const segTotais = Math.round(minutosEstimados * 60);
  const min = Math.floor(segTotais / 60);
  const seg = segTotais % 60;
  const alterado = conteudo !== original;

  const isShort = projeto.tipo === "short";
  const dentroMeta = isShort
    ? segTotais >= 25 && segTotais <= 65
    : segTotais >= 240 && segTotais <= 540;

  if (carregando) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400 gap-2 text-sm">
        <Loader2 className="w-4 h-4 animate-spin text-[#ffc928]" />
        Carregando 02-narracao.txt...
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3 bg-[#141821] border border-slate-800 rounded-xl px-4 py-3">
        <div className="flex items-center gap-2.5 flex-wrap">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
            <FileText className="w-4 h-4 text-[#ffc928]" />
            <span>02-narracao.txt</span>
          </div>
          <span className="text-xs px-2.5 py-1 rounded-lg bg-slate-800/80 text-slate-300">
            {palavras} palavras
          </span>
          <span className="text-xs px-2.5 py-1 rounded-lg bg-slate-800/80 text-slate-300">
            {caracteres} caracteres
          </span>
          <span
            className={`text-xs px-2.5 py-1 rounded-lg flex items-center gap-1.5 ${
              palavras === 0
                ? "bg-slate-800/80 text-slate-400"
                : dentroMeta
                ? "bg-emerald-500/15 text-emerald-300"
                : "bg-amber-500/15 text-amber-300"
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            ~{String(min).padStart(2, "0")}:{String(seg).padStart(2, "0")} •{" "}
            {isShort ? "Meta Short: 30s–60s" : "Meta Longo: 5m–8m"}
          </span>
          {alterado && (
            <span className="text-xs px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 font-medium">
              Alterações não salvas
            </span>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => void handleSalvar()}
            disabled={salvando || gerando}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-100 font-semibold text-xs transition cursor-pointer"
          >
            {salvando ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            Salvar (Ctrl+S)
          </button>

          <button
            type="button"
            onClick={() => void handleGerarStoryboardDoRoteiro()}
            disabled={gerando || salvando || !conteudo.trim()}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-[#ffc928] hover:bg-[#ffd452] disabled:opacity-50 text-black font-semibold text-xs transition cursor-pointer"
          >
            {gerando ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Wand2 className="w-4 h-4" />
            )}
            Gerar Cenas & Prompts
          </button>

          <button
            type="button"
            onClick={() => onIrParaAba("audio")}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-slate-700 hover:border-[#ffc928]/60 text-slate-200 text-xs font-medium transition cursor-pointer"
          >
            Áudio <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {erro && (
        <div className="px-4 py-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
          {erro}
        </div>
      )}

      {mensagem && (
        <div className="px-4 py-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4" />
            <span>{mensagem}</span>
          </div>
          <button
            type="button"
            onClick={() => onIrParaAba("storyboard")}
            className="px-2.5 py-1 rounded bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-200 font-semibold cursor-pointer"
          >
            Abrir Storyboard →
          </button>
        </div>
      )}

      <textarea
        value={conteudo}
        onChange={(e) => setConteudo(e.target.value)}
        placeholder={
          isShort
            ? "Escreva aqui a narração direta do Short (30s a 60s, gancho nos primeiros 2s e fechamento em loop)..."
            : "Cole ou escreva aqui o texto corrido de narração que vai para o VoiceStudio..."
        }
        className="flex-1 min-h-[440px] w-full bg-[#12151d] border border-slate-800 focus:border-[#ffc928]/70 rounded-xl p-5 text-sm leading-relaxed text-slate-100 outline-none resize-none font-sans"
      />
    </div>
  );
}
