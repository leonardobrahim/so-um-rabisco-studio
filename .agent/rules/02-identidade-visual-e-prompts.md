# Identidade Visual, Storyboard e Prompts - Só um Rabisco

## Estilo das Cenas dos Vídeos
- Estilo padrão: ilustração 2D cartoon, minimalista, desenhada à mão com estética de rabisco/marcador, contornos pretos grossos e limpos, cores chapadas e linhas levemente irregulares.
- Fundo padrão para cenas internas: fundo branco sólido puro (`#FFFFFF`) para facilitar recorte automático e animação no HyperFrames/GSAP.
- Proibido nas cenas dos vídeos: fotorrealismo, renderização 3D, gradientes pesados, sombras realistas ou excesso de detalhes.

## Protagonista (Manter Consistência Absoluta)
- Cabeça grande e arredondada de cor branca/branco-pálida (representando cerca de 1/3 da altura total do corpo).
- Cabelo preto bagunçado e espetado.
- Olhos pretos simples e ovais, rosto minimalista extremamente expressivo através de sobrancelhas e boca.
- Corpo pequeno e compacto usando moletom amarelo vibrante (`#FFC928`), calça azul-marinho escura e tênis brancos baixos com detalhes pretos.
- Pode ter uma leve área de sombreamento azul-claro na lateral esquerda da cabeça.

## Personagens Secundários
- Bia: cabelo castanho preso em rabo de cavalo, regata verde, calça legging preta, segurando um pequeno caderno, no mesmo traço 2D minimalista.

## Direção de Storyboard e Prompts de Imagem
- Ritmo visual dinâmico: planeje cortes a cada **1,5 a 3 segundos** no máximo (cerca de **25 a 35 cenas por minuto**), acompanhando a fala.
- Fidelidade ao roteiro atual: leia o roteiro completo do projeto e crie uma ação/cena específica para a fala exata de cada corte (literal ou metafórica), sem usar poses genéricas nem repetir a mesma pose em sequência.
- Timestamps únicos e estritamente crescentes: quando houver arquivo `03-timestamps.json`, vincule cada prompt ao tempo exato no formato `[MM:SS] prompt`, sem nunca repetir o mesmo segundo em duas linhas.
- Idioma dos prompts: sempre em **INGLÊS** (otimizado para Whisk/ImageFX/Flow). Qualquer texto que apareça dentro da ilustração deve ser especificado em **PORTUGUÊS DO BRASIL**.
- Nunca confie na memória do gerador de imagens: repita a descrição física completa do protagonista e do estilo em **todas as linhas** (`Featuring a minimalist 2D cartoon character with a large rounded pale-white head (about 1/3 of total body height) with a slight light-blue shading area on the left side of the head, messy spiky black hair, simple oval black eyes, expressive minimalist face with eyebrows and mouth, compact small body wearing a vibrant yellow hoodie (#FFC928), dark navy blue pants, and low white sneakers with black details. 2D minimalist cartoon illustration, hand-drawn doodle and marker aesthetic, thick clean black outlines, flat colors, slightly irregular lines, pure solid white background (#FFFFFF), no photorealism, no 3D, no heavy gradients, no realistic shadows, no excessive detail, 9:16 aspect ratio.` ou `16:9 aspect ratio.`).
- Proporção obrigatória: `9:16` para Shorts, Reels e TikTok e `16:9` para vídeos longos do YouTube.
