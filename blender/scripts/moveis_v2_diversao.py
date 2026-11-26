"""
moveis_v2_diversao.py — móveis e set dressing do grupo "diversão" da V2.4:
Fliperama, Cozinha, Câmara fria e Banheiros (mais o Disjuntor da Cozinha).

O que sai daqui:
  - blender/v2_diversao.blend
  - godot/assets/cenario/v2_diversao.glb

Rodar sozinho (a partir da pasta TurnoDaNoite):
  blender --background --python blender/scripts/moveis_v2_diversao.py

Ideia geral (igual à V1): cada móvel é montado "em casa" (na origem, de frente para -Y)
e depois levado para o lugar dele na planta com montar(). As peças são filhas da peça
principal, então mover a principal no Blender leva o móvel inteiro, inclusive a colisão.
Peças pequenas e repetidas (lixo, teias, pelúcias) são juntadas num objeto só com a
classe Lote, porque muitos objetos pesam mais no Godot do que muitos triângulos.
"""

import math
import pathlib
import random
import sys

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import comum  # noqa: E402
import planta_v2  # noqa: E402

V = Vector
P = planta_v2.PONTOS

# ---------------------------------------------------------------------------
# Cores lisas que só este grupo usa ("Nome": ("#RRGGBB", emissão))
# ---------------------------------------------------------------------------
CORES_DIVERSAO = {
    # plano_arte usa este material por padrão, e ele não está na paleta do comum
    "Mat_Papel_Branco": ("#e8e4d6", 0.0),
    "Mat_Papel_Amarelo": ("#e3cf6a", 0.0),
    "Mat_Texto_Preto": ("#141414", 0.0),
    "Mat_Texto_Branco": ("#f0ede4", 0.0),
    "Mat_Teia": ("#d8d8d0", 0.0),
    # Gabinetes do fliperama: uma cor de corpo e uma de detalhe por tema (PLANO_V2 §9)
    "Mat_Arcade_Tito_Kart": ("#c8302a", 0.0),
    "Mat_Arcade_Tito_Kart_Detalhe": ("#f0c33a", 0.0),
    "Mat_Arcade_Space_Pizza": ("#1d3a8a", 0.0),
    "Mat_Arcade_Space_Pizza_Detalhe": ("#ff8a2a", 0.0),
    "Mat_Arcade_Pipoca_Pula_Pula": ("#e07aa8", 0.0),
    "Mat_Arcade_Pipoca_Pula_Pula_Detalhe": ("#b08ae0", 0.0),
    "Mat_Arcade_Serpente_Neon": ("#141c16", 0.0),
    "Mat_Arcade_Serpente_Neon_Detalhe": ("#3aff6a", 0.6),
    "Mat_Arcade_Fantasminha": ("#4b2a7a", 0.0),
    "Mat_Arcade_Fantasminha_Detalhe": ("#f2efe6", 0.0),
    "Mat_Luz_Ficha": ("#ff8a1a", 1.5),          # luz da entrada de fichas
    "Mat_Vidro_Vitrine": ("#d6eef4", 0.0),       # vidro claro da garra e do balcão
    "Mat_Garra_Corpo": ("#d8402e", 0.0),
    "Mat_Garra_Detalhe": ("#f0c33a", 0.0),
    "Mat_Capsula_Chave": ("#f2c84a", 0.3),       # brilho fraco: a cápsula tem que ser achada
    "Mat_Feltro_Verde": ("#2f6a3a", 0.0),
    "Mat_Mesa_Hoquei": ("#e8e8f0", 0.0),
    "Mat_Pinball_Mesa": ("#3a2a8a", 0.0),
    "Mat_Pinball_Vidro": ("#c04a9a", 0.2),
    "Mat_Ticket": ("#e8873a", 0.0),
    "Mat_Bola_Madeira": ("#b8874a", 0.0),
    "Mat_Placar_Led": ("#5a1010", 0.3),
    # Cozinha
    "Mat_Tijolo_Forno": ("#8a3b26", 0.0),
    "Mat_Cinza_Forno": ("#3a3532", 0.0),
    "Mat_Lenha": ("#6b4a2e", 0.0),
    "Mat_Caixa_Pizza": ("#c9a46a", 0.0),
    "Mat_Luz_Geladeira": ("#fff4d6", 2.5),
    "Mat_Gordura": ("#5a4a2a", 0.0),
    "Mat_Fio_Vermelho": ("#c22a22", 0.0),
    "Mat_Fio_Azul": ("#2a52c2", 0.0),
    "Mat_Fio_Amarelo": ("#e0c02a", 0.0),
    "Mat_Cobre": ("#c07a40", 0.0),
    "Mat_Farinha": ("#ece6d6", 0.0),
    # Câmara fria
    "Mat_Luz_Fria": ("#9fd8ff", 3.0),
    "Mat_PVC_Tiras": ("#bfe0ec", 0.0),
    "Mat_Gelo": ("#e4f4fa", 0.0),
    "Mat_Engradado": ("#2f5f8f", 0.0),
    # Banheiros
    "Mat_Rachadura": ("#1a1a1a", 0.0),
    "Mat_Giz_Rosa": ("#f07ab0", 0.0),
    "Mat_Giz_Azul": ("#5aa0f0", 0.0),
    "Mat_Giz_Verde": ("#6ad06a", 0.0),
    "Mat_Papel_Toalha": ("#ddd8c8", 0.0),
    "Mat_Lampada_Fluorescente": ("#e8f4f0", 0.4),
}

COMODOS_GRUPO = ["Fliperama", "Cozinha", "Camara_Fria", "Banheiros"]
COLECAO_DISJUNTORES = "Disjuntores_Diversao"

# Para onde a FRENTE aponta: (giro em Z no Blender, direção (dx, dz) na planta)
FRENTES = {
    "sul": (comum.ROT_OLHA_SUL, (0.0, 1.0)),
    "leste": (comum.ROT_OLHA_LESTE, (1.0, 0.0)),
    "norte": (comum.ROT_OLHA_NORTE, (0.0, -1.0)),
    "oeste": (comum.ROT_OLHA_OESTE, (-1.0, 0.0)),
}

# Semente fixa: a "bagunça" muda de um lugar para outro, mas é igual a cada geração.
SORTE = random.Random(1998)

FONTES = {
    "Bungee": "Bungee/Bungee-Regular.ttf",
    "PressStart": "PressStart2P/PressStart2P-Regular.ttf",
    "VT323": "VT323/VT323-Regular.ttf",
    "Caveat": "Caveat/Caveat-Variable.ttf",
    "Gochi": "GochiHand/GochiHand-Regular.ttf",
    "Fredoka": "Fredoka/Fredoka-Variable.ttf",
    "Courier": "CourierPrime/CourierPrime-Bold.ttf",
}


# ---------------------------------------------------------------------------
# Ajudantes gerais
# ---------------------------------------------------------------------------

def M(nome):
    return comum.material(nome)


def deixar_transparente(nome, alfa):
    """Vidro e cortina de PVC: o glTF leva o alfa e o Godot usa transparência."""
    mat = M(nome)
    bsdf = next(n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    bsdf.inputs["Alpha"].default_value = alfa
    bsdf.inputs["Roughness"].default_value = 0.15
    cor = list(mat.diffuse_color)
    mat.diffuse_color = (cor[0], cor[1], cor[2], alfa)
    for atributo, valor in (("surface_render_method", "BLENDED"), ("blend_method", "BLEND")):
        try:
            setattr(mat, atributo, valor)
        except (AttributeError, TypeError):
            pass


def _rot(rot):
    return Euler([math.radians(a) for a in rot]).to_matrix().to_4x4()


class Lote:
    """
    Junta várias peças simples (caixas, cilindros, esferas, tubos) num objeto só.
    Cada peça pode ter um material; as coordenadas são as do objeto final.
    """

    def __init__(self):
        self.bm = bmesh.new()
        self.mats = []

    def _indice(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def _pintar(self, verts, mat):
        i = self._indice(mat)
        for f in {f for v in verts for f in v.link_faces}:
            f.material_index = i

    def caixa(self, tam, base, mat, rot=(0, 0, 0)):
        """Caixa com 'base' no centro da face de baixo (antes de girar)."""
        r = bmesh.ops.create_cube(self.bm, size=1.0)
        m = Matrix.Translation(V(base)) @ _rot(rot) @ Matrix.Translation((0, 0, tam[2] / 2)) \
            @ Matrix.Diagonal((tam[0], tam[1], tam[2], 1.0))
        bmesh.ops.transform(self.bm, matrix=m, verts=r["verts"])
        self._pintar(r["verts"], mat)

    def cilindro(self, raio, altura, base, mat, rot=(0, 0, 0), lados=8, raio_topo=None):
        """Cilindro (ou cone) com 'base' no centro da tampa de baixo (antes de girar)."""
        r = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=lados, radius1=raio,
                                  radius2=raio if raio_topo is None else raio_topo, depth=altura)
        m = Matrix.Translation(V(base)) @ _rot(rot) @ Matrix.Translation((0, 0, altura / 2))
        bmesh.ops.transform(self.bm, matrix=m, verts=r["verts"])
        self._pintar(r["verts"], mat)

    def esfera(self, raio, centro, mat, escala=(1, 1, 1), seg=8, aneis=6, rot=(0, 0, 0)):
        r = bmesh.ops.create_uvsphere(self.bm, u_segments=seg, v_segments=aneis, radius=raio)
        m = Matrix.Translation(V(centro)) @ _rot(rot) @ Matrix.Diagonal((*escala, 1.0))
        bmesh.ops.transform(self.bm, matrix=m, verts=r["verts"])
        for f in {f for v in r["verts"] for f in v.link_faces}:
            f.smooth = True
        self._pintar(r["verts"], mat)

    def tubo(self, pontos, raio, mat, lados=4, fechado=False):
        """Tubo fino passando pelos pontos (fios, neon, canos tortos)."""
        pts = [V(p) for p in pontos]
        n = len(pts)
        aneis = []
        for i, p in enumerate(pts):
            if fechado:
                a, b = pts[i - 1], pts[(i + 1) % n]
            else:
                a, b = pts[max(i - 1, 0)], pts[min(i + 1, n - 1)]
            t = (b - a).normalized()
            ref = V((0, 0, 1)) if abs(t.z) < 0.9 else V((1, 0, 0))
            u = t.cross(ref).normalized()
            w = t.cross(u).normalized()
            aneis.append([self.bm.verts.new(p + raio * (math.cos(2 * math.pi * k / lados) * u +
                                                        math.sin(2 * math.pi * k / lados) * w))
                          for k in range(lados)])
        novos = []
        for i in (range(n) if fechado else range(n - 1)):
            a1, a2 = aneis[i], aneis[(i + 1) % n]
            for k in range(lados):
                novos += [a1[k], a1[(k + 1) % lados], a2[(k + 1) % lados], a2[k]]
                self.bm.faces.new((a1[k], a1[(k + 1) % lados], a2[(k + 1) % lados], a2[k]))
        self._pintar(novos, mat)

    def poligono(self, pontos, mat, dois_lados=False):
        vs = [self.bm.verts.new(V(p)) for p in pontos]
        self.bm.faces.new(vs)
        if dois_lados:
            vs2 = [self.bm.verts.new(V(p)) for p in reversed(pontos)]
            self.bm.faces.new(vs2)
            vs += vs2
        self._pintar(vs, mat)

    def objeto(self, nome, col, origem=(0, 0, 0)):
        """Cria o objeto. 'origem' (coordenadas do Blender) vira a origem; a malha fica no mesmo lugar."""
        bmesh.ops.translate(self.bm, verts=self.bm.verts, vec=-V(origem))
        malha = bpy.data.meshes.new(nome)
        self.bm.to_mesh(malha)
        self.bm.free()
        obj = bpy.data.objects.new(nome, malha)
        col.objects.link(obj)
        for m in self.mats:
            obj.data.materials.append(M(m))
        obj.location = V(origem)
        return obj


def caixas(nome, itens, mat, col):
    """Várias caixas num objeto. itens = [((larg, prof, alt), (x, y, z_base)), ...]"""
    lote = Lote()
    for tam, base in itens:
        lote.caixa(tam, base, mat)
    return lote.objeto(nome, col)


def perfil_extrudado(nome, perfil, largura, mat, col):
    """Sólido a partir de um perfil lateral (y, z), esticado em X. Bom para gabinetes e coifas."""
    bm = bmesh.new()
    w = largura / 2
    esq = [bm.verts.new((-w, y, z)) for y, z in perfil]
    dir_ = [bm.verts.new((w, y, z)) for y, z in perfil]
    bm.faces.new(esq)
    bm.faces.new(list(reversed(dir_)))
    n = len(perfil)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((esq[i], esq[j], dir_[j], dir_[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    malha = bpy.data.meshes.new(nome)
    bm.to_mesh(malha)
    bm.free()
    obj = bpy.data.objects.new(nome, malha)
    col.objects.link(obj)
    obj.data.materials.append(M(mat))
    return obj


def plano_uv(nome, verts, mat, col):
    """Quadrilátero com UV de 0 a 1 (telas). verts: baixo-esq, baixo-dir, cima-dir, cima-esq (vistos de frente)."""
    obj = comum.malha_de_pontos(nome, verts, [(0, 1, 2, 3)], (0, 0, 0), mat, col)
    uv = obj.data.uv_layers.new(name="UVMap")
    cantos = [(0, 0), (1, 0), (1, 1), (0, 1)]
    for i, loop in enumerate(obj.data.loops):
        uv.data[i].uv = cantos[loop.vertex_index]
    obj["uv_propria"] = True
    return obj


def vazio(nome, col, tamanho=0.3):
    obj = bpy.data.objects.new(nome, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = tamanho
    col.objects.link(obj)
    return obj


def fonte(chave):
    return bpy.data.fonts.load(str(comum.RAIZ / "godot" / "assets" / "fontes" / FONTES[chave]), check_existing=True)


def texto(nome, corpo, tamanho, mat, col, centro=(0, 0, 0), largura_max=None, fonte_chave="Bungee", deitado=False):
    """Texto 3D com fonte OFL do projeto, já convertido em malha. Em pé, virado para -Y."""
    curva = bpy.data.curves.new(nome + "_Curva", type="FONT")
    curva.body = corpo
    curva.font = fonte(fonte_chave)
    curva.size = tamanho
    curva.align_x = "CENTER"
    curva.align_y = "CENTER"
    curva.resolution_u = 2  # poucas curvas = poucos triângulos
    temp = bpy.data.objects.new(nome + "_Temp", curva)
    bpy.context.scene.collection.objects.link(temp)
    dg = bpy.context.evaluated_depsgraph_get()
    malha = bpy.data.meshes.new_from_object(temp.evaluated_get(dg))
    bpy.data.objects.remove(temp)
    bpy.data.curves.remove(curva)
    malha.name = nome
    if largura_max is not None and malha.vertices:
        xs = [v.co.x for v in malha.vertices]
        largura = max(xs) - min(xs)
        if largura > largura_max:
            malha.transform(Matrix.Scale(largura_max / largura, 4))
    if not deitado:
        malha.transform(Matrix.Rotation(math.radians(90), 4, "X"))
    malha.materials.clear()
    malha.materials.append(M(mat))
    obj = bpy.data.objects.new(nome, malha)
    col.objects.link(obj)
    obj.location = V(centro)
    # O que está escrito e a fonte vão para o .glb ("extras"): o Godot confere os textos 3D com isso.
    obj["texto_3d"] = corpo
    obj["texto_fonte"] = pathlib.Path(FONTES[fonte_chave]).name
    return obj


def montar(principal, filhos, x, z, h=0.0, frente="sul", giro=0.0):
    """Prende as peças na principal e leva o conjunto para (x, z) da planta V2, olhando para 'frente'."""
    for f in filhos:
        f.parent = principal
    principal.location = comum.p2(x, z, h)
    principal.rotation_euler = (0.0, 0.0, math.radians(FRENTES[frente][0] + giro))
    return principal


def colisao(nome_base, tamanho, base_local, col):
    """Caixa de colisão filha do móvel. base_local = centro da face de baixo, nas coordenadas do móvel."""
    return comum.colisao_caixa(nome_base, tamanho, V(base_local), col)


def marcador(nome, col, x, z, h, escala=(1, 1, 1), rot=(0, 0, 0)):
    """Empty que o Godot troca por luz, som, decal ou esconderijo."""
    obj = vazio(nome, col, 0.25)
    obj.location = comum.p2(x, z, h)
    obj.rotation_euler = [math.radians(a) for a in rot]
    obj.scale = escala
    return obj


# Rotação em Z para um decal de parede (depois de girar 90° em X ele projeta para +Y)
GIRO_PAREDE = {"norte": 0.0, "sul": 180.0, "leste": -90.0, "oeste": 90.0}
CONTADOR = {}


def numero(prefixo):
    CONTADOR[prefixo] = CONTADOR.get(prefixo, 0) + 1
    return CONTADOR[prefixo]


def decal(tipo, col, x, z, largura, comprimento, parede=None, h=None, giro=0.0):
    """
    Decal no chão (parede=None: largura em x, comprimento em z) ou numa parede
    ('norte', 'sul', 'leste', 'oeste': a parede para onde ele projeta; largura na parede, comprimento = altura).
    """
    nome = f"Decal__{tipo}_{numero('Decal__' + tipo):02d}"
    if parede is None:
        return marcador(nome, col, x, z, 0.05 if h is None else h, (largura, comprimento, 0.4), (0, 0, giro))
    return marcador(nome, col, x, z, h, (largura, comprimento, 0.4), (90, 0, GIRO_PAREDE[parede] + giro))


def teias(nome, col, cantos, altura):
    """Teias de aranha: triângulos nos cantos do teto. cantos = [(x, z, sx, sz)], s = sentido para dentro."""
    lote = Lote()
    for x, z, sx, sz in cantos:
        a = comum.p2(x + sx * SORTE.uniform(0.35, 0.55), z, altura - 0.02)
        b = comum.p2(x, z + sz * SORTE.uniform(0.35, 0.55), altura - 0.02)
        c = comum.p2(x, z, altura - SORTE.uniform(0.3, 0.45))
        lote.poligono([a, b, c], "Mat_Teia", dois_lados=True)
        # um fiapo solto ao lado, para não parecer recortado
        d = comum.p2(x + sx * 0.25, z + sz * 0.05, altura - 0.02)
        e = comum.p2(x + sx * 0.3, z + sz * 0.02, altura - 0.5)
        f = comum.p2(x + sx * 0.32, z + sz * 0.06, altura - 0.02)
        lote.poligono([d, e, f], "Mat_Teia", dois_lados=True)
    return lote.objeto(nome, col)


def forro_caido(nome, col, x, z, giro, altura_teto):
    """Placa do forro caída no chão (com um pedaço quebrado) e fios pendurados do buraco."""
    lote = Lote()
    lote.caixa((0.6, 0.6, 0.015), comum.p2(x, z, 0.0), "Mat_Teto_Escuro", rot=(4, 2, giro))
    lote.caixa((0.3, 0.22, 0.015), comum.p2(x + 0.55, z - 0.3, 0.0), "Mat_Teto_Escuro", rot=(0, -6, giro + 35))
    lote.caixa((0.08, 0.06, 0.015), comum.p2(x - 0.4, z + 0.35, 0.0), "Mat_Teto_Escuro", rot=(0, 0, giro + 70))
    fx, fz = x + 0.3, z - 0.6
    lote.tubo([comum.p2(fx, fz, altura_teto), comum.p2(fx + 0.05, fz, altura_teto - 0.4),
               comum.p2(fx + 0.02, fz + 0.06, altura_teto - 0.75), comum.p2(fx + 0.1, fz + 0.1, altura_teto - 0.95)],
              0.008, "Mat_Plastico_Preto")
    lote.tubo([comum.p2(fx - 0.1, fz, altura_teto), comum.p2(fx - 0.12, fz + 0.05, altura_teto - 0.5),
               comum.p2(fx - 0.05, fz + 0.02, altura_teto - 0.62)], 0.007, "Mat_Fio_Vermelho")
    return lote.objeto(nome, col, comum.p2(x, z, 0.0))


def estante(nome, col, largura, prof, altura, n_prat, mat, mat_itens="Mat_Papelao_Caixa", itens_por_prat=3,
            fundo=True, faltando=()):
    """Estante encostada na parede de trás (+Y local), aberta na frente (-Y). 'faltando' = itens que caíram."""
    lote = Lote()
    for sx in (-1, 1):
        lote.caixa((0.04, prof, altura), (sx * (largura / 2 - 0.02), 0, 0), mat)
    if fundo:
        lote.caixa((largura, 0.02, altura), (0, prof / 2 - 0.01, 0), mat)
    passo = (altura - 0.1) / n_prat
    for i in range(n_prat + 1):
        lote.caixa((largura, prof, 0.03), (0, 0, 0.08 + i * passo if i < n_prat else altura - 0.03), mat)
    frame = lote.objeto(nome, col)
    itens = Lote()
    k = 0
    for i in range(n_prat):
        z0 = 0.11 + i * passo
        for j in range(itens_por_prat):
            k += 1
            if k in faltando:
                continue
            larg = largura / itens_por_prat
            x = -largura / 2 + larg * (j + 0.5) + SORTE.uniform(-0.04, 0.04)
            alt = min(passo - 0.08, 0.2 + 0.08 * ((i + j) % 3))
            itens.caixa((larg * SORTE.uniform(0.6, 0.8), prof * 0.75, alt), (x, SORTE.uniform(-0.03, 0.03), z0),
                        mat_itens, rot=(0, 0, SORTE.uniform(-8, 8)))
    filhos = [itens.objeto(nome + "_Itens", col),
              colisao(nome, (largura, prof, altura), (0, 0, 0), col)]
    return frame, filhos


# ---------------------------------------------------------------------------
# FLIPERAMA
# ---------------------------------------------------------------------------

# Perfil lateral do gabinete (y, z): frente em -Y. Painel de controle saliente, tela
# inclinada e letreiro em cima. Fundo do gabinete em y = 0,40.
PERFIL_ARCADE = [(-0.30, 0.0), (0.40, 0.0), (0.40, 1.89), (-0.25, 1.89), (-0.25, 1.55), (-0.18, 1.52),
                 (-0.30, 1.02), (-0.48, 0.97), (-0.48, 0.88), (-0.30, 0.80)]
TELA_BAIXO = (-0.30, 1.02)
TELA_CIMA = (-0.18, 1.52)

MAQUINAS = [
    # (chave em PONTOS / arte, nome do objeto, bola do manche, botões)
    ("tito_kart", "Arcade_Tito_Kart", "Mat_Plastico_Azul", ("Mat_Plastico_Vermelho", "Mat_Plastico_Amarelo", "Mat_Plastico_Azul")),
    ("space_pizza", "Arcade_Space_Pizza", "Mat_Plastico_Laranja", ("Mat_Plastico_Laranja", "Mat_Plastico_Azul", "Mat_Plastico_Branco")),
    ("pipoca_pula_pula", "Arcade_Pipoca_Pula_Pula", "Mat_Plastico_Lilas", ("Mat_Plastico_Rosa", "Mat_Plastico_Lilas", "Mat_Plastico_Branco")),
    ("serpente_neon", "Arcade_Serpente_Neon", "Mat_Plastico_Verde", ("Mat_Plastico_Verde", "Mat_Plastico_Preto", "Mat_Plastico_Verde")),
    ("fantasminha", "Arcade_Fantasminha", "Mat_Plastico_Branco", ("Mat_Plastico_Lilas", "Mat_Plastico_Branco", "Mat_Plastico_Lilas")),
]


def pontos_tela(largura, altura, afastamento):
    """Cantos de um retângulo deitado na inclinação da tela (baixo-esq, baixo-dir, cima-dir, cima-esq)."""
    (y0, z0), (y1, z1) = TELA_BAIXO, TELA_CIMA
    comp = math.hypot(y1 - y0, z1 - z0)
    d = ((y1 - y0) / comp, (z1 - z0) / comp)
    n = (-d[1], d[0])  # normal para a frente e um pouco para cima
    my, mz = (y0 + y1) / 2, (z0 + z1) / 2

    def pt(s):
        return (my + d[0] * s + n[0] * afastamento, mz + d[1] * s + n[1] * afastamento)

    (ya, za), (yb, zb) = pt(-altura / 2), pt(altura / 2)
    w = largura / 2
    return [(-w, ya, za), (w, ya, za), (w, yb, zb), (-w, yb, zb)]


def gabinete_arcade(nome, col, mat_corpo, mat_detalhe, mat_bola, botoes, tela_nome=None, mat_tela="Mat_Tela_Arcade_Desligada"):
    """Gabinete de fliperama montado na origem (frente -Y). Devolve (corpo, filhos)."""
    corpo = perfil_extrudado(nome, PERFIL_ARCADE, 0.72, mat_corpo, col)
    filhos = []
    # Moldura preta da tela e a tela (objeto separado, plano 4:3 com UV 0-1)
    filhos.append(comum.malha_de_pontos(nome + "_Moldura_Tela", pontos_tela(0.62, 0.49, 0.003), [(0, 1, 2, 3)],
                                        (0, 0, 0), "Mat_Plastico_Preto", col))
    filhos.append(plano_uv(tela_nome or nome + "_Vidro", pontos_tela(0.48, 0.36, 0.007), mat_tela, col))
    # Painel de controle (tampa colorida), manche e botões
    det = Lote()
    det.caixa((0.73, 0.19, 0.012), (0, -0.39, 0.965), mat_detalhe, rot=(-15.5, 0, 0))
    det.caixa((0.73, 0.012, 0.09), (0, -0.486, 0.88), mat_detalhe)          # frente do painel
    det.caixa((0.73, 0.012, 0.08), (0, -0.306, 0.0), mat_detalhe)           # rodapé (chute)
    det.caixa((0.725, 0.02, 0.025), (0, -0.25, 1.545), mat_detalhe)          # filete sob o letreiro
    filhos.append(det.objeto(nome + "_Detalhes", col))
    ctrl = Lote()
    ctrl.cilindro(0.04, 0.012, (-0.17, -0.40, 0.985), "Mat_Plastico_Preto", lados=10)
    ctrl.cilindro(0.009, 0.08, (-0.17, -0.40, 0.99), "Mat_Metal_Cinza", lados=6)
    ctrl.esfera(0.026, (-0.17, -0.40, 1.085), mat_bola, seg=8, aneis=6)
    for i, mb in enumerate(botoes):
        ctrl.cilindro(0.022, 0.018, (0.02 + i * 0.075, -0.40 - 0.01 * (i % 2), 0.985), mb, lados=10)
    filhos.append(ctrl.objeto(nome + "_Controles", col))
    # Entrada de fichas: portinhola de metal com duas fendas iluminadas e a devolução
    fichas = Lote()
    fichas.caixa((0.26, 0.02, 0.32), (0, -0.31, 0.32), "Mat_Metal_Escuro")
    for sx in (-0.06, 0.06):
        fichas.caixa((0.035, 0.008, 0.06), (sx, -0.322, 0.55), "Mat_Luz_Ficha")
        fichas.caixa((0.05, 0.012, 0.035), (sx, -0.322, 0.4), "Mat_Plastico_Preto")
    filhos.append(fichas.objeto(nome + "_Fichas", col))
    filhos.append(colisao(nome, (0.72, 0.88, 1.89), (0, -0.04, 0), col))
    return corpo, filhos


def arcade_tematico(chave, nome, mat_bola, botoes, col, artes_laterais):
    corpo, filhos = gabinete_arcade(nome, col, f"Mat_{nome}", f"Mat_{nome}_Detalhe", mat_bola, botoes,
                                    tela_nome=nome + "_Tela")
    filhos.append(comum.plano_arte(f"marquee_{chave}.jpg", 0.7, 0.3, V((0, -0.256, 1.57)), col))
    # Arte lateral 9:16 nas duas laterais. A primeira de todas sai do plano_arte; as outras
    # são cópias renomeadas (.001, .002...), e o Godot reconhece pelo começo do nome.
    for lado, rz in ((-1, -90.0), (1, 90.0)):
        base = V((lado * 0.366, 0.1, 0.75))
        if not artes_laterais:
            arte = comum.plano_arte("lateral_arcade.jpg", 0.5, 0.889, base, col, rz)
        else:
            arte = artes_laterais[0].copy()
            arte.data = artes_laterais[0].data.copy()
            arte.name = f"Arte__lateral_arcade.{len(artes_laterais):03d}"
            arte.data.name = arte.name
            col.objects.link(arte)
            arte.parent = None
            arte.location = base
            arte.rotation_euler = (0, 0, math.radians(rz))
        artes_laterais.append(arte)
        filhos.append(arte)
    return corpo, filhos


def banquinho(lote, x, z, giro, tombado=False):
    """Banquinho redondo de fliperama (sem colisão: é pequeno e o jogador empurra no Godot)."""
    base = comum.p2(x, z, 0.0)
    if tombado:
        lote.cilindro(0.17, 0.05, base + V((0, 0, 0.17)), "Mat_Plastico_Vermelho", rot=(90, 0, giro), lados=10)
        lote.cilindro(0.025, 0.5, base + V((0, 0, 0.17)), "Mat_Metal_Escuro", rot=(-90, 0, giro), lados=6)
        return
    lote.cilindro(0.2, 0.02, base, "Mat_Metal_Escuro", lados=10)
    lote.cilindro(0.025, 0.5, base, "Mat_Metal_Escuro", lados=6)
    lote.cilindro(0.17, 0.06, base + V((0, 0, 0.5)), "Mat_Plastico_Vermelho", rot=(SORTE.uniform(-3, 3), 0, giro),
                  lados=10)


def maquinas_tematicas(col):
    artes = []
    for chave, nome, bola, botoes in MAQUINAS:
        x, z, frente = P["maquina_" + chave]
        corpo, filhos = arcade_tematico(chave, nome, bola, botoes, col, artes)
        if chave == "tito_kart":
            # Detalhe de história: bilhete colado na lateral sobre o recorde do "GER"
            filhos.append(caixas(nome + "_Bilhete", [((0.004, 0.18, 0.13), (-0.362, 0.05, 0.42))], "Mat_Papel_Amarelo", col))
            nota = texto(nome + "_Bilhete_Texto", "RECORDE: GER\nninguém bate!", 0.03, "Mat_Texto_Preto", col,
                         (-0.367, 0.05, 0.485), largura_max=0.16, fonte_chave="Caveat")
            nota.rotation_euler = (0, 0, math.radians(-90))
            filhos.append(nota)
        if chave == "serpente_neon":
            # A máquina com defeito: aviso colado na frente e um cabo solto saindo de trás
            filhos.append(caixas(nome + "_Aviso", [((0.24, 0.004, 0.1), (0, -0.312, 0.67))], "Mat_Papel_Branco", col))
            filhos.append(texto(nome + "_Aviso_Texto", "DEFEITO!\nNÃO LIGAR", 0.028, "Mat_Plastico_Vermelho", col,
                                (0, -0.317, 0.72), largura_max=0.2, fonte_chave="Caveat"))
            cabo = Lote()
            cabo.tubo([(0.2, 0.41, 0.3), (0.25, 0.5, 0.15), (0.32, 0.47, 0.02), (0.45, 0.55, 0.012), (0.55, 0.5, 0.012)],
                      0.01, "Mat_Plastico_Preto")
            filhos.append(cabo.objeto(nome + "_Cabo_Solto", col))
        montar(corpo, filhos, x, z, 0.0, frente)
    # Banquinhos na frente, fora do lugar
    lote = Lote()
    for i, (chave, *_resto) in enumerate(MAQUINAS):
        x, z, _ = P["maquina_" + chave]
        if i == 3:
            banquinho(lote, x + 0.5, z + 1.2, 30, tombado=True)
        else:
            banquinho(lote, x + SORTE.uniform(-0.25, 0.25), z + SORTE.uniform(0.95, 1.25), SORTE.uniform(0, 90))
    lote.objeto("Banquinhos_Fliperama", col, comum.p2(23.0, 20.8, 0.0))


def maquina_garra(col):
    x, z, frente = P["maquina_garra"]
    corpo = caixas("Maquina_Garra", [((1.0, 1.0, 0.85), (0, 0, 0)), ((1.0, 1.0, 0.3), (0, 0, 1.85))], "Mat_Garra_Corpo", col)
    filhos = []
    det = Lote()
    for sx in (-1, 1):
        for sy in (-1, 1):
            det.caixa((0.05, 0.05, 1.0), (sx * 0.475, sy * 0.475, 0.85), "Mat_Metal_Cinza")
    det.caixa((1.02, 1.02, 0.04), (0, 0, 0.83), "Mat_Garra_Detalhe")          # faixa amarela
    det.caixa((1.02, 1.02, 0.04), (0, 0, 2.15), "Mat_Garra_Detalhe")
    det.caixa((0.92, 0.92, 0.02), (0, 0, 0.85), "Mat_Plastico_Preto")         # fundo da vitrine
    # Painel de controle saliente na frente, com manche, botão e fichas com luz
    det.caixa((0.8, 0.14, 0.08), (0, -0.56, 0.78), "Mat_Garra_Detalhe")
    det.cilindro(0.01, 0.1, (-0.2, -0.56, 0.86), "Mat_Metal_Cinza", lados=6)
    det.esfera(0.03, (-0.2, -0.56, 0.97), "Mat_Plastico_Vermelho")
    det.cilindro(0.035, 0.02, (0.12, -0.56, 0.86), "Mat_Plastico_Verde", lados=10)
    det.caixa((0.04, 0.01, 0.07), (0.3, -0.506, 0.58), "Mat_Luz_Ficha")
    det.caixa((0.2, 0.02, 0.3), (0.3, -0.505, 0.3), "Mat_Metal_Escuro")
    # Boca de saída do prêmio
    det.caixa((0.3, 0.02, 0.25), (-0.22, -0.505, 0.2), "Mat_Plastico_Preto")
    det.caixa((0.3, 0.01, 0.12), (-0.22, -0.518, 0.33), "Mat_Vidro_Vitrine", rot=(-20, 0, 0))
    # Trilhos da garra
    for sy in (-0.43, 0.43):
        det.caixa((0.9, 0.03, 0.03), (0, sy, 1.79), "Mat_Metal_Escuro")
    det.caixa((0.04, 0.86, 0.03), (0.1, 0, 1.76), "Mat_Metal_Escuro")
    det.caixa((0.1, 0.1, 0.05), (0.1, 0.1, 1.76), "Mat_Metal_Cinza")
    # Lâmpadas apagadas em volta do painel de cima
    for i in range(7):
        det.esfera(0.025, (-0.33 + i * 0.11, -0.53, 2.17), "Mat_Lampada_Apagada", seg=6, aneis=4)
    filhos.append(det.objeto("Maquina_Garra_Detalhes", col))
    # Vidros da vitrine (finos, transparentes)
    vidro = Lote()
    vidro.caixa((0.9, 0.006, 1.0), (0, -0.475, 0.85), "Mat_Vidro_Vitrine")
    vidro.caixa((0.9, 0.006, 1.0), (0, 0.475, 0.85), "Mat_Vidro_Vitrine")
    vidro.caixa((0.006, 0.9, 1.0), (-0.475, 0, 0.85), "Mat_Vidro_Vitrine")
    vidro.caixa((0.006, 0.9, 1.0), (0.475, 0, 0.85), "Mat_Vidro_Vitrine")
    filhos.append(vidro.objeto("Maquina_Garra_Vidro", col))
    # Pilha de pelúcias simples do Tito (marrom, focinho bege) e da Pipoca (lilás, orelhas brancas)
    tito, focinho, pipoca, orelhas = Lote(), Lote(), Lote(), Lote()
    posicoes = []
    for camada, (n, raio_anel, zc) in enumerate(((9, 0.3, 0.95), (7, 0.25, 1.07), (4, 0.2, 1.17))):
        for i in range(n):
            a = 2 * math.pi * i / n + camada * 0.5 + SORTE.uniform(-0.15, 0.15)
            r = raio_anel + SORTE.uniform(-0.04, 0.04)
            posicoes.append((r * math.cos(a), r * math.sin(a), zc + SORTE.uniform(-0.02, 0.02)))
    for i, (px, py, pz) in enumerate(posicoes):
        giro = SORTE.uniform(-60, 60)
        if i % 2 == 0:
            tito.esfera(0.085, (px, py, pz), "Mat_Tito_Marrom", escala=(1, 0.9, 0.95), rot=(0, 0, giro))
            for ox in (-0.06, 0.06):
                tito.esfera(0.025, (px + ox, py, pz + 0.075), "Mat_Tito_Marrom", seg=6, aneis=4)
            focinho.esfera(0.03, (px + 0.03 * math.sin(math.radians(giro)), py - 0.07, pz - 0.01), "Mat_Tito_Bege",
                           seg=6, aneis=4)
        else:
            pipoca.esfera(0.08, (px, py, pz), "Mat_Pipoca_Lilas", escala=(1, 0.9, 1.0), rot=(0, 0, giro))
            for ox in (-0.03, 0.03):
                orelhas.esfera(0.02, (px + ox, py, pz + 0.12), "Mat_Pipoca_Branco", escala=(1, 1, 3.0),
                               rot=(SORTE.uniform(-25, 25), 0, 0), seg=6, aneis=4)
    filhos += [tito.objeto("Garra_Pelucias_Tito", col), focinho.objeto("Garra_Pelucias_Tito_Focinho", col),
               pipoca.objeto("Garra_Pelucias_Pipoca", col), orelhas.objeto("Garra_Pelucias_Pipoca_Orelhas", col)]
    # A cápsula com a chave do gerente, no meio das pelúcias (origem no centro dela)
    filhos.append(comum.esfera("Garra_Capsula_Chave", 0.06, V((0.02, -0.01, 1.03)), "Mat_Capsula_Chave", col,
                               segmentos=10, aneis=6, escala=(1, 1, 1.35)))
    # A garra: origem no topo (onde o cabo prende no carrinho); três dedos filhos que giram em X
    pinca = Lote()
    pinca.cilindro(0.006, 0.30, (0, 0, -0.30), "Mat_Metal_Cinza", lados=6)
    pinca.cilindro(0.04, 0.07, (0, 0, -0.37), "Mat_Metal_Escuro", lados=10)
    pinca_obj = pinca.objeto("Garra_Pinca", col)
    pinca_obj.location = V((0.1, 0.1, 1.735))
    for i in range(3):
        dedo = Lote()
        dedo.tubo([(0, 0.03, 0), (0, 0.075, -0.06), (0, 0.07, -0.13), (0, 0.035, -0.17)], 0.008, "Mat_Metal_Cinza")
        dedo_obj = dedo.objeto(f"Garra_Pinca_Dedo_{i + 1}", col)
        dedo_obj.parent = pinca_obj
        dedo_obj.location = V((0, 0, -0.37))
        dedo_obj.rotation_euler = (0, 0, math.radians(i * 120))
    filhos.append(pinca_obj)
    # Painel de cima com a arte (1:1), numa placa de fundo
    filhos.append(caixas("Maquina_Garra_Painel", [((0.74, 0.04, 0.72), (0, -0.3, 2.17))], "Mat_Garra_Detalhe", col))
    filhos.append(comum.plano_arte("painel_maquina_garra.jpg", 0.64, 0.64, V((0, -0.326, 2.21)), col))
    filhos.append(colisao("Maquina_Garra", (1.0, 1.12, 2.15), (0, -0.06, 0), col))
    montar(corpo, filhos, x, z, 0.0, frente)


def skee_ball(nome, col, x, z, frente, quebrada=False):
    """Pista de skee-ball: o jogador fica na frente (-Y) e rola a bola subindo a rampa até os alvos."""
    perfil_pista = [(-1.4, 0.0), (1.0, 0.0), (1.0, 0.95), (-1.0, 0.72), (-1.4, 0.72)]
    corpo = perfil_extrudado(nome, perfil_pista, 0.8, "Mat_Madeira_Envernizada", col)
    perfil_alvo = [(1.0, 0.0), (1.6, 0.0), (1.6, 2.2), (1.35, 2.2), (1.35, 1.7), (1.0, 1.0)]
    filhos = [perfil_extrudado(nome + "_Alvo", perfil_alvo, 0.8, "Mat_Plastico_Azul", col)]
    det = Lote()
    for sx in (-1, 1):
        det.caixa((0.03, 2.4, 0.35), (sx * 0.385, -0.2, 0.72), "Mat_Plastico_Amarelo", rot=(6.4, 0, 0))
        det.caixa((0.03, 0.4, 0.2), (sx * 0.385, -1.2, 0.72), "Mat_Plastico_Amarelo")
    det.caixa((0.7, 0.3, 0.03), (0, -1.2, 0.69), "Mat_Plastico_Preto")       # calha de volta das bolas
    # Alvos: anéis coloridos com o buraco escuro, deitados na inclinação
    for i, (sy, sz, raio) in enumerate(((1.08, 1.17, 0.16), (1.18, 1.38, 0.12), (1.27, 1.57, 0.08))):
        det.cilindro(raio + 0.03, 0.01, (0, sy, sz), "Mat_Plastico_Amarelo", rot=(63.4, 0, 0), lados=12)
        det.cilindro(raio, 0.012, (0, sy - 0.003, sz + 0.002), "Mat_Plastico_Preto", rot=(63.4, 0, 0), lados=12)
    # Placar e saída de tickets
    det.caixa((0.6, 0.02, 0.22), (0, 1.34, 1.88), "Mat_Plastico_Preto")
    det.caixa((0.12, 0.08, 0.12), (0.25, -1.44, 0.45), "Mat_Metal_Escuro")
    filhos.append(det.objeto(nome + "_Detalhes", col))
    filhos.append(texto(nome + "_Placar", "00000" if not quebrada else "88888", 0.11, "Mat_Placar_Led", col,
                        (0, 1.325, 1.99), largura_max=0.5, fonte_chave="VT323"))
    filhos.append(texto(nome + "_Letreiro", "SKEE-BALL", 0.12, "Mat_Plastico_Amarelo", col, (0, 1.33, 2.12),
                        largura_max=0.7))
    bolas = Lote()
    for i in range(4 if not quebrada else 1):
        bolas.esfera(0.05, (-0.25 + i * 0.12, -1.2, 0.77), "Mat_Bola_Madeira")
    # Fita de tickets saindo da máquina e enrolada no chão
    bolas.tubo([(0.25, -1.49, 0.47), (0.27, -1.52, 0.3), (0.3, -1.55, 0.1), (0.4, -1.6, 0.01), (0.55, -1.5, 0.01),
                (0.5, -1.7, 0.01)], 0.012, "Mat_Ticket", lados=3)
    filhos.append(bolas.objeto(nome + "_Bolas", col))
    if quebrada:
        # (na face vertical da frente do alvo, y = 1,35, entre a rampa e o placar; antes ficava
        # atrás da rampa inclinada e não aparecia)
        filhos.append(caixas(nome + "_Aviso", [((0.3, 0.004, 0.15), (0, 1.344, 1.715))], "Mat_Papel_Branco", col))
        filhos.append(texto(nome + "_Aviso_Texto", "QUEBRADA", 0.05, "Mat_Plastico_Vermelho", col, (0, 1.338, 1.79),
                            largura_max=0.26, fonte_chave="Caveat"))
    filhos.append(colisao(nome, (0.8, 3.0, 1.1), (0, 0.1, 0), col))
    filhos.append(colisao(nome + "_Alvo", (0.8, 0.6, 2.2), (0, 1.3, 0), col))
    montar(corpo, filhos, x, z, 0.0, frente)


def balcao_premios(col):
    """
    O ponto do balcão fica bem na frente da porta larga para a recepção. Para não trancar
    a passagem, o balcão é dividido em duas alas (com vitrine de vidro) que emolduram a
    porta, com as prateleiras de prêmios na parede atrás e a placa em cima do vão.
    """
    x, z, frente = P["balcao_premios"]
    raiz = vazio("Balcao_Premios", col, 0.5)
    filhos = []
    for lado, sx in (("Esq", -1), ("Dir", 1)):
        nome = f"Balcao_Premios_{lado}"
        cx = sx * 2.35
        ala = Lote()
        ala.caixa((1.3, 0.5, 0.95), (cx, -0.05, 0), "Mat_Madeira_Velha")
        ala.caixa((1.36, 0.56, 0.04), (cx, -0.05, 0.95), "Mat_Plastico_Vermelho")
        ala.caixa((1.3, 0.012, 0.3), (cx, -0.32, 0.6), "Mat_Plastico_Amarelo")   # faixa na frente
        ala.caixa((1.3, 0.5, 0.3), (cx, -0.05, 0.99), "Mat_Vidro_Vitrine")         # vitrine de cima
        # Brinquedinhos baratos dentro da vitrine
        for i in range(6):
            bx = cx - 0.5 + i * 0.2
            mat = ["Mat_Plastico_Rosa", "Mat_Plastico_Azul", "Mat_Plastico_Verde", "Mat_Plastico_Amarelo"][i % 4]
            if i % 2:
                ala.esfera(0.04, (bx, -0.05, 1.04), mat, seg=6, aneis=4)
            else:
                ala.caixa((0.08, 0.05, 0.1), (bx, -0.1 + 0.03 * (i % 3), 0.99), mat, rot=(0, 0, 20 * i))
        filhos.append(ala.objeto(nome, col))
        filhos.append(colisao(nome, (1.36, 0.56, 1.3), (cx, -0.05, 0), col))
        # Prateleira de prêmios encostada na parede atrás da ala
        pr_x = sx * 2.4
        prat = Lote()
        for k in range(4):
            prat.caixa((1.6, 0.25, 0.025), (pr_x, 0.555, 0.35 + k * 0.45), "Mat_Madeira_Velha")
        for s2 in (-1, 1):
            prat.caixa((0.03, 0.25, 1.75), (pr_x + s2 * 0.785, 0.555, 0.0), "Mat_Madeira_Velha")
        filhos.append(prat.objeto(nome + "_Prateleira", col))
        brinq = Lote()
        cores = ["Mat_Plastico_Rosa", "Mat_Plastico_Azul", "Mat_Plastico_Verde", "Mat_Plastico_Amarelo",
                 "Mat_Plastico_Lilas", "Mat_Plastico_Laranja", "Mat_Plastico_Vermelho"]
        for k in range(4):
            zb = 0.375 + k * 0.45
            for j in range(7):
                if SORTE.random() < 0.25:  # prêmios que já foram trocados (ou caíram)
                    continue
                bx = pr_x - 0.66 + j * 0.22 + SORTE.uniform(-0.03, 0.03)
                cor = cores[(j + k) % len(cores)]
                tipo = (j * 3 + k) % 4
                if tipo == 0:   # bolinha pula-pula
                    brinq.esfera(0.05, (bx, 0.55, zb + 0.05), cor, seg=6, aneis=4)
                elif tipo == 1:  # caixinha de brinquedo
                    brinq.caixa((0.12, 0.08, 0.16), (bx, 0.56, zb), cor, rot=(0, 0, SORTE.uniform(-15, 15)))
                elif tipo == 2:  # ioiô
                    brinq.cilindro(0.045, 0.04, (bx, 0.54, zb + 0.045), cor, rot=(90, 0, 0), lados=8)
                else:           # pelúcia pequena
                    brinq.esfera(0.06, (bx, 0.56, zb + 0.06), "Mat_Tito_Marrom" if j % 2 else "Mat_Pipoca_Lilas",
                                 seg=6, aneis=5)
        filhos.append(brinq.objeto(nome + "_Brinquedos", col))
        filhos.append(colisao(nome + "_Prateleira", (1.6, 0.25, 1.8), (pr_x, 0.555, 0), col))
    # Placa "TROQUE SEUS TICKETS!" na parede, em cima do vão da porta
    filhos.append(caixas("Balcao_Premios_Placa", [((2.6, 0.03, 0.45), (0, 0.665, 2.3))], "Mat_Plastico_Vermelho", col))
    filhos.append(texto("Balcao_Premios_Placa_Texto", "TROQUE SEUS TICKETS!", 0.16, "Mat_Plastico_Amarelo", col,
                        (0, 0.645, 2.52), largura_max=2.4))
    lamp = Lote()
    for i in range(12):
        lamp.esfera(0.022, (-1.21 + i * 0.22, 0.64, 2.33 if i % 2 else 2.71), "Mat_Lampada_Apagada", seg=6, aneis=4)
    filhos.append(lamp.objeto("Balcao_Premios_Placa_Lampadas", col))
    # Tickets e tabela de preços em cima das alas
    tickets = Lote()
    tickets.tubo([(-2.0, -0.1, 1.3), (-1.85, -0.2, 1.31), (-1.7, -0.05, 1.31), (-1.55, -0.32, 1.1), (-1.6, -0.4, 0.6),
                  (-1.5, -0.5, 0.01), (-1.3, -0.7, 0.01)], 0.014, "Mat_Ticket", lados=3)
    tickets.caixa((0.25, 0.01, 0.18), (2.35, -0.25, 1.29), "Mat_Papel_Branco", rot=(-15, 0, 0))
    filhos.append(tickets.objeto("Balcao_Premios_Tickets", col))
    montar(raiz, filhos, x, z, 0.0, frente)


def pinball(nome, col, x, z, frente, giro=0.0, perna_quebrada=False):
    perfil = [(-0.65, 0.72), (0.65, 0.72), (0.65, 1.0), (-0.65, 0.88)]
    corpo = perfil_extrudado(nome, perfil, 0.7, "Mat_Plastico_Preto", col)
    det = Lote()
    for sx in (-1, 1):
        for sy in (-1, 1):
            alt = 0.72 if not (perna_quebrada and sx == 1 and sy == -1) else 0.45
            det.caixa((0.05, 0.05, alt), (sx * 0.3, sy * 0.58, 0.0), "Mat_Metal_Cinza")
    det.caixa((0.66, 1.26, 0.005), (0, 0.0, 0.94), "Mat_Pinball_Mesa", rot=(-6.1, 0, 0))
    det.caixa((0.7, 0.16, 0.66), (0, 0.6, 0.96), "Mat_Plastico_Preto")         # caixa de trás
    det.caixa((0.62, 0.005, 0.5), (0, 0.517, 1.04), "Mat_Pinball_Vidro")         # vidro de trás
    for sx in (-1, 1):
        det.cilindro(0.015, 0.03, (sx * 0.355, -0.55, 0.78), "Mat_Plastico_Vermelho", rot=(0, 90 * sx, 0), lados=8)
    det.caixa((0.06, 0.06, 0.04), (0.25, -0.66, 0.78), "Mat_Metal_Cinza")       # lançador
    filhos = [det.objeto(nome + "_Detalhes", col), colisao(nome, (0.7, 1.4, 1.62), (0, 0.0, 0), col)]
    montar(corpo, filhos, x, z, 0.0, frente, giro)
    if perna_quebrada:
        # A perna da frente quebrou: a máquina tomba para a frente e para o lado
        corpo.rotation_euler = (math.radians(-8), math.radians(5), corpo.rotation_euler.z)


def hoquei_de_mesa(col, x, z, frente, giro):
    nome = "Hoquei_De_Mesa"
    corpo = caixas(nome, [((1.1, 2.0, 0.65), (0, 0, 0.15))], "Mat_Plastico_Azul", col)
    det = Lote()
    det.caixa((1.0, 1.9, 0.01), (0, 0, 0.8), "Mat_Mesa_Hoquei")
    for sx in (-1, 1):
        det.caixa((0.05, 2.0, 0.07), (sx * 0.525, 0, 0.8), "Mat_Plastico_Amarelo")
        det.caixa((0.6, 0.12, 0.15), (0, sx * 1.06, 0.7), "Mat_Plastico_Vermelho")
        det.caixa((0.08, 0.08, 0.15), (sx * 0.5, sx * 0.95, 0.0), "Mat_Metal_Escuro")
        det.caixa((0.08, 0.08, 0.15), (-sx * 0.5, sx * 0.95, 0.0), "Mat_Metal_Escuro")
    for sx in (-1, 1):
        det.caixa((1.1, 0.05, 0.07), (0, sx * 0.975, 0.8), "Mat_Plastico_Amarelo")
    det.caixa((1.0, 0.01, 0.002), (0, 0, 0.81), "Mat_Plastico_Vermelho")
    det.cilindro(0.04, 0.012, (0.2, 0.3, 0.81), "Mat_Plastico_Preto", lados=10)                # disco
    det.cilindro(0.05, 0.03, (-0.15, -0.6, 0.81), "Mat_Plastico_Vermelho", lados=10)           # rebatedor
    det.cilindro(0.02, 0.05, (-0.15, -0.6, 0.84), "Mat_Plastico_Vermelho", lados=6)
    det.cilindro(0.05, 0.03, (0.75, 0.7, 0.0), "Mat_Plastico_Vermelho", rot=(0, 0, 0), lados=10)  # caído no chão
    filhos = [det.objeto(nome + "_Detalhes", col), colisao(nome, (1.1, 2.1, 0.88), (0, 0, 0), col)]
    montar(corpo, filhos, x, z, 0.0, frente, giro)


def carrinho_tito(col, x, z, frente, giro):
    """Brinquedo de moeda: carrinho vermelho com a cabeça do Tito na frente."""
    nome = "Brinquedo_Carrinho_Tito"
    corpo = caixas(nome, [((0.75, 1.15, 0.2), (0, 0, 0))], "Mat_Plastico_Azul", col)
    det = Lote()
    det.caixa((0.6, 0.95, 0.35), (0, 0.05, 0.2), "Mat_Plastico_Vermelho")
    det.caixa((0.5, 0.35, 0.12), (0, 0.25, 0.55), "Mat_Plastico_Amarelo")    # assento
    det.caixa((0.5, 0.06, 0.35), (0, 0.42, 0.55), "Mat_Plastico_Vermelho")   # encosto
    det.cilindro(0.015, 0.25, (0, -0.15, 0.55), "Mat_Metal_Cinza", rot=(-30, 0, 0), lados=6)
    det.cilindro(0.1, 0.02, (0, -0.21, 0.76), "Mat_Plastico_Preto", rot=(-30, 0, 0), lados=10)   # volante
    for sx in (-1, 1):
        for sy in (-1, 1):
            det.cilindro(0.11, 0.06, (sx * 0.33, sy * 0.35, 0.12), "Mat_Plastico_Preto", rot=(0, 90, 0), lados=10)
    det.esfera(0.2, (0, -0.42, 0.75), "Mat_Tito_Marrom", seg=10, aneis=7)
    for sx in (-1, 1):
        det.esfera(0.07, (sx * 0.15, -0.42, 0.93), "Mat_Tito_Marrom", seg=6, aneis=5)
        det.esfera(0.03, (sx * 0.07, -0.58, 0.8), "Mat_Plastico_Preto", seg=6, aneis=4)
    det.esfera(0.08, (0, -0.6, 0.7), "Mat_Tito_Bege", seg=8, aneis=5)
    det.caixa((0.14, 0.1, 0.25), (0.3, 0.55, 0.2), "Mat_Metal_Escuro")
    det.caixa((0.035, 0.01, 0.06), (0.3, 0.6, 0.36), "Mat_Luz_Ficha")
    filhos = [det.objeto(nome + "_Detalhes", col), colisao(nome, (0.75, 1.3, 1.0), (0, -0.05, 0), col)]
    montar(corpo, filhos, x, z, 0.0, frente, giro)


def maquina_troca(col, x, z, frente):
    nome = "Maquina_Troca_Fichas"
    corpo = caixas(nome, [((0.6, 0.5, 1.6), (0, 0, 0))], "Mat_Metal_Pintado_Amarelo", col)
    det = Lote()
    det.caixa((0.4, 0.02, 0.25), (0, -0.26, 1.1), "Mat_Plastico_Preto")
    det.caixa((0.2, 0.02, 0.06), (0, -0.26, 0.9), "Mat_Luz_Ficha")
    det.caixa((0.3, 0.12, 0.1), (0, -0.3, 0.45), "Mat_Metal_Escuro")
    filhos = [det.objeto(nome + "_Detalhes", col),
              texto(nome + "_Texto", "FICHAS", 0.1, "Mat_Plastico_Vermelho", col, (0, -0.255, 1.45), largura_max=0.5),
              colisao(nome, (0.6, 0.5, 1.6), (0, 0, 0), col)]
    montar(corpo, filhos, x, z, 0.0, frente)


def banco_parede(nome, col, x, z, frente, comprimento=1.6, mat="Mat_Plastico_Vermelho"):
    corpo = caixas(nome, [((comprimento, 0.45, 0.08), (0, 0, 0.42))], mat, col)
    det = Lote()
    det.caixa((comprimento, 0.06, 0.45), (0, 0.2, 0.5), mat, rot=(-8, 0, 0))
    for sx in (-1, 1):
        det.caixa((0.05, 0.4, 0.42), (sx * (comprimento / 2 - 0.1), 0, 0), "Mat_Metal_Escuro")
    filhos = [det.objeto(nome + "_Estrutura", col), colisao(nome, (comprimento, 0.45, 0.95), (0, 0, 0), col)]
    montar(corpo, filhos, x, z, 0.0, frente)


def mesa_lanche(col, x, z):
    nome = "Mesa_Lanche_Fliperama"
    tampo = comum.cilindro(nome, 0.42, 0.04, V((0, 0, 0.72)), "Mat_Plastico_Branco", col, vertices=12)
    tampo.data.transform(Matrix.Translation((0, 0, 0.72)))
    tampo.location = (0, 0, 0)
    det = Lote()
    det.cilindro(0.04, 0.72, (0, 0, 0), "Mat_Metal_Escuro", lados=8)
    det.cilindro(0.25, 0.03, (0, 0, 0), "Mat_Metal_Escuro", lados=10)
    # Uma cadeira em pé (torta) e outra tombada
    det.caixa((0.4, 0.4, 0.04), (0.65, -0.1, 0.42), "Mat_Plastico_Amarelo", rot=(0, 0, 25))
    det.caixa((0.4, 0.04, 0.42), (0.74, 0.08, 0.46), "Mat_Plastico_Amarelo", rot=(0, 0, 25))
    for dx, dy in ((0.5, -0.25), (0.83, -0.1), (0.48, 0.1), (0.8, 0.25)):
        det.caixa((0.03, 0.03, 0.42), (dx, dy, 0.0), "Mat_Metal_Escuro")
    det.caixa((0.4, 0.4, 0.04), (-0.75, 0.25, 0.2), "Mat_Plastico_Amarelo", rot=(90, 0, -40))
    det.caixa((0.4, 0.42, 0.04), (-0.9, 0.0, 0.02), "Mat_Plastico_Amarelo", rot=(0, 0, -40))
    # Restos de lanche: copo, balde de pipoca, prato de papel
    det.cilindro(0.04, 0.13, (0.1, 0.12, 0.76), "Mat_Plastico_Vermelho", lados=8, raio_topo=0.05)
    det.cilindro(0.07, 0.18, (-0.15, -0.05, 0.76), "Mat_Plastico_Branco", lados=8, raio_topo=0.09)
    det.cilindro(0.11, 0.01, (0.05, -0.2, 0.76), "Mat_Papel_Branco", lados=10)
    filhos = [det.objeto(nome + "_Detalhes", col), colisao(nome, (0.85, 0.85, 0.76), (0, 0, 0), col)]
    montar(tampo, filhos, x, z)


def neon_rosa(col):
    """Neon rosa na parede oeste: um raio e uma estrela, presos numa placa preta."""
    lote = Lote()
    lote.caixa((1.5, 0.03, 0.8), (0, 0.0, 0), "Mat_Plastico_Preto")
    estrela = []
    for i in range(10):
        a = math.radians(90 + i * 36)
        r = 0.28 if i % 2 == 0 else 0.12
        estrela.append((-0.35 + r * math.cos(a), -0.03, 0.4 + r * math.sin(a)))
    lote.tubo(estrela, 0.012, "Mat_Neon_Rosa", lados=4, fechado=True)
    raio = [(0.3, -0.03, 0.72), (0.15, -0.03, 0.42), (0.35, -0.03, 0.44), (0.18, -0.03, 0.08)]
    lote.tubo(raio, 0.012, "Mat_Neon_Rosa", lados=4)
    obj = lote.objeto("Neon_Rosa_Fliperama", col)
    montar(obj, [], 14.13, 24.3, 1.95, "leste")
    marcador("Luz__neon_rosa_01", col, 14.35, 24.3, 2.35)


def neon_ciano(col):
    placa = caixas("Neon_Ciano_Fliperama", [((2.4, 0.03, 0.55), (0, 0.0, 0))], "Mat_Plastico_Preto", col)
    letras = texto("Neon_Ciano_Fliperama_Texto", "FLIPERAMA", 0.32, "Mat_Neon_Ciano", col, (0, -0.02, 0.28),
                   largura_max=2.2)
    borda = Lote()
    borda.tubo([(-1.15, -0.03, 0.04), (1.15, -0.03, 0.04), (1.15, -0.03, 0.51), (-1.15, -0.03, 0.51)], 0.01,
               "Mat_Neon_Ciano", fechado=True)
    montar(placa, [letras, borda.objeto("Neon_Ciano_Fliperama_Borda", col)], 31.87, 23.3, 2.15, "oeste")
    marcador("Luz__neon_ciano_01", col, 31.6, 23.3, 2.4)


def claraboia(col, x, z, teto):
    """Moldura da claraboia suja no forro (o luar entra por ela)."""
    lote = Lote()
    b = comum.p2(x, z, teto - 0.06)
    for sx in (-1, 1):
        lote.caixa((0.08, 1.3, 0.06), b + V((sx * 0.61, 0, 0)), "Mat_Metal_Escuro")
        lote.caixa((1.3, 0.08, 0.06), b + V((0, sx * 0.61, 0)), "Mat_Metal_Escuro")
    lote.caixa((0.04, 1.2, 0.04), b + V((0, 0, 0.01)), "Mat_Metal_Escuro")
    lote.caixa((1.16, 1.16, 0.01), b + V((0, 0, 0.04)), "Mat_Vidro_Aramado")
    lote.objeto("Claraboia_Fliperama", col, b)
    marcador("Luz__claraboia_03", col, x, z, teto - 0.1)


def grade_duto(nome, col, x, z, teto):
    """Grade do duto no forro (caixa fina, com aletas), origem no centro, logo abaixo do teto."""
    grade = comum.caixa(nome, (0.6, 0.6, 0.03), comum.p2(x, z, teto - 0.035), "Mat_Metal_Cinza", col, origem="base")
    aletas = Lote()
    for i in range(6):
        aletas.caixa((0.5, 0.025, 0.02), (0, -0.21 + i * 0.084, -0.02), "Mat_Metal_Escuro", rot=(30, 0, 0))
    a = aletas.objeto(nome + "_Aletas", col)
    a.parent = grade
    # um parafuso solto: a grade parece que dá para abrir
    p = comum.cilindro(nome + "_Parafuso_Solto", 0.01, 0.02, comum.p2(x + 0.5, z + 0.3, 0.0), "Mat_Metal_Cinza", col,
                       vertices=6)
    return grade, p


def lixo_fliperama(col):
    lote = Lote()
    copos = [(20.4, 21.3), (24.6, 20.9), (15.2, 26.2), (27.3, 25.4), (21.6, 30.6), (18.6, 29.2), (30.6, 24.9),
             (24.2, 27.8)]
    for i, (x, z) in enumerate(copos):
        if i % 3 == 0:
            lote.cilindro(0.04, 0.13, comum.p2(x, z, 0.0), "Mat_Plastico_Vermelho", lados=8, raio_topo=0.05)
        else:
            lote.cilindro(0.04, 0.13, comum.p2(x, z, 0.045), ["Mat_Plastico_Vermelho", "Mat_Plastico_Branco"][i % 2],
                          rot=(90, 0, SORTE.uniform(0, 360)), lados=8, raio_topo=0.05)
    # Fitas de tickets jogadas
    for x, z in ((19.5, 21.6), (25.8, 28.6), (22.2, 31.4), (29.0, 28.2), (16.5, 29.6)):
        pts = []
        for k in range(6):
            pts.append(comum.p2(x + k * 0.12 + SORTE.uniform(-0.05, 0.05), z + SORTE.uniform(-0.1, 0.1), 0.006))
        lote.tubo(pts, 0.012, "Mat_Ticket", lados=3)
    # Chapéus de festa amassados e um balão murcho
    for x, z, cor in ((18.2, 26.6, "Mat_Plastico_Azul"), (26.8, 22.2, "Mat_Plastico_Amarelo"), (21.0, 23.5, "Mat_Plastico_Verde")):
        lote.cilindro(0.07, 0.2, comum.p2(x, z, 0.07), cor, rot=(85, 0, SORTE.uniform(0, 360)), lados=8, raio_topo=0.0)
    lote.esfera(0.12, comum.p2(28.4, 21.2, 0.04), "Mat_Plastico_Rosa", escala=(1.3, 1.0, 0.3))
    lote.tubo([comum.p2(28.55, 21.2, 0.02), comum.p2(28.9, 21.3, 0.005), comum.p2(29.2, 21.15, 0.005)], 0.004,
              "Mat_Plastico_Branco", lados=3)
    # Pipoca e baldinho derrubado
    lote.cilindro(0.07, 0.18, comum.p2(17.6, 21.6, 0.07), "Mat_Plastico_Branco", rot=(90, 0, 40), lados=8, raio_topo=0.09)
    for k in range(10):
        lote.esfera(0.015, comum.p2(17.75 + SORTE.uniform(0, 0.4), 21.4 + SORTE.uniform(0, 0.4), 0.012),
                    "Mat_Plastico_Amarelo", seg=4, aneis=3)
    # Lixeira transbordando
    lote.cilindro(0.2, 0.6, comum.p2(14.5, 26.9, 0.0), "Mat_Metal_Escuro", lados=10)
    for k in range(6):
        lote.esfera(0.07, comum.p2(14.45 + SORTE.uniform(-0.12, 0.12), 26.9 + SORTE.uniform(-0.12, 0.12),
                                   0.62 + k * 0.03), ["Mat_Papel_Branco", "Mat_Plastico_Vermelho"][k % 2], seg=6, aneis=4)
    lote.objeto("Lixo_Fliperama", col, comum.p2(23.0, 26.0, 0.0))
    comum.colisao_caixa("Lixeira_Fliperama", (0.42, 0.42, 0.65), comum.p2(14.5, 26.9, 0.0), col)


def fliperama(col):
    teto = 3.2
    maquinas_tematicas(col)
    maquina_garra(col)
    skee_ball("Skee_Ball", col, *P["skee_ball"])
    sx, sz, sf = P["skee_ball"]
    skee_ball("Skee_Ball_02", col, sx, sz + 0.85, sf, quebrada=True)
    balcao_premios(col)
    # Ilha oeste: pinballs (um com a perna quebrada, tombado)
    pinball("Pinball_01", col, 17.0, 24.6, "sul")
    pinball("Pinball_02", col, 17.85, 24.55, "sul", giro=-4)
    pinball("Pinball_03", col, 19.05, 24.7, "sul", giro=12, perna_quebrada=True)
    # Ilha leste: gabinetes velhos costas com costas (quebram a visão do salão inteiro)
    velhos = [("Gabinete_Velho_01", 26.25, 26.55, "norte", 2, "Mat_Plastico_Preto", "Mat_Plastico_Vermelho", "TURBO"),
              ("Gabinete_Velho_02", 27.0, 26.5, "norte", -3, "Mat_Plastico_Azul", "Mat_Plastico_Amarelo", "FOGUETE"),
              ("Gabinete_Velho_03", 27.78, 26.6, "norte", 5, "Mat_Plastico_Verde", "Mat_Plastico_Branco", "ESTRELA"),
              ("Gabinete_Velho_04", 26.6, 27.45, "sul", -2, "Mat_Plastico_Vermelho", "Mat_Plastico_Preto", "PULO"),
              ("Gabinete_Velho_05", 27.45, 27.5, "sul", 7, "Mat_Plastico_Preto", "Mat_Plastico_Laranja", "PIZZA")]
    for nome, x, z, frente, giro, mc, md, titulo in velhos:
        corpo, filhos = gabinete_arcade(nome, col, mc, md, "Mat_Plastico_Vermelho",
                                        ("Mat_Plastico_Branco", "Mat_Plastico_Amarelo"))
        filhos.append(caixas(nome + "_Letreiro", [((0.68, 0.01, 0.28), (0, -0.255, 1.58))], md, col))
        filhos.append(texto(nome + "_Letreiro_Texto", titulo, 0.08, "Mat_Texto_Preto", col, (0, -0.262, 1.72),
                            largura_max=0.55, fonte_chave="PressStart"))
        montar(corpo, filhos, x, z, 0.0, frente, giro)
    # Tela rachada num dos velhos
    rach = Lote()
    for a, b in (((-0.1, -0.25, 1.3), (0.05, -0.26, 1.2)), ((0.05, -0.26, 1.2), (0.15, -0.27, 1.25)),
                 ((0.05, -0.26, 1.2), (0.02, -0.28, 1.08))):
        rach.tubo([a, b], 0.004, "Mat_Plastico_Branco", lados=3)
    r = rach.objeto("Gabinete_Velho_03_Rachadura", col)
    r.parent = bpy.data.objects["Gabinete_Velho_03"]
    hoquei_de_mesa(col, 27.5, 23.8, "leste", 3)
    carrinho_tito(col, 24.4, 22.5, "sul", -14)
    maquina_troca(col, 31.6, 21.6, "oeste")
    banco_parede("Banco_Fliperama", col, 14.38, 22.2, "leste")
    mesa_lanche(col, 21.0, 28.4)
    neon_rosa(col)
    neon_ciano(col)
    claraboia(col, 21.0, 27.6, teto)
    grade_duto("Duto_Grade_Fliperama", col, *[(gx, gz) for n, gx, gz in planta_v2.DUTO_GRADES if n == "Fliperama"][0], teto)
    forro_caido("Forro_Caido_Fliperama", col, 24.8, 29.6, 20, teto)
    lixo_fliperama(col)
    teias("Teias_Fliperama", col, [(14.12, 19.12, 1, 1), (31.88, 19.12, -1, 1), (14.12, 32.88, 1, -1),
                                   (31.88, 32.88, -1, -1), (22.0, 19.12, 1, 1)], teto)
    marcador("Som__bipes_01", col, 23.0, 20.0, 1.4)
    # Sujeira: refrigerante na frente das máquinas, confete perto dos prêmios, pegadas da recepção
    decal("refrigerante", col, 20.6, 21.0, 0.9, 0.7)
    decal("refrigerante", col, 27.2, 25.3, 0.7, 0.6, giro=30)
    decal("refrigerante", col, 16.0, 30.0, 0.6, 0.6)
    decal("confete", col, 23.0, 31.0, 1.6, 1.0)
    decal("confete", col, 17.6, 28.4, 1.2, 1.2, giro=15)
    decal("confete", col, 30.8, 31.9, 1.0, 1.4)
    decal("pegadas", col, 23.4, 29.5, 0.7, 3.0, giro=8)
    decal("pegadas", col, 28.0, 21.0, 0.6, 2.2, giro=-20)
    decal("mancha_agua", col, 14.6, 19.6, 1.0, 1.0)
    decal("mancha_agua", col, 31.5, 32.6, 1.0, 0.8)
    decal("marca_mao", col, 31.88, 28.2, 0.5, 0.5, parede="leste", h=1.1)


# ---------------------------------------------------------------------------
# COZINHA
# ---------------------------------------------------------------------------

def forno_pizza(col):
    """Forno de pizza a lenha: base de tijolo, cúpula, boca em arco, cinzas frias e chaminé até o teto."""
    nome = "Forno_Pizza"
    corpo = caixas(nome, [((2.4, 1.8, 1.0), (0, 0, 0))], "Mat_Tijolo_Forno", col)
    det = Lote()
    det.esfera(1.0, (0, 0.05, 1.0), "Mat_Tijolo_Forno", escala=(1.1, 0.82, 0.72), seg=14, aneis=7)
    det.caixa((2.46, 1.86, 0.06), (0, 0, 0.97), "Mat_Concreto_Sujo")                 # bancada da boca
    det.caixa((0.8, 0.5, 0.42), (0, -0.7, 1.03), "Mat_Tijolo_Forno")                  # moldura da boca
    det.caixa((0.6, 0.02, 0.32), (0, -0.955, 1.05), "Mat_Plastico_Preto")              # boca escura
    det.cilindro(0.3, 0.02, (0, -0.955, 1.37), "Mat_Plastico_Preto", rot=(90, 0, 0), lados=10)
    det.caixa((0.5, 0.2, 0.04), (0, -0.85, 1.03), "Mat_Cinza_Forno")                   # cinzas frias
    det.caixa((0.6, 0.6, 0.04), (0, 0.1, 1.68), "Mat_Metal_Escuro")
    det.cilindro(0.16, 1.48, (0, 0.1, 1.7), "Mat_Metal_Escuro", lados=8)                # chaminé até o forro
    det.caixa((0.7, 0.02, 0.6), (0, -0.91, 0.15), "Mat_Metal_Escuro")                  # porta da lenha embaixo
    filhos = [det.objeto(nome + "_Detalhes", col),
              texto(nome + "_Placa", "FORNO À LENHA", 0.07, "Mat_Plastico_Amarelo", col, (0, -0.985, 1.58),
                    largura_max=0.75),
              colisao(nome, (2.4, 1.8, 1.9), (0, 0, 0), col)]
    # Pá de pizza encostada e lenha empilhada ao lado
    pa = Lote()
    pa.caixa((0.35, 0.02, 0.4), (0.95, -0.95, 0.02), "Mat_Madeira_Clara", rot=(-12, 0, 0))
    pa.cilindro(0.018, 1.1, (0.95, -0.86, 0.42), "Mat_Madeira_Clara", rot=(-12, 0, 0), lados=6)
    filhos.append(pa.objeto(nome + "_Pa", col))
    lenha = Lote()
    for i in range(9):
        camada, k = divmod(i, 3)
        lenha.cilindro(0.06, 1.0, (-1.55 + k * 0.13 + camada * 0.06, 0.4, 0.06 + camada * 0.11), "Mat_Lenha",
                       rot=(90, 0, SORTE.uniform(-6, 6)), lados=6)
    lenha.cilindro(0.06, 0.9, (-1.35, -0.6, 0.06), "Mat_Lenha", rot=(90, 0, 70), lados=6)   # uma caída
    filhos.append(lenha.objeto(nome + "_Lenha", col))
    filhos.append(colisao(nome + "_Lenha", (0.45, 1.0, 0.35), (-1.42, -0.05, 0), col))
    montar(corpo, filhos, 42.6, 1.05, 0.0, "sul")


def fogao_coifa(col):
    nome = "Fogao"
    corpo = caixas(nome, [((1.2, 0.75, 0.9), (0, 0, 0))], "Mat_Inox", col)
    det = Lote()
    det.caixa((0.95, 0.02, 0.45), (0, -0.385, 0.2), "Mat_Metal_Escuro")
    det.caixa((0.6, 0.03, 0.03), (0, -0.41, 0.6), "Mat_Metal_Cinza")
    for i in range(5):
        det.cilindro(0.025, 0.03, (-0.4 + i * 0.2, -0.39, 0.78), "Mat_Plastico_Preto", rot=(90, 0, 0), lados=8)
    for sx in (-1, 1):
        for sy in (-1, 1):
            det.cilindro(0.11, 0.025, (sx * 0.3, sy * 0.17, 0.9), "Mat_Plastico_Preto", lados=10)
    det.cilindro(0.16, 0.16, (-0.3, -0.17, 0.925), "Mat_Metal_Escuro", lados=10)          # panela
    det.cilindro(0.13, 0.05, (0.3, 0.17, 0.925), "Mat_Metal_Escuro", lados=10)            # frigideira
    det.cilindro(0.015, 0.25, (0.3, -0.05, 0.95), "Mat_Plastico_Preto", rot=(90, 0, 0), lados=6)
    # Coifa: perfil trapézio esticado em X
    filhos = [det.objeto(nome + "_Detalhes", col)]
    coifa = perfil_extrudado("Coifa", [(-0.5, 1.95), (0.375, 1.95), (0.375, 2.6), (0.0, 2.6), (-0.5, 2.15)], 1.4,
                             "Mat_Inox", col)
    filhos.append(coifa)
    filhos.append(caixas("Coifa_Duto", [((0.45, 0.3, 0.58), (0, 0.2, 2.6))], "Mat_Inox", col))
    filhos.append(caixas("Coifa_Filtro", [((1.3, 0.4, 0.01), (0, -0.15, 1.95))], "Mat_Gordura", col))
    filhos.append(colisao(nome, (1.2, 0.75, 0.9), (0, 0, 0), col))
    montar(corpo, filhos, 48.7, 0.52, 0.0, "sul")


def geladeira(col):
    """Geladeira com a porta entreaberta e a luz de dentro acesa (a ilha de luz da cozinha)."""
    nome = "Geladeira"
    w, d, h, e = 0.9, 0.75, 1.95, 0.05
    corpo = caixas(nome, [((w, e, h), (0, d / 2 - e / 2, 0)), ((e, d, h), (-w / 2 + e / 2, 0, 0)),
                          ((e, d, h), (w / 2 - e / 2, 0, 0)), ((w, d, e), (0, 0, 0)), ((w, d, e), (0, 0, h - e))],
                   "Mat_Plastico_Branco", col)
    det = Lote()
    for k in range(3):
        det.caixa((w - 2 * e, d - 0.1, 0.015), (0, 0.03, 0.45 + k * 0.45), "Mat_Vidro_Vitrine")
    det.caixa((w - 2 * e, d - 0.06, 0.04), (0, 0.0, 1.45), "Mat_Plastico_Branco")         # congelador
    det.caixa((0.12, 0.03, 0.04), (0, 0.33, 1.38), "Mat_Luz_Geladeira")                  # lâmpada acesa
    # Potes, garrafas e uma caixa de leite esquecida
    det.cilindro(0.04, 0.25, (-0.25, 0.1, 0.465), "Mat_Plastico_Verde", lados=8, raio_topo=0.02)
    det.cilindro(0.04, 0.25, (-0.15, 0.15, 0.465), "Mat_Plastico_Verde", lados=8, raio_topo=0.02)
    det.cilindro(0.07, 0.1, (0.15, 0.0, 0.915), "Mat_Plastico_Branco", lados=8)
    det.caixa((0.08, 0.08, 0.2), (0.25, 0.1, 0.915), "Mat_Papel_Branco")
    det.caixa((0.25, 0.2, 0.08), (-0.1, 0.05, 1.365), "Mat_Plastico_Vermelho")
    filhos = [det.objeto(nome + "_Interior", col), colisao(nome, (w, d, h), (0, 0, 0), col)]
    # Porta: origem na dobradiça (lado direito), aberta uns 40 graus
    porta = Lote()
    porta.caixa((w, 0.06, h - 0.04), (-w / 2, -0.03, 0.02), "Mat_Plastico_Branco")
    porta.caixa((0.03, 0.04, 0.5), (-w + 0.06, -0.08, 0.9), "Mat_Metal_Cinza")
    porta.caixa((w - 0.12, 0.06, 0.012), (-w / 2, 0.03, 0.9), "Mat_Plastico_Branco")      # prateleira da porta
    porta.cilindro(0.035, 0.2, (-0.25, 0.04, 0.912), "Mat_Plastico_Vermelho", lados=6)
    porta.caixa((0.2, 0.005, 0.25), (-w / 2, -0.062, 1.2), "Mat_Papel_Amarelo", rot=(0, 4, 0))  # bilhete na porta
    porta_obj = porta.objeto(nome + "_Porta", col)
    porta_obj.location = V((w / 2, -d / 2, 0))
    porta_obj.rotation_euler = (0, 0, math.radians(40))
    pcol = colisao(nome + "_Porta", (w, 0.06, h), (-w / 2, -0.03, 0), col)
    pcol.parent = porta_obj
    filhos.append(porta_obj)
    montar(corpo, filhos, 50.9, 0.55, 0.0, "sul")
    marcador("Luz__abajur_01", col, 50.9, 0.75, 1.3)


def ilha_inox(col):
    """Ilha de inox no meio: corta a linha de visão de quem entra pela porta vaivém."""
    nome = "Ilha_Inox"
    corpo = caixas(nome, [((3.2, 1.2, 0.05), (0, 0, 0.86)), ((3.1, 1.1, 0.03), (0, 0, 0.2))], "Mat_Inox", col)
    det = Lote()
    for sx in (-1, 1):
        for sy in (-1, 1):
            det.caixa((0.05, 0.05, 0.86), (sx * 1.52, sy * 0.52, 0), "Mat_Inox")
    # Embaixo: pilha de assadeiras, saco de farinha, panelões
    det.caixa((0.5, 0.4, 0.15), (-1.0, 0.1, 0.23), "Mat_Metal_Cinza")
    det.caixa((0.5, 0.35, 0.3), (0.2, 0.0, 0.23), "Mat_Farinha", rot=(0, 0, 8))
    det.cilindro(0.22, 0.3, (1.0, 0.1, 0.23), "Mat_Metal_Escuro", lados=10)
    # Em cima: tábua, massa ressecada, rolo, potes
    det.caixa((0.5, 0.35, 0.03), (-0.9, 0.15, 0.91), "Mat_Madeira_Clara", rot=(0, 0, 10))
    det.cilindro(0.2, 0.025, (-0.9, 0.15, 0.94), "Mat_Massa_Pizza" if "Mat_Massa_Pizza" in CORES_DIVERSAO else "Mat_Caixa_Pizza", lados=10)
    det.cilindro(0.03, 0.42, (-0.4, 0.4, 0.94), "Mat_Madeira_Clara", rot=(0, 90, 15), lados=8)
    det.cilindro(0.08, 0.15, (0.6, 0.35, 0.91), "Mat_Louca_Branca", lados=8)
    det.cilindro(0.06, 0.12, (0.78, 0.3, 0.91), "Mat_Louca_Branca", lados=8)
    filhos = [det.objeto(nome + "_Itens", col), colisao(nome, (3.2, 1.2, 0.91), (0, 0, 0), col)]
    # O pedido de festa nunca entregue: caixas de pizza amarradas com fita e um balão murcho
    pedido = Lote()
    for k in range(6):
        pedido.caixa((0.42, 0.42, 0.05), (0.15 + SORTE.uniform(-0.02, 0.02), -0.2 + SORTE.uniform(-0.02, 0.02),
                                         0.91 + k * 0.05), "Mat_Caixa_Pizza", rot=(0, 0, SORTE.uniform(-6, 6)))
    pedido.caixa((0.43, 0.03, 0.31), (0.15, -0.2, 0.905), "Mat_Plastico_Vermelho")
    pedido.caixa((0.03, 0.43, 0.31), (0.15, -0.2, 0.905), "Mat_Plastico_Vermelho")
    pedido.tubo([(0.2, -0.2, 1.21), (0.25, -0.25, 1.4), (0.22, -0.3, 1.55)], 0.003, "Mat_Plastico_Branco", lados=3)
    pedido.esfera(0.11, (0.22, -0.33, 1.6), "Mat_Plastico_Azul", escala=(1.0, 0.6, 0.8), rot=(30, 0, 0))
    filhos.append(pedido.objeto("Pedido_Festa_Caixas", col))
    filhos.append(caixas("Pedido_Festa_Etiqueta", [((0.2, 0.15, 0.004), (0.15, -0.2, 1.215))], "Mat_Papel_Branco", col))
    etq = texto("Pedido_Festa_Etiqueta_Texto", "FESTA\nLUCAS", 0.04, "Mat_Texto_Preto", col, (0.15, -0.2, 1.223),
                largura_max=0.16, fonte_chave="Caveat", deitado=True)
    filhos.append(etq)
    montar(corpo, filhos, 45.6, 4.6, 0.0, "sul", 2)


def comanda_presa(col):
    """Trilho de comandas na parede perto da porta vaivém, com o pedido da festa preso."""
    nome = "Comanda_Trilho"
    corpo = caixas(nome, [((0.9, 0.05, 0.04), (0, -0.025, 0))], "Mat_Inox", col)
    det = Lote()
    det.caixa((0.14, 0.004, 0.24), (-0.25, -0.055, -0.22), "Mat_Papel_Branco", rot=(0, 3, 0))
    det.caixa((0.12, 0.004, 0.16), (0.3, -0.055, -0.15), "Mat_Papel_Branco", rot=(0, -6, 0))
    det.caixa((0.18, 0.004, 0.3), (0.02, -0.056, -0.28), "Mat_Papel_Amarelo")
    filhos = [det.objeto(nome + "_Papeis", col),
              texto("Comanda_Festa", "FESTA LUCAS\n12 PIZZAS\n+ BOLO\n19:30\nURGENTE!", 0.028, "Mat_Texto_Preto", col,
                    (0.02, -0.06, -0.12), largura_max=0.16, fonte_chave="Caveat")]
    montar(corpo, filhos, 40.13, 6.3, 1.55, "leste")


def pia_cozinha(col):
    nome = "Pia_Cozinha"
    corpo = caixas(nome, [((3.0, 0.65, 0.88), (0, 0, 0)), ((3.04, 0.68, 0.04), (0, 0, 0.88))], "Mat_Inox", col)
    det = Lote()
    det.caixa((0.8, 0.45, 0.02), (0.4, 0.0, 0.9), "Mat_Metal_Escuro")                 # cuba
    det.caixa((0.04, 0.04, 0.35), (0.4, 0.27, 0.92), "Mat_Metal_Cinza")
    det.caixa((0.04, 0.22, 0.04), (0.4, 0.17, 1.23), "Mat_Metal_Cinza")
    # Louça suja empilhada na cuba e na bancada
    for k in range(7):
        det.cilindro(0.13, 0.015, (0.35 + SORTE.uniform(-0.05, 0.05), SORTE.uniform(-0.05, 0.05), 0.92 + k * 0.02),
                     "Mat_Louca_Branca", rot=(SORTE.uniform(-10, 10), SORTE.uniform(-10, 10), 0), lados=10)
    det.cilindro(0.16, 0.14, (0.6, -0.05, 0.92), "Mat_Metal_Escuro", rot=(25, 0, 0), lados=10)
    for k in range(4):
        det.cilindro(0.045, 0.1, (-0.4 + k * 0.12, -0.18, 0.92), "Mat_Louca_Branca", lados=8)
    for k in range(5):
        det.cilindro(0.12, 0.012, (-0.9, 0.05, 0.92 + k * 0.015), "Mat_Louca_Branca", lados=10)
    det.cilindro(0.12, 0.012, (-1.1, -0.45, 0.004), "Mat_Louca_Branca", rot=(4, 0, 0), lados=10)   # prato no chão
    det.caixa((0.25, 0.05, 0.004), (-1.25, -0.5, 0.0), "Mat_Louca_Branca", rot=(0, 0, 40))     # caco
    det.caixa((0.6, 0.02, 0.6), (-0.9, -0.335, 0.15), "Mat_Metal_Cinza", rot=(0, 0, 0))     # porta do armário
    det.caixa((0.6, 0.02, 0.6), (-0.3, -0.5, 0.15), "Mat_Metal_Cinza", rot=(0, 0, -50))    # porta aberta
    filhos = [det.objeto(nome + "_Louca", col), colisao(nome, (3.04, 0.68, 0.92), (0, 0, 0), col)]
    montar(corpo, filhos, 51.54, 11.0, 0.0, "oeste")
    marcador("Som__goteira_01", col, 51.6, 10.6, 1.0)
    decal("mancha_agua", col, 50.9, 10.6, 0.9, 1.2)
    decal("gordura", col, 51.88, 11.0, 2.6, 0.8, parede="leste", h=1.25)


def prateleiras_panelas(col):
    frame, filhos = estante("Prateleira_Panelas", col, 2.0, 0.4, 1.9, 4, "Mat_Inox", "Mat_Metal_Escuro", 3,
                            faltando=(5,))
    pan = Lote()
    for k in range(5):
        pan.cilindro(0.11 + 0.02 * (k % 2), 0.12, (-0.75 + k * 0.38, 0.0, 1.88), "Mat_Metal_Cinza", lados=10)
    pan.cilindro(0.14, 0.1, (0.5, -0.7, 0.0), "Mat_Metal_Escuro", rot=(70, 0, 30), lados=10)   # panela caída
    filhos.append(pan.objeto("Prateleira_Panelas_Panelas", col))
    montar(frame, filhos, 40.32, 11.5, 0.0, "leste")
    # Estante dupla de inox no meio (sem fundo), com panelões: mais uma quebra de visão
    frame, filhos = estante("Estante_Inox_Cozinha", col, 1.8, 0.55, 1.8, 3, "Mat_Inox", "Mat_Metal_Cinza", 3,
                            fundo=False, faltando=(2,))
    montar(frame, filhos, 44.0, 10.0, 0.0, "leste", 4)


def caixas_pizza(col):
    lote = Lote()
    for pilha, (x, z, n) in enumerate(((40.55, 15.3, 18), (41.05, 15.4, 11))):
        for k in range(n):
            lote.caixa((0.42, 0.42, 0.05), comum.p2(x + SORTE.uniform(-0.02, 0.02) + k * 0.004 * (pilha * 2 - 1),
                                                    z + SORTE.uniform(-0.02, 0.02), k * 0.05), "Mat_Caixa_Pizza",
                       rot=(0, 0, SORTE.uniform(-8, 8)))
    for k in range(3):  # caixas que escorregaram da pilha
        lote.caixa((0.42, 0.42, 0.05), comum.p2(41.4 + k * 0.25, 14.8 - k * 0.15, 0.0), "Mat_Caixa_Pizza",
                   rot=(0, 0, 25 + k * 30))
    obj = lote.objeto("Caixas_Pizza", col, comum.p2(40.8, 15.35, 0.0))
    c = comum.colisao_caixa("Caixas_Pizza", (0.95, 0.5, 0.9), comum.p2(40.8, 15.35, 0.0), col)
    comum.parentar(c, obj)
    # Mesa de montagem encostada na parede sul, com mais caixas
    nome = "Mesa_Montagem"
    corpo = caixas(nome, [((1.8, 0.7, 0.05), (0, 0, 0.85)), ((1.7, 0.6, 0.03), (0, 0, 0.2))], "Mat_Inox", col)
    det = Lote()
    for sx in (-1, 1):
        for sy in (-1, 1):
            det.caixa((0.04, 0.04, 0.85), (sx * 0.86, sy * 0.31, 0), "Mat_Inox")
    for k in range(9):
        det.caixa((0.42, 0.42, 0.05), (-0.5 + SORTE.uniform(-0.03, 0.03), 0.05, 0.9 + k * 0.05), "Mat_Caixa_Pizza",
                  rot=(0, 0, SORTE.uniform(-10, 10)))
    for k in range(3):
        det.caixa((0.3, 0.3, 0.08), (0.4 + k * 0.05, 0.0, 0.9 + k * 0.08), "Mat_Plastico_Branco", rot=(0, 0, 12 * k))
    det.caixa((0.3, 0.4, 0.25), (0.1, 0.0, 0.23), "Mat_Papelao_Caixa")
    filhos = [det.objeto(nome + "_Itens", col), colisao(nome, (1.8, 0.7, 0.9), (0, 0, 0), col)]
    montar(corpo, filhos, 49.6, 15.5, 0.0, "norte")


def disjuntor_cozinha(col):
    """
    Disjuntor 1 (conserto de fios). Caixa com a origem no centro da face de trás, encostada
    na parede, centro a 1,3 m. Filhos: alavanca (desligada = -40° em X), LED, placa, a tampa
    do painel (aberta, origem na dobradiça) e 3 fios coloridos soltos.
    """
    x, z, frente = P["disjuntor_cozinha"]
    nome = "Disjuntor_Cozinha"
    cx = caixas(nome, [((0.45, 0.15, 0.6), (0, -0.075, -0.3))], "Mat_Disjuntor_Caixa", col)
    alav = caixas(nome + "_Alavanca", [((0.12, 0.04, 0.04), (0, 0, -0.02)), ((0.03, 0.14, 0.03), (0, 0.07, -0.015)),
                                       ((0.09, 0.04, 0.04), (0, 0.15, -0.02))], "Mat_Disjuntor_Alavanca", col)
    alav.parent = cx
    alav.location = V((0, -0.15, 0))
    alav.rotation_euler = (math.radians(-40), 0, math.radians(180))
    led = caixas(nome + "_Led", [((0.03, 0.01, 0.03), (0.16, -0.155, 0.2))], "Mat_Led_Disjuntor", col)
    led.parent = cx
    placa = texto(nome + "_Placa", "COZINHA", 0.05, "Mat_Texto_Branco", col, (-0.03, -0.152, 0.22), largura_max=0.3)
    placa.parent = cx
    tampa = caixas(nome + "_Tampa", [((0.45, 0.015, 0.6), (0.225, -0.0075, -0.3))], "Mat_Disjuntor_Caixa", col)
    tampa.parent = cx
    tampa.location = V((-0.225, -0.15, 0))
    tampa.rotation_euler = (0, 0, math.radians(-110))
    fios = []
    for cor, dx, pontos in (("Vermelho", -0.1, [(0, -0.1, -0.22), (0, -0.2, -0.3), (0.02, -0.22, -0.45), (-0.03, -0.18, -0.58), (0.02, -0.21, -0.66)]),
                            ("Azul", 0.0, [(0, -0.1, -0.22), (0.01, -0.22, -0.28), (0.05, -0.26, -0.4), (0.03, -0.24, -0.52)]),
                            ("Amarelo", 0.1, [(0, -0.1, -0.22), (-0.02, -0.19, -0.32), (0.04, -0.2, -0.5), (0.0, -0.23, -0.62), (0.05, -0.26, -0.7)])):
        lote = Lote()
        pts = [(px + dx, py, pz) for px, py, pz in pontos]
        lote.tubo(pts, 0.008, f"Mat_Fio_{cor}", lados=4)
        ponta = V(pts[-1])
        lote.cilindro(0.004, 0.025, ponta - V((0, 0, 0.025)), "Mat_Cobre", lados=4)   # cobre descascado
        fio = lote.objeto(f"{nome}_Fio_{cor}", col)
        fio.parent = cx
        fios.append(fio)
    cx.location = comum.p2(x, z, 1.3)
    cx.rotation_euler = (0, 0, math.radians(FRENTES[frente][0]))
    return cx


def desenho_crianca(col):
    """ARTE-20 colada na parede perto do disjuntor, com papel de fundo e fita adesiva."""
    fundo = caixas("Desenho_Crianca_Vigia", [((0.44, 0.004, 0.34), (0, -0.002, -0.02))], "Mat_Papel_Branco", col)
    arte = comum.plano_arte("desenho_crianca_vigia.jpg", 0.4, 0.3, V((0, -0.01, 0.0)), col)  # 6 mm do papel
    fita = Lote()
    for sx in (-1, 1):
        fita.caixa((0.08, 0.003, 0.025), (sx * 0.2, -0.0135, 0.29), "Mat_Papel_Amarelo", rot=(0, 30 * sx, 0))
    obj = montar(fundo, [arte, fita.objeto("Desenho_Crianca_Vigia_Fita", col)], 47.1, 0.115, 1.2, "sul")
    obj.rotation_euler = (0, math.radians(3), obj.rotation_euler.z)


def lixo_cozinha(col):
    lote = Lote()
    # Lixeira transbordando
    lote.cilindro(0.24, 0.65, comum.p2(43.2, 15.2, 0.0), "Mat_Plastico_Verde", lados=10)
    for k in range(5):
        lote.esfera(0.09, comum.p2(43.2 + SORTE.uniform(-0.15, 0.15), 15.2 + SORTE.uniform(-0.15, 0.15), 0.68 + 0.05 * k),
                    "Mat_Plastico_Preto", seg=6, aneis=4)
    lote.esfera(0.12, comum.p2(43.7, 14.9, 0.1), "Mat_Plastico_Preto", escala=(1, 1, 0.8), seg=6, aneis=4)
    # Latas, guardanapos e uma cadeira tombada
    for x, z in ((48.3, 6.8), (42.6, 9.2), (50.2, 8.3), (46.8, 12.6)):
        lote.cilindro(0.033, 0.12, comum.p2(x, z, 0.033), "Mat_Metal_Cinza", rot=(90, 0, SORTE.uniform(0, 180)), lados=8)
    for x, z in ((44.6, 7.2), (47.6, 9.6), (42.2, 5.4)):
        lote.caixa((0.15, 0.15, 0.004), comum.p2(x, z, 0.0), "Mat_Papel_Branco", rot=(0, 0, SORTE.uniform(0, 90)))
    lote.caixa((0.42, 0.42, 0.04), comum.p2(42.5, 7.3, 0.2), "Mat_Plastico_Vermelho", rot=(90, 0, 30))
    lote.caixa((0.42, 0.4, 0.04), comum.p2(42.75, 7.45, 0.0), "Mat_Plastico_Vermelho", rot=(0, 0, 30))
    # Saco de farinha rasgado no chão
    lote.esfera(0.25, comum.p2(48.6, 7.2, 0.1), "Mat_Farinha", escala=(1.4, 0.9, 0.45), seg=8, aneis=5)
    lote.objeto("Lixo_Cozinha", col, comum.p2(46.0, 8.0, 0.0))
    comum.colisao_caixa("Lixeira_Cozinha", (0.5, 0.5, 0.7), comum.p2(43.2, 15.2, 0.0), col)


def cozinha(col, col_disj):
    teto = 3.2
    forno_pizza(col)
    fogao_coifa(col)
    geladeira(col)
    ilha_inox(col)
    comanda_presa(col)
    pia_cozinha(col)
    prateleiras_panelas(col)
    caixas_pizza(col)
    disjuntor_cozinha(col_disj)
    desenho_crianca(col)
    lixo_cozinha(col)
    gx, gz = [(gx, gz) for n, gx, gz in planta_v2.DUTO_GRADES if n == "Cozinha"][0]
    grade_duto("Duto_Grade_Cozinha", col, gx, gz, teto)
    forro_caido("Forro_Caido_Cozinha", col, 48.6, 10.4, -15, teto)
    teias("Teias_Cozinha", col, [(40.12, 0.12, 1, 1), (51.88, 0.12, -1, 1), (40.12, 15.88, 1, -1), (51.88, 15.88, -1, -1),
                                 (44.6, 0.12, 1, 1)], teto)
    decal("gordura", col, 48.7, 1.3, 1.6, 1.0)
    decal("gordura", col, 48.7, 0.1, 1.6, 1.2, parede="norte", h=1.4)
    decal("gordura", col, 42.6, 2.4, 1.4, 0.8)
    decal("pegadas", col, 44.0, 7.8, 0.6, 2.5, giro=80)
    decal("mancha_agua", col, 40.6, 0.6, 1.0, 1.0)
    decal("mancha_agua", col, 51.4, 15.4, 0.9, 0.9)
    decal("marca_mao", col, 46.4, 0.1, 0.5, 0.5, parede="norte", h=1.0)


# ---------------------------------------------------------------------------
# CÂMARA FRIA (beco sem saída)
# ---------------------------------------------------------------------------

def rotular(lote_txt, nome, col, texto_corpo, centro, largura):
    return texto(nome, texto_corpo, 0.045, "Mat_Texto_Preto", col, centro, largura_max=largura, fonte_chave="Courier")


def camara_fria(col):
    teto = 2.8
    estantes = [("Estante_Fria_01", 54.15, 0.45, 3.0, "sul"),
                ("Estante_Fria_02", 59.55, 2.35, 2.4, "oeste"),
                ("Estante_Fria_03", 59.55, 5.75, 2.4, "oeste"),
                ("Estante_Fria_04", 55.6, 7.55, 3.0, "norte")]
    for i, (nome, x, z, larg, frente) in enumerate(estantes):
        frame, filhos = estante(nome, col, larg, 0.6, 2.0, 4, "Mat_Metal_Cinza", "Mat_Papelao_Caixa", 4,
                                fundo=False, faltando=(3 + i, 9 + i))
        if i in (0, 3):
            # Etiquetas "MASSA VENCIDA 1998" nas caixas de baixo
            for k, ex in enumerate((-0.9, 0.35)):
                # colada na beirada da prateleira de baixo (tábua de 0,08 a 0,11 m), como etiqueta de
                # preço: antes ficava atrás das caixas, que têm posição sorteada, e sumia
                filhos.append(caixas(f"{nome}_Etiqueta_{k + 1}", [((0.3, 0.004, 0.06), (ex, -0.304, 0.065))],
                                     "Mat_Papel_Branco", col))
                filhos.append(rotular(None, f"{nome}_Etiqueta_{k + 1}_Texto", col, "MASSA VENCIDA 1998",
                                      (ex, -0.309, 0.095), 0.27))
        gelo = Lote()
        for k in range(6):
            gelo.cilindro(0.015, 0.08, (-larg / 2 + 0.2 + k * (larg - 0.4) / 5, -0.25, 0.53 + 0.47 * (k % 3)),
                          "Mat_Gelo", rot=(180, 0, 0), lados=4, raio_topo=0.0)
        filhos.append(gelo.objeto(nome + "_Gelo", col))
        montar(frame, filhos, x, z, 0.0, frente)
    # Estante dupla no meio (sem fundo): quebra a visão e cria a volta
    frame, filhos = estante("Estante_Fria_Centro", col, 2.4, 0.6, 1.8, 3, "Mat_Metal_Cinza", "Mat_Papelao_Caixa", 3,
                            fundo=False, faltando=(4,))
    filhos.append(caixas("Estante_Fria_Centro_Etiqueta", [((0.3, 0.004, 0.06), (0.0, -0.304, 0.632))], "Mat_Papel_Branco", col))
    filhos.append(rotular(None, "Estante_Fria_Centro_Etiqueta_Texto", col, "MASSA VENCIDA 1998", (0.0, -0.309, 0.662), 0.27))
    montar(frame, filhos, 56.0, 4.3, 0.0, "sul", -3)
    # Carcaças de plástico: engradados vazios empilhados, um tombado, e uma cabeça de fantasia velha
    eng = Lote()
    for k, (x, z, h, g) in enumerate(((53.05, 6.95, 0.0, 3), (53.1, 6.9, 0.32, -8), (53.0, 6.95, 0.64, 12),
                                      (53.75, 7.05, 0.0, -4), (58.45, 0.6, 0.0, 10), (58.4, 0.62, 0.32, -5))):
        b = comum.p2(x, z, h)
        eng.caixa((0.55, 0.38, 0.32), b, "Mat_Engradado", rot=(0, 0, g))
    eng.caixa((0.55, 0.38, 0.32), comum.p2(54.5, 6.3, 0.19), "Mat_Engradado", rot=(70, 0, 35))
    eng.esfera(0.22, comum.p2(53.05, 6.95, 1.18), "Mat_Tito_Marrom", seg=10, aneis=7)
    for sx in (-1, 1):
        eng.esfera(0.08, comum.p2(53.05 + sx * 0.16, 6.95, 1.36), "Mat_Tito_Marrom", seg=6, aneis=5)
    eng.esfera(0.09, comum.p2(53.05, 6.75, 1.12), "Mat_Tito_Bege", seg=8, aneis=5)
    eng.objeto("Carcacas_Plastico", col, comum.p2(53.4, 7.0, 0.0))
    comum.colisao_caixa("Carcacas_Plastico_A", (1.3, 0.5, 1.4), comum.p2(53.4, 7.0, 0.0), col)
    comum.colisao_caixa("Carcacas_Plastico_B", (0.6, 0.45, 0.65), comum.p2(58.43, 0.6, 0.0), col)
    # Caixa grande no chão perto da porta
    cx = caixas("Caixa_Massa_Chao", [((0.6, 0.5, 0.45), (0, 0, 0))], "Mat_Papelao_Caixa", col)
    filhos = [caixas("Caixa_Massa_Chao_Etiqueta", [((0.34, 0.004, 0.12), (0, -0.253, 0.22))], "Mat_Papel_Branco", col),
              rotular(None, "Caixa_Massa_Chao_Texto", col, "MASSA\nVENCIDA 1998", (0, -0.258, 0.28), 0.3),
              colisao("Caixa_Massa_Chao", (0.6, 0.5, 0.45), (0, 0, 0), col)]
    montar(cx, filhos, 53.0, 1.6, 0.0, "leste", 12)
    # Cortina de tiras de PVC logo dentro da porta (sem colisão: o jogador passa por ela)
    tiras = Lote()
    for k in range(8):
        zc = 3.35 + k * 0.18
        dx = SORTE.uniform(-0.03, 0.03)
        b0 = comum.p2(52.2 + dx, zc - 0.09, 0.05)
        tiras.poligono([b0, b0 + V((0, -0.17, 0)), b0 + V((0, -0.17, 2.15)), b0 + V((0, 0, 2.15))], "Mat_PVC_Tiras",
                       dois_lados=True)
    tiras.caixa((0.06, 1.5, 0.05), comum.p2(52.2, 4.0, 2.2), "Mat_Metal_Cinza")
    tiras.objeto("Cortina_PVC", col, comum.p2(52.2, 4.0, 0.0))
    # Luz azul fria no teto e o compressor com o ventilador
    lum = Lote()
    lum.caixa((0.25, 0.25, 0.08), comum.p2(56.0, 2.6, teto - 0.08), "Mat_Metal_Escuro")
    lum.esfera(0.08, comum.p2(56.0, 2.6, teto - 0.14), "Mat_Luz_Fria", seg=8, aneis=5)
    for k in range(4):
        lum.tubo([comum.p2(56.0, 2.6, teto - 0.08) + V((0.1 * math.cos(k * math.pi / 2), 0.1 * math.sin(k * math.pi / 2), 0)),
                  comum.p2(56.0, 2.6, teto - 0.24)], 0.006, "Mat_Metal_Escuro", lados=3)
    lum.objeto("Luminaria_Fria", col, comum.p2(56.0, 2.6, teto))
    marcador("Luz__tela_01", col, 56.0, 2.6, teto - 0.25)
    comp = caixas("Compressor_Camara", [((1.1, 0.45, 0.45), (0, 0, 0))], "Mat_Metal_Cinza", col)
    det = Lote()
    for sx in (-0.28, 0.28):
        det.cilindro(0.16, 0.02, (sx, -0.225, 0.225), "Mat_Metal_Escuro", rot=(90, 0, 0), lados=12)
        det.caixa((0.3, 0.01, 0.03), (sx, -0.245, 0.21), "Mat_Metal_Cinza", rot=(0, 25, 0))
    det.tubo([(0.5, 0.0, 0.45), (0.5, 0.0, 0.6), (-1.5, 0.05, 0.6)], 0.025, "Mat_Metal_Cinza", lados=6)
    filhos = [det.objeto("Compressor_Camara_Detalhes", col)]
    montar(comp, filhos, 58.3, 7.6, 2.05, "norte")
    marcador("Som__geladeira_01", col, 58.3, 7.5, 2.3)
    # Chão: pacotes caídos e gelo derretido
    chao = Lote()
    for x, z, g in ((57.2, 3.0, 20), (55.0, 5.6, -30), (58.2, 6.4, 60)):
        chao.caixa((0.35, 0.28, 0.2), comum.p2(x, z, 0.0), "Mat_Papelao_Caixa", rot=(0, 0, g))
    chao.caixa((0.25, 0.25, 0.012), comum.p2(54.0, 3.2, 0.0), "Mat_Papel_Branco", rot=(0, 0, 15))
    chao.objeto("Pacotes_Caidos_Fria", col, comum.p2(56.0, 4.0, 0.0))
    teias("Teias_Camara_Fria", col, [(52.12, 0.12, 1, 1), (59.88, 7.88, -1, -1)], teto)
    decal("mancha_agua", col, 56.0, 2.6, 1.4, 1.4)
    decal("mancha_agua", col, 59.2, 7.3, 1.0, 1.0)
    decal("pegadas", col, 53.6, 4.1, 0.6, 2.4, giro=90)
    decal("mancha_agua", col, 52.4, 0.5, 0.8, 0.8)


# ---------------------------------------------------------------------------
# BANHEIROS
# ---------------------------------------------------------------------------

def pias_espelho(col):
    nome = "Bancada_Pias"
    corpo = caixas(nome, [((2.4, 0.58, 0.82), (0, 0, 0)), ((2.44, 0.6, 0.04), (0, 0, 0.82))], "Mat_Plastico_Branco", col)
    det = Lote()
    for sx in (-0.6, 0.6):
        det.cilindro(0.19, 0.05, (sx, -0.02, 0.84), "Mat_Louca_Branca", lados=12)
        det.cilindro(0.15, 0.01, (sx, -0.02, 0.885), "Mat_Metal_Escuro", lados=12)
        det.caixa((0.04, 0.04, 0.15), (sx, 0.22, 0.86), "Mat_Metal_Cinza")
        det.caixa((0.04, 0.12, 0.03), (sx, 0.17, 0.99), "Mat_Metal_Cinza")
    det.caixa((0.1, 0.08, 0.18), (0.0, 0.2, 0.86), "Mat_Plastico_Rosa")            # sabonete líquido
    det.cilindro(0.05, 0.1, (0.95, 0.0, 0.86), "Mat_Papel_Branco", rot=(90, 0, 20), lados=8)   # rolo de papel
    filhos = [det.objeto(nome + "_Detalhes", col), colisao(nome, (2.44, 0.6, 0.88), (0, 0, 0), col)]
    # Espelho rachado (plano com Mat_Espelho) e as rachaduras por cima
    filhos.append(plano_uv("Espelho_Banheiro", [(-1.1, 0.285, 1.15), (1.1, 0.285, 1.15), (1.1, 0.285, 2.05),
                                                 (-1.1, 0.285, 2.05)], "Mat_Espelho", col))
    filhos.append(caixas("Espelho_Banheiro_Moldura", [((2.26, 0.02, 0.05), (0, 0.3, 1.12)), ((2.26, 0.02, 0.05), (0, 0.3, 2.04))],
                         "Mat_Metal_Cinza", col))
    rach = Lote()
    centro = (0.45, 0.28, 1.65)
    for ang in (10, 75, 140, 200, 260, 320):
        a = math.radians(ang)
        comp = SORTE.uniform(0.25, 0.5)
        meio = (centro[0] + 0.5 * comp * math.cos(a) + SORTE.uniform(-0.03, 0.03), 0.28,
                centro[2] + 0.5 * comp * math.sin(a) * 0.8)
        fim = (centro[0] + comp * math.cos(a), 0.28, min(2.02, max(1.18, centro[2] + comp * math.sin(a) * 0.8)))
        rach.tubo([centro, meio, fim], 0.003, "Mat_Rachadura", lados=3)
    rach.poligono([(0.45, 0.279, 1.65), (0.6, 0.279, 1.72), (0.52, 0.279, 1.8)], "Mat_Rachadura")   # caco que caiu
    filhos.append(rach.objeto("Espelho_Banheiro_Rachaduras", col))
    montar(corpo, filhos, 52.42, 10.7, 0.0, "leste")
    marcador("Som__goteira_02", col, 52.45, 10.1, 0.95)
    decal("mancha_agua", col, 53.1, 10.4, 1.0, 1.6)


def mictorios(col):
    nome = "Mictorios"
    corpo = caixas(nome, [((1.8, 0.04, 0.05), (0, 0.15, 1.6))], "Mat_Metal_Cinza", col)   # cano
    det = Lote()
    for sx in (-0.5, 0.5):
        det.caixa((0.4, 0.3, 0.6), (sx, 0.0, 0.45), "Mat_Louca_Branca")
        det.caixa((0.3, 0.02, 0.4), (sx, -0.155, 0.55), "Mat_Metal_Escuro")
        det.cilindro(0.015, 0.55, (sx, 0.12, 1.05), "Mat_Metal_Cinza", lados=6)
    det.caixa((0.04, 0.4, 0.9), (0.0, -0.05, 0.4), "Mat_Plastico_Azul")              # divisória
    filhos = [det.objeto(nome + "_Louca", col), colisao(nome, (1.4, 0.36, 1.1), (0, -0.0, 0.0), col)]
    montar(corpo, filhos, 54.2, 8.3, 0.0, "sul")


def cabines(col):
    """
    3 cabines na parede leste, cada uma com a porta (objeto filho _Porta, origem na dobradiça).
    Colisão nas divisórias e nos painéis da frente; o vão da porta fica sem colisão (entrada aberta).
    O Empty Esconderijo__cabine_NN fica no ponto de PONTOS (logo depois da porta).
    """
    frente_x, fundo_x = 57.8, 59.88
    divisorias = [10.5, 12.5, 14.15]
    limites = [(8.13, 10.5), (10.5, 12.5), (12.5, 14.15)]
    pontos = [(x, z) for tipo, x, z in P["esconderijos"] if tipo == "cabine"]
    aberturas = [85, 95, 80]  # bem abertas (para dentro): o vão da porta fica claramente livre
    for i, ((za, zb), (ex, ez)) in enumerate(zip(limites, pontos)):
        nome = f"Cabine_{i + 1:02d}"
        origem = comum.p2(ex, ez, 0.0)
        lote = Lote()
        largura_porta = 0.8
        p0, p1 = ez - largura_porta / 2, ez + largura_porta / 2
        cx = (frente_x + fundo_x) / 2
        if i < len(divisorias):
            zd = divisorias[i]
            lote.caixa((fundo_x - frente_x, 0.04, 1.85), comum.p2(cx, zd, 0.15), "Mat_Plastico_Azul")
        for a, b in ((za, p0), (p1, zb)):
            lote.caixa((0.04, b - a, 1.85), comum.p2(frente_x, (a + b) / 2, 0.15), "Mat_Plastico_Azul")
        lote.caixa((0.06, zb - za, 0.04), comum.p2(frente_x, (za + zb) / 2, 2.0), "Mat_Metal_Cinza")
        # Vaso sanitário no fundo, de frente para o oeste, e papel higiênico
        lote.cilindro(0.2, 0.42, comum.p2(59.35, ez, 0.0), "Mat_Louca_Branca", lados=10)
        lote.caixa((0.18, 0.42, 0.38), comum.p2(59.7, ez, 0.42), "Mat_Louca_Branca")
        lote.cilindro(0.05, 0.1, comum.p2(59.3, ez + 0.5, 0.6), "Mat_Papel_Branco", rot=(90, 0, 0), lados=8)
        if i == 1:
            lote.tubo([comum.p2(59.3, ez + 0.5, 0.55), comum.p2(59.0, ez + 0.4, 0.01), comum.p2(58.4, ez + 0.2, 0.01)],
                      0.03, "Mat_Papel_Branco", lados=3)   # papel desenrolado até a porta
        cab = lote.objeto(nome, col, origem)
        for k, (a, b) in enumerate(((za, p0), (p1, zb))):
            c = comum.colisao_caixa(f"{nome}_Frente_{k + 1}", (0.06, b - a, 2.0), comum.p2(frente_x, (a + b) / 2, 0.0), col)
            comum.parentar(c, cab)
        if i < len(divisorias):
            c = comum.colisao_caixa(f"{nome}_Divisoria", (fundo_x - frente_x, 0.06, 2.0),
                                    comum.p2(cx, divisorias[i], 0.0), col)
            comum.parentar(c, cab)
        # Porta: origem na dobradiça (z = p0), folha indo para +z da planta (-Y do Blender)
        porta = Lote()
        porta.caixa((0.03, largura_porta - 0.04, 1.7), (0, -(largura_porta / 2), 0.22), "Mat_Plastico_Azul")
        porta.caixa((0.05, 0.03, 0.08), (-0.03, -(largura_porta - 0.1), 1.0), "Mat_Metal_Cinza")
        porta_obj = porta.objeto(nome + "_Porta", col)
        porta_obj.location = comum.p2(frente_x, p0, 0.0)
        porta_obj.rotation_euler = (0, 0, math.radians(aberturas[i]))
        comum.parentar(porta_obj, cab)
        marcador(f"Esconderijo__cabine_{i + 1:02d}", col, ex, ez, 0.0)
    # Pichação infantil num painel da cabine 3 (decal de giz e um coraçãozinho desenhado)
    decal("giz_cera", col, 57.7, 12.9, 0.5, 0.5, parede="leste", h=1.1)


def banheiros(col):
    teto = 3.0
    pias_espelho(col)
    mictorios(col)
    cabines(col)
    # Secador de mãos e lixeira transbordando de papel-toalha
    sec = caixas("Secador_Maos", [((0.3, 0.2, 0.28), (0, -0.1, 0))], "Mat_Metal_Cinza", col)
    bico = caixas("Secador_Maos_Bico", [((0.08, 0.08, 0.06), (0, -0.14, -0.05))], "Mat_Metal_Escuro", col)
    montar(sec, [bico], 52.12, 12.75, 1.15, "leste")
    lixo = Lote()
    lixo.cilindro(0.2, 0.55, comum.p2(52.45, 13.6, 0.0), "Mat_Metal_Escuro", lados=10)
    for k in range(9):
        lixo.esfera(0.06, comum.p2(52.45 + SORTE.uniform(-0.15, 0.15), 13.6 + SORTE.uniform(-0.15, 0.15), 0.58 + k * 0.025),
                    "Mat_Papel_Toalha", seg=5, aneis=4)
    for k in range(7):
        lixo.esfera(0.05, comum.p2(52.6 + SORTE.uniform(0, 0.8), 13.3 + SORTE.uniform(0, 0.8), 0.03),
                    "Mat_Papel_Toalha", escala=(1.2, 1.0, 0.6), seg=5, aneis=4)
    # Placa "CUIDADO: PISO MOLHADO" tombada e rolos de papel no chão
    lixo.caixa((0.3, 0.6, 0.02), comum.p2(55.3, 11.2, 0.02), "Mat_Plastico_Amarelo", rot=(0, 0, 35))
    lixo.caixa((0.3, 0.6, 0.02), comum.p2(55.25, 11.25, 0.04), "Mat_Plastico_Amarelo", rot=(0, 0, 41))
    lixo.cilindro(0.05, 0.1, comum.p2(56.4, 13.8, 0.05), "Mat_Papel_Branco", rot=(90, 0, 60), lados=8)
    lixo.cilindro(0.05, 0.1, comum.p2(54.0, 9.6, 0.05), "Mat_Papel_Branco", rot=(90, 0, 10), lados=8)
    lixo.objeto("Lixo_Banheiros", col, comum.p2(55.0, 12.0, 0.0))
    comum.colisao_caixa("Lixeira_Banheiros", (0.42, 0.42, 0.6), comum.p2(52.45, 13.6, 0.0), col)
    aviso = texto("Placa_Piso_Molhado_Texto", "CUIDADO\nPISO MOLHADO", 0.05, "Mat_Texto_Preto", col,
                  comum.p2(55.25, 11.25, 0.064), largura_max=0.26, fonte_chave="Bungee", deitado=True)
    aviso.rotation_euler = (0, 0, math.radians(41))  # mesmo giro da placa de cima, 4 mm acima dela
    # Fluorescente piscando (um tubo caído pendurado pelo fio)
    flu = Lote()
    b = comum.p2(55.2, 12.0, teto)
    flu.caixa((0.3, 1.3, 0.06), b - V((0, 0, 0.06)), "Mat_Metal_Escuro")
    flu.cilindro(0.015, 1.2, b - V((-0.06, -0.6, 0.08)), "Mat_Lampada_Fluorescente", rot=(90, 0, 0), lados=6)
    flu.tubo([b - V((0.06, -0.55, 0.08)), b - V((0.06, -0.3, 0.5)), b - V((0.06, 0.1, 0.85))], 0.015,
             "Mat_Lampada_Fluorescente", lados=6)
    flu.tubo([b - V((0.06, -0.6, 0.06)), b - V((0.04, -0.62, 0.3)), b - V((0.06, -0.55, 0.08))], 0.004,
             "Mat_Plastico_Preto", lados=3)
    flu.objeto("Fluorescente_Banheiros", col, b)
    marcador("Luz__fluorescente_02", col, 55.2, 12.0, teto - 0.12)
    # Placa menino/menina estilizada, no lado de fora da parede da porta (virada para o corredor)
    placa = caixas("Placa_Banheiros", [((0.5, 0.025, 0.48), (0, 0.0, -0.08))], "Mat_Plastico_Branco", col)
    fig = Lote()
    fig.cilindro(0.045, 0.01, (-0.12, -0.02, 0.3), "Mat_Plastico_Azul", rot=(90, 0, 0), lados=10)
    fig.caixa((0.1, 0.01, 0.13), (-0.12, -0.016, 0.12), "Mat_Plastico_Azul")
    fig.caixa((0.03, 0.01, 0.08), (-0.145, -0.016, 0.04), "Mat_Plastico_Azul")
    fig.caixa((0.03, 0.01, 0.08), (-0.095, -0.016, 0.04), "Mat_Plastico_Azul")
    fig.cilindro(0.045, 0.01, (0.12, -0.02, 0.3), "Mat_Plastico_Rosa", rot=(90, 0, 0), lados=10)
    fig.poligono([(0.05, -0.027, 0.06), (0.19, -0.027, 0.06), (0.12, -0.027, 0.25)], "Mat_Plastico_Rosa")
    fig.caixa((0.02, 0.01, 0.06), (0.1, -0.016, 0.0), "Mat_Plastico_Rosa")
    fig.caixa((0.02, 0.01, 0.06), (0.14, -0.016, 0.0), "Mat_Plastico_Rosa")
    fig.caixa((0.008, 0.01, 0.3), (0.0, -0.016, 0.05), "Mat_Plastico_Preto")
    montar(placa, [fig.objeto("Placa_Banheiros_Figuras", col),
                   texto("Placa_Banheiros_Texto", "BANHEIROS", 0.05, "Mat_Texto_Preto", col, (0, -0.016, -0.04),
                         largura_max=0.4, fonte_chave="Fredoka")], 54.6, 16.115, 1.75, "sul")
    # Pichação infantil inocente na parede norte, perto do chão (giz de cera)
    desenho = Lote()
    sol = comum.p2(56.6, 8.115, 0.75)
    for k in range(8):
        a = 2 * math.pi * k / 8
        desenho.tubo([sol + V((0.09 * math.cos(a), -0.002, 0.09 * math.sin(a))),
                      sol + V((0.15 * math.cos(a), -0.002, 0.15 * math.sin(a)))], 0.006, "Mat_Plastico_Amarelo", lados=3)
    desenho.tubo([sol + V((0.07 * math.cos(2 * math.pi * k / 10), -0.002, 0.07 * math.sin(2 * math.pi * k / 10)))
                  for k in range(10)], 0.006, "Mat_Plastico_Amarelo", lados=3, fechado=True)
    desenho.objeto("Pichacao_Sol", col, sol)
    # A fonte GochiHand não tem o "♥" (o Blender desenhava um espaço vazio): o coração agora é
    # desenhado com um tubo de giz, ao lado do texto.
    montar(texto("Pichacao_Texto", "EU AMO\nA PIPOCA", 0.09, "Mat_Giz_Rosa", col, (0, 0, 0), largura_max=0.46,
                 fonte_chave="Gochi"), [], 55.9, 8.122, 0.75, "sul", -4)
    coracao = Lote()
    pontos = []
    for k in range(24):
        t = 2 * math.pi * k / 24
        hx = 16 * math.sin(t) ** 3
        hz = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pontos.append((hx * 0.0045, -0.004, hz * 0.0045))
    coracao.tubo(pontos, 0.006, "Mat_Giz_Rosa", lados=3, fechado=True)
    montar(coracao.objeto("Pichacao_Coracao", col), [], 56.25, 8.12, 0.66, "sul", -4)
    montar(texto("Pichacao_Texto_02", "TITO = MEU\nMELHOR AMIGO", 0.07, "Mat_Giz_Azul", col, (0, 0, 0), largura_max=0.45,
                 fonte_chave="Gochi"), [], 57.76, 12.9, 1.05, "oeste", 3)
    decal("giz_cera", col, 56.2, 8.1, 1.2, 0.8, parede="norte", h=0.7)
    decal("giz_cera", col, 52.1, 14.4, 0.8, 0.6, parede="oeste", h=0.6)
    decal("rachadura", col, 59.9, 15.2, 0.8, 1.0, parede="leste", h=1.8)
    decal("mancha_agua", col, 57.2, 12.6, 0.8, 1.2)
    decal("mancha_agua", col, 52.5, 15.5, 0.8, 0.8)
    forro_caido("Forro_Caido_Banheiros", col, 54.6, 14.0, 40, teto)
    teias("Teias_Banheiros", col, [(52.12, 8.12, 1, 1), (59.88, 15.88, -1, -1), (52.12, 15.88, 1, -1)], teto)


# ---------------------------------------------------------------------------
# Conferências e principal
# ---------------------------------------------------------------------------

def contar_triangulos():
    total = 0
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and not obj.name.endswith("-colonly"):
            total += sum(len(p.vertices) - 2 for p in obj.data.polygons)
    return total


def conferir_teto():
    """Nada passa do pé-direito do cômodo (com 2 cm de folga)."""
    alturas = {c[0]: c[6] for c in planta_v2.COMODOS}
    erros = []
    for col_nome in COMODOS_GRUPO:
        teto = alturas[col_nome]
        for obj in bpy.data.collections[col_nome].all_objects:
            if obj.type != "MESH":
                continue
            topo = max((obj.matrix_world @ V(c)).z for c in obj.bound_box)
            if topo > teto + 0.02:
                erros.append(f"{obj.name} passa do teto ({topo:.2f} > {teto})")
    return erros


def gerar():
    comum.limpar_cena()
    for nome, (cor, em) in CORES_DIVERSAO.items():
        comum.material(nome, cor, em)
    deixar_transparente("Mat_Vidro_Vitrine", 0.25)
    deixar_transparente("Mat_PVC_Tiras", 0.45)

    cols = {nome: comum.colecao(nome) for nome in COMODOS_GRUPO}
    col_disj = comum.colecao(COLECAO_DISJUNTORES)

    fliperama(cols["Fliperama"])
    cozinha(cols["Cozinha"], col_disj)
    camara_fria(cols["Camara_Fria"])
    banheiros(cols["Banheiros"])

    bpy.context.view_layer.update()
    problemas = comum.conferir_areas_livres_v2(permitidos=("Arcade_", "Maquina_Garra", "Skee_Ball", "Balcao_Premios"))
    problemas += conferir_teto()
    for p in problemas:
        print("PROBLEMA:", p)
    if problemas:
        raise RuntimeError(f"{len(problemas)} problema(s) de área livre/teto; veja acima.")
    print("[diversao] áreas livres OK")

    objetos = list(bpy.context.scene.objects)
    tri = contar_triangulos()
    vazios = [o for o in objetos if o.type == "EMPTY"]
    print(f"[diversao] objetos: {len(objetos)} ({len(vazios)} Empties, "
          f"{sum(1 for o in objetos if o.name.endswith('-colonly'))} colisões)")
    print(f"[diversao] triângulos: {tri}")
    if tri > 55000:  # o coordenador liberou até 55 mil neste arquivo (o fliperama é cheio de máquinas)
        raise RuntimeError("Passou de 55 mil triângulos; simplifique.")

    comum.salvar_blend(comum.PASTA_BLENDER / "v2_diversao.blend")
    comum.exportar_glb(comum.PASTA_CENARIO / "v2_diversao.glb")


if __name__ == "__main__":
    gerar()
