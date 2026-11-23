import json
import re
import shutil
import sys
from pathlib import Path


def encontrar_projeto_pronto(base_dir: Path) -> Path:
    projetos_dir = base_dir / "projetos"
    pastas = sorted(
        [p for p in projetos_dir.iterdir() if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for pasta in pastas:
        if (pasta / "cenas.json").exists():
            return pasta
    raise FileNotFoundError("Nenhum 'cenas.json' encontrado dentro de projetos/.")


def atualizar_index_html(template_dir: Path, cenas_data: dict, nome_audio: str):
    index_path = template_dir / "index.html"
    if not index_path.exists():
        return

    formato = cenas_data.get("formato", "9:16")
    width = "1920" if formato == "16:9" else "1080"
    height = "1080" if formato == "16:9" else "1920"
    fps = str(cenas_data.get("fps", 30))
    duracao = str(cenas_data.get("duracao_total", 10))

    html = index_path.read_text(encoding="utf-8")
    html = re.sub(
        r'<div id="composition"[^>]*>',
        f'<div id="composition" data-composition-id="main" data-width="{width}" data-height="{height}" data-fps="{fps}" data-duration="{duracao}">',
        html,
        count=1,
    )
    html = re.sub(
        r'<audio id="voiceover"[^>]*></audio>',
        f'<audio id="voiceover" src="./assets_atual/{nome_audio}" data-start="0" data-duration="{duracao}" preload="auto"></audio>',
        html,
        count=1,
    )
    index_path.write_text(html, encoding="utf-8")


def preparar(pasta_projeto: Path, template_dir: Path):
    assets_atual = template_dir / "assets_atual"
    if assets_atual.exists():
        shutil.rmtree(assets_atual)
    assets_atual.mkdir(parents=True)

    # Copia cenas.json para a raiz do template
    cenas_origem_json = pasta_projeto / "cenas.json"
    shutil.copy2(cenas_origem_json, template_dir / "cenas.json")
    cenas_data = json.loads(cenas_origem_json.read_text(encoding="utf-8"))

    # Copia audio.wav ou audio.mp3
    midia_dir = pasta_projeto / "midia"
    nome_audio = "audio.wav"
    for ext in ("audio.wav", "audio.mp3", "audio.m4a"):
        origem_audio = midia_dir / ext
        if origem_audio.exists():
            shutil.copy2(origem_audio, assets_atual / ext)
            nome_audio = ext
            break

    # Copia todas as imagens recortadas
    cenas_origem = midia_dir / "cenas"
    if cenas_origem.exists():
        shutil.copytree(cenas_origem, assets_atual / "cenas")

    atualizar_index_html(template_dir, cenas_data, nome_audio)

    print(
        f"Template pronto para renderizar o projeto: {pasta_projeto.name} "
        f"({cenas_data.get('formato', '9:16')}, {cenas_data.get('duracao_total', 0)}s)"
    )


if __name__ == "__main__":
    raiz = Path(__file__).resolve().parent.parent
    template = raiz / "template-hyperframes"

    alvo = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else encontrar_projeto_pronto(raiz)
    preparar(alvo, template)
