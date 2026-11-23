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
- Ritmo visual dinâmico: planeje cortes ou mudanças de enquadramento a cada 1 a 2 segundos acompanhando a fala.
- Quando houver arquivo de timestamps (`03-timestamps.json`), vincule cada prompt ao tempo exato da narração no formato `[00:00] prompt`.
- Idioma dos prompts: sempre em INGLÊS (otimizado para Whisk/ImageFX). Se houver texto dentro da ilustração, especifique esse texto em PORTUGUÊS.
- Nunca confie na memória do gerador de imagens: repita a descrição física completa do protagonista e do estilo em todos os prompts.
- Proporção obrigatória: `16:9` para vídeos longos do YouTube e `9:16` para Shorts, Reels e TikTok.