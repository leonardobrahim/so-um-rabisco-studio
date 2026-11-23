---
description: Cria um novo vídeo longo de domingo para o Só um Rabisco etapa por etapa
---

# Fluxo de Criação - Vídeo Longo (YouTube)

1. Pergunte qual é o tema ou ideia bruta do vídeo (caso eu ainda não tenha informado no comando).
2. Avalie a ideia de forma crítica seguindo `.agent/rules/01-identidade-e-roteiro.md` e proponha 3 ângulos fortes com opções de gancho inicial. Pare e aguarde eu escolher o ângulo.
3. Assim que eu escolher, crie uma nova pasta em `projetos/AAAA-MM-slug-do-tema/` e salve:
   - `01-ideia-e-roteiro.md` com a premissa e o roteiro completo (5 a 8 minutos, apenas texto de narração limpo).
   - `02-narracao.txt` contendo exclusivamente o texto corrido que vai para o VoiceStudio.
4. Pare e aguarde minha aprovação ou ajustes no roteiro antes de gerar prompts visuais, thumbnail ou SEO.
5. Depois do meu "ok", pergunte se eu já rodei o áudio para gerar o `03-timestamps.json` ou se devo montar o storyboard estimado primeiro.
6. Gere `04-storyboard-e-prompts.md` (em `16:9`, inglês, fundo branco sólido `#FFFFFF`) e `05-seo-e-thumb.md` seguindo `.agent/rules/03-thumbs-e-seo.md`. Sempre que gerar os prompts em `04-storyboard-e-prompts.md`, substitua também o arquivo `prompts_imagens.txt` na raiz do repositório com todos os prompts `[MM:SS] ...` gerados para este projeto (separados por linha em branco).