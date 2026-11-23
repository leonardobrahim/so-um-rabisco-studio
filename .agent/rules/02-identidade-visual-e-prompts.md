# Identidade Visual, Storyboard e Prompts - Só um Rabisco

## Estilo das Cenas dos Vídeos
- Estilo padrão: ilustração 2D cartoon, minimalista, desenhada à mão com estética de rabisco/marcador, contornos pretos grossos e limpos, cores chapadas e linhas levemente irregulares.
- **Fundo em Shorts (`9:16`):** fundo branco sólido puro (`#FFFFFF`) para recorte automático e animação no HyperFrames/GSAP.
- **Fundo em Vídeos Longos (`16:9`):** cenas com **fundo ilustrado completo** (cores, objetos, ambientes e paisagens coerentes com a fala), mantendo o mesmo traço 2D minimalista. As cores do fundo devem ser **suaves, pastel ou dessaturadas** (proibido cores muito fortes/berrantes como azulão, vermelhão ou amarelão), para o protagonista de moletom amarelo (`#FFC928`) continuar se destacando. Não há remoção de fundo em vídeos longos.
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
- Nunca confie na memória do gerador de imagens: repita a descrição física completa do protagonista e do estilo em **todas as linhas** (`...pure solid white background (#FFFFFF), ..., 9:16 aspect ratio.` para Shorts, ou `...soft muted pastel illustrated background with subtle scenery/objects, no oversaturated or harsh bright primary colors in the background, ..., 16:9 aspect ratio.` para Vídeos Longos).
- Proporção obrigatória: `9:16` para Shorts, Reels e TikTok e `16:9` para vídeos longos do YouTube.
