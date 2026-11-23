import { useEffect, useState } from "react";
import { Save, Loader2, CheckCircle2, FileText, Clock } from "lucide-react";
import { api } from "../api";

interface Props {
  projeto: string;
  onAtualizado: () => void;
}

export function TabRoteiro({ projeto, onAtualizado }: Props) {
  const [conteudo, setConteudo] = useState("");
  const [original, setOriginal] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [mensagem, setMensagem] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    let ativo = true;
    setCarregando(true);
    setMensagem(null);
    setErro(null);
    api
      .lerNarracao(projeto)
      .then((res) => {
        if (!ativo) return;
        setConteudo(res.conteudo);
        setOriginal(res.conteudo);
      })
      .catch((err) => {
        if (!ativo) return;
        setErro(err instanceof Error ? err.message : "Erro ao carregar narração");
      })
      .finally(() => {
        if (ativo) setCarregando(false);
      });
    return () => {
      ativo = false;
    };
  }, [projeto]);

  async function handleSalvar() {
    setSalvando(true);
    setErro(null);
    setMensagem(null);
    try {
      const res = await api.salvarNarracao(projeto, conteudo);
      setOriginal(conteudo);
      setMensagem(`Salvo em 02-narracao.txt (${res.palavras} palavras)`);
      onAtualizado();
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Erro ao salvar narração");
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

  const palavras = conteudo.trim() ? conteudo.trim().split(/\s+/).filter(Boolean).length : 0;
  const caracteres = conteudo.length;
  const minutosEstimados = palavras / 145;
  const min = Math.floor(minutosEstimados);
  const seg = Math.round((minutosEstimados - min) * 60);
  const alterado = conteudo !== original;

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
        <div className="flex items-center gap-3 flex-wrap">
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
          <span className="text-xs px-2.5 py-1 rounded-lg bg-slate-800/80 text-slate-300 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-slate-400" />
            ~{String(min).padStart(2, "0")}:{String(seg).padStart(2, "0")} estimados
          </span>
          {alterado && (
            <span className="text-xs px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 font-medium">
              Alterações não salvas
            </span>
          )}
        </div>

        <button
          type="button"
          onClick={handleSalvar}
          disabled={salvando}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#ffc928] hover:bg-[#ffd452] disabled:opacity-50 text-black font-semibold text-xs transition cursor-pointer"
        >
          {salvando ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          Salvar Narração (Ctrl+S)
        </button>
      </div>

      {erro && (
        <div className="px-4 py-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
          {erro}
        </div>
      )}

      {mensagem && (
        <div className="px-4 py-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          {mensagem}
        </div>
      )}

      <textarea
        value={conteudo}
        onChange={(e) => setConteudo(e.target.value)}
        placeholder="Cole ou escreva aqui o texto corrido de narração que vai para o VoiceStudio..."
        className="flex-1 min-h-[440px] w-full bg-[#12151d] border border-slate-800 focus:border-[#ffc928]/70 rounded-xl p-5 text-sm leading-relaxed text-slate-100 outline-none resize-none font-sans"
      />
    </div>
  );
}
