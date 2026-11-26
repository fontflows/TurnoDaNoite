"""
gerar_texturas_animatronicos.py — texturas dos animatrônicos finais (Tito e Pipoca), "assadas" em imagem
(o glTF não leva material procedural nem pelo do Blender).

Base de pelúcia: Fabric084 (ambientCG, CC0 — "fur, microfiber, soft"): o normal map dela tem os tufos
de pelo. A cor original (azul) vira cinza neutro e depois é tingida para cada personagem.
Versões "sujas" (mãos, pés, barriga, juntas): a mesma pelúcia com manchas de graxa e poeira.
Tecidos: xadrez vermelho e branco (lenço do Tito) e rosa com bolinhas (laço da Pipoca).

Uso (na pasta TurnoDaNoite):
    python ferramentas/gerar_texturas_animatronicos.py <pasta onde está a Fabric084 baixada>
Saída: godot/assets/texturas/animatronicos/*.jpg (2048 px nas pelúcias; 1024 nos tecidos)
Precisa de numpy e Pillow.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "godot" / "assets" / "texturas" / "animatronicos"
RNG = np.random.default_rng(2611)

# Cores das pelúcias (sRGB 0-1). Batem com o visual do jogo (capa, cartazes e PROMPTS_ARTE.md).
TINTAS = {
    "tito_pelo": (0.46, 0.25, 0.11),       # caramelo/marrom
    "tito_creme": (0.86, 0.72, 0.52),      # barriga, focinho, dentro das orelhas
    "pipoca_pelo": (0.60, 0.43, 0.82),     # lilás
    "pipoca_branco": (0.92, 0.89, 0.90),   # barriga e focinho
    "pipoca_rosa": (0.93, 0.58, 0.72),     # dentro das orelhas, bochechas
    "chapeu": (0.93, 0.92, 0.88),          # chapéu de chef (algodão)
    "gravata": (0.82, 0.56, 0.06),         # gravata-borboleta mostarda
    "tutu": (0.78, 0.66, 0.92),            # saia de tule lilás (v1)
    "sobrancelha_tito": (0.25, 0.13, 0.06),  # sobrancelhas (plástico/pelúcia escura)
    "sobrancelha_pipoca": (0.42, 0.28, 0.62),
}


def ruido_suave(tam, escala, oitavas=4):
    """Ruído de valor suave e TILEÁVEL (emenda nas bordas), 0..1."""
    total = np.zeros((tam, tam))
    amp, soma = 1.0, 0.0
    for o in range(oitavas):
        n = max(2, int(escala * 2 ** o))
        grade = RNG.random((n, n))
        img = Image.fromarray((grade * 255).astype(np.uint8)).resize((tam, tam), Image.BICUBIC)
        # tileável: repete a grade e corta o meio
        g2 = np.tile(grade, (3, 3))
        img = Image.fromarray((g2 * 255).astype(np.uint8)).resize((tam * 3, tam * 3), Image.BICUBIC)
        total += amp * np.asarray(img, dtype=np.float64)[tam:2 * tam, tam:2 * tam] / 255.0
        soma += amp
        amp *= 0.5
    return total / soma


def salvar(nome, arr):
    SAIDA.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8)).save(SAIDA / f"{nome}.jpg", quality=92)


def main():
    pasta_fabric = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not pasta_fabric or not (pasta_fabric / "Fabric084_2K-JPG_Color.jpg").exists():
        print("Passe a pasta da Fabric084 (ambientCG) baixada: ... python gerar_texturas_animatronicos.py <pasta>")
        sys.exit(1)
    SAIDA.mkdir(parents=True, exist_ok=True)
    cor = np.asarray(Image.open(pasta_fabric / "Fabric084_2K-JPG_Color.jpg").convert("RGB"), dtype=np.float64) / 255.0
    tam = cor.shape[0]
    # Cinza neutro: só a variação de luz e sombra dos tufos (média 1.0)
    lum = cor @ np.array([0.299, 0.587, 0.114])
    variacao = lum / lum.mean()
    variacao = 1.0 + (variacao - 1.0) * 2.2  # realça os tufos (a original é bem lisa)
    # Normal, aspereza e AO: copiados da Fabric084 (normal GL, que é o do Godot e do Blender)
    for origem, destino in (("Roughness", "pelucia_aspereza"), ("AmbientOcclusion", "pelucia_ao")):
        Image.open(pasta_fabric / f"Fabric084_2K-JPG_{origem}.jpg").convert("RGB").save(SAIDA / f"{destino}.jpg", quality=92)
    # Normal: tufos da Fabric084 + pelo curto assado no Blender (blender/scripts/assar_pelo.py),
    # repetido 2x2 (fios mais finos) e somado ("whiteout blend").
    n1 = np.asarray(Image.open(pasta_fabric / "Fabric084_2K-JPG_NormalGL.jpg").convert("RGB"), dtype=np.float64) / 127.5 - 1.0
    caminho_pelo = RAIZ / "blender" / "texturas_assadas" / "pelo_curto_normal.png"
    if caminho_pelo.exists():
        pelo = Image.open(caminho_pelo).convert("RGB")
        lado = tam // 2
        pelo = np.tile(np.asarray(pelo.resize((lado, lado), Image.LANCZOS), dtype=np.float64), (2, 2, 1)) / 127.5 - 1.0
        forca = 0.8
        n = np.stack([n1[..., 0] + pelo[..., 0] * forca, n1[..., 1] + pelo[..., 1] * forca, n1[..., 2] * pelo[..., 2]], axis=-1)
    else:
        print("AVISO: falta o pelo assado (rode blender/scripts/assar_pelo.py); usando só a Fabric084")
        n = n1
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    salvar("pelucia_normal", (n + 1.0) / 2.0)
    # Sujeira: manchas grandes de graxa + poeira fina (tileável)
    manchas = np.clip((ruido_suave(tam, 3, 4) - 0.45) * 2.6, 0, 1)
    poeira = ruido_suave(tam, 24, 3)
    for nome, tinta in TINTAS.items():
        base = variacao[..., None] * np.array(tinta)[None, None, :]
        # leve variação de tom na pelúcia (não fica "de plástico")
        base *= (0.93 + 0.14 * ruido_suave(tam, 6, 3))[..., None]
        if nome in ("tito_pelo", "tito_creme", "pipoca_pelo", "pipoca_branco", "pipoca_rosa", "chapeu"):
            # todas as pelúcias com um pouco de poeira (estão velhas)
            base *= (1.0 - 0.12 * poeira)[..., None]
        salvar(f"{nome}_cor", base)
        if nome in ("tito_pelo", "tito_creme", "pipoca_pelo", "pipoca_branco", "chapeu", "tutu"):
            graxa = np.array([0.20, 0.15, 0.10])
            suja = base * (1.0 - 0.55 * manchas)[..., None] + graxa * (0.35 * manchas)[..., None]
            suja *= (0.82 + 0.18 * poeira)[..., None]
            salvar(f"{nome}_sujo_cor", suja)
    # Tecidos (1024): xadrez vermelho e branco e rosa com bolinhas
    t = 1024
    y, x = np.mgrid[0:t, 0:t]
    casa = 128
    xadrez = (((x // casa) + (y // casa)) % 2).astype(np.float64)
    trama = 0.92 + 0.08 * np.sin(x * 0.9) * np.sin(y * 0.9)
    vermelho = np.array([0.72, 0.12, 0.10])
    branco = np.array([0.93, 0.90, 0.84])
    img = np.where(xadrez[..., None] > 0.5, vermelho, branco) * trama[..., None]
    salvar("xadrez_vermelho_cor", img * (0.85 + 0.15 * ruido_suave(t, 4, 2))[..., None])
    rosa = np.array(TINTAS["pipoca_rosa"])
    passo = 128
    cx = (x % passo) - passo / 2
    cy = ((y + (x // passo % 2) * passo // 2) % passo) - passo / 2
    bolinha = (cx ** 2 + cy ** 2) < (passo * 0.22) ** 2
    img = np.where(bolinha[..., None], np.array([0.97, 0.95, 0.93]), rosa) * trama[..., None]
    salvar("laco_bolinhas_cor", img)
    # Plástico (focinho, queixo, dentes): liso, só arranhões finos. A versão "_sujo" vai nas bordas
    # do focinho e perto da boca: um pouco mais escura e encardida, SEM manchas grandes.
    arranhoes = np.zeros((t, t))
    for _ in range(160):
        x0, y0 = RNG.random(2) * t
        ang = RNG.random() * np.pi
        comp = RNG.uniform(15, 90)
        for s in np.linspace(0, comp, int(comp)):
            xi, yi = int(x0 + np.cos(ang) * s) % t, int(y0 + np.sin(ang) * s) % t
            arranhoes[yi, xi] = 1.0
    arranhoes = np.asarray(Image.fromarray((arranhoes * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)), dtype=np.float64) / 255.0
    pontinhos = (ruido_suave(t, 90, 2) > 0.62).astype(np.float64) * ruido_suave(t, 40, 2)
    for nome, cor_plastico in (("plastico_creme", (0.90, 0.78, 0.58)), ("plastico_branco", (0.93, 0.91, 0.90)),
                               ("dentes", (0.90, 0.87, 0.76))):
        base = np.ones((t, t, 3)) * np.array(cor_plastico)
        base *= (0.97 + 0.03 * ruido_suave(t, 6, 2))[..., None]
        base = base * (1 - 0.18 * arranhoes)[..., None]
        salvar(f"{nome}_cor", base)
        if nome != "dentes":
            suja = base * 0.86 * (1 - 0.18 * pontinhos)[..., None] + np.array([0.30, 0.24, 0.16]) * 0.06
            salvar(f"{nome}_sujo_cor", suja)
    print(f"Texturas dos animatrônicos em {SAIDA}")
    for f in sorted(SAIDA.glob("*.jpg")):
        print("  ", f.name)


if __name__ == "__main__":
    main()
