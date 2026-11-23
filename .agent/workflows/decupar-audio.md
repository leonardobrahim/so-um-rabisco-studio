---
description: Lê o arquivo de timestamps do Whisper e monta os prompts visuais sincronizados
---

# Sincronização de Áudio com Storyboard

1. Localize a pasta mais recente em `projetos/` que contenha o arquivo `03-timestamps.json` (ou o arquivo indicado por mim).
2. Leia os intervalos de fala frase por frase e quebre trechos longos em blocos visuais de 1,5 a 2 segundos para manter a retenção alta.
3. Verifique se é um vídeo longo (`16:9`) ou Short (`9:16`).
4. Gere a lista completa de cenas no formato `[MM:SS] Prompt em inglês` seguindo `.agent/rules/02-identidade-visual-e-prompts.md`, salvando o resultado em `04-storyboard-e-prompts.md` dentro da mesma pasta do projeto.
5. **Substitua o arquivo `prompts_imagens.txt` na raiz do repositório** com todos os prompts `[MM:SS] ...` gerados para este projeto (um por bloco, separados por linha em branco).
6. Se existir um arquivo `cenas.json` de template na pasta `template-hyperframes/`, gere também uma cópia preenchida na pasta do projeto com os tempos de entrada, saída e sugestões de animação (`zoom-in`, `shake`, `slide-up`, `cut`).
7. Gere o arquivo `cenas.json` na pasta do projeto seguindo a estrutura do `template-hyperframes/cenas.json`:
   - Use `"formato": "9:16"` para Shorts ou `"16:9"` para vídeos longos.
   - Aponte `"audio"` para `"assets_atual/audio.wav"` e cada `"arquivo"` para `"assets_atual/cenas/cena_01.png"` (em sequência).
   - Varie `"efeito"` entre `"pop-in"`, `"zoom-in"`, `"zoom-out"`, `"shake"`, `"slide-up"` e `"cut"` conforme a emoção da frase.
   - Preencha `"texto"` apenas com palavras-chave curtas (máximo 3 palavras) nos momentos de maior impacto.