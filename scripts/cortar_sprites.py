import argparse
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

RAIZ_DIR = Path(__file__).resolve().parent.parent
PASTA_ENTRADA = RAIZ_DIR / "assets" / "personagem" / "grades_input"
PASTA_SAIDA = RAIZ_DIR / "assets" / "personagem" / "sprites_output"
TAMANHO_QUADRO = 512  # Tamanho final de cada frame quadrado (512x512)


def ler_imagem_windows(caminho: Path):
    dados = np.fromfile(str(caminho), dtype=np.uint8)
    return cv2.imdecode(dados, cv2.IMREAD_COLOR)


def remover_fundo_seguro(bgr):
    # 1. Identifica apenas pixels realmente claros e neutros (sem saturacao de cor).
    # Garante que moletom amarelo (#FFC928), calca azul e cabelo preto NUNCA sejam
    # tratados como fundo, mesmo que haja degradê ou falhas no contorno.
    b_ch, g_ch, r_ch = cv2.split(bgr)
    min_ch = np.minimum(np.minimum(b_ch, g_ch), r_ch)
    max_ch = np.maximum(np.maximum(b_ch, g_ch), r_ch)
    diff_ch = max_ch.astype(np.int16) - min_ch.astype(np.int16)

    pode_ser_fundo = (min_ch >= 224) & (diff_ch <= 20)

    # 2. Cria barreira temporaria selando micro-falhas (1-2px) do traco escuro
    # para que a remocao externa nao vaze para dentro da cabeca branca ou dos tenis.
    cinza = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    linhas_escuras = (cinza < 185).astype(np.uint8) * 255
    kernel_selo = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    linhas_seladas = cv2.dilate(linhas_escuras, kernel_selo, iterations=1)

    candidatos_selados = (pode_ser_fundo & (linhas_seladas == 0)).astype(np.uint8) * 255

    # 3. Borda externa de 1px de fundo garantido para capturar TODO o fundo conectado
    # as 4 bordas em um unico connectedComponents (nunca invade o personagem).
    padded = np.pad(candidatos_selados, ((1, 1), (1, 1)), mode="constant", constant_values=255)
    _, labels = cv2.connectedComponents(padded, connectivity=4)
    fundo_exterior = labels[1:-1, 1:-1] == labels[0, 0]

    # 4. Recupera 1px adjacente ao traco escuro apenas se for realmente claro e neutro
    fundo_expandido = cv2.dilate(fundo_exterior.astype(np.uint8), kernel_selo, iterations=1) > 0
    fundo_final = fundo_exterior | (fundo_expandido & (min_ch >= 216) & (diff_ch <= 22))

    # 5. Canal alpha com suavizacao leve apenas na borda externa de transicao
    alpha = np.where(fundo_final, 0, 255).astype(np.uint8)
    borda_suave = cv2.GaussianBlur(alpha, (3, 3), 0)
    alpha = np.where(
        fundo_final,
        np.minimum(alpha, borda_suave),
        np.where(borda_suave < 255, borda_suave, 255),
    )

    bgra = cv2.cvtColor(bgr, cv2.COLOR_BGR2BGRA)
    bgra[:, :, 3] = alpha
    return bgra


def processar_grade(
    caminho_img: Path,
    mesma_escala: bool = True,
    pasta_saida: Path = PASTA_SAIDA,
):
    img_bgr = ler_imagem_windows(caminho_img)
    if img_bgr is None:
        print(f"Erro ao abrir: {caminho_img.name}")
        return

    h, w = img_bgr.shape[:2]
    mid_y, mid_x = h // 2, w // 2
    pad_y, pad_x = int(h * 0.015), int(w * 0.015)  # Corta 1.5% nas bordas para eliminar a linha cinza da grade

    quadrantes = [
        img_bgr[pad_y:mid_y - pad_y, pad_x:mid_x - pad_x],          # Top-left
        img_bgr[pad_y:mid_y - pad_y, mid_x + pad_x:w - pad_x],      # Top-right
        img_bgr[mid_y + pad_y:h - pad_y, pad_x:mid_x - pad_x],      # Bottom-left
        img_bgr[mid_y + pad_y:h - pad_y, mid_x + pad_x:w - pad_x],  # Bottom-right
    ]

    recortes = []
    max_w, max_h = 1, 1

    for q in quadrantes:
        rgba = remover_fundo_seguro(q)
        ys, xs = np.where(rgba[:, :, 3] > 25)
        if len(xs) == 0 or len(ys) == 0:
            continue
        crop = rgba[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        recortes.append(crop)
        max_w = max(max_w, crop.shape[1])
        max_h = max(max_h, crop.shape[0])

    if not recortes:
        return

    destino = pasta_saida / caminho_img.stem
    destino.mkdir(parents=True, exist_ok=True)

    area_util = int(TAMANHO_QUADRO * 0.88)
    margem_base = int(TAMANHO_QUADRO * 0.06)
    escala_global = min(area_util / max_w, area_util / max_h)

    frames_prontos = []
    for i, crop in enumerate(recortes, start=1):
        ch, cw = crop.shape[:2]
        escala = escala_global if mesma_escala else min(area_util / cw, area_util / ch)
        nw, nh = max(1, int(cw * escala)), max(1, int(ch * escala))

        pil_crop = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGRA2RGBA)).resize(
            (nw, nh), Image.Resampling.LANCZOS
        )

        canvas = Image.new("RGBA", (TAMANHO_QUADRO, TAMANHO_QUADRO), (0, 0, 0, 0))
        pos_x = (TAMANHO_QUADRO - nw) // 2
        pos_y = TAMANHO_QUADRO - margem_base - nh  # Mantém os pés e a base do corpo travados no mesmo nível
        canvas.paste(pil_crop, (pos_x, pos_y), pil_crop)

        canvas.save(destino / f"frame_{i:02d}.png")
        frames_prontos.append(canvas)

    # Monta a tira horizontal (2048x512) pronta para animação com steps() no GSAP
    tira = Image.new("RGBA", (TAMANHO_QUADRO * len(frames_prontos), TAMANHO_QUADRO), (0, 0, 0, 0))
    for idx, frame in enumerate(frames_prontos):
        tira.paste(frame, (idx * TAMANHO_QUADRO, 0))
    tira.save(destino / "strip.png")

    # meta.json alimenta a biblioteca de personagem do Studio (modo, frames e tags editaveis).
    # Em re-execucoes preserva as tags ja editadas.
    meta_path = destino / "meta.json"
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
    meta.update({"modo": "sprite" if mesma_escala else "poses", "frames": len(frames_prontos), "quadro": TAMANHO_QUADRO})
    meta.setdefault("fps", 8)
    meta.setdefault("tags_pasta", [])
    meta.setdefault("tags", {})
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Concluído: {caminho_img.name} -> {len(frames_prontos)} frames salvos em {destino}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Corta grades 2x2 de sprites ou poses avulsas em quadros 512x512 com fundo transparente e gera strip.png."
    )
    parser.add_argument(
        "--poses",
        action="store_true",
        help="Usa escala individual por quadrante (mesma_escala=False) para grades de poses avulsas.",
    )
    parser.add_argument(
        "--entrada",
        type=Path,
        default=PASTA_ENTRADA,
        help="Pasta com as grades 2x2 de entrada (padrão: assets/personagem/grades_input).",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=PASTA_SAIDA,
        help="Pasta de saída dos frames e strips (padrão: assets/personagem/sprites_output).",
    )
    args = parser.parse_args()

    pasta_entrada: Path = args.entrada.resolve()
    pasta_saida: Path = args.saida.resolve()
    pasta_entrada.mkdir(parents=True, exist_ok=True)
    pasta_saida.mkdir(parents=True, exist_ok=True)

    mesma_escala = not args.poses
    extensoes = {".png", ".jpg", ".jpeg", ".webp"}
    arquivos = [p for p in pasta_entrada.iterdir() if p.is_file() and p.suffix.lower() in extensoes]

    if not arquivos:
        rel_entrada = pasta_entrada.relative_to(RAIZ_DIR) if pasta_entrada.is_relative_to(RAIZ_DIR) else pasta_entrada
        print(f"Coloque suas grades 2x2 na pasta '{rel_entrada}' e rode o script novamente.")
    else:
        modo = "poses avulsas (mesma_escala=False)" if args.poses else "sprite sheet animado (mesma_escala=True)"
        print(f"Processando {len(arquivos)} grade(s) em modo {modo}...")
        for arq in sorted(arquivos, key=lambda f: f.name.lower()):
            processar_grade(arq, mesma_escala=mesma_escala, pasta_saida=pasta_saida)