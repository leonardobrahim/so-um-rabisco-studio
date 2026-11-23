import sys
from pathlib import Path
import cv2
import numpy as np
from PIL import Image


def eh_branco(b: int, g: int, r: int, limite: int = 235) -> bool:
    return b >= limite and g >= limite and r >= limite


def remover_fundo_externo(caminho_img: Path, margem: int = 16) -> Image.Image:
    dados = np.fromfile(str(caminho_img), dtype=np.uint8)
    img = cv2.imdecode(dados, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"Nao foi possivel ler a imagem: {caminho_img}")

    if img.shape[2] == 4:
        bgr = img[:, :, :3].copy()
    else:
        bgr = img.copy()

    h, w = bgr.shape[:2]
    mask = np.zeros((h + 2, w + 2), np.uint8)
    flags = 4 | (255 << 8) | cv2.FLOODFILL_MASK_ONLY
    tolerancia = (18, 18, 18)

    # Varre as 4 bordas da imagem para remover apenas o fundo branco conectado ao exterior
    # Isso preserva a cabeca branca e o tenis branco dentro dos contornos pretos
    for x in range(w):
        if mask[1, x + 1] == 0 and eh_branco(*bgr[0, x]):
            cv2.floodFill(bgr, mask, (x, 0), (0, 0, 0), tolerancia, tolerancia, flags)
        if mask[h, x + 1] == 0 and eh_branco(*bgr[h - 1, x]):
            cv2.floodFill(bgr, mask, (x, h - 1), (0, 0, 0), tolerancia, tolerancia, flags)

    for y in range(h):
        if mask[y + 1, 1] == 0 and eh_branco(*bgr[y, 0]):
            cv2.floodFill(bgr, mask, (0, y), (0, 0, 0), tolerancia, tolerancia, flags)
        if mask[y + 1, w] == 0 and eh_branco(*bgr[y, w - 1]):
            cv2.floodFill(bgr, mask, (w - 1, y), (0, 0, 0), tolerancia, tolerancia, flags)

    fundo = mask[1:-1, 1:-1]
    alpha = 255 - fundo

    # Suaviza levemente a borda do recorte para evitar serrilhado no traco preto
    alpha = cv2.GaussianBlur(alpha, (3, 3), 0)

    rgba = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGBA)
    rgba[:, :, 3] = alpha

    pil_img = Image.fromarray(rgba)
    bbox = pil_img.getbbox()

    if bbox:
        left = max(0, bbox[0] - margem)
        top = max(0, bbox[1] - margem)
        right = min(w, bbox[2] + margem)
        bottom = min(h, bbox[3] + margem)
        pil_img = pil_img.crop((left, top, right, bottom))

    return pil_img


def processar_lote(pasta_origem: Path, pasta_destino: Path):
    extensoes = {".png", ".jpg", ".jpeg", ".webp"}
    arquivos = [
        f for f in pasta_origem.iterdir()
        if f.is_file() and f.suffix.lower() in extensoes
    ]

    if not arquivos:
        print(f"Nenhuma imagem encontrada em: {pasta_origem}")
        return

    # Ordena pela data de modificacao/download para manter a sequencia das cenas
    arquivos.sort(key=lambda f: f.stat().st_mtime)
    pasta_destino.mkdir(parents=True, exist_ok=True)

    print(f"Processando {len(arquivos)} imagens de '{pasta_origem}'...")

    for idx, arquivo in enumerate(arquivos, start=1):
        nome_saida = f"cena_{idx:02d}.png"
        caminho_saida = pasta_destino / nome_saida

        img_limpa = remover_fundo_externo(arquivo)
        img_limpa.save(caminho_saida, "PNG")
        print(f"  [OK] {arquivo.name} -> {nome_saida}")

    print(f"\nFinalizado! Imagens prontas em: {pasta_destino}")


if __name__ == "__main__":
    raiz = Path(__file__).resolve().parent.parent

    if len(sys.argv) >= 3:
        origem = Path(sys.argv[1]).resolve()
        destino = Path(sys.argv[2]).resolve()
    else:
        # Padrao: busca a pasta de projeto mais recente e le de midia/raw para midia/cenas
        projetos_dir = raiz / "projetos"
        pastas = sorted(
            [p for p in projetos_dir.iterdir() if p.is_dir()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not pastas:
            raise FileNotFoundError("Nenhuma pasta de projeto encontrada.")

        projeto_atual = pastas[0]
        origem = projeto_atual / "midia" / "raw"
        destino = projeto_atual / "midia" / "cenas"

    processar_lote(origem, destino)