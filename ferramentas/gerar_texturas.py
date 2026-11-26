"""
gerar_texturas.py — gera por script as texturas próprias do jogo (nada é baixado).

Como rodar (precisa do Python que vem dentro do Blender, que já tem numpy):
    "C:\\Program Files\\Blender Foundation\\Blender 5.3\\blender.exe" --background --factory-startup --python ferramentas/gerar_texturas.py
    Só algumas (as outras ficam como estão):  ... --python ferramentas/gerar_texturas.py -- papel tecido

Saída (mesmo padrão das texturas baixadas do ambientCG):
    godot/assets/texturas/<material>/<material>_cor.jpg
    godot/assets/texturas/<material>/<material>_normal.jpg   (padrão OpenGL: verde = Y para cima)
    godot/assets/texturas/<material>/<material>_aspereza.jpg
Além disso: máscara de sujeira, decals (PNG com alfa) e o "cookie" da lanterna.

As sementes aleatórias são fixas: rodar de novo gera exatamente as mesmas imagens.

Como as texturas repetem sem emenda:
- todo ruído é feito filtrando ruído branco na FFT. A FFT trata a imagem como se
  ela desse a volta (a borda direita encosta na esquerda), então o ruído já sai repetível;
- as formas (estrelas, manchas, rachaduras...) são desenhadas numa "janela" cujos
  índices dão a volta na imagem (índice % tamanho). O que sai por um lado entra pelo outro;
- o mapa normal usa diferenças com np.roll, que também dá a volta.
"""

from pathlib import Path

import bpy
import numpy as np

# Raiz do projeto = pasta acima de ferramentas/
RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "godot" / "assets" / "texturas"

DOIS_PI = 2.0 * np.pi


# ---------------------------------------------------------------------------
# Ferramentas básicas
# ---------------------------------------------------------------------------

def gerador(semente):
    """Gerador aleatório com semente fixa."""
    return np.random.default_rng(semente)


def ruido(n, tamanho, rng, tamanho_y=None):
    """
    Ruído suave que repete sem emenda (média 0, desvio 1).
    tamanho = tamanho típico das manchas em pixels (na horizontal).
    tamanho_y = idem na vertical; se for maior que 'tamanho', o ruído vira riscos verticais.
    """
    if tamanho_y is None:
        tamanho_y = tamanho
    branco = rng.standard_normal((n, n))
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.rfftfreq(n)[None, :]
    # Desfoque gaussiano feito na frequência (só frequências inteiras -> repete)
    filtro = np.exp(-2.0 * np.pi ** 2 * ((fx * tamanho) ** 2 + (fy * tamanho_y) ** 2))
    r = np.fft.irfft2(np.fft.rfft2(branco) * filtro, s=(n, n))
    r -= r.mean()
    r /= r.std() + 1e-12
    return r.astype(np.float32)


def fbm(n, tamanho, rng, oitavas=4):
    """Soma de ruídos de vários tamanhos (manchas grandes com detalhe menor por cima)."""
    total = np.zeros((n, n), np.float32)
    peso = 1.0
    for _ in range(oitavas):
        total += peso * ruido(n, tamanho, rng)
        tamanho *= 0.5
        peso *= 0.5
    return total / total.std()


def suave(a, b, x):
    """Passagem suave de 0 (em a) para 1 (em b). Funciona com a > b também."""
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def cobertura(d, aa=1.0):
    """Converte distância com sinal (negativa = dentro) em cobertura 0..1 com borda suave."""
    return np.clip(0.5 - d / aa, 0.0, 1.0)


def misturar(a, b, t):
    """Mistura a -> b na proporção t (t pode ser imagem 2D; vira 3D sozinho)."""
    t = np.asarray(t)
    if t.ndim == 2 and np.ndim(a) == 3:
        t = t[..., None]
    return a * (1.0 - t) + b * t


def coordenadas(n):
    """Centro de cada pixel: X é linha (1, n), Y é coluna (n, 1)."""
    c = np.arange(n, dtype=np.float32) + 0.5
    return c[None, :], c[:, None]


def janela(n, cx, cy, rx, ry=None):
    """
    Pedaço da imagem em volta de (cx, cy), com índices que dão a volta nas bordas.
    Devolve (indice, dx, dy): 'indice' serve para ler/escrever na imagem e
    dx, dy são as distâncias de cada pixel até o centro.
    """
    if ry is None:
        ry = rx
    xs = np.arange(int(np.floor(cx - rx)), int(np.ceil(cx + rx)) + 1)
    ys = np.arange(int(np.floor(cy - ry)), int(np.ceil(cy + ry)) + 1)
    dx = (xs + 0.5 - cx).astype(np.float32)[None, :]
    dy = (ys + 0.5 - cy).astype(np.float32)[:, None]
    return np.ix_(ys % n, xs % n), dx, dy


def girar(dx, dy, ang):
    """Gira as coordenadas locais (para desenhar a forma girada)."""
    c, s = np.cos(ang), np.sin(ang)
    return c * dx + s * dy, -s * dx + c * dy


def pintar(img, indice, cob, cor):
    """Pinta 'cor' por cima da imagem RGB onde a cobertura for maior que zero."""
    cob = cob[..., None]
    img[indice] = img[indice] * (1.0 - cob) + np.asarray(cor, np.float32) * cob


def distancia_toroidal(a, b, n):
    """Distância entre dois pontos numa imagem que dá a volta."""
    d = np.abs(np.asarray(a) - np.asarray(b))
    d = np.minimum(d, n - d)
    return float(np.hypot(d[0], d[1]))


# ---------------------------------------------------------------------------
# Formas (distância com sinal: negativo = dentro da forma)
# ---------------------------------------------------------------------------

def sdf_circulo(x, y, r):
    return np.sqrt(x * x + y * y) - r


def sdf_elipse(x, y, a, b):
    """Distância aproximada até uma elipse de semi-eixos a e b."""
    q = np.sqrt((x / a) ** 2 + (y / b) ** 2) + 1e-6
    g = np.sqrt((x / (a * a)) ** 2 + (y / (b * b)) ** 2) / q + 1e-6
    return (q - 1.0) / g


def sdf_segmento(x, y, ax, ay, bx, by):
    """Distância até o segmento de reta A-B."""
    ex, ey = bx - ax, by - ay
    wx, wy = x - ax, y - ay
    t = np.clip((wx * ex + wy * ey) / (ex * ex + ey * ey + 1e-9), 0.0, 1.0)
    return np.sqrt((wx - ex * t) ** 2 + (wy - ey * t) ** 2)


def sdf_polilinha(x, y, pontos):
    """Distância até uma linha quebrada (lista de pontos)."""
    d = None
    for (ax, ay), (bx, by) in zip(pontos[:-1], pontos[1:]):
        s = sdf_segmento(x, y, ax, ay, bx, by)
        d = s if d is None else np.minimum(d, s)
    return d


def sdf_poligono(x, y, vertices):
    """Distância com sinal até um polígono qualquer (dentro = negativo)."""
    v = np.asarray(vertices, np.float32)
    x, y = np.broadcast_arrays(x, y)
    d = (x - v[0, 0]) ** 2 + (y - v[0, 1]) ** 2
    sinal = np.ones(x.shape, np.float32)
    j = len(v) - 1
    for i in range(len(v)):
        ex, ey = v[j, 0] - v[i, 0], v[j, 1] - v[i, 1]
        wx, wy = x - v[i, 0], y - v[i, 1]
        t = np.clip((wx * ex + wy * ey) / (ex * ex + ey * ey + 1e-9), 0.0, 1.0)
        bx, by = wx - ex * t, wy - ey * t
        d = np.minimum(d, bx * bx + by * by)
        c1 = y >= v[i, 1]
        c2 = y < v[j, 1]
        c3 = ex * wy > ey * wx
        troca = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
        sinal = np.where(troca, -sinal, sinal)
        j = i
    return sinal * np.sqrt(d)


def vertices_estrela(pontas, r_fora, r_dentro, ang=0.0):
    """Vértices de uma estrela (alternando ponta e vão)."""
    vs = []
    for k in range(pontas * 2):
        a = ang - np.pi / 2 + k * np.pi / pontas
        r = r_fora if k % 2 == 0 else r_dentro
        vs.append((r * np.cos(a), r * np.sin(a)))
    return vs


def contorno_irregular(th, rng, forca=0.15, harmonicos=6):
    """Fator de raio que varia com o ângulo (para manchas não ficarem redondas demais)."""
    f = np.zeros_like(th)
    for k in range(2, harmonicos + 1):
        f += (forca / k) * rng.uniform(0.5, 1.0) * np.sin(k * th + rng.uniform(0, DOIS_PI))
    return 1.0 + f


# ---------------------------------------------------------------------------
# Mapas derivados e gravação
# ---------------------------------------------------------------------------

def normal_de_altura(altura, forca):
    """
    Mapa normal (padrão OpenGL, verde = Y para cima) a partir do mapa de altura.
    As diferenças usam np.roll, que dá a volta: o mapa normal também repete.
    """
    gx = (np.roll(altura, -1, axis=1) - np.roll(altura, 1, axis=1)) * 0.5
    # derivada "para baixo" na imagem; para cima é o contrário
    gl = (np.roll(altura, -1, axis=0) - np.roll(altura, 1, axis=0)) * 0.5
    nx = -gx * forca
    ny = gl * forca
    nz = np.ones_like(nx)
    comp = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([nx / comp, ny / comp, nz / comp], axis=-1) * 0.5 + 0.5


def salvar(arr, caminho, alfa=False):
    """
    Grava a imagem com a API do Blender. 'arr' vem de cima para baixo (linha 0 = topo):
    pode ser cinza (h, w), RGB (h, w, 3) ou RGBA (h, w, 4), com valores 0..1.
    O Blender guarda as linhas de baixo para cima, por isso a imagem é invertida.
    """
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    arr = np.clip(np.asarray(arr, np.float32), 0.0, 1.0)
    h, w = arr.shape[:2]
    rgba = np.ones((h, w, 4), np.float32)
    if arr.ndim == 2:
        rgba[..., :3] = arr[..., None]
    else:
        rgba[..., :arr.shape[2]] = arr
    img = bpy.data.images.new(caminho.stem, w, h, alpha=alfa)
    img.pixels.foreach_set(rgba[::-1].ravel())
    img.filepath_raw = str(caminho)
    if caminho.suffix.lower() == ".jpg":
        img.file_format = "JPEG"
        bpy.context.scene.render.image_settings.quality = 90
        img.save(filepath=str(caminho), quality=90)
    else:
        img.file_format = "PNG"
        img.save(filepath=str(caminho))
    bpy.data.images.remove(img)
    print(f"  ok  {caminho.relative_to(RAIZ)}  ({w}x{h})")


def salvar_material(nome, cor, normal, aspereza):
    pasta = PASTA / nome
    salvar(cor, pasta / f"{nome}_cor.jpg")
    salvar(normal, pasta / f"{nome}_normal.jpg")
    salvar(aspereza, pasta / f"{nome}_aspereza.jpg")


# ---------------------------------------------------------------------------
# 1. Carpete de fliperama (anos 90)
# ---------------------------------------------------------------------------

def carpete_fliperama():
    n = 2048
    rng = gerador(101)

    # Fundo azul-marinho bem escuro, com leve variação
    fundo = np.array([0.025, 0.030, 0.085], np.float32)
    cor = np.ones((n, n, 3), np.float32) * fundo
    cor *= (1.0 + 0.12 * ruido(n, 80, rng))[..., None]

    # Neon desbotado: magenta, ciano, amarelo, laranja
    neon = np.array([
        [0.80, 0.22, 0.62],
        [0.18, 0.70, 0.76],
        [0.88, 0.78, 0.26],
        [0.90, 0.46, 0.16],
    ], np.float32)
    cinza = neon.mean(axis=1, keepdims=True)
    neon = (neon * 0.78 + cinza * 0.22) * 0.85

    def cor_neon(exceto=None):
        opcoes = [i for i in range(len(neon)) if i != exceto]
        i = int(rng.choice(opcoes))
        return i, neon[i] * rng.uniform(0.85, 1.0)

    # Sorteio das posições sem alinhar (distância mínima, contando a volta)
    tipos = ["planeta", "estrela", "triangulo", "circulo", "zigue"]
    tamanhos = {"planeta": (36, 58), "estrela": (24, 44), "triangulo": (26, 52),
                "circulo": (16, 38), "zigue": (55, 95)}
    formas = []
    for _ in range(190):
        tipo = tipos[int(rng.integers(len(tipos)))]
        r = rng.uniform(*tamanhos[tipo])
        alcance = r * (1.75 if tipo == "planeta" else 1.0)
        for _tentativa in range(60):
            c = rng.uniform(0, n, 2)
            if all(distancia_toroidal(c, f[1], n) > alcance + f[3] + 18 for f in formas):
                formas.append((tipo, c, r, alcance))
                break
    # Estrelinhas e pontinhos para encher os vãos
    for _ in range(420):
        tipo = "brilho" if rng.random() < 0.55 else "ponto"
        r = rng.uniform(6, 12) if tipo == "brilho" else rng.uniform(3, 5.5)
        for _tentativa in range(30):
            c = rng.uniform(0, n, 2)
            if all(distancia_toroidal(c, f[1], n) > r + f[3] + 10 for f in formas):
                formas.append((tipo, c, r, r))
                break

    for tipo, (cx, cy), r, alcance in formas:
        ang = rng.uniform(0, DOIS_PI)
        indice_a, ca = cor_neon()
        _, cb = cor_neon(indice_a)
        idx, dx, dy = janela(n, cx, cy, alcance + 8)
        x, y = girar(dx, dy, ang)
        if tipo == "planeta":
            # anel atrás, planeta, e a metade da frente do anel por cima
            fora = sdf_elipse(x, y, r * 1.75, r * 0.50)
            dentro = sdf_elipse(x, y, r * 1.38, r * 0.33)
            anel = cobertura(np.maximum(fora, -dentro))
            disco = cobertura(sdf_circulo(x, y, r))
            pintar(cor, idx, anel, cb)
            pintar(cor, idx, disco, ca)
            faixa = cobertura(np.abs(y + r * 0.35) - r * 0.12) * disco
            pintar(cor, idx, faixa, ca * 0.6 + fundo * 0.4)
            pintar(cor, idx, anel * suave(-1.0, 1.0, y), cb)
        elif tipo == "estrela":
            d = sdf_poligono(x, y, vertices_estrela(5, r, r * 0.45))
            if rng.random() < 0.35:
                d = np.abs(d) - 3.0
            pintar(cor, idx, cobertura(d), ca)
        elif tipo == "triangulo":
            d = sdf_poligono(x, y, vertices_estrela(3, r, r * 0.5)[::2])
            if rng.random() < 0.5:
                d = np.abs(d + 3.0) - 3.0
            pintar(cor, idx, cobertura(d), ca)
        elif tipo == "circulo":
            d = np.abs(sdf_circulo(x, y, r)) - rng.uniform(2.5, 4.0)
            pintar(cor, idx, cobertura(d), ca)
            if rng.random() < 0.4:
                pintar(cor, idx, cobertura(sdf_circulo(x, y, r * 0.35)), cb)
        elif tipo == "zigue":
            segs = int(rng.integers(5, 8))
            amp = rng.uniform(12, 22)
            px = np.linspace(-r, r, segs + 1)
            py = np.array([amp if k % 2 else -amp for k in range(segs + 1)])
            d = sdf_polilinha(x, y, list(zip(px, py))) - rng.uniform(2.5, 3.5)
            pintar(cor, idx, cobertura(d), ca)
        elif tipo == "brilho":
            d = sdf_poligono(x, y, vertices_estrela(4, r, r * 0.25))
            pintar(cor, idx, cobertura(d), ca if rng.random() < 0.7 else (0.75, 0.75, 0.70))
        else:  # ponto
            pintar(cor, idx, cobertura(sdf_circulo(x, y, r)), ca)

    # Fibra: ruído bem fino, mais tufinhos um pouco maiores
    fibra = ruido(n, 0.7, rng)
    tufo = ruido(n, 3.0, rng)
    cor *= np.clip(1.0 + 0.10 * fibra + 0.07 * tufo, 0.6, 1.4)[..., None]

    # Desgaste: manchas grandes e suaves mais claras e sem cor (caminho das pessoas)
    gasto = suave(0.3, 2.2, fbm(n, 260, rng, 3)) * 0.85
    lum = cor.mean(axis=2, keepdims=True)
    alvo = cor * 0.6 + lum * 0.4 + 0.05
    cor = misturar(cor, alvo, gasto)

    # Manchas escuras de refrigerante (com borda um pouco mais escura)
    borda_ruido = ruido(n, 10, rng)
    mancha_total = np.zeros((n, n), np.float32)
    for _ in range(7):
        R = rng.uniform(40, 120)
        cx, cy = rng.uniform(0, n, 2)
        idx, dx, dy = janela(n, cx, cy, R * 2.0 + 20)
        th = np.arctan2(dy, dx)
        d = np.sqrt(dx * dx + dy * dy) - R * contorno_irregular(th, rng, 0.3) + 8.0 * borda_ruido[idx]
        dentro = suave(6.0, -10.0, d) * rng.uniform(0.4, 0.6)
        borda = np.exp(-(d / 4.0) ** 2) * 0.3
        mancha_total[idx] = np.maximum(mancha_total[idx], np.clip(dentro + borda, 0, 1))
    cor = misturar(cor, cor * 0.4 + np.array([0.05, 0.028, 0.010], np.float32), mancha_total)

    altura = fibra * 0.6 + tufo * 0.8 - mancha_total * 0.5
    normal = normal_de_altura(altura, 0.22)
    aspereza = 0.90 + 0.03 * fibra + 0.02 * gasto - 0.06 * mancha_total
    salvar_material("carpete_fliperama", cor, normal, aspereza)


# ---------------------------------------------------------------------------
# 2. Piso quadriculado gasto
# ---------------------------------------------------------------------------

def quadriculado_gasto():
    n = 1024
    lado = n // 4  # 4x4 ladrilhos
    rng = gerador(202)
    X, Y = coordenadas(n)

    # Distância até a linha de rejunte mais próxima (as linhas ficam nas divisas 0, 256, 512...)
    mx, my = X % lado, Y % lado
    dist = np.minimum(np.minimum(mx, lado - mx), np.minimum(my, lado - my))
    dist = np.broadcast_to(dist, (n, n)).astype(np.float32)
    rejunte = cobertura(dist - 1.5)  # ~3 px de rejunte

    # Xadrez preto/branco com tom um pouco diferente em cada ladrilho
    ix = (np.arange(n) // lado)[None, :]
    iy = (np.arange(n) // lado)[:, None]
    branco_peca = ((ix + iy) % 2 == 0)
    branco = np.array([0.80, 0.76, 0.62], np.float32)
    preto = np.array([0.095, 0.095, 0.10], np.float32)
    cor = np.where(branco_peca[..., None], branco, preto).astype(np.float32)
    tom = 1.0 + 0.04 * rng.standard_normal((4, 4)).astype(np.float32)
    matiz = 0.008 * rng.standard_normal((4, 4, 3)).astype(np.float32)
    cor = cor * tom[iy, ix][..., None] + matiz[iy, ix] * cor
    cor *= (1.0 + 0.035 * ruido(n, 5, rng) + 0.04 * ruido(n, 40, rng))[..., None]

    altura = suave(1.5, 4.0, dist)  # peça alta, rejunte afundado, quina arredondada
    aspereza = 0.58 + 0.04 * ruido(n, 6, rng)

    # Lascas nas bordas de algumas peças (aparece a massa cinza por baixo)
    massa = np.array([0.36, 0.34, 0.31], np.float32)
    borda_ruido = ruido(n, 3, rng)
    lascado = np.zeros((n, n), np.float32)
    for _ in range(9):
        px_, py_ = int(rng.integers(4)), int(rng.integers(4))
        lado_peca = int(rng.integers(4))
        t = rng.uniform(0.15, 0.85) * lado
        cx = px_ * lado + [t, t, 0, lado][lado_peca]
        cy = py_ * lado + [0, lado, t, t][lado_peca]
        R = rng.uniform(8, 22)
        idx, dx, dy = janela(n, cx, cy, R * 2.0 + 6)
        th = np.arctan2(dy, dx)
        d = np.sqrt(dx * dx + dy * dy) - R * contorno_irregular(th, rng, 0.4) + 2.0 * borda_ruido[idx]
        lascado[idx] = np.maximum(lascado[idx], cobertura(d, 1.5))
    lascado *= 1.0 - rejunte
    cor = misturar(cor, massa * (1.0 + 0.1 * borda_ruido[..., None]), lascado)
    altura -= 0.6 * lascado

    # Rachaduras: linhas finas que andam meio sem rumo dentro de uma peça
    rachas = np.zeros((n, n), np.float32)
    for _ in range(7):
        px_, py_ = int(rng.integers(4)), int(rng.integers(4))
        x0 = px_ * lado + rng.uniform(4, lado - 4)
        y0 = py_ * lado + (4 if rng.random() < 0.5 else lado - 4)
        ang = (np.pi / 2 if y0 % lado < lado / 2 else -np.pi / 2) + rng.uniform(-0.6, 0.6)
        pts = [(x0, y0)]
        for _passo in range(int(rng.integers(10, 30))):
            ang += rng.uniform(-0.5, 0.5)
            nx_ = np.clip(pts[-1][0] + 7 * np.cos(ang), px_ * lado + 3, (px_ + 1) * lado - 3)
            ny_ = np.clip(pts[-1][1] + 7 * np.sin(ang), py_ * lado + 3, (py_ + 1) * lado - 3)
            pts.append((nx_, ny_))
        pts = np.array(pts)
        cx, cy = pts.mean(axis=0)
        r = np.abs(pts - (cx, cy)).max() + 6
        idx, dx, dy = janela(n, cx, cy, r)
        d = sdf_polilinha(dx, dy, list(pts - (cx, cy))) - 0.6
        rachas[idx] = np.maximum(rachas[idx], cobertura(d, 1.2))
    cor *= (1.0 - 0.7 * rachas)[..., None]
    altura -= 0.5 * rachas

    # Sujeira: manchas espalhadas e acúmulo perto do rejunte
    sujeira = suave(0.3, 1.8, fbm(n, 70, rng)) * 0.6
    sujeira += np.exp(-dist / 9.0) * 0.45 * (0.6 + 0.4 * ruido(n, 15, rng))
    sujeira = np.clip(sujeira, 0, 1) * (1.0 - rejunte)
    cor_sujeira = np.array([0.24, 0.20, 0.14], np.float32)
    cor = misturar(cor, cor * 0.5 + cor_sujeira * 0.5, sujeira * 0.7)

    # Rejunte escuro e sujo
    cor_rejunte = np.array([0.11, 0.10, 0.085], np.float32) * (1.0 + 0.25 * ruido(n, 2, rng))[..., None]
    cor = misturar(cor, cor_rejunte, rejunte)

    aspereza = aspereza + 0.25 * sujeira + 0.3 * lascado + 0.25 * rachas
    aspereza = misturar(aspereza, 0.9, rejunte)
    normal = normal_de_altura(altura, 1.6)
    salvar_material("quadriculado_gasto", cor, normal, aspereza)


# ---------------------------------------------------------------------------
# 3. Papel de parede de festa
# ---------------------------------------------------------------------------

def papel_parede_festa():
    n = 1024
    rng = gerador(303)

    vinho = np.array([0.34, 0.11, 0.14], np.float32)
    mostarda = np.array([0.72, 0.56, 0.20], np.float32)
    creme = np.array([0.84, 0.77, 0.62], np.float32)
    azul = np.array([0.34, 0.45, 0.57], np.float32)

    def desbotar(c):
        return c * 0.82 + vinho * 0.18

    cor = np.ones((n, n, 3), np.float32) * vinho
    cor *= (1.0 + 0.05 * ruido(n, 30, rng))[..., None]

    # Grade deslocada: pontos (64 + 128a, 64 + 128b) com a + b par.
    # Linhas b pares = chapéus, linhas b ímpares = estrelas; vãos (a + b ímpar) = bolinhas.
    for b in range(8):
        for a in range(8):
            cx, cy = 64 + 128 * a, 64 + 128 * b
            if (a + b) % 2 == 0 and b % 2 == 0:
                # Chapéu de festa: triângulo listrado com pompom na ponta
                alterna = (a // 2 + b // 2) % 2
                corpo, listra, pompom = (mostarda, azul, creme) if alterna == 0 else (azul, creme, mostarda)
                inclina = 0.18 if (a // 2) % 2 == 0 else -0.18
                idx, dx, dy = janela(n, cx, cy, 80)
                x, y = girar(dx, dy, inclina)
                tri = cobertura(sdf_poligono(x, y, [(0, -55), (36, 48), (-36, 48)]))
                faixas = np.clip(np.sin(DOIS_PI * (x * 0.6 + y) / 30.0) * 4.0, -1, 1) * 0.5 + 0.5
                pintar(cor, idx, tri, desbotar(corpo))
                pintar(cor, idx, tri * faixas, desbotar(listra))
                # barrado em zigue-zague na base
                zig = np.abs(((x / 9.0) % 2.0) - 1.0) * 6.0
                barra = cobertura(np.abs(y - 44 + zig * 0.5) - 3.0) * suave(37, 33, np.abs(x))
                pintar(cor, idx, barra, desbotar(creme))
                th = np.arctan2(y + 58, x)
                fofo = 12.0 * (1.0 + 0.12 * np.sin(8 * th))
                pintar(cor, idx, cobertura(sdf_circulo(x, y + 58, fofo)), desbotar(pompom))
            elif (a + b) % 2 == 0:
                # Estrela
                c = creme if (a // 2 + b // 2) % 2 == 0 else mostarda
                idx, dx, dy = janela(n, cx, cy, 34)
                x, y = girar(dx, dy, 0.12)
                pintar(cor, idx, cobertura(sdf_poligono(x, y, vertices_estrela(5, 26, 11))), desbotar(c))
            else:
                # Três bolinhas de confete nos vãos
                idx, dx, dy = janela(n, cx, cy, 24)
                for k, c in enumerate((azul, mostarda, creme)):
                    ang = DOIS_PI * k / 3 + 0.4
                    pintar(cor, idx, cobertura(sdf_circulo(dx - 11 * np.cos(ang), dy - 11 * np.sin(ang), 4.5)),
                           desbotar(c))

    # Textura do papel: grão fino e fibrinhas
    grao = ruido(n, 0.7, rng)
    fibras = ruido(n, 0.8, rng, 6.0)
    cor *= (1.0 + 0.04 * grao + 0.03 * fibras)[..., None]

    # Manchas de umidade amareladas com borda marcada
    umidade_base = fbm(n, 150, rng, 4)
    limite = 1.0
    umidade = suave(limite - 0.15, limite + 0.4, umidade_base)
    borda = np.exp(-((umidade_base - limite) / 0.07) ** 2)
    amarelado = np.array([0.74, 0.64, 0.36], np.float32)
    cor = misturar(cor, cor * 0.5 + amarelado * 0.5, umidade * 0.7)
    cor = misturar(cor, cor * 0.6 + np.array([0.20, 0.13, 0.05], np.float32) * 0.4, borda * 0.5)

    # Escurecimento irregular (fumaça, tempo)
    escuro = suave(-1.5, 1.5, fbm(n, 200, rng, 3))
    cor *= (0.72 + 0.28 * escuro)[..., None]

    altura = grao * 0.5 + fibras * 0.4 + umidade * 0.6
    normal = normal_de_altura(altura, 0.25)
    aspereza = 0.80 + 0.03 * grao + 0.06 * umidade
    salvar_material("papel_parede_festa", cor, normal, aspereza)


# ---------------------------------------------------------------------------
# 4. Forro de placas manchado
# ---------------------------------------------------------------------------

def furos_espalhados(n, quantidade, raio, rng):
    """Furinhos redondos espalhados (feitos por convolução na FFT, então repetem)."""
    pontos = np.zeros((n, n), np.float32)
    ys = rng.integers(0, n, quantidade)
    xs = rng.integers(0, n, quantidade)
    np.add.at(pontos, (ys, xs), 1.0)
    c = np.arange(n, dtype=np.float32)
    c = np.minimum(c, n - c)
    nucleo = np.clip(raio + 0.5 - np.sqrt(c[None, :] ** 2 + c[:, None] ** 2), 0.0, 1.0)
    r = np.fft.irfft2(np.fft.rfft2(pontos) * np.fft.rfft2(nucleo), s=(n, n))
    return np.clip(r, 0.0, 1.0).astype(np.float32)


def forro_manchado():
    n = 1024
    lado = n // 2  # a imagem cobre 2x2 placas
    rng = gerador(404)
    X, Y = coordenadas(n)

    mx, my = X % lado, Y % lado
    dist = np.minimum(np.minimum(mx, lado - mx), np.minimum(my, lado - my))
    dist = np.broadcast_to(dist, (n, n)).astype(np.float32)
    junta = cobertura(dist - 1.0)  # junta fina (~2 px)

    base = np.array([0.80, 0.79, 0.76], np.float32)
    cor = np.ones((n, n, 3), np.float32) * base
    cor *= (1.0 + 0.02 * ruido(n, 3, rng) + 0.025 * ruido(n, 50, rng))[..., None]

    # Furinhos do forro mineral (longe das juntas)
    furos = np.maximum(furos_espalhados(n, 5200, 0.9, rng), furos_espalhados(n, 1300, 1.6, rng))
    furos *= suave(4.0, 7.0, dist)
    cor = misturar(cor, cor * 0.55, furos)

    # Manchas de infiltração em anel: borda marrom mais escura, miolo mais claro
    marrom = np.array([0.55, 0.42, 0.22], np.float32)
    borda_ruido = ruido(n, 8, rng)
    tinta_miolo = np.zeros((n, n), np.float32)
    tinta_borda = np.zeros((n, n), np.float32)
    for cx, cy, R in ((300, 260, 150), (800, 700, 110), (120, 840, 80)):
        idx, dx, dy = janela(n, cx, cy, R * 2.0)
        th = np.arctan2(dy, dx)
        rel = np.sqrt(dx * dx + dy * dy) / (R * contorno_irregular(th, rng, 0.35)) + 0.06 * borda_ruido[idx]
        miolo = suave(1.02, 0.9, rel) * 0.22
        anel = np.exp(-((rel - 0.98) / 0.035) ** 2) * 0.75
        anel += np.exp(-((rel - 0.72) / 0.03) ** 2) * 0.30  # marca de uma infiltração antiga
        tinta_miolo[idx] = np.maximum(tinta_miolo[idx], miolo)
        tinta_borda[idx] = np.maximum(tinta_borda[idx], anel)
    cor = misturar(cor, cor * 0.6 + marrom * 0.4, tinta_miolo)
    cor = misturar(cor, cor * 0.45 + marrom * 0.40, tinta_borda)

    # Juntas cinza-escuras
    cor = misturar(cor, np.array([0.24, 0.24, 0.25], np.float32), junta)

    altura = suave(1.0, 3.0, dist) - 0.8 * furos + 0.15 * ruido(n, 2, rng)
    normal = normal_de_altura(altura, 1.2)
    aspereza = 0.85 + 0.03 * ruido(n, 4, rng) + 0.05 * junta + 0.03 * tinta_borda
    salvar_material("forro_manchado", cor, normal, aspereza)


# ---------------------------------------------------------------------------
# 5. Máscara de sujeira para cantos
# ---------------------------------------------------------------------------

def sujeira_cantos():
    n = 1024
    rng = gerador(505)

    manchas = suave(0.3, 2.0, fbm(n, 90, rng)) * 0.75
    riscos = suave(0.8, 2.8, ruido(n, 5.0, rng, 110.0)) * 0.3  # riscos verticais compridos

    # Escorridos: filetes verticais que afinam e terminam numa gotinha
    escorrido = np.zeros((n, n), np.float32)
    for _ in range(30):
        x0, y0 = rng.uniform(0, n, 2)
        L = rng.uniform(80, 360)
        w0 = rng.uniform(1.2, 3.8)
        forca = rng.uniform(0.35, 0.85)
        fase = rng.uniform(0, DOIS_PI)
        idx, dx, dy = janela(n, x0, y0 + L / 2, w0 * 3 + 8, L / 2 + 10)
        desce = dy + L / 2  # 0 no começo do filete
        t = np.clip(desce / L, 0, 1)
        balanco = 1.5 * np.sin(desce * 0.035 + fase)
        d = np.abs(dx - balanco) - w0 * (1.0 - 0.45 * t)
        fio = cobertura(d) * suave(-2, 8, desce) * suave(L + 1, L - 3, desce) * (0.45 + 0.55 * (1 - t))
        gota = cobertura(sdf_circulo(dx - 1.5 * np.sin(L * 0.035 + fase), desce - L, w0 * 1.3))
        valor = np.maximum(fio, gota * 0.9) * forca
        escorrido[idx] = np.maximum(escorrido[idx], valor)

    # Poeira granulada, mais densa em algumas regiões
    densidade = 0.3 + 0.7 * suave(-0.8, 1.2, ruido(n, 60, rng))
    graos = suave(1.5, 2.8, ruido(n, 0.6, rng)) * 0.55 * densidade

    # Junta tudo sem estourar (como sobrepor camadas transparentes)
    mascara = 1.0 - (1.0 - manchas) * (1.0 - riscos) * (1.0 - escorrido) * (1.0 - graos)
    mascara = np.clip(mascara * (0.92 + 0.08 * ruido(n, 1.0, rng)), 0, 1)
    salvar(mascara, PASTA / "sujeira_cantos" / "sujeira_cantos_cor.png")


# ---------------------------------------------------------------------------
# 6. Decals (PNG com alfa, não precisam repetir)
# ---------------------------------------------------------------------------

class Tela:
    """Tela RGBA para os decals (guarda a cor já multiplicada pelo alfa)."""

    def __init__(self, n=512):
        self.n = n
        self.p = np.zeros((n, n, 3), np.float32)
        self.a = np.zeros((n, n), np.float32)
        self.X, self.Y = coordenadas(n)

    def pintar(self, alfa, cor, indice=(slice(None), slice(None))):
        alfa = np.clip(alfa, 0, 1)
        cor = np.asarray(cor, np.float32)
        self.p[indice] = cor * alfa[..., None] + self.p[indice] * (1.0 - alfa[..., None])
        self.a[indice] = alfa + self.a[indice] * (1.0 - alfa)

    def salvar(self, caminho):
        n = self.n
        # Garante alfa 0 perto das bordas da imagem
        borda = np.minimum(np.minimum(self.X, n - self.X), np.minimum(self.Y, n - self.Y))
        a = self.a * suave(2.0, 14.0, borda)
        media = self.p.sum(axis=(0, 1)) / max(self.a.sum(), 1e-6)
        rgb = np.where(self.a[..., None] > 1e-3, self.p / np.maximum(self.a, 1e-6)[..., None], media)
        salvar(np.concatenate([rgb, a[..., None]], axis=-1), caminho, alfa=True)


def decal_mancha_agua(pasta):
    rng = gerador(601)
    t = Tela()
    dx, dy = t.X - 256, t.Y - 256
    th = np.arctan2(dy, dx)
    rel = np.sqrt(dx * dx + dy * dy) / (175 * contorno_irregular(th, rng, 0.3)) + 0.03 * ruido(512, 12, rng)
    miolo = suave(1.01, 0.92, rel) * (0.16 + 0.06 * ruido(512, 20, rng))
    anel = np.exp(-((rel - 0.985) / 0.03) ** 2) * 0.75 + np.exp(-((rel - 0.80) / 0.02) ** 2) * 0.25
    t.pintar(miolo, (0.45, 0.34, 0.20))
    t.pintar(anel, (0.33, 0.22, 0.11))
    t.salvar(pasta / "decal_mancha_agua.png")


def decal_gordura(pasta):
    rng = gerador(602)
    t = Tela()
    alfa = np.zeros((512, 512), np.float32)
    r_borda = ruido(512, 5, rng)
    dx, dy = t.X - 256, t.Y - 256
    th = np.arctan2(dy, dx)
    d = np.sqrt(dx * dx + dy * dy) - 105 * contorno_irregular(th, rng, 0.55, 9) + 6 * r_borda
    alfa = np.maximum(alfa, cobertura(d, 2.0))
    # Respingos em volta (alguns compridos, apontando para fora)
    for _ in range(34):
        ang = rng.uniform(0, DOIS_PI)
        dist = rng.uniform(120, 215)
        cx, cy = 256 + dist * np.cos(ang), 256 + dist * np.sin(ang)
        r = rng.uniform(3, 13) * (1.2 - dist / 300)
        idx, ddx, ddy = janela(512, cx, cy, r * 3 + 3)
        x, y = girar(ddx, ddy, ang)
        alongado = rng.uniform(1.0, 2.6)
        gota = cobertura(sdf_elipse(x, y, r * alongado, r), 1.5)
        alfa[idx] = np.maximum(alfa[idx], gota)
    alfa *= 0.82 + 0.1 * ruido(512, 15, rng)
    # Cor quase preta amarelada, com reflexos claros (aparência brilhante)
    brilho = suave(1.2, 2.2, ruido(512, 4, rng)) * 0.6 * suave(-5, -20, d)
    cor = misturar(np.ones((512, 512, 3), np.float32) * np.array([0.10, 0.075, 0.035], np.float32),
                   np.array([0.42, 0.36, 0.24], np.float32), brilho)
    t.pintar(alfa, cor)
    t.salvar(pasta / "decal_gordura.png")


def decal_pegadas(pasta):
    rng = gerador(603)
    t = Tela()
    cor_terra = np.array([0.28, 0.24, 0.19], np.float32)
    mancha = ruido(512, 4, rng)
    falha = ruido(512, 1.2, rng)
    direcao = np.deg2rad(-50)  # andando de baixo/esquerda para cima/direita
    passo = 112
    inicio = np.array([256.0, 256.0]) - np.array([np.cos(direcao), np.sin(direcao)]) * passo * 1.5
    for k in range(4):
        lado = -1 if k % 2 == 0 else 1  # esquerdo, direito...
        perp = np.array([-np.sin(direcao), np.cos(direcao)]) * 24 * lado
        cx, cy = inicio + np.array([np.cos(direcao), np.sin(direcao)]) * passo * k + perp
        idx, dx, dy = janela(512, cx, cy, 75)
        # eixo do pé: y local aponta para o calcanhar
        x, y = girar(dx, dy, direcao + np.pi / 2)
        x = x * lado
        frente = sdf_elipse(x - 4, y + 22, 24, 38)
        calcanhar = sdf_elipse(x + 1, y - 40, 18, 22)
        arco = sdf_segmento(x, y, 2, -10, 0, 34) - 13
        d = np.minimum(np.minimum(frente, calcanhar), arco)
        sola = cobertura(d, 1.5)
        # Desenho da sola: gomos em zigue-zague e um vão entre a frente e o calcanhar
        gomos = np.clip(np.sin(DOIS_PI * (y + 3 * np.abs(((x / 6) % 2) - 1)) / 9.0) * 3 + 0.8, 0, 1)
        vao = suave(16, 26, y) * suave(36, 26, y) * 0.75
        contorno = cobertura(np.abs(d + 3) - 2.5)
        desenho = np.maximum(gomos * (1 - vao), contorno)
        sujo = suave(-1.2, 0.6, mancha[idx]) * suave(-1.5, 0.0, falha[idx])
        alfa = sola * desenho * sujo * (0.85 - 0.13 * k)
        t.pintar(alfa, cor_terra, idx)
    t.salvar(pasta / "decal_pegadas.png")


def decal_confete(pasta):
    rng = gerador(604)
    t = Tela()
    cores = [(0.95, 0.80, 0.15), (0.95, 0.42, 0.66), (0.22, 0.52, 0.95), (0.30, 0.80, 0.38),
             (0.98, 0.56, 0.16), (0.62, 0.38, 0.88), (0.25, 0.82, 0.85)]
    for _ in range(260):
        r = 215 * np.sqrt(rng.random())
        ang = rng.uniform(0, DOIS_PI)
        cx, cy = 256 + r * np.cos(ang), 256 + r * np.sin(ang)
        idx, dx, dy = janela(512, cx, cy, 14)
        x, y = girar(dx, dy, rng.uniform(0, np.pi))
        if rng.random() < 0.65:
            w, h = rng.uniform(2.5, 4.5), rng.uniform(5, 9)
            d = np.maximum(np.abs(x) - w, np.abs(y) - h)
        else:
            d = sdf_circulo(x, y, rng.uniform(3.5, 6))
        c = np.array(cores[int(rng.integers(len(cores)))], np.float32) * rng.uniform(0.8, 1.0)
        t.pintar(cobertura(d) * rng.uniform(0.85, 1.0), c, idx)
    t.salvar(pasta / "decal_confete.png")


def decal_refrigerante(pasta):
    rng = gerador(605)
    t = Tela()
    dx, dy = t.X - 250, t.Y - 262
    th = np.arctan2(dy, dx)
    d = np.sqrt(dx * dx + dy * dy) - 140 * contorno_irregular(th, rng, 0.45, 8) + 7 * ruido(512, 6, rng)
    for _ in range(10):
        ang = rng.uniform(0, DOIS_PI)
        dist = rng.uniform(150, 200)
        gota = sdf_circulo(dx - dist * np.cos(ang), dy - dist * np.sin(ang), rng.uniform(4, 12))
        d = np.minimum(d, gota)
    dentro = cobertura(d, 2.5) * (0.55 + 0.12 * ruido(512, 18, rng))
    borda = np.exp(-((d + 4) / 4.0) ** 2) * 0.85
    t.pintar(dentro, (0.22, 0.10, 0.04))
    t.pintar(borda * cobertura(d, 2.5), (0.11, 0.05, 0.02))
    t.salvar(pasta / "decal_refrigerante.png")


def decal_rachadura(pasta):
    rng = gerador(606)
    t = Tela()
    segmentos = []  # (x0, y0, x1, y1, largura)

    def crescer(x, y, ang, comprimento, largura, nivel):
        passos = int(comprimento / 8)
        for _ in range(passos):
            ang += rng.uniform(-0.45, 0.45)
            nx_, ny_ = x + 8 * np.cos(ang), y + 8 * np.sin(ang)
            if not (30 < nx_ < 482 and 30 < ny_ < 482):
                return
            segmentos.append((x, y, nx_, ny_, largura))
            if nivel < 3 and rng.random() < 0.10:
                lado = 1 if rng.random() < 0.5 else -1
                crescer(nx_, ny_, ang + lado * rng.uniform(0.5, 1.1), comprimento * 0.45,
                        largura * 0.6, nivel + 1)
            x, y = nx_, ny_
            largura = max(0.5, largura * 0.985)

    crescer(256, 256, rng.uniform(0, DOIS_PI), 230, 3.2, 0)
    crescer(256, 256, rng.uniform(0, DOIS_PI) + np.pi, 200, 3.0, 0)
    nucleo = np.zeros((512, 512), np.float32)
    halo = np.zeros((512, 512), np.float32)
    for x0, y0, x1, y1, w in segmentos:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        idx, dx, dy = janela(512, cx, cy, 20)
        d = sdf_segmento(dx, dy, x0 - cx, y0 - cy, x1 - cx, y1 - cy)
        nucleo[idx] = np.maximum(nucleo[idx], cobertura(d - w / 2, 1.0))
        halo[idx] = np.maximum(halo[idx], np.exp(-d / (3 + w * 2)) * 0.3)
    t.pintar(halo * (0.7 + 0.3 * ruido(512, 4, rng)), (0.16, 0.15, 0.14))
    t.pintar(nucleo * 0.92, (0.04, 0.04, 0.04))
    t.salvar(pasta / "decal_rachadura.png")


def decal_giz_cera(pasta):
    rng = gerador(607)
    t = Tela()
    # grão do giz: o traço falha onde o papel/parede tem "dentinhos"
    grao = ruido(512, 0.8, rng) + 0.4 * ruido(512, 2.5, rng)

    def traco(pontos, largura, cor, densidade=0.0):
        pontos = np.asarray(pontos, np.float32)
        # tremidinha de mão de criança
        pontos = pontos + rng.normal(0, 1.2, pontos.shape)
        cx, cy = pontos.mean(axis=0)
        r = np.abs(pontos - (cx, cy)).max() + largura + 4
        idx, dx, dy = janela(512, cx, cy, r)
        d = sdf_polilinha(dx, dy, list(pontos - (cx, cy))) - largura / 2
        cob = cobertura(d, 1.5) * suave(-0.9 + densidade, 0.4 + densidade, grao[idx])
        t.pintar(cob * 0.92, cor, idx)

    def rabisco_dentro(mascara_fn, x0, y0, x1, y1, espaco, largura, cor):
        """Preenche uma área com vai-e-vem (como criança pintando)."""
        pts = []
        y = y0
        ida = True
        while y < y1:
            pts.append((x0, y) if ida else (x1, y))
            pts.append((x1, y + espaco / 2) if ida else (x0, y + espaco / 2))
            ida = not ida
            y += espaco
        pts = np.asarray(pts, np.float32) + rng.normal(0, 1.5, (len(pts), 2))
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        idx, dx, dy = janela(512, cx, cy, max(x1 - x0, y1 - y0) / 2 + 8)
        d = sdf_polilinha(dx, dy, list(pts - (cx, cy))) - largura / 2
        dentro = mascara_fn(dx + cx, dy + cy)
        cob = cobertura(d, 1.5) * dentro * suave(-0.6, 0.6, grao[idx])
        t.pintar(cob * 0.8, cor, idx)

    amarelo, laranja = (0.98, 0.82, 0.18), (0.98, 0.55, 0.15)
    azul, marrom = (0.20, 0.42, 0.90), (0.55, 0.33, 0.16)
    verde, rosa = (0.25, 0.70, 0.30), (0.95, 0.45, 0.70)

    # Sol
    sx, sy, sr = 115, 110, 42
    circ = [(sx + sr * np.cos(a), sy + sr * np.sin(a)) for a in np.linspace(0, DOIS_PI * 1.05, 40)]
    rabisco_dentro(lambda x, y: cobertura(sdf_circulo(x - sx, y - sy, sr - 2), 2.0),
                   sx - sr, sy - sr, sx + sr, sy + sr, 9, 6, amarelo)
    traco(circ, 7, laranja)
    for a in np.linspace(0, DOIS_PI, 11)[:-1]:
        traco([(sx + 54 * np.cos(a), sy + 54 * np.sin(a)), (sx + 82 * np.cos(a), sy + 82 * np.sin(a))],
              6, laranja)

    # Casinha
    traco([(250, 270), (410, 270), (410, 410), (250, 410), (250, 268)], 7, azul)
    traco([(238, 275), (330, 185), (422, 275), (238, 275)], 7, laranja)
    rabisco_dentro(lambda x, y: cobertura(sdf_poligono(x, y, [(248, 270), (330, 192), (412, 270)]), 2.0),
                   240, 190, 420, 272, 10, 6, laranja)
    traco([(305, 410), (305, 345), (345, 345), (345, 410)], 6, marrom)
    traco([(365, 295), (395, 295), (395, 325), (365, 325), (365, 294)], 5, amarelo)
    traco([(380, 295), (380, 325)], 4, amarelo)
    traco([(365, 310), (395, 310)], 4, amarelo)

    # Coração
    tt = np.linspace(0, DOIS_PI, 60)
    hx = 120 + 3.0 * 16 * np.sin(tt) ** 3
    hy = 330 - 3.0 * (13 * np.cos(tt) - 5 * np.cos(2 * tt) - 2 * np.cos(3 * tt) - np.cos(4 * tt))
    coracao = list(zip(hx, hy))
    rabisco_dentro(lambda x, y: cobertura(sdf_poligono(x, y, coracao) + 2, 2.0),
                   70, 285, 170, 385, 8, 6, rosa)
    traco(coracao, 7, rosa, densidade=-0.2)

    # Grama
    gx = np.linspace(40, 470, 30)
    gy = 445 + np.where(np.arange(30) % 2 == 0, 0, -16)
    traco(list(zip(gx, gy)), 6, verde)
    t.salvar(pasta / "decal_giz_cera.png")


def decal_marca_mao(pasta):
    rng = gerador(608)
    t = Tela()
    X, Y = t.X, t.Y
    # Palma + 5 dedinhos (cápsulas), mão pequena de criança
    palma = sdf_elipse(X - 258, Y - 318, 64, 72)
    dedos = [((198, 312), (140, 240), 17), ((226, 255), (206, 150), 15), ((256, 250), (254, 128), 15.5),
             ((286, 255), (300, 142), 14.5), ((312, 272), (346, 190), 12.5)]
    d = palma
    pontas = np.zeros((512, 512), np.float32)
    for (ax, ay), (bx, by), r in dedos:
        dd = sdf_segmento(X, Y, ax, ay, bx, by) - r
        # união suave (dedo "emenda" na palma sem quina)
        k = 10.0
        h = np.clip(0.5 + 0.5 * (dd - d) / k, 0, 1)
        d = dd * (1 - h) + d * h - k * h * (1 - h)
        pontas = np.maximum(pontas, np.exp(-((X - bx) ** 2 + (Y - by) ** 2) / (2 * (r * 0.9) ** 2)))
    forma = cobertura(d, 3.0)
    # Pressão: pontas dos dedos e base da palma marcam mais; o meio da palma marca menos
    meio = np.exp(-((X - 262) ** 2 + (Y - 305) ** 2) / (2 * 30.0 ** 2))
    pressao = 0.55 + 0.35 * pontas - 0.35 * meio + 0.12 * suave(-60, 60, Y - 318)
    # Linhas finas da pele e falhas da sujeira
    linhas = 0.85 + 0.15 * np.sin(DOIS_PI * (X * 0.3 + Y) / 7.0)
    falhas = suave(-1.4, 0.3, ruido(512, 3, rng)) * (0.8 + 0.2 * ruido(512, 1, rng))
    alfa = forma * np.clip(pressao, 0, 1) * linhas * falhas * 0.75
    t.pintar(alfa, (0.29, 0.28, 0.27))
    t.salvar(pasta / "decal_marca_mao.png")


# ---------------------------------------------------------------------------
# 7. Cookie da lanterna
# ---------------------------------------------------------------------------

def lanterna_cookie():
    n = 512
    rng = gerador(707)
    X, Y = coordenadas(n)
    r = np.sqrt((X - 256) ** 2 + (Y - 256) ** 2) / 236.0  # r = 1 na borda do facho

    luz = 0.74 + 0.10 * suave(0.0, 0.7, r)                 # miolo levemente mais escuro
    luz = luz + 0.12 * np.exp(-((r - 0.84) / 0.05) ** 2)     # anel mais claro perto da borda
    # Pequenas manchas (sujeira na lente)
    for _ in range(6):
        cx, cy = 256 + rng.uniform(-150, 150, 2)
        s = rng.uniform(6, 18)
        luz = luz - rng.uniform(0.04, 0.09) * np.exp(-((X - cx) ** 2 + (Y - cy) ** 2) / (2 * s * s))
    # Um risco suave na lente
    d = sdf_segmento(X, Y, 150, 330, 360, 210)
    luz = luz - 0.05 * np.exp(-(d / 5.0) ** 2)
    luz = luz * (1.0 + 0.02 * ruido(n, 3, rng))
    # Borda caindo para preto com suavidade; fora do facho é preto absoluto
    luz = luz * (1.0 - suave(0.86, 1.0, r))
    luz = np.where(r >= 1.0, 0.0, luz)
    salvar(luz, PASTA / "lanterna" / "lanterna_cookie.png")


# ---------------------------------------------------------------------------
# 7. Texturas dos objetos pequenos (AJUSTES V2.2 §3.5): papel, papelão, cortiça e tecido.
#    Saem quase neutras (claras e acinzentadas): quem dá a cor é a "tinta" de cada material
#    em blender/scripts/materiais_v2.py, que multiplica a textura.
# ---------------------------------------------------------------------------

def papel():
    """Papel comum (pratos, copos, cartazes, tickets, post-its): fibras finas e manchinhas."""
    n = 512
    rng = gerador(701)
    fibras = 0.6 * ruido(n, 1.2, rng, 9.0) + 0.4 * ruido(n, 9.0, rng, 1.2)   # fibras em pé e deitadas
    manchas = ruido(n, 60, rng)
    claro = 0.93 + 0.025 * fibras + 0.03 * manchas
    cor = np.stack([claro, claro * 0.99, claro * 0.965], axis=-1)
    pontos = furos_espalhados(n, 260, 0.7, rng)                              # sujeirinha
    cor = misturar(cor, cor * 0.7, pontos * 0.6)
    normal = normal_de_altura(0.5 * fibras + 0.3 * manchas, 0.35)
    aspereza = 0.88 + 0.04 * fibras
    salvar_material("papel", cor, normal, aspereza)


def papelao():
    """Papelão (caixas de pizza, castelo e foguete de papelão): ondas do miolo e manchas."""
    n = 512
    rng = gerador(702)
    X, Y = coordenadas(n)
    ondas = 0.5 + 0.5 * np.cos(DOIS_PI * X / 16.0)                          # 32 ondas na largura (repete)
    ondas = np.broadcast_to(ondas, (n, n)).astype(np.float32)
    manchas = fbm(n, 90, rng)
    claro = 0.86 + 0.035 * ondas + 0.04 * manchas + 0.015 * ruido(n, 1.5, rng)
    cor = np.stack([claro, claro * 0.97, claro * 0.92], axis=-1)
    normal = normal_de_altura(0.8 * ondas + 0.2 * manchas, 0.6)
    aspereza = 0.9 + 0.03 * manchas
    salvar_material("papelao", cor, normal, aspereza)


def cortica():
    """Cortiça (quadros de aviso): grãos pequenos de tons diferentes e furinhos de tachinha."""
    n = 512
    rng = gerador(703)
    graos = ruido(n, 2.2, rng)
    graos_grandes = ruido(n, 6.0, rng)
    claro = 0.8 + 0.09 * np.tanh(1.6 * graos) + 0.05 * graos_grandes
    cor = np.stack([claro, claro * 0.93, claro * 0.84], axis=-1)
    poros = furos_espalhados(n, 900, 1.0, rng)
    cor = misturar(cor, cor * 0.45, poros)
    normal = normal_de_altura(0.6 * graos - 1.2 * poros, 0.9)
    aspereza = 0.93 + 0.03 * graos
    salvar_material("cortica", cor, normal, aspereza)


def tecido():
    """Tecido de trama simples (toalhas, tule, bandeira, lenço, corda): fios que passam por cima e por baixo."""
    n = 512
    rng = gerador(704)
    X, Y = coordenadas(n)
    passo = 8.0
    cx = np.floor(X / passo)
    cy = np.floor(Y / passo)
    fx = (X % passo) / passo                                                 # posição dentro da célula (0..1)
    fy = (Y % passo) / passo
    por_cima = ((cx + cy) % 2 == 0)                                          # xadrez: trama x urdidura
    fio_h = np.sin(np.pi * np.broadcast_to(fy, (n, n)))                      # "gomo" do fio deitado
    fio_v = np.sin(np.pi * np.broadcast_to(fx, (n, n)))                      # "gomo" do fio em pé
    altura = np.where(por_cima, fio_h, fio_v).astype(np.float32)
    felpa = ruido(n, 1.0, rng)
    claro = 0.8 + 0.14 * altura + 0.03 * felpa + 0.03 * ruido(n, 70, rng)
    cor = np.stack([claro, claro, claro * 0.98], axis=-1)
    normal = normal_de_altura(altura + 0.15 * felpa, 0.8)
    aspereza = 0.92 - 0.04 * altura
    salvar_material("tecido", cor, normal, aspereza)


# ---------------------------------------------------------------------------

def main():
    # "-- papel tecido" depois do nome do script gera só essas (as outras ficam como estão).
    import sys
    so = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if so:
        print("Gerando só:", ", ".join(so))
        for nome in so:
            globals()[nome]()
        print("Pronto.")
        return
    print("Gerando texturas em", PASTA)
    carpete_fliperama()
    quadriculado_gasto()
    papel_parede_festa()
    forro_manchado()
    sujeira_cantos()
    pasta_decals = PASTA / "decals"
    decal_mancha_agua(pasta_decals)
    decal_gordura(pasta_decals)
    decal_pegadas(pasta_decals)
    decal_confete(pasta_decals)
    decal_refrigerante(pasta_decals)
    decal_rachadura(pasta_decals)
    decal_giz_cera(pasta_decals)
    decal_marca_mao(pasta_decals)
    lanterna_cookie()
    papel()
    papelao()
    cortica()
    tecido()
    print("Pronto.")


main()


# O Godot não lê JPEGs com os metadados EXIF/ICC que o Blender grava: tiramos esses blocos
# (sem recomprimir). Ver ferramentas/limpar_jpeg.py.
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
import limpar_jpeg  # noqa: E402
print("limpar_jpeg:", limpar_jpeg.limpar_tudo([_Path(__file__).resolve().parents[1] / "godot" / "assets" / "texturas"]), "arquivo(s) limpo(s)")
