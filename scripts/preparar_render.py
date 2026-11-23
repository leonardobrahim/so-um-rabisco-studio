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


def preparar(pasta_projeto: Path, template_dir: Path):
    assets_atual = template_dir / "assets_atual"
    if assets_atual.exists():
        shutil.rmtree(assets_atual)
    assets_atual.mkdir(parents=True)

    # Copia cenas.json para a raiz do template
    shutil.copy2(pasta_projeto / "cenas.json", template_dir / "cenas.json")

    # Copia audio.wav ou audio.mp3
    midia_dir = pasta_projeto / "midia"
    for ext in ("audio.wav", "audio.mp3", "audio.m4a"):
        origem_audio = midia_dir / ext
        if origem_audio.exists():
            shutil.copy2(origem_audio, assets_atual / ext)
            break

    # Copia todas as imagens recortadas
    cenas_origem = midia_dir / "cenas"
    if cenas_origem.exists():
        shutil.copytree(cenas_origem, assets_atual / "cenas")

    print(f"Template pronto para renderizar o projeto: {pasta_projeto.name}")


if __name__ == "__main__":
    raiz = Path(__file__).resolve().parent.parent
    template = raiz / "template-hyperframes"

    alvo = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else encontrar_projeto_pronto(raiz)
    preparar(alvo, template)