---
description: Lê o arquivo de timestamps do Whisper e monta os prompts visuais sincronizados
---

# Sincronização de Áudio com Storyboard

1. Localize a pasta do projeto ativo em `projetos/` que contenha `03-timestamps.json` e o roteiro completo (`02-narracao.txt`).
2. Leia o roteiro completo e os intervalos de fala decupados, mantendo cortes dinâmicos a cada **1,5 a 3 segundos** no máximo (25 a 35 cenas por minuto), com timestamps `[MM:SS]` únicos e estritamente crescentes (nunca repita o mesmo segundo em duas linhas).
3. Verifique se é um Short (`9:16`) ou um vídeo longo (`16:9`).
4. Para cada corte, crie uma cena/ação específica em **INGLÊS** fiel à fala exata daquele momento no roteiro (sem poses genéricas ou repetidas em sequência; textos dentro da imagem em **PORTUGUÊS DO BRASIL**), descrevendo APENAS o fundo (cenário vazio ou objeto/ícone em destaque, sem pessoas ou personagens; o personagem entra depois em camada), e concatene o sufixo de fundo completo em **todas as linhas** seguindo `.agent/rules/02-identidade-visual-e-prompts.md`.
5. Salve o resultado no formato `[MM:SS] Prompt em inglês` em `04-storyboard-e-prompts.md` dentro da pasta do projeto.
6. **Substitua o arquivo `prompts_imagens.txt` na raiz do repositório** com todos os prompts `[MM:SS] ...` gerados para este projeto (um por bloco, separados por linha em branco).
7. Gere o arquivo `cenas.json` na pasta do projeto seguindo a estrutura em camadas (versão 2):
   - Use `"formato": "9:16"` para Shorts ou `"16:9"` para vídeos longos.
   - Aponte `"audio"` para `"assets_atual/audio.wav"`, `"arquivo"` e `"fundo.arquivo"` para `"assets_atual/cenas/cena_01.png"` (em sequência) e `"fundo.prompt"` com o prompt do fundo.
   - Inclua `"personagem"` com `tipo` (`"pose"`, `"sprite"` ou `"none"`), `asset`, `posicao`, `escala`, `flip` e `animacao` (ou gere pelo Studio usando a biblioteca em `assets/personagem/sprites_output/`).
   - Varie `"efeito"` entre `"pop-in"`, `"zoom-in"`, `"zoom-out"`, `"shake"`, `"slide-up"` e `"cut"` conforme a emoção da frase.
   - Preencha `"texto"` apenas com palavras-chave curtas (máximo 3 palavras) nos momentos de maior impacto.
