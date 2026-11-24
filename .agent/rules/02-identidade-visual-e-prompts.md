# Identidade Visual, Storyboard e Prompts - Só um Rabisco

## Arquitetura Visual em Camadas (Shorts e Vídeos Longos)
- As cenas **não** são mais geradas com o personagem junto do cenário. Cada cena tem duas camadas independentes, montadas no HyperFrames/GSAP:
  1. **Fundo** (imagem gerada a partir do prompt): apenas cenário vazio ou objeto/ícone em destaque, **sem pessoas, sem personagens, sem mãos ou partes do corpo**.
  2. **Personagem** (PNG transparente da biblioteca `assets/personagem/sprites_output/`, gerada por `scripts/cortar_sprites.py`): pose estática (`frame_XX.png`) ou sprite sheet animado (`strip.png`), posicionado por cima do fundo.
- O prompt de imagem **nunca** descreve o protagonista. A pose, a posição e a animação do personagem são escolhidas depois (automaticamente pela biblioteca ou à mão no Studio), reagindo ao objeto/cenário da cena.
- Cada pasta da biblioteca tem um `meta.json` com `modo` (`poses` ou `sprite`), `fps` e **tags** (ex.: `ansioso`, `feliz`, `pensativo`, `andar`). O sistema pontua as tags de cada asset contra a fala e a emoção da cena e evita repetir o mesmo asset em sequência. As tags são editáveis no Studio.

## Estilo do Fundo
- Estilo padrão: ilustração 2D cartoon, minimalista, desenhada à mão com estética de rabisco/marcador, contornos pretos grossos e limpos, cores chapadas e linhas levemente irregulares.
- **Fundo em Shorts (`9:16`):** UM objeto/ícone em destaque, centralizado, sobre fundo branco sólido puro (`#FFFFFF`) para recorte automático (`limpar_imagens.py`). O personagem entra por cima, na parte de baixo do quadro, reagindo ao objeto.
- **Fundo em Vídeos Longos (`16:9`):** cenário ilustrado completo e **vazio** (cores, objetos, ambientes e paisagens coerentes com a fala), com o terço inferior do quadro livre para o personagem. Cores **suaves, pastel ou dessaturadas** (proibido azulão, vermelhão ou amarelão), para o protagonista de moletom amarelo (`#FFC928`) continuar se destacando por cima. Não há remoção de fundo em vídeos longos.
- Proibido nas cenas dos vídeos: fotorrealismo, renderização 3D, gradientes pesados, sombras realistas ou excesso de detalhes.

## Protagonista (Consistência Absoluta — usado nas grades de poses/sprites e na thumbnail, NÃO nos prompts de cena)
- Cabeça grande e arredondada de cor branca/branco-pálida (representando cerca de 1/3 da altura total do corpo).
- Cabelo preto bagunçado e espetado.
- Olhos pretos simples e ovais, rosto minimalista extremamente expressivo através de sobrancelhas e boca.
- Corpo pequeno e compacto usando moletom amarelo vibrante (`#FFC928`), calça azul-marinho escura e tênis brancos baixos com detalhes pretos.
- Pode ter uma leve área de sombreamento azul-claro na lateral esquerda da cabeça.

## Personagens Secundários
- Não entram nos fundos (regra "sem pessoas"). Personagens como a Bia (cabelo castanho preso em rabo de cavalo, regata verde, calça legging preta, segurando um pequeno caderno) passam a viver em `assets/secundarios/`, com a mesma estrutura da biblioteca, e são escolhidos pelo campo `fonte` do `personagem` na cena.

## Direção de Storyboard e Prompts de Imagem
- Ritmo visual dinâmico: planeje cortes a cada **1,5 a 3 segundos** no máximo (cerca de **25 a 35 cenas por minuto**), acompanhando a fala.
- Fidelidade ao roteiro: leia o roteiro completo do projeto e crie um cenário/objeto específico para a fala exata de cada corte (literal ou metafórico), sem repetir o mesmo cenário/objeto em sequência.
- Timestamps únicos e estritamente crescentes: quando houver arquivo `03-timestamps.json`, vincule cada prompt ao tempo exato no formato `[MM:SS] prompt`, sem nunca repetir o mesmo segundo em duas linhas.
- Idioma dos prompts: sempre em **INGLÊS** (otimizado para ComfyUI/Whisk/ImageFX/Flow). Qualquer texto que apareça dentro da ilustração deve ser especificado em **PORTUGUÊS DO BRASIL**.
- Nunca confie na memória do gerador de imagens: repita o sufixo de fundo completo em **todas as linhas**.
  - Shorts: `Single highlighted object or icon centered in the frame, empty scene, no people, no characters, minimalist 2d cartoon background, thick black ink outlines, flat colors, hand-drawn doodle and marker aesthetic, slightly irregular lines, pure solid white background (#FFFFFF), no hands, no body parts, ..., 9:16 aspect ratio.`
  - Vídeos Longos: `empty scene, no people, no characters, minimalist 2d cartoon background, thick black ink outlines, flat colors, hand-drawn doodle and marker aesthetic, slightly irregular lines, full illustrated background with soft muted pastel or desaturated colors, subtle scenery and objects matching the scene, uncluttered lower foreground, ..., 16:9 aspect ratio.`
- Proporção obrigatória: `9:16` para Shorts, Reels e TikTok e `16:9` para vídeos longos do YouTube.
