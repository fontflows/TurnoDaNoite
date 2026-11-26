"""
gerar_predio.py — gera a "casca" da pizzaria: pisos, paredes (com vãos de porta),
tetos, batentes e o palco. Salva blender/predio.blend e exporta
godot/assets/cenario/predio.glb.

A planta e as medidas estão em docs/CONTRATOS.md (seção 3).
Rodar sozinho:  blender --background --python blender/scripts/gerar_predio.py
"""

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import comum  # noqa: E402

# ---------------------------------------------------------------------------
# Medidas gerais (metros)
# ---------------------------------------------------------------------------
PE_DIREITO = 3.2       # altura do piso ao teto
ESPESSURA = 0.2        # espessura das paredes
ALTURA_FAIXA = 1.1     # a faixa colorida vai do chão até aqui
LARGURA_PORTA = 1.4
ALTURA_PORTA = 2.2
TAMANHO_LADRILHO = 0.5  # lado de cada quadrado do piso quadriculado

# ---------------------------------------------------------------------------
# Cômodos: nome (também é o nome da Collection), retângulo na planta
# (x0, x1, z0, z1), tipo de piso, material da faixa e material da parede.
# Para mudar a cor da faixa de um cômodo, troque o material aqui.
# ---------------------------------------------------------------------------
COMODOS = [
    ("Cozinha", (0, 10, 0, 13), "xadrez", "Mat_Faixa_Azulejo_Branco", "Mat_Parede_Creme"),
    ("Salao", (10, 30, 0, 13), "Mat_Carpete_Fliperama", "Mat_Faixa_Vermelha", "Mat_Papel_Parede_Festa"),
    ("Deposito", (30, 40, 0, 13), "Mat_Piso_Concreto", "Mat_Faixa_Cinza", "Mat_Parede_Concreto"),
    ("Corredor_Principal", (0, 40, 13, 16), "xadrez", "Mat_Faixa_Azul_Petroleo", "Mat_Parede_Creme"),
    ("Fliperama", (0, 14, 16, 27), "Mat_Carpete_Fliperama", "Mat_Faixa_Roxa", "Mat_Parede_Creme"),
    ("Banheiros", (14, 22, 16, 27), "Mat_Piso_Azulejo_Azul", "Mat_Faixa_Azul_Claro", "Mat_Faixa_Azulejo_Branco"),
    ("Sala_Seguranca", (22, 30, 16, 27), "xadrez", "Mat_Faixa_Verde_Oliva", "Mat_Parede_Creme"),
    ("Recepcao", (30, 40, 16, 30), "xadrez", "Mat_Faixa_Amarela", "Mat_Parede_Creme"),
    ("Corredor_Fundos", (0, 30, 27, 30), "Mat_Piso_Concreto", "Mat_Faixa_Cinza", "Mat_Parede_Concreto"),
]

# ---------------------------------------------------------------------------
# Paredes: (nome, eixo, coordenada fixa, início, fim, [centros das portas])
#   eixo "z": parede horizontal na planta (z fixo, vai de x=início a x=fim)
#   eixo "x": parede vertical na planta (x fixo, vai de z=início a z=fim)
# ---------------------------------------------------------------------------
PAREDES = [
    ("Parede_Externa_Norte", "z", 0, 0, 40, []),
    ("Parede_Externa_Sul", "z", 30, 0, 40, []),
    ("Parede_Externa_Oeste", "x", 0, 0, 30, []),
    ("Parede_Externa_Leste", "x", 40, 0, 30, []),
    ("Parede_Corredor_Principal_Norte", "z", 13, 0, 40, [5, 15, 25, 35]),
    ("Parede_Corredor_Principal_Sul", "z", 16, 0, 40, [7, 18, 26, 35]),
    ("Parede_Corredor_Fundos_Norte", "z", 27, 0, 30, [7, 26]),
    ("Parede_Cozinha_Salao", "x", 10, 0, 13, [6.5]),
    ("Parede_Salao_Deposito", "x", 30, 0, 13, [6.5]),
    ("Parede_Sala_Seguranca_Recepcao", "x", 30, 16, 30, [28.5]),
    ("Parede_Fliperama_Banheiros", "x", 14, 16, 27, []),
    ("Parede_Banheiros_Sala_Seguranca", "x", 22, 16, 27, []),
]

# Palco (dentro do salão)
PALCO = (14, 26, 0, 4)      # x0, x1, z0, z1
ALTURA_PALCO = 0.5
ESCADA = (19, 21, 4, 5.5)   # x0, x1, z0, z1 (na frente do palco)


def comodo_em(x, z):
    """Diz em qual cômodo fica o ponto (x, z) da planta, ou None se for fora do prédio."""
    for nome, (x0, x1, z0, z1), *_ in COMODOS:
        if x0 - 1e-6 <= x <= x1 + 1e-6 and z0 - 1e-6 <= z <= z1 + 1e-6:
            return nome
    return None


def info_comodo(nome):
    return next(c for c in COMODOS if c[0] == nome)


def blender_para_planta(v):
    """Inverso de comum.p(): coordenadas do Blender -> (x, z) da planta."""
    return v.x + 20.0, 15.0 - v.y


# ---------------------------------------------------------------------------
# Construção de malhas com vários materiais
# ---------------------------------------------------------------------------

class MalhaMultiMaterial:
    """
    Junta várias caixas numa malha só e escolhe o material de cada face.
    Por que: assim cada parede é UM objeto, mas cada lado dela pode ter a cor
    do cômodo para o qual está virado.
    """

    def __init__(self):
        self.bm = bmesh.new()
        self.materiais = []  # nomes, na ordem dos slots

    def indice(self, nome_mat):
        if nome_mat not in self.materiais:
            self.materiais.append(nome_mat)
        return self.materiais.index(nome_mat)

    def caixa(self, xmin, xmax, ymin, ymax, zmin, zmax, escolher_material):
        """Caixa alinhada aos eixos do Blender; escolher_material(centro, normal) -> nome."""
        bm = self.bm
        vs = [bm.verts.new((x, y, z)) for z in (zmin, zmax) for y in (ymin, ymax) for x in (xmin, xmax)]
        # índices: z0: 0(x0y0) 1(x1y0) 2(x0y1) 3(x1y1); z1: +4
        faces = [
            (0, 2, 3, 1),  # baixo
            (4, 5, 7, 6),  # cima
            (0, 1, 5, 4),  # -Y
            (2, 6, 7, 3),  # +Y
            (0, 4, 6, 2),  # -X
            (1, 3, 7, 5),  # +X
        ]
        for ids in faces:
            f = bm.faces.new([vs[i] for i in ids])
            f.normal_update()
            f.material_index = self.indice(escolher_material(f.calc_center_median(), f.normal))

    def plano(self, xmin, xmax, ymin, ymax, z, nome_mat, para_baixo=False):
        bm = self.bm
        cantos = [(xmin, ymin), (xmax, ymin), (xmax, ymax), (xmin, ymax)]
        if para_baixo:
            cantos.reverse()
        f = bm.faces.new([bm.verts.new((x, y, z)) for x, y in cantos])
        f.material_index = self.indice(nome_mat)

    def criar_objeto(self, nome, col, origem=(0, 0, 0)):
        """Cria o objeto. 'origem' é onde fica o ponto de origem (as malhas são deslocadas)."""
        origem = Vector(origem)
        for v in self.bm.verts:
            v.co -= origem
        malha = bpy.data.meshes.new(nome)
        self.bm.to_mesh(malha)
        self.bm.free()
        for nome_mat in self.materiais:
            malha.materials.append(comum.material(nome_mat))
        obj = bpy.data.objects.new(nome, malha)
        col.objects.link(obj)
        obj.location = origem
        return obj


def material_da_face_de_parede(centro, normal):
    """
    Escolhe a cor de uma face de parede olhando para qual cômodo ela está virada.
    Faces de baixo (até ALTURA_FAIXA) recebem a faixa; as de cima, a cor da parede.
    """
    if abs(normal.z) > 0.5:
        # Topo e fundo da parede quase nunca aparecem; usamos a cor da parede.
        x, z = blender_para_planta(centro)
        nome = comodo_em(x, z)
        return info_comodo(nome)[4] if nome else "Mat_Parede_Externa"
    ponto = centro + normal * 0.15
    x, z = blender_para_planta(ponto)
    nome = comodo_em(x, z)
    if nome is None:
        return "Mat_Parede_Externa"
    _, _, _, faixa, parede = info_comodo(nome)
    return faixa if centro.z < ALTURA_FAIXA - 1e-4 else parede


def trechos_da_parede(eixo, inicio, fim, portas):
    """
    Divide a linha da parede em trechos cheios e vãos de porta.
    Os trechos cheios também são cortados nos limites dos cômodos, para que
    cada pedaço pegue a cor do cômodo certo (uma parede longa passa por vários).
    """
    cheios, vaos = [], []
    cursor = inicio
    for c in sorted(portas):
        a, b = c - LARGURA_PORTA / 2, c + LARGURA_PORTA / 2
        cheios.append((cursor, a))
        vaos.append((a, b))
        cursor = b
    cheios.append((cursor, fim))

    # Limites dos cômodos ao longo da parede (x para paredes "z", z para paredes "x").
    limites = sorted({r[0] for _, r, *_ in COMODOS} | {r[1] for _, r, *_ in COMODOS}) if eixo == "z" \
        else sorted({r[2] for _, r, *_ in COMODOS} | {r[3] for _, r, *_ in COMODOS})
    cortados = []
    for a, b in cheios:
        pontos = [a] + [t for t in limites if a + 1e-6 < t < b - 1e-6] + [b]
        cortados += list(zip(pontos[:-1], pontos[1:]))
    return cortados, vaos


def caixa_de_parede_blender(eixo, fixo, a, b):
    """Converte um trecho de parede da planta em limites (xmin, xmax, ymin, ymax) do Blender."""
    meia = ESPESSURA / 2
    if eixo == "z":   # z fixo, varia x
        p0, p1 = comum.p(a, fixo), comum.p(b, fixo)
        return min(p0.x, p1.x), max(p0.x, p1.x), p0.y - meia, p0.y + meia
    p0, p1 = comum.p(fixo, a), comum.p(fixo, b)   # x fixo, varia z
    return p0.x - meia, p0.x + meia, min(p0.y, p1.y), max(p0.y, p1.y)


# ---------------------------------------------------------------------------
# Partes do prédio
# ---------------------------------------------------------------------------

def gerar_pisos_e_tetos():
    for nome, (x0, x1, z0, z1), piso, *_ in COMODOS:
        col = comum.colecao(nome)
        a, b = comum.p(x0, z1), comum.p(x1, z0)  # canto sudoeste e nordeste no Blender
        centro = comum.p((x0 + x1) / 2, (z0 + z1) / 2)

        m = MalhaMultiMaterial()
        # V2: um piso só por cômodo; o desenho (quadriculado, carpete...) vem da textura,
        # com UV em escala real (comum.aplicar_uv_mundo).
        material_piso = "Mat_Piso_Quadriculado" if piso == "xadrez" else piso
        m.plano(a.x, b.x, a.y, b.y, 0.0, material_piso)
        m.criar_objeto(f"Piso_{nome}", col, origem=centro)

        # Teto virado para baixo (o Godot só desenha o lado da frente da face).
        t = MalhaMultiMaterial()
        t.plano(a.x, b.x, a.y, b.y, PE_DIREITO, "Mat_Teto_Escuro", para_baixo=True)
        t.criar_objeto(f"Teto_{nome}", col, origem=(centro.x, centro.y, PE_DIREITO))


def gerar_paredes():
    col_paredes = comum.colecao("Paredes")
    col_portas = comum.colecao("Portas")
    caixas_colisao = []
    meia = ESPESSURA / 2

    for nome, eixo, fixo, inicio, fim, portas in PAREDES:
        m = MalhaMultiMaterial()
        cheios, vaos = trechos_da_parede(eixo, inicio, fim, portas)
        for k, (a, b) in enumerate(cheios):
            # Estica as pontas meia espessura para fechar bem os cantos.
            a2 = a - meia if k == 0 else a
            b2 = b + meia if k == len(cheios) - 1 else b
            xmin, xmax, ymin, ymax = caixa_de_parede_blender(eixo, fixo, a2, b2)
            m.caixa(xmin, xmax, ymin, ymax, 0.0, ALTURA_FAIXA, material_da_face_de_parede)
            m.caixa(xmin, xmax, ymin, ymax, ALTURA_FAIXA, PE_DIREITO, material_da_face_de_parede)
            caixas_colisao.append((xmin, xmax, ymin, ymax, 0.0, PE_DIREITO))
        for a, b in vaos:
            # Verga: o pedaço de parede em cima da porta.
            xmin, xmax, ymin, ymax = caixa_de_parede_blender(eixo, fixo, a, b)
            m.caixa(xmin, xmax, ymin, ymax, ALTURA_PORTA, PE_DIREITO, material_da_face_de_parede)
            caixas_colisao.append((xmin, xmax, ymin, ymax, ALTURA_PORTA, PE_DIREITO))
            gerar_batente(eixo, fixo, (a + b) / 2, col_portas)

        meio = (inicio + fim) / 2
        origem = comum.p(meio, fixo) if eixo == "z" else comum.p(fixo, meio)
        m.criar_objeto(nome, col_paredes, origem=origem)

    # Colisão de todas as paredes num objeto só (o Godot cria um corpo estático invisível).
    col_colisao = comum.colecao("Colisao")
    mc = MalhaMultiMaterial()
    for c in caixas_colisao:
        mc.caixa(*c, lambda *_: "Mat_Parede_Creme")
    obj = mc.criar_objeto("Colisao_Paredes-colonly", col_colisao)
    obj.data.materials.clear()
    obj.display_type = "WIRE"
    obj.hide_render = True


def gerar_batente(eixo, fixo, centro, col):
    """Moldura de madeira em volta do vão da porta (só visual)."""
    if eixo == "z":
        lados = (comodo_em(centro, fixo - 0.5), comodo_em(centro, fixo + 0.5))
    else:
        lados = (comodo_em(fixo - 0.5, centro), comodo_em(fixo + 0.5, centro))
    nome = "Batente_" + "_".join(sorted(n for n in lados if n))
    if bpy.data.objects.get(nome):
        nome += "_2"

    m = MalhaMultiMaterial()
    prof = ESPESSURA / 2 + 0.03   # um pouco mais grosso que a parede
    larg = 0.08
    mat = lambda *_: "Mat_Batente_Madeira"  # noqa: E731
    a, b = centro - LARGURA_PORTA / 2, centro + LARGURA_PORTA / 2
    for (s0, s1, h0, h1) in ((a - larg, a, 0, ALTURA_PORTA), (b, b + larg, 0, ALTURA_PORTA),
                             (a - larg, b + larg, ALTURA_PORTA, ALTURA_PORTA + larg)):
        if eixo == "z":
            p0, p1 = comum.p(s0, fixo), comum.p(s1, fixo)
            m.caixa(min(p0.x, p1.x), max(p0.x, p1.x), p0.y - prof, p0.y + prof, h0, h1, mat)
        else:
            p0, p1 = comum.p(fixo, s0), comum.p(fixo, s1)
            m.caixa(p0.x - prof, p0.x + prof, min(p0.y, p1.y), max(p0.y, p1.y), h0, h1, mat)
    origem = comum.p(centro, fixo) if eixo == "z" else comum.p(fixo, centro)
    m.criar_objeto(nome, col, origem=origem)


def gerar_palco():
    col = comum.colecao("Salao")
    col_colisao = comum.colecao("Colisao")
    x0, x1, z0, z1 = PALCO
    largura, prof = x1 - x0, z1 - z0
    base = comum.p((x0 + x1) / 2, (z0 + z1) / 2)
    comum.caixa("Palco_Piso", (largura, prof, ALTURA_PALCO), base, "Mat_Palco_Madeira", col)
    comum.colisao_caixa("Palco_Piso", (largura, prof, ALTURA_PALCO), base, col_colisao)

    # Escada com 3 degraus (visual) + rampa invisível (para andar e para a navegação).
    ex0, ex1, ez0, ez1 = ESCADA
    m = MalhaMultiMaterial()
    degraus = 3
    passo = (ez1 - ez0) / degraus
    # Degrau k (1 = o mais baixo): vai da frente do palco até ez1 - (k-1)*passo.
    for k in range(1, degraus + 1):
        altura = ALTURA_PALCO * k / degraus
        a, b = comum.p(ex0, ez1 - (k - 1) * passo), comum.p(ex1, ez0)
        m.caixa(a.x, b.x, a.y, b.y, 0.0, altura, lambda *_: "Mat_Palco_Madeira")
    m.criar_objeto("Palco_Escada", col, origem=comum.p((ex0 + ex1) / 2, (ez0 + ez1) / 2))

    # Rampa: cunha que sobe de z=5,5 (chão) até z=4 (altura do palco).
    pa, pb = comum.p(ex0, ez1), comum.p(ex1, ez0)
    xa, xb = pa.x, pb.x
    y_baixo, y_alto = pa.y, pb.y   # y_baixo fica ao sul (z maior)
    verts = [
        (xa, y_baixo, 0), (xb, y_baixo, 0), (xb, y_alto, 0), (xa, y_alto, 0),
        (xa, y_alto, ALTURA_PALCO), (xb, y_alto, ALTURA_PALCO),
    ]
    faces = [(0, 3, 2, 1), (0, 1, 5, 4), (3, 4, 5, 2), (0, 4, 3), (1, 2, 5)]
    rampa = comum.malha_de_pontos("Palco_Rampa_Colisao-colonly", verts, faces, col=col_colisao)
    rampa.display_type = "WIRE"
    rampa.hide_render = True


def gerar_colisao_piso():
    col = comum.colecao("Colisao")
    comum.colisao_caixa("Piso", (40.6, 30.6, 0.3), comum.p(20, 15, -0.3), col)
    # colisao_caixa já acrescenta "_Colisao-colonly"; renomeamos para o nome do contrato.
    bpy.data.objects["Piso_Colisao-colonly"].name = "Colisao_Piso-colonly"


def contar_triangulos():
    total = 0
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and not obj.name.endswith("-colonly"):
            total += sum(len(p.vertices) - 2 for p in obj.data.polygons)
    return total


def gerar():
    comum.limpar_cena()
    gerar_pisos_e_tetos()
    gerar_paredes()
    gerar_palco()
    gerar_colisao_piso()
    print(f"[predio] objetos: {len(bpy.context.scene.objects)}  triângulos visíveis: {contar_triangulos()}")
    comum.salvar_blend(comum.PASTA_BLENDER / "predio.blend")
    comum.exportar_glb(comum.PASTA_CENARIO / "predio.glb")


if __name__ == "__main__":
    gerar()
