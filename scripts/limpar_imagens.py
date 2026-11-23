import json
import sys
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageOps


def eh_branco(b: int, g: int, r: int, limite: int = 235) -> bool:
    return b >= limite and g >= limite and r >= limite


def remover_fundo_externo(caminho_img: Path, margem: int = 16) -> Image.Image:
    dados = np.fromfile(str(caminho_img), dtype=np.uint8)
    img = cv2.imdecode(dados, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"Nao foi possivel ler a imagem: {caminho_img}")

    if img.ndim == 2:
        bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        # Compoe sobre branco caso a imagem de entrada ja tenha canal alpha
        alpha_in = img[:, :, 3:4].astype(np.float32) / 255.0
        bgr_in = img[:, :, :3].astype(np.float32)
        bgr = np.clip(bgr_in * alpha_in + 255.0 * (1.0 - alpha_in), 0, 255).astype(np.uint8)
    else:
        bgr = img[:, :, :3].copy()

    h, w = bgr.shape[:2]

    # 1. Identifica apenas pixels realmente claros e neutros (sem saturacao de cor)
    # Isso garante que moletom amarelo (#FFC928), calca azul, cerebro rosa ou sombras azuis
    # NUNCA sejam considerados fundo, mesmo que o contorno tenha falhas.
    b_ch, g_ch, r_ch = cv2.split(bgr)
    min_ch = np.minimum(np.minimum(b_ch, g_ch), r_ch)
    max_ch = np.maximum(np.maximum(b_ch, g_ch), r_ch)
    diff_ch = max_ch.astype(np.int16) - min_ch.astype(np.int16)

    pode_ser_fundo = (min_ch >= 232) & (diff_ch <= 16)

    # 2. Cria uma barreira temporaria selando micro-falhas (1-2px) do traco preto desenhado a mao
    # para que o preenchimento externo nao vaze para dentro da cabeca branca ou dos tenis.
    cinza = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    linhas_escuras = (cinza < 185).astype(np.uint8) * 255
    kernel_selo = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    linhas_seladas = cv2.dilate(linhas_escuras, kernel_selo, iterations=1)

    candidatos_selados = (pode_ser_fundo & (linhas_seladas == 0)).astype(np.uint8) * 255

    # 3. Adiciona borda externa de 1px de fundo garantido para capturar TODO o fundo conectado
    # as 4 bordas da imagem em um unico connectedComponents (muito mais seguro que floodFill flutuante).
    padded = np.pad(candidatos_selados, ((1, 1), (1, 1)), mode="constant", constant_values=255)
    _, labels = cv2.connectedComponents(padded, connectivity=4)
    fundo_exterior = (labels[1:-1, 1:-1] == labels[0, 0])

    # 4. Recupera o 1px adjacente ao traco escuro que foi bloqueado apenas pelo selo temporario,
    # desde que esse pixel seja realmente branco/neutro (evita halo branco ao redor do personagem).
    fundo_expandido = cv2.dilate(fundo_exterior.astype(np.uint8), kernel_selo, iterations=1) > 0
    fundo_final = fundo_exterior | (fundo_expandido & (min_ch >= 224) & (diff_ch <= 18))

    # 5. Constroi canal alpha limpo com suavizacao leve apenas na borda de transicao
    alpha = np.where(fundo_final, 0, 255).astype(np.uint8)
    borda_suave = cv2.GaussianBlur(alpha, (3, 3), 0)
    # Mantem o interior do personagem 100% opaco e o fundo distante 100% transparente
    alpha = np.where(fundo_final, np.minimum(alpha, borda_suave), np.where(borda_suave < 255, borda_suave, 255))

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


def _detectar_manter_fundo_por_projeto(pasta_origem: Path) -> bool:
    meta_path = pasta_origem.parent.parent / "projeto.json"
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            return meta.get("tipo") == "longo"
        except Exception:
            return False
    return False


def processar_lote(pasta_origem: Path, pasta_destino: Path, manter_fundo: bool = False):
    extensoes = {".png", ".jpg", ".jpeg", ".webp"}
    arquivos = [
        f for f in pasta_origem.iterdir()
        if f.is_file() and f.suffix.lower() in extensoes
    ]

    if not arquivos:
        print(f"Nenhuma imagem encontrada em: {pasta_origem}")
        return

    # Ordena alfabeticamente pelo nome do arquivo para manter a sequencia das cenas
    arquivos.sort(key=lambda f: f.name.lower())
    pasta_destino.mkdir(parents=True, exist_ok=True)

    modo_txt = "mantendo fundo original (video longo)" if manter_fundo else "removendo fundo branco"
    print(f"Processando {len(arquivos)} imagens de '{pasta_origem}' ({modo_txt})...")

    for idx, arquivo in enumerate(arquivos, start=1):
        nome_saida = f"cena_{idx:02d}.png"
        caminho_saida = pasta_destino / nome_saida

        if manter_fundo:
            with Image.open(arquivo) as img_raw:
                img_corrigida = ImageOps.exif_transpose(img_raw)
                if img_corrigida.mode not in ("RGB", "RGBA"):
                    img_corrigida = img_corrigida.convert("RGB")
                img_corrigida.save(caminho_saida, "PNG")
        else:
            img_limpa = remover_fundo_externo(arquivo)
            img_limpa.save(caminho_saida, "PNG")
        print(f"  [OK] {arquivo.name} -> {nome_saida}")

    print(f"\nFinalizado! Imagens prontas em: {pasta_destino}")


if __name__ == "__main__":
    raiz = Path(__file__).resolve().parent.parent
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    manter_fundo_flag = "--manter-fundo" in sys.argv[1:]

    if len(args) >= 2:
        origem = Path(args[0]).resolve()
        destino = Path(args[1]).resolve()
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

    if not manter_fundo_flag:
        manter_fundo_flag = _detectar_manter_fundo_por_projeto(origem)

    processar_lote(origem, destino, manter_fundo=manter_fundo_flag)
