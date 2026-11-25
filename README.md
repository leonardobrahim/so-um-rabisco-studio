# Só um Rabisco — Studio

Aplicativo web local e conjunto de automações para gerenciar a produção de vídeos do canal **Só um Rabisco** (roteiro, narração com Whisper, storyboard, remoção de fundo em lote, preview de thumbnail mobile e preparação de render).

## Estrutura do Repositório

- `backend/` — API em **FastAPI** (`backend/main.py`) para gerenciar projetos, arquivos e execução dos scripts.
- `frontend/` — Interface web em **React + TypeScript + Vite + Tailwind CSS**.
- `assets/` — Biblioteca fixa do canal (`personagem/grades_input/`, `personagem/sprites_output/`, `secundarios/`, `audio-base/`).
- `scripts/` — Automações em Python:
  - `extrair_tempos.py` — Transcrição e timestamps por palavra/segmento via `faster-whisper`.
  - `limpar_imagens.py` — Remoção de fundo branco externo em lote com OpenCV/Pillow (ou `--manter-fundo` para vídeos longos).
  - `cortar_sprites.py` — Recorte automático de grades 2x2 em quadros `512x512` com fundo transparente e geração de `strip.png` horizontal para GSAP (use `--poses` para grades de poses avulsas com `mesma_escala=False`).
  - `preparar_render.py` — Cópia de `cenas.json`, áudio e PNGs para `template-remotion/public/`.
- `template-remotion/` — Composição em React/Remotion para renderização fluida do vídeo.
- `preview-thumb/` — Preview standalone de thumbnail mobile.
- `.agent/` — Regras e workflows de criação de roteiro, prompts visuais e SEO.
- `iniciar_studio.bat` — Script para iniciar backend e frontend juntos no Windows.

## Pré-requisitos

- **Python 3.10+** (com ambiente virtual `.venv` na raiz)
- **Node.js 18+** e **npm**

## Instalação

1. Crie e ative o ambiente virtual na raiz e instale as dependências Python:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Instale as dependências do frontend:
   ```powershell
   cd frontend
   npm install
   ```

## Como Usar

Execute o arquivo `iniciar_studio.bat` na raiz do repositório (ou dê dois cliques nele). Ele iniciará:
- **Frontend**: `http://localhost:5173`
- **Backend API (Docs)**: `http://localhost:8000/docs`

### Fluxo por Projeto (5 Abas)

1. **Roteiro**: Edição e salvamento de `02-narracao.txt` com contagem de palavras e duração estimada.
2. **Áudio**: Upload de `audio.wav` com execução automática de `scripts/extrair_tempos.py` e player interativo de `03-timestamps.json`.
3. **Storyboard**: Editor visual/JSON de `cenas.json`, cópia rápida de prompts de `04-storyboard-e-prompts.md` e sincronização com `prompts_imagens.txt`.
4. **Imagens**: Upload em lote para `midia/raw/` com remoção de fundo via `scripts/limpar_imagens.py` e galeria dos PNGs em `midia/cenas/`.
5. **Thumb / Render**: Preview mobile do YouTube (com suporte a `Ctrl + V` de imagem e validação de corte de título) e execução de `scripts/preparar_render.py`.
