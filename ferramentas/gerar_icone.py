"""
gerar_icone.py — gera o ÍCONE do jogo (janela, barra de tarefas e o próprio TurnoDaNoite.exe).

De onde vem a imagem:
  1. Se existir a arte ARTE-33 (godot/assets/arte_externa/icone/icone_jogo.jpg ou .png), usa ela:
     o fundo verde chapado é apagado e o desenho é centralizado.
  2. Senão, recorta a cabeça do Tito da capa do menu (ARTE-10).
O resultado ganha um quadrado de cantos arredondados escuro com borda âmbar (lê bem até em 16 px).

Saída:
  godot/assets/icone/icone.png  (256x256, usado na janela e na barra de tarefas)
  godot/assets/icone/icone.ico  (16, 24, 32, 48, 64, 128 e 256 px, gravado dentro do .exe ao exportar)

Rodar (na pasta TurnoDaNoite):  python ferramentas/gerar_icone.py
Precisa do Pillow (pip install pillow).
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

RAIZ = Path(__file__).resolve().parents[1]
ARTE = RAIZ / "godot" / "assets" / "arte_externa"
SAIDA = RAIZ / "godot" / "assets" / "icone"
TAMANHOS = [16, 24, 32, 48, 64, 128, 256]
LADO = 512  # trabalhamos grande e reduzimos no fim (fica mais nítido)


def arte_externa():
    for ext in ("png", "jpg", "jpeg", "webp"):
        c = ARTE / "icone" / f"icone_jogo.{ext}"
        if c.exists():
            return c
    return None


def tirar_fundo_verde(img):
    """Apaga o verde chapado (#00FF00 e parecidos) e o 'vazamento' verde na borda do desenho."""
    img = img.convert("RGBA")
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            verde = g - max(r, b)
            if verde > 60 and g > 120:
                px[x, y] = (r, g, b, 0)
            elif verde > 20:
                px[x, y] = (r, min(g, max(r, b) + 10), b, a)  # tira o halo verde
    caixa = img.getbbox()
    return img.crop(caixa) if caixa else img


def quadrado(img):
    lado = max(img.size)
    fundo = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    fundo.paste(img, ((lado - img.width) // 2, (lado - img.height) // 2), img)
    return fundo


def montar(desenho, recortado_da_capa):
    """Quadrado arredondado escuro + borda âmbar + o desenho por cima."""
    base = Image.new("RGBA", (LADO, LADO), (0, 0, 0, 0))
    mascara = Image.new("L", (LADO, LADO), 0)
    raio = LADO // 5
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, LADO - 1, LADO - 1), raio, fill=255)
    fundo = Image.new("RGBA", (LADO, LADO), (24, 14, 18, 255))
    # leve brilho de holofote atrás da cabeça
    luz = Image.new("L", (LADO, LADO), 0)
    ImageDraw.Draw(luz).ellipse((LADO * 0.12, LADO * 0.05, LADO * 0.88, LADO * 0.8), fill=90)
    luz = luz.filter(ImageFilter.GaussianBlur(LADO // 8))
    fundo = Image.composite(Image.new("RGBA", (LADO, LADO), (140, 95, 60, 255)), fundo, luz)
    base.paste(fundo, (0, 0), mascara)
    margem = int(LADO * 0.06)
    if recortado_da_capa:
        # a capa já tem fundo: recorta com a mesma máscara, um pouco menor
        interno = desenho.convert("RGBA").resize((LADO - 2 * margem, LADO - 2 * margem), Image.LANCZOS)
        m2 = Image.new("L", interno.size, 0)
        ImageDraw.Draw(m2).rounded_rectangle((0, 0, interno.width - 1, interno.height - 1), raio - margem, fill=255)
        base.paste(interno, (margem, margem), m2)
    else:
        interno = quadrado(desenho).resize((LADO - 2 * margem, LADO - 2 * margem), Image.LANCZOS)
        base.alpha_composite(interno, (margem, margem))
    borda = Image.new("RGBA", (LADO, LADO), (0, 0, 0, 0))
    ImageDraw.Draw(borda).rounded_rectangle((6, 6, LADO - 7, LADO - 7), raio - 4, outline=(235, 170, 60, 255), width=14)
    base.alpha_composite(borda)
    return base


def main():
    externo = arte_externa()
    if externo:
        desenho = tirar_fundo_verde(Image.open(externo))
        origem = f"arte ARTE-33 ({externo.name})"
        icone = montar(desenho, False)
    else:
        capa = Image.open(ARTE / "menu" / "menu_fundo.jpg")
        desenho = capa.crop((700, 150, 980, 430))  # a cabeça do Tito na capa do menu
        origem = "recorte da capa do menu (ARTE-10) — gere a ARTE-33 para um ícone próprio"
        icone = montar(desenho, True)
    SAIDA.mkdir(parents=True, exist_ok=True)
    icone.resize((256, 256), Image.LANCZOS).save(SAIDA / "icone.png")
    icone.save(SAIDA / "icone.ico", sizes=[(t, t) for t in TAMANHOS])
    previa = RAIZ / "docs" / "progresso"
    for t in (16, 32):
        icone.resize((t, t), Image.LANCZOS).save(previa / f"icone_previa_{t}.png")  # para conferir de olho (fora do jogo)
    print(f"Ícone gerado a partir de: {origem}")
    print(f"  {SAIDA / 'icone.png'}\n  {SAIDA / 'icone.ico'} ({', '.join(str(t) for t in TAMANHOS)} px)")


if __name__ == "__main__":
    main()
