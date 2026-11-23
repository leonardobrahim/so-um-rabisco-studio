import { useEffect, useRef, useState, type DragEvent } from "react";
import {
  ImagePlus,
  Loader2,
  Sparkles,
  CheckCircle2,
  Trash2,
  Images,
} from "lucide-react";
import { api } from "../api";

interface Props {
  projeto: string;
  onAtualizado: () => void;
}

export function TabImagens({ projeto, onAtualizado }: Props) {
  const [fila, setFila] = useState<File[]>([]);
  const [cenasProntas, setCenasProntas] = useState<string[]>([]);
  const [rawArquivos, setRawArquivos] = useState<string[]>([]);
  const [limparAnteriores, setLimparAnteriores] = useState(true);
  const [carregando, setCarregando] = useState(true);
  const [processando, setProcessando] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [cacheBust, setCacheBust] = useState(() => Date.now());
  const [log, setLog] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  async function carregarLista() {
    setCarregando(true);
    try {
      const res = await api.listarImagens(projeto);
      setCenasProntas(res.cenas);
      setRawArquivos(res.raw);
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Erro ao listar imagens");
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    setFila([]);
    setLog(null);
    setErro(null);
    void carregarLista();
  }, [projeto]);

  function adicionarArquivos(fileList: FileList | null) {
    if (!fileList) return;
    const validos = Array.from(fileList).filter((f) =>
      /\.(png|jpe?g|webp)$/i.test(f.name)
    );
    if (validos.length > 0) {
      setFila((prev) => [...prev, ...validos]);
    }
  }

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
    try {
      const res = await api.uploadImagens(projeto, fila, limparAnteriores);
      setCenasProntas(res.cenas_geradas);
      setFila([]);
      setCacheBust(Date.now());
      setLog(
        res.log ||
          `${res.cenas_geradas.length} imagens processadas em midia/cenas/.`
      );
      await carregarLista();
      onAtualizado();
    } catch (err) {
      setErro(err instanceof Error ? err.message : "Erro ao processar imagens");
    } finally {
      setProcessando(false);
    }
  }

  return (
    <div className="flex flex-col gap-5">
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
            Upload em lote de ilustrações (<code>midia/raw/</code>)
          </div>
          <p className="text-xs text-slate-400">
            Arraste várias imagens (.png, .jpg, .webp) na ordem das cenas ou clique para selecionar.
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
                  onClick={handleEnviarEProcessar}
                  disabled={processando}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#ffc928] hover:bg-[#ffd452] disabled:opacity-50 text-black font-semibold text-xs transition cursor-pointer"
                >
                  {processando ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Sparkles className="w-4 h-4" />
                  )}
                  Enviar e Limpar Fundo (limpar_imagens.py)
                </button>
              </div>
            </div>

            <div className="max-h-40 overflow-y-auto grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-2">
              {fila.map((f, idx) => (
                <div
                  key={`${f.name}-${idx}`}
                  className="bg-[#0e1117] border border-slate-800 rounded-lg px-2.5 py-2 flex items-center justify-between gap-1 text-[11px]"
                >
                  <span className="truncate text-slate-300" title={f.name}>
                    {idx + 1}. {f.name}
                  </span>
                  <button
                    type="button"
                    onClick={() =>
                      setFila((prev) => prev.filter((_, i) => i !== idx))
                    }
                    className="text-slate-500 hover:text-rose-400 shrink-0 cursor-pointer"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
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
        ) : cenasProntas.length === 0 ? (
          <div className="py-10 text-center text-xs text-slate-500 border border-slate-800/70 rounded-xl bg-[#0e1117]">
            Nenhuma imagem processada em <code>midia/cenas/</code> ainda.
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {cenasProntas.map((nome) => (
              <div
                key={nome}
                className="bg-[#0e1117] border border-slate-800 rounded-xl overflow-hidden flex flex-col"
              >
                <div className="aspect-video checkerboard-dark flex items-center justify-center p-2">
                  <img
                    src={api.imagemCenaUrl(projeto, nome, cacheBust)}
                    alt={nome}
                    className="max-h-full max-w-full object-contain"
                    loading="lazy"
                  />
                </div>
                <div className="px-2.5 py-1.5 border-t border-slate-800/80 text-[11px] font-mono text-slate-300 truncate">
                  {nome}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
