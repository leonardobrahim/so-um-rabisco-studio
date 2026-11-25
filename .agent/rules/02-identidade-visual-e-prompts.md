# Identidade Visual, Bíblia de Estilo e Prompts - Só um Rabisco

## Arquitetura Visual em Camadas (Shorts e Vídeos Longos)
Cada cena decupada gera **DOIS prompts distintos em INGLÊS** (sem marcações `[MM:SS]` dentro do texto enviado ao gerador de imagens):
1. **`prompt_fundo` (Camada 1 — Cenário/Fundo):** apenas o cenário ou objeto de apoio, **zero pessoas, zero silhuetas humanas, zero protagonista**, com espaço livre no centro ou centro-inferior para encaixar o personagem por cima.
2. **`prompt_personagem` (Camada 2 — Personagem Isolado):** o personagem atuando na cena (ou o asset transparente equivalente da biblioteca `assets/personagem/`), sempre isolado em **fundo branco sólido puro (`#FFFFFF`)** para facilitar recorte e sobreposição.

---

## DNA Artístico Obrigatório (para ambas as camadas)
Todo prompt (tanto `prompt_fundo` quanto `prompt_personagem`) deve seguir rigorosamente este DNA artístico:
```text
Minimalist 2D cartoon doodle illustration, hand-drawn sketch aesthetic with thick clean black marker outlines and flat colors, slightly irregular hand-crafted lines, simple expressive composition. Strictly NO photorealism, NO 3D rendering, NO heavy gradients, NO realistic cast shadows, NO complex textures.
```

---

## Camada 1: Regras do Prompt de Fundo (`prompt_fundo`)
- **Zero pessoas:** nunca inclua personagens, silhuetas humanas ou o protagonista no fundo. Deixe espaço livre no centro ou centro-inferior para encaixar o personagem por cima.
- **Vídeos Longos (`16:9`):**
  - **Nunca gere fundo todo branco.**
  - Crie cenários completos com cores, objetos, móveis, paisagens e detalhes diretamente ligados ao que está sendo narrado naquele trecho (ex.: quarto à noite, mesa de estudos bagunçada, corredor de mercado, sala de aula, parque, escritório).
  - Use **obrigatoriamente tons suaves, pastéis ou dessaturados** (ex.: bege quente `#EFECE6`, azul-acinzentado `#3A4659`, verde-sálvia `#DCE5DC`, azul-céu claro `#DCE8EE`, lavanda suave `#E6E4EE`, areia `#EDE6D8`).
  - **Proibido** usar cores muito fortes, saturadas ou neon (como azulão, vermelhão ou amarelão) para não competir com o moletom amarelo `#FFC928` do protagonista.
  - Termine sempre com:
    `No characters or people in the scene. Soft muted pastel colors only, no overly bright, saturated, or neon colors.`
- **Shorts (`9:16`):**
  - Mantenha fundo branco sólido puro (`pure solid white background (#FFFFFF)`) limpo, com no máximo um objeto simples de apoio quando necessário.

---

## Camada 2: Regras do Prompt de Personagem (`prompt_personagem`)
- **Fundo branco puro obrigatório:** tanto em `16:9` quanto em `9:16`, gere o personagem sempre isolado em fundo branco sólido (`pure solid white background (#FFFFFF)`) para facilitar o recorte automático (`limpar_imagens.py`) e a sobreposição sobre o fundo ilustrado.
- **Enquadramento seguro:** plano médio ou corpo inteiro com margem livre nas bordas para nunca cortar o cabelo, a cabeça ou as mãos (ou close-up expressivo bem enquadrado quando a cena pedir).
- **Descrição fixa do protagonista (repetir em toda cena em que ele aparecer):**
  `Compact cartoon character whose large rounded pale-white head with subtle light-blue shading on the left side takes up one-third of his height, messy irregular spiky black hair, simple oval black eyes, minimalist expressive face, wearing a bright yellow hoodie (#FFC928), dark navy blue pants, and low white sneakers with black details.`
- **Personagem secundária (quando a cena pedir outra pessoa, ex.: Bia):**
  `Cartoon girl with brown hair tied in a ponytail, green tank top, black leggings, holding a small notebook, same 2D hand-drawn marker doodle style.`
- **Ação e metáfora visual:** cada cena deve traduzir a fala exata daquele segundo em uma ação física, reação exagerada ou metáfora cômica, variando planos (close-up de expressão, plano médio, plano aberto) e sem repetir a mesma pose em cenas seguidas.
- **Textos internos:** qualquer texto desenhado em placas, cadernos, relógios ou etiquetas deve estar em **Português do Brasil**.

---

## Direção de Storyboard e Ritmo
- **Cortes naturais:** respeitando pontuação e sentido completo, com alvo de **2,5s a 4,5s** em `16:9` e **1,2s a 2,5s** em `9:16`, nunca partindo números ou frases no meio.
- **Limpeza de prompts:** nunca envie marcações `[MM:SS]` no texto dos prompts enviados aos geradores de imagem.
- **Proporção obrigatória:** `16:9` para vídeos longos do YouTube e `9:16` para Shorts, Reels e TikTok.
