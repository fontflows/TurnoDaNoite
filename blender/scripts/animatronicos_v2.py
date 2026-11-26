"""
animatronicos_v2.py — design v2 do Tito e da Pipoca (docs: ANIMATRONICOS_V2_CORRECOES.md).

O que muda em relação à v1 (animatronicos_finais.py, que continua gerando a v1 para comparação):
  - O corpo é UM volume contínuo (metaballs: as formas se fundem com transições suaves), depois
    reduzido (decimate) e só então CORTADO nas juntas. Em cada junta: a peça de cima abraça a de
    baixo (alarga um pouco perto do corte), bainha gasta na borda e fresta de 1 a 3 cm mostrando o
    metal. Cada pedaço continua rígido e preso no seu osso.
  - Rosto: globo ocular de verdade (esclera, íris que brilha e pupila) encaixado numa órbita
    esculpida na máscara, pálpebras em meia-casca, sobrancelhas, focinho com volume, bochechas,
    mandíbula separada com dobradiças de metal nos cantos da boca e dentes de plástico, e uma
    costura entre a máscara e a cabeça.
  - Sinais de animatrônico: placa de acesso com rebites nas costas do Tito, cabos saindo de uma
    fenda atrás da orelha do Tito, zíper nas costas da Pipoca, rasgo com cabos na coxa da Pipoca,
    arame na orelha dobrada da Pipoca.

O endoesqueleto e as juntas continuam os originais (blender/endoesqueleto/animatronic.blend,
que não é alterado). Saída: blender/personagens/<nome>_final.blend.

Rodar (na pasta TurnoDaNoite):
    blender --background --factory-startup --python blender/scripts/animatronicos_v2.py -- tito renders=<pasta>
    blender --background --factory-startup --python blender/scripts/animatronicos_v2.py -- pipoca renders=<pasta>
"""

import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import endoesqueleto as E  # noqa: E402
import animatronicos_finais as A  # noqa: E402
from animatronicos_finais import (CIMA, FRENTE, TEXA, Montador, adicionar_osso, base_osso, capsula,  # noqa: E402
                                  caixa, elipsoide, material, torno, tubo, uv_caixa)

K = 1 / 0.575  # raio do metaball para a superfície ter o raio pedido (calibrado: rigidez 2, limiar 0,6)

# Proporções v2 (comprimento, grossura) por osso. Tito: braços compridos até o quadril, pernas curtas
# e grossas. A mandíbula gira mais para a frente (dobradiça nos cantos da boca).
PROPORCOES_V2 = {
    "tito": {"quadril": (1.0, 1.45), "tronco": (1.0, 1.0), "pescoco": (0.95, 1.3), "cabeca": (1.28, 1.48),
             "braco": (1.18, 1.3), "antebraco": (1.12, 1.3), "mao": (0.95, 1.4),
             "coxa": (0.78, 1.35), "canela": (0.7, 1.35), "pe": (1.0, 1.4)},
    "pipoca": {"quadril": (1.0, 0.9), "tronco": (1.0, 0.72), "pescoco": (1.55, 0.85), "cabeca": (0.98, 0.98),
               "braco": (1.25, 0.82), "antebraco": (1.3, 0.82), "mao": (1.1, 0.85),
               "coxa": (1.3, 0.85), "canela": (1.38, 0.85), "pe": (1.2, 0.85)},
}
E.JUNTAS["mandibula"] = ((0, 0.5, 9.12), (0, 1.2, 9.0))


# ---------------------------------------------------------------------------------------------
# Volume com metaballs

class Massa:
    """Um volume orgânico: várias formas que se fundem suavemente (metaballs) e viram malha."""
    contador = 0

    def __init__(self, resolucao=0.011):
        Massa.contador += 1
        nome = f"Massa{Massa.contador}x"  # nomes sem ponto: metaballs de mesmo nome-base se juntariam
        self.mb = bpy.data.metaballs.new(nome)
        self.mb.resolution = resolucao
        self.mb.render_resolution = resolucao
        self.mb.threshold = 0.6
        self.ob = bpy.data.objects.new(nome, self.mb)
        bpy.context.scene.collection.objects.link(self.ob)

    def _el(self, tipo, c, R, neg):
        el = self.mb.elements.new(type=tipo)
        el.co = c
        el.radius = R
        el.stiffness = 2.0
        el.use_negative = neg
        return el

    def bola(self, c, r, neg=False):
        self._el("BALL", Vector(c), r * K, neg)

    def elipse(self, c, rx, ry, rz, eixos=None, neg=False):
        el = self._el("ELLIPSOID", Vector(c), K, neg)
        el.size_x, el.size_y, el.size_z = rx, ry, rz
        if eixos is not None:
            el.rotation = eixos.to_quaternion()

    def capsula(self, a, b, r, neg=False):
        a, b = Vector(a), Vector(b)
        d = b - a
        el = self._el("CAPSULE", (a + b) / 2, r * K, neg)
        el.size_x = d.length / 2
        el.rotation = Vector((1, 0, 0)).rotation_difference(d.normalized())

    def tubo(self, pontos):
        """Tubo afunilado [(ponto, raio)]: bolas próximas (o raio é compensado: bolas juntas engordam)."""
        for i in range(len(pontos) - 1):
            (p0, r0), (p1, r1) = pontos[i], pontos[i + 1]
            n = max(1, int((p1 - p0).length / (0.4 * min(r0, r1))))
            ultimo = i == len(pontos) - 2
            for k in range(n + (1 if ultimo else 0)):
                t = k / n
                self.bola(p0.lerp(p1, t), (r0 + (r1 - r0) * t) * 0.86)

    def malha(self, tris_alvo):
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(self.ob.evaluated_get(deps))
        bpy.data.objects.remove(self.ob)
        bpy.data.metaballs.remove(self.mb)
        ob = bpy.data.objects.new("tmp_massa", me)
        bpy.context.scene.collection.objects.link(ob)
        ntris = sum(len(p.vertices) - 2 for p in me.polygons)
        if ntris > tris_alvo * 1.15:
            dec = ob.modifiers.new("reduzir", "DECIMATE")
            dec.ratio = tris_alvo / ntris
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(deps))
        bm = bmesh.new()
        bm.from_mesh(me2)
        bpy.data.objects.remove(ob)
        bpy.data.meshes.remove(me)
        bpy.data.meshes.remove(me2)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return bm


# ---------------------------------------------------------------------------------------------
# Cortes nas juntas, aberturas e ilhas

def cortar_juntas(bm, cortes):
    """
    cortes: dicts com p (ponto), n (direção do pai para o filho), raio (só corta perto do eixo),
    fp/ff (fresta para o lado do pai / do filho), abraca ("pai" ou "filho": quem alarga e cobre).
    """
    for c in cortes:
        p, n, R = c["p"], c["n"], c["raio"]
        # 1) a peça que abraça alarga perto do corte; a outra afina um pouco (entra na "manga")
        for v in bm.verts:
            d = (v.co - p).dot(n)
            radial = (v.co - p) - n * d
            if radial.length > R or abs(d) > 0.07:
                continue
            w = 1 - abs(d) / 0.07
            lado_pai = d < 0
            abraca = (c.get("abraca", "pai") == "pai") == lado_pai
            v.co = p + n * d + radial * (1 + (0.075 if abraca else -0.045) * w * w)
        # 2) corta nos dois planos (só perto do eixo) e apaga a faixa do meio
        for off in (-c["fp"], c["ff"]):
            q = p + n * off
            faces = [f for f in bm.faces if ((f.calc_center_median() - p) - n * (f.calc_center_median() - p).dot(n)).length < R * 1.15
                     and abs((f.calc_center_median() - q).dot(n)) < 0.06]
            if not faces:
                continue
            arestas = list({e for f in faces for e in f.edges})
            verts = list({v for f in faces for v in f.verts})
            bmesh.ops.bisect_plane(bm, geom=verts + arestas + faces, plane_co=q, plane_no=n)
        apagar = []
        for f in bm.faces:
            cc = f.calc_center_median()
            d = (cc - p).dot(n)
            if -c["fp"] < d < c["ff"] and ((cc - p) - n * d).length < R:
                apagar.append(f)
        bmesh.ops.delete(bm, geom=apagar, context="FACES")
    return bm


def ilhas(bm):
    """Separa em bmeshes, um por pedaço solto."""
    bm.faces.ensure_lookup_table()
    visto = set()
    grupos = []
    for f in bm.faces:
        if f.index in visto:
            continue
        grupo = []
        pilha = [f]
        while pilha:
            g = pilha.pop()
            if g.index in visto:
                continue
            visto.add(g.index)
            grupo.append(g.index)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in visto:
                        pilha.append(h)
        grupos.append(set(grupo))
    saida = []
    for grupo in grupos:
        b = bm.copy()
        b.faces.ensure_lookup_table()
        bmesh.ops.delete(b, geom=[b.faces[i] for i in range(len(b.faces)) if i not in grupo], context="FACES")
        bmesh.ops.delete(b, geom=[v for v in b.verts if not v.link_faces], context="VERTS")
        saida.append(b)
    return saida


def lacos_de_borda(bm):
    bordas = [e for e in bm.edges if e.is_boundary]
    visto = set()
    lacos = []
    for e in bordas:
        if e.index in visto:
            continue
        grupo = []
        pilha = [e]
        while pilha:
            a = pilha.pop()
            if a.index in visto:
                continue
            visto.add(a.index)
            grupo.append(a)
            for v in a.verts:
                for b in v.link_edges:
                    if b.is_boundary and b.index not in visto:
                        pilha.append(b)
        lacos.append(grupo)
    return lacos


def fechar_aberturas(bm, para_dentro, mat_bainha, mat_forro, profundidade=0.02, bainha=0.006):
    """
    Fecha cada abertura com acabamento de fantasia: uma bainha (borda enrolada, gasta) e um fundo
    escuro afundado. Pelo vão entre a borda e o fundo aparece o metal que passa pela junta.
    para_dentro(centro_do_laco) -> direção para dentro da peça.
    """
    for laco in lacos_de_borda(bm):
        verts = list({v for e in laco for v in e.verts})
        centro = sum((v.co for v in verts), Vector()) / len(verts)
        dentro = para_dentro(centro)
        # bainha: um anel um pouco para fora e para dentro (rolinho)
        r = bmesh.ops.extrude_edge_only(bm, edges=laco)
        novos = [g for g in r["geom"] if isinstance(g, bmesh.types.BMVert)]
        for v in novos:
            radial = v.co - centro
            radial -= dentro * radial.dot(dentro)
            v.co += radial.normalized() * bainha * 0.5 + dentro * bainha
        for f in [g for g in r["geom"] if isinstance(g, bmesh.types.BMFace)]:
            f.material_index = mat_bainha
        laco2 = [g for g in r["geom"] if isinstance(g, bmesh.types.BMEdge) and g.is_boundary]
        # fundo escuro afundado
        r2 = bmesh.ops.extrude_edge_only(bm, edges=laco2)
        novos2 = [g for g in r2["geom"] if isinstance(g, bmesh.types.BMVert)]
        for v in novos2:
            v.co = centro + (v.co - centro) * 0.8 + dentro * profundidade
        for f in [g for g in r2["geom"] if isinstance(g, bmesh.types.BMFace)]:
            f.material_index = mat_forro
        laco3 = [g for g in r2["geom"] if isinstance(g, bmesh.types.BMEdge) and g.is_boundary]
        rf = bmesh.ops.holes_fill(bm, edges=laco3, sides=0)
        for f in rf["faces"]:
            f.material_index = mat_forro
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)


def para_dentro_dos_cortes(cortes):
    def regra(centro):
        c = min(cortes, key=lambda c: (centro - c["p"]).length)
        return -c["n"] if (centro - c["p"]).dot(c["n"]) < 0 else c["n"]
    return regra


def distancia_segmento(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (p - (a + ab * t)).length


def costura_entre(bm, mat_a, mat_b, raio=0.0028, minimo=12):
    """Tubos (costura) nas bordas entre duas regiões de material; devolve uma bmesh com todos (ou None)."""
    arestas = {e for e in bm.edges if len(e.link_faces) == 2
               and {e.link_faces[0].material_index, e.link_faces[1].material_index} == {mat_a, mat_b}}
    visto = set()
    partes = []
    for e0 in arestas:
        if e0 in visto:
            continue
        # junta a cadeia de arestas ligadas
        cadeia = []
        pilha = [e0]
        while pilha:
            e = pilha.pop()
            if e in visto:
                continue
            visto.add(e)
            cadeia.append(e)
            for v in e.verts:
                for e2 in v.link_edges:
                    if e2 in arestas and e2 not in visto:
                        pilha.append(e2)
        if len(cadeia) < minimo:
            continue
        adj = {}
        for e in cadeia:
            a, b = e.verts
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)
        inicio = next((v for v, l in adj.items() if len(l) == 1), cadeia[0].verts[0])
        ordem = [inicio]
        usados = {inicio}
        while True:
            viz = [w for w in adj[ordem[-1]] if w not in usados]
            if not viz:
                break
            ordem.append(viz[0])
            usados.add(viz[0])
        if len(ordem) < 4:
            continue
        pts = [v.co + v.normal * 0.0025 for v in ordem]
        fechado = ordem[0] in adj[ordem[-1]]
        if fechado:
            pts.append(pts[0])
        for _ in range(4):  # suaviza (a borda entre faces é serrilhada)
            pts = [pts[0]] + [(pts[i - 1] + pts[i] * 2 + pts[i + 1]) / 4 for i in range(1, len(pts) - 1)] + [pts[-1]]
        partes.append(tubo(pts, raio, 5))
    return A.juntar(*partes) if partes else None


def fora_do_volume(bm, pontos):
    """Quantos pontos ficam fora do volume (para conferir se a fantasia cobre o metal)."""
    arvore = BVHTree.FromBMesh(bm)
    fora = []
    for p in pontos:
        achado = arvore.find_nearest(p)
        if achado[0] is not None and (p - achado[0]).dot(achado[1]) > 0.002:
            fora.append(p)
    return fora


def na_superficie(bm, origem, direcao):
    """Ponto e normal onde um raio (de dentro para fora) encontra a superfície."""
    arvore = BVHTree.FromBMesh(bm)
    longe = origem + direcao.normalized() * 3.0
    hit = arvore.ray_cast(longe, -direcao.normalized())
    if hit[0] is None:
        return origem, direcao.normalized()
    return hit[0], hit[1]


# ---------------------------------------------------------------------------------------------
# Montagem

NOMES_PECAS = {"quadril": "Quadril", "tronco": "Tronco", "pescoco": "Pescoco", "braco": "Braco", "antebraco": "Antebraco",
               "coxa": "Coxa", "canela": "Canela"}


class MontadorV2(Montador):
    def B(self, n):
        """(cabeça, cauda, comprimento, u, lado, frente) do osso NA POSE ATUAL, no mundo."""
        pb = self.arm.pose.bones[n]
        h, t = self.arm.matrix_world @ pb.head, self.arm.matrix_world @ pb.tail
        u = (t - h).normalized()
        return (h, t, (t - h).length) + base_osso(u)

    def eixo_cima(self, n):
        """Eixo Z do osso na pose atual (nos braços, na pose T, é "para cima": a palma fica do lado oposto)."""
        pb = self.arm.pose.bones[n]
        return (self.arm.matrix_world.to_3x3() @ pb.matrix.to_3x3() @ Vector((0, 0, 1))).normalized()

    def pecas_de_volume(self, bm, cortes, ossos_permitidos, nome_base, mats, casca_ossos=(), nomes=None,
                        para_dentro=None, profundidade=0.02):
        """Corta o volume nas juntas, separa os pedaços, fecha as aberturas e prende cada um no seu osso."""
        cortar_juntas(bm, cortes)
        segs = {n: (self.B(n)[0], self.B(n)[1]) for n in ossos_permitidos}
        criados = {}
        for b in ilhas(bm):
            if len(b.faces) < 30:
                b.free()
                continue
            centro = sum((v.co for v in b.verts), Vector()) / len(b.verts)
            osso = min(segs, key=lambda n: distancia_segmento(centro, *segs[n]))
            print(f"[v2]   pedaço -> {osso} ({len(b.faces)} faces)")
            fechar_aberturas(b, para_dentro or para_dentro_dos_cortes(cortes), mat_bainha=2, mat_forro=3,
                             profundidade=profundidade)
            nome = (nomes or {}).get(osso) or NOMES_PECAS.get(osso.split(".")[0], osso) + (
                "" if "." not in osso else ("_Esq" if osso.endswith(".L") else "_Dir"))
            ob = self.peca(f"{self.N}_{nome}", b, mats, osso, casca=0.012 if osso in casca_ossos else 0.0)
            criados[osso] = ob
        return criados


def materiais_v2(chave):
    N = A.PERSONAGENS[chave]["Nome"]
    # Olhos como nas artes do jogo: Tito âmbar, Pipoca ciano (criados antes, com o nome que A.materiais usa)
    if chave == "pipoca":
        material(f"Mat_Olho_{N}", cor=(0.2, 0.95, 1.0), emissao=(0.1, 0.85, 1.0), forca_emissao=3.0, aspereza=0.15)
    else:
        material(f"Mat_Olho_{N}", cor=(1.0, 0.5, 0.05), emissao=(1.0, 0.42, 0.02), forca_emissao=3.0, aspereza=0.15)
    M = A.materiais(chave)
    M["sobrancelha"] = material(f"Mat_{N}_Sobrancelha", img_cor=TEXA / f"sobrancelha_{chave}_cor.jpg",
                                img_normal=TEXA / "pelucia_normal.jpg", aspereza=0.7)
    M["linha"] = material("Mat_Animatronico_Costura", cor=(0.12, 0.09, 0.07), aspereza=0.9)
    M["placa"] = material("Mat_Animatronico_Placa", img_cor=TEXA / "metal_escuro_cor.jpg", metal=0.8, aspereza=0.5)
    M["cabo_vermelho"] = material("Mat_Endo_Cabo_Vermelho", cor=(0.6, 0.06, 0.04), aspereza=0.5)
    M["cabo_amarelo"] = material("Mat_Endo_Cabo_Amarelo", cor=(0.75, 0.6, 0.08), aspereza=0.5)
    M["cabo_preto"] = material("Mat_Endo_Cabo_Preto", cor=(0.03, 0.03, 0.03), aspereza=0.5)
    clara = "plastico_creme" if chave == "tito" else "plastico_branco"
    M["plastico_sujo"] = material(f"Mat_{N}_Plastico_Gasto", img_cor=TEXA / f"{clara}_sujo_cor.jpg", aspereza=0.45)
    M["plastico_sujo"]["metros_por_repeticao"] = 0.5
    if chave == "pipoca":
        tec = dict(img_normal=A.TEX / "tecido" / "tecido_normal.jpg", aspereza=0.75, brilho_tecido=0.7)
        M["tutu_sujo"] = material("Mat_Pipoca_Tutu_Gasto", img_cor=TEXA / "tutu_sujo_cor.jpg", **tec)
        M["tutu_sujo"]["metros_por_repeticao"] = 0.4
    M["linha"]["metros_por_repeticao"] = 0.3
    M["sobrancelha"]["metros_por_repeticao"] = 0.3
    M["placa"]["metros_por_repeticao"] = 0.3
    return M


def olho_globo(mt, lado, r, c, iris_graus=40, pupila_graus=17):
    """Globo ocular de verdade: esfera com o polo para a frente; íris e pupila são anéis em volta do polo."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=18, radius=r)
    gira = Matrix.Rotation(math.radians(90), 3, "X")  # polo +Z -> frente (−Y)
    for v in bm.verts:
        v.co = c + gira @ v.co
    for f in bm.faces:
        d = (f.calc_center_median() - c).normalized()
        ang = math.degrees(math.acos(max(-1, min(1, d.dot(FRENTE)))))
        f.material_index = 2 if ang < pupila_graus else (1 if ang < iris_graus else 0)
    nl = "Esq" if lado == "L" else "Dir"
    return mt.peca(f"{mt.N}_Olho_{nl}", bm, [mt.M["olho"], mt.M["iris"], mt.M["pupila"]], f"olho.{lado}")


def palpebra(mt, lado, r, c, qual, borda_z, mat="pelo"):
    """Meia-casca em volta do globo: a de cima cobre do alto até borda_z (em fração do raio)."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=28, v_segments=16, radius=r * 1.12)
    for v in bm.verts:
        v.co += c
    apagar = []
    for f in bm.faces:
        d = (f.calc_center_median() - c) / (r * 1.12)
        manter = (d.z > borda_z) if qual == "sup" else (d.z < borda_z)
        if not manter or d.y > 0.35:
            apagar.append(f)
    bmesh.ops.delete(bm, geom=apagar, context="FACES")
    nl = "Esq" if lado == "L" else "Dir"
    return mt.peca(f"{mt.N}_Palpebra_{qual.capitalize()}_{nl}", bm, [mt.M[mat]], f"palpebra_{qual}.{lado}", casca=0.006)


def rosto(mt, cfg):
    """
    Cabeça + máscara num volume só (crânio, bochechas, focinho, testa), órbitas esculpidas para os
    olhos, boca aberta onde entra a mandíbula, costura da máscara, dentes de plástico, dobradiças.
    """
    M = mt.M
    olhos = {}
    for lado in ("L", "R"):
        ps = mt.pontos_endo(f"olho.{lado}")
        oc = sum(ps, Vector()) / len(ps)
        r = (max(p.x for p in ps) - min(p.x for p in ps)) / 2
        olhos[lado] = (oc, r)
    oL, r_o = olhos["L"]
    dsup = A._pontos_material(mt, "cabeca", "Mat_Animatronico_Dentes")
    dinf = A._pontos_material(mt, "mandibula", "Mat_Animatronico_Dentes")
    mand_mn, mand_mx = mt.caixa_endo(["mandibula"])
    z_dsup = (min(p.z for p in dsup), max(p.z for p in dsup))
    z_dinf = (min(p.z for p in dinf), max(p.z for p in dinf))
    y_dentes = min(p.y for p in dsup + dinf)
    x_dentes = max(abs(p.x) for p in dsup + dinf)
    W = abs(oL.x) + r_o  # meia-largura dos olhos
    Rx, Ry, Rz = W * cfg["cranio"][0], W * cfg["cranio"][1], W * cfg["cranio"][2]
    cz = oL.z - Rz * cfg["olhos_acima"]
    # o crânio passa pelo olho deixando 'saltado' do globo para fora
    k = 1 - (oL.x / Rx) ** 2 - ((oL.z - cz) / Rz) ** 2
    cy = (oL.y - r_o * (1 - cfg["saltado"])) + Ry * math.sqrt(max(0.05, k))
    c = Vector((0, cy, cz))

    def frente_y(x, z):
        kk = 1 - (x / Rx) ** 2 - ((z - c.z) / Rz) ** 2
        return c.y - Ry * math.sqrt(max(0.0, kk))

    m = Massa(0.011)
    m.elipse(c, Rx, Ry, Rz)
    # focinho com volume, saindo do rosto
    fz = z_dsup[1] + cfg["focinho"][2] * W * 0.55
    fr = (cfg["focinho"][0] * W, cfg["focinho"][1] * W, cfg["focinho"][2] * W)
    fc = Vector((0, frente_y(0, fz) + fr[1] * (1 - cfg["focinho_sai"]), fz))
    m.elipse(fc, *fr)
    # bochechas cheias
    for sx in (-1, 1):
        bx = sx * cfg["bochecha"][0] * W
        bz = fz + cfg["bochecha"][1] * W
        m.bola(Vector((bx, frente_y(bx, bz) + cfg["bochecha"][2] * W * 0.55, bz)), cfg["bochecha"][2] * W)
    # testa/arco das sobrancelhas: leve volume acima dos olhos
    for lado, (oc, r) in olhos.items():
        m.elipse(Vector((oc.x, oc.y + r * 0.35, oc.z + r * 1.05)), r * 0.95, r * 0.6, r * 0.35)
    # órbitas: o volume é escavado em volta do globo (o olho fica rente/saltado, com uma folga escura)
    for lado, (oc, r) in olhos.items():
        m.bola(oc, r * 1.07, neg=True)
    bm = m.malha(cfg["tris_cabeca"])
    # materiais por região: 0 pelo, 1 focinho (plástico), 2 pelo sujo (bainha), 3 forro, 4 bochecha
    for f in bm.faces:
        p = f.calc_center_median()
        dfoc = ((p.x - fc.x) / (fr[0] * 1.12)) ** 2 + ((p.z - fc.z) / (fr[2] * 1.2)) ** 2
        if dfoc < 1.0 and p.y < c.y - Ry * 0.55:
            # centro limpo; borda do focinho e perto da boca um pouco encardidos
            f.material_index = 5 if (dfoc > 0.6 or p.z < z_dsup[1] + 0.03) else 1
        elif cfg.get("bochecha_rosa"):
            for sx in (-1, 1):
                bx = sx * cfg["bochecha"][0] * W * 1.05
                if (Vector((bx, p.y, fz + cfg["bochecha"][1] * W)) - p).length < cfg["bochecha"][2] * W * 0.75 and p.y < c.y - Ry * 0.4:
                    f.material_index = 4
    # boca: abre onde a mandíbula entra (dos dentes de cima até o queixo)
    larg_boca = max(x_dentes + 0.012, fr[0] * 0.78)
    z_boca0, z_boca1 = mand_mn.z - 0.012, z_dsup[0] + 0.004
    # cortes retos antes de abrir a boca (bordas limpas)
    for co, no in ((Vector((0, 0, z_boca0)), CIMA), (Vector((0, 0, z_boca1)), CIMA),
                   (Vector((larg_boca, 0, 0)), Vector((1, 0, 0))), (Vector((-larg_boca, 0, 0)), Vector((1, 0, 0)))):
        frente_faces = [f for f in bm.faces if f.calc_center_median().y < c.y - Ry * 0.25]
        geo = list({v for f in frente_faces for v in f.verts}) + list({e for f in frente_faces for e in f.edges}) + frente_faces
        bmesh.ops.bisect_plane(bm, geom=geo, plane_co=co, plane_no=no)
    apagar = [f for f in bm.faces if abs(f.calc_center_median().x) < larg_boca
              and z_boca0 < f.calc_center_median().z < z_boca1 and f.calc_center_median().y < c.y - Ry * 0.25]
    bmesh.ops.delete(bm, geom=apagar, context="FACES")
    # pescoço: abertura embaixo
    rp = cfg["pescoco_r"]
    apagar = [f for f in bm.faces if f.calc_center_median().z < c.z - Rz * 0.72
              and math.hypot(f.calc_center_median().x, f.calc_center_median().y - c.y) < rp * 1.1]
    bmesh.ops.delete(bm, geom=apagar, context="FACES")

    def dentro_cabeca(centro):
        if centro.z < c.z - Rz * 0.6:
            return CIMA.copy()
        return -FRENTE  # boca: para trás
    costura = costura_entre(bm, 0, 5)
    if costura:
        mt.peca(f"{mt.N}_Costura_Focinho", costura, [M["linha"]], "cabeca")
    fechar_aberturas(bm, dentro_cabeca, 2, 3, profundidade=0.05, bainha=0.005)
    mats = [M["pelo"], M["plastico"], M["pelo_sujo"], M["forro"], M["bochecha"], M["plastico_sujo"]]
    bm_copia = bm.copy()
    mt.peca(f"{mt.N}_Cabeca", bm, mats, "cabeca")
    # olhos, pálpebras e sobrancelhas
    for lado, (oc, r) in olhos.items():
        olho_globo(mt, lado, r * 1.02, oc)
        palpebra(mt, lado, r * 1.02, oc, "sup", cfg["palpebra_sup"])
        palpebra(mt, lado, r * 1.02, oc, "inf", cfg["palpebra_inf"])
        sx = 1 if oc.x > 0 else -1
        arco = []
        for i in range(7):
            t = i / 6
            ang = math.radians(-60 + 120 * t)
            x = oc.x + sx * math.sin(ang) * r * 0.95
            z = oc.z + r * (1.25 + cfg["sobrancelha_arco"] * math.cos(ang)) + cfg["sobrancelha_inclina"] * sx * (x - oc.x)
            pnt, nrm = na_superficie(bm_copia, Vector((x, c.y, z)), Vector((0, -1, 0)))
            arco.append(pnt + nrm * 0.004)
        ms = Massa(0.0035)
        for i in range(6):
            rr = cfg["sobrancelha_r"] * (0.55 + 0.45 * math.sin(math.pi * ((i + 0.5) / 6)))
            ms.capsula(arco[i], arco[i + 1], rr)
        mt.peca(f"{mt.N}_Sobrancelha_{'Esq' if lado == 'L' else 'Dir'}", ms.malha(900), [M["sobrancelha"]], "cabeca")
    # bochechas rosadas (peças lisas encostadas na máscara)
    if cfg.get("blush"):
        for sx in (-1, 1):
            bx = sx * cfg["bochecha"][0] * W * 1.08
            bz = fz + cfg["bochecha"][1] * W + 0.005
            pb_, nb_ = na_superficie(bm_copia, Vector((bx * 0.5, c.y, bz)), Vector((bx, -Ry * 0.8, bz - c.z)))
            eixb = Matrix((nb_.cross(CIMA).normalized(), nb_, CIMA)).transposed()
            mt.peca(f"{mt.N}_Bochecha_{'Esq' if sx > 0 else 'Dir'}", elipsoide(pb_, W * 0.17, 0.006, W * 0.12, eixb, 20, 8),
                    [M["bochecha"]], "cabeca")
    # nariz
    nz = fc.z + fr[2] * 0.55
    pn, nn = na_superficie(bm_copia, Vector((0, fc.y, nz)), Vector((0, -1, 0.35)))
    rn = cfg["nariz_r"] * W
    mt.peca(f"{mt.N}_Nariz", elipsoide(pn + nn * rn * 0.35, rn * 1.35, rn * 0.85, rn * 0.9, None, 20, 10), [M["nariz"]], "cabeca")
    # costura da máscara (contorna olhos, focinho e bochechas)
    pontos = []
    for i in range(41):
        ang = 2 * math.pi * i / 40
        x = math.cos(ang) * Rx * 0.86
        z = fz + 0.12 * W + math.sin(ang) * Rz * 0.78
        dirc = Vector((x, -Ry, z - c.z))
        pnt, nrm = na_superficie(bm_copia, c, dirc)
        if abs(x) < larg_boca + 0.02 and z < z_boca1 + 0.02 and pnt.y < c.y - Ry * 0.3:
            continue  # não passa pela boca
        pontos.append(pnt + nrm * 0.0015)
    if len(pontos) > 8:
        mt.peca(f"{mt.N}_Costura_Mascara", tubo(pontos, 0.0028, 5), [M["linha"]], "cabeca")
    # dentes de plástico (em cima: presos na cabeça; embaixo: na mandíbula)
    def fileira(z, osso, n, larg, alt, y_extra, nome, mat="dentes"):
        partes = []
        for i in range(n):
            t = (i + 0.5) / n
            x = (t - 0.5) * 2 * larg
            y = frente_y(x * 0.8, z) + y_extra + (x / larg) ** 2 * 0.012
            partes.append(caixa(Vector((x, y, z)), larg * 2 / n * 0.82, 0.012, alt))
        mt.peca(f"{mt.N}_{nome}", A.juntar(*partes), [M[mat]], osso, liso=False)

    y_boca = min(fr[1], 0.02)
    if cfg.get("dentinhos"):
        mt.peca(f"{mt.N}_Dentinhos", A.juntar(*[caixa(Vector((sx * larg_boca * 0.2, frente_y(0, z_boca1) + 0.02, z_boca1 - 0.02)),
                                                       larg_boca * 0.34, 0.012, 0.045) for sx in (-1, 1)]),
                [M["dentes"]], "cabeca", liso=False)
    else:
        fileira(z_boca1 - 0.01, "cabeca", 6, larg_boca * 0.85, 0.022, 0.025, "Dentes_Cima")
    # mandíbula (queixo) com o próprio volume
    mq = Massa(0.008)
    # o queixo cobre a placa de metal da mandíbula do endoesqueleto (fica na frente dela) e deixa os dentes de baixo à mostra
    zq = (z_boca0 + z_dinf[0]) / 2 - 0.004
    rq = (larg_boca * 1.04, max(fr[1] * 0.7, 0.03), (z_dinf[0] - z_boca0) * 0.62 + 0.014)
    y_frente_q = min(frente_y(0, zq), mand_mn.y) - 0.012
    mq.elipse(Vector((0, y_frente_q + rq[1], zq)), *rq)
    bq = mq.malha(900)
    mt.peca(f"{mt.N}_Queixo", bq, [M["plastico" if cfg.get("queixo_plastico", True) else "pelo"]], "mandibula")
    fileira(z_dinf[0] + 0.016, "mandibula", 6 if not cfg.get("dentinhos") else 5, larg_boca * 0.8, 0.018, 0.03, "Dentes_Baixo")
    # dobradiças de metal nos cantos da boca (no eixo da mandíbula)
    hb = mt.B("mandibula")[0]
    for sx in (-1, 1):
        ph = Vector((sx * (larg_boca + 0.004), frente_y(sx * larg_boca, hb.z) + 0.03, hb.z))
        cil = torno(ph - Vector((sx * 0.006, 0, 0)), Vector((sx, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)),
                    [(0, 0, 0), (0, 0.016, 0), (0.016, 0.016, 0), (0.02, 0.01, 0), (0.022, 0, 0)], 1, 1, 12)
        mt.peca(f"{mt.N}_Dobradica_{'Esq' if sx > 0 else 'Dir'}", cil, [M["metal_claro"]], "cabeca")
    return {"c": c, "raios": (Rx, Ry, Rz), "W": W, "bm": bm_copia, "olhos": olhos, "fz": fz}


# ---------------------------------------------------------------------------------------------
# Tito

def corpo_tito(mt):
    M = mt.M
    hq, tq, Lq, uq, sq, fq = mt.B("quadril")
    ht, tt, Lt, ut, st, ft = mt.B("tronco")
    S = abs(mt.B("braco.L")[0].x)  # meia-largura dos ombros
    m = Massa(0.024)
    # tronco em pera: barriga grande embaixo, ombros largos e redondos em cima
    m.elipse(ht + ut * (Lt * 0.3) + ft * 0.08, S * 1.3, S * 1.2, Lt * 0.5)
    m.bola(ht + ut * (Lt * 0.2) + ft * (S * 0.55), S * 0.75)          # barriga caída, para a frente
    m.elipse(ht + ut * (Lt * 0.7), S * 0.78, S * 0.66, Lt * 0.32)
    hp0 = mt.B("pescoco")[0]
    for lado in ("L", "R"):
        hb = mt.B(f"braco.{lado}")[0]
        ombro = hb - Vector((math.copysign(0.045, hb.x), 0, 0.015))
        m.bola(ombro, 0.115)
        m.capsula(hp0 - ut * 0.04, ombro, 0.085)                       # trapézio: o ombro cai do pescoço
    # quadril
    m.elipse(hq + uq * (Lq * 0.15), S * 1.0, S * 0.82, Lq * 0.9 + 0.05)
    # pescoço curto e grosso
    hp, tp, Lp, up, sp, fp = mt.B("pescoco")
    m.capsula(hp - up * 0.03, tp + up * 0.01, 0.11)
    # braços grossos e compridos, afunilando
    for lado in ("L", "R"):
        h1, t1, _L, u1, *_ = mt.B(f"braco.{lado}")
        h2, t2, *_ = mt.B(f"antebraco.{lado}")
        m.tubo([(h1, 0.125), (h1.lerp(t1, 0.5), 0.118), (t1, 0.1), (h2.lerp(t2, 0.45), 0.1), (t2 + u1 * 0.02, 0.078)])
    # pernas curtas e grossas como colunas
    for lado in ("L", "R"):
        h1, t1, *_ = mt.B(f"coxa.{lado}")
        h2, t2, *_ = mt.B(f"canela.{lado}")
        m.tubo([(h1 + Vector((0, 0, -0.02)), 0.14), (t1, 0.13), (t2 + Vector((0, 0, -0.03)), 0.125)])
    bm = m.malha(8500)
    endo = [ob.matrix_world @ v.co for ob in mt.endo if ob["osso"] in ("tronco", "quadril", "braco.L", "braco.R", "antebraco.L",
                                                                          "antebraco.R", "coxa.L", "coxa.R", "canela.L", "canela.R")
            for v in ob.data.vertices]
    fora = fora_do_volume(bm, endo)
    print(f"[v2] Tito: {len(fora)} de {len(endo)} pontos do metal fora do corpo (antes de cortar)")
    # barriga bege como parte do volume (região do material), joelhos encardidos
    cb = ht + ut * (Lt * 0.33)
    for f in bm.faces:
        p = f.calc_center_median()
        if ((p.x - cb.x) / (S * 0.98)) ** 2 + ((p.z - cb.z) / (Lt * 0.46)) ** 2 < 1 and p.y < cb.y - S * 0.35:
            f.material_index = 1
        for lado in ("L", "R"):
            joelho = mt.B(f"canela.{lado}")[0]
            if (p - joelho).length < 0.1 and p.y < joelho.y:
                f.material_index = 2
    costura = costura_entre(bm, 0, 1)
    if costura:
        mt.peca("Tito_Costura_Barriga", costura, [M["linha"]], "tronco")
    bm_ref = bm.copy()
    cortes = juntas_padrao(mt, S, quadril_desce=0.075, raio_ombro=0.18, raio_quadril=0.19, raio_joelho=0.18,
                           raio_cotovelo=0.17)
    mt.pecas_de_volume(bm, cortes, ["quadril", "tronco", "pescoco", "braco.L", "braco.R", "antebraco.L", "antebraco.R",
                                    "coxa.L", "coxa.R", "canela.L", "canela.R"], "Corpo",
                       [M["pelo"], M["claro_sujo"], M["pelo_sujo"], M["forro"]])
    return bm_ref, S


def juntas_padrao(mt, S, quadril_desce, raio_ombro, raio_quadril, raio_joelho, raio_cotovelo=None, pescoco_r=0.16):
    """Cortes nas juntas do corpo (pai -> filho)."""
    cortes = []
    ht, _tt, *_ = mt.B("tronco")
    cortes.append(dict(p=ht + Vector((0, 0, 0.02)), n=CIMA.copy(), raio=S * 1.6, fp=0.008, ff=0.008, abraca="filho"))
    hp, tp, Lp, up, *_ = mt.B("pescoco")
    cortes.append(dict(p=hp + up * 0.01, n=up, raio=pescoco_r, fp=0.008, ff=0.01))
    cortes.append(dict(p=tp - up * 0.005, n=up, raio=pescoco_r, fp=0.0, ff=0.5))  # o topo do pescoço fica aberto (cabeça à parte)
    for lado in ("L", "R"):
        hb, _tb, _Lb, ub, *_ = mt.B(f"braco.{lado}")
        cortes.append(dict(p=hb + ub * 0.035, n=ub, raio=raio_ombro, fp=0.008, ff=0.012))
        ha, ta, _La, ua, *_ = mt.B(f"antebraco.{lado}")
        cortes.append(dict(p=ha, n=ua, raio=raio_cotovelo or raio_ombro, fp=0.008, ff=0.012))
        cortes.append(dict(p=ta - ua * 0.005, n=ua, raio=raio_ombro, fp=0.0, ff=0.5))  # punho: a mão é peça à parte
        hc, _tc, _Lc, uc, *_ = mt.B(f"coxa.{lado}")
        cortes.append(dict(p=hc + uc * quadril_desce, n=uc, raio=raio_quadril, fp=0.008, ff=0.012))
        hk, tk, _Lk, uk, *_ = mt.B(f"canela.{lado}")
        cortes.append(dict(p=hk, n=uk, raio=raio_joelho, fp=0.008, ff=0.012))
        cortes.append(dict(p=tk - uk * 0.005, n=uk, raio=raio_joelho, fp=0.0, ff=0.5))  # tornozelo: o pé é peça à parte
    return cortes


GRUPOS_DEDOS = {"dedo_meio": range(9, 20), "dedo_a": range(20, 30), "dedo_b": range(30, 40), "polegar": range(40, 47)}


def _grupo_dedo(origem):
    try:
        k = int(origem.split(".")[1])
    except (IndexError, ValueError):
        return None
    return next((nome for nome, faixa in GRUPOS_DEDOS.items() if k in faixa), None)


def criar_ossos_dedos(mt):
    """
    No endoesqueleto, cada dedo é feito de segmentos (3 dedos + polegar por mão). Aqui cada dedo ganha 2 ossos
    (base e ponta) no eixo real das peças dele, e as peças passam a seguir esses ossos.
    """
    arm = mt.arm
    arm.data.pose_position = "REST"
    bpy.context.view_layer.update()
    planos = []
    for lado in ("L", "R"):
        hm = arm.matrix_world @ arm.data.bones[f"mao.{lado}"].head_local
        grupos = {}
        for ob in mt.endo:
            if ob["osso"] == f"mao.{lado}":
                g = _grupo_dedo(ob["origem"])
                if g:
                    grupos.setdefault(g, []).append(ob)
        for g, obs in grupos.items():
            cents = sorted((sum((ob.matrix_world @ v.co for v in ob.data.vertices), Vector()) / len(ob.data.vertices), i)
                           for i, ob in enumerate(obs))
            cents.sort(key=lambda c: (c[0] - hm).length)
            pts = [ob.matrix_world @ v.co for ob in obs for v in ob.data.vertices]
            b0, b1 = cents[0][0], cents[-1][0]
            d = (b1 - b0).normalized()
            proj = [(q - b0).dot(d) for q in pts]
            base, ponta = b0 + d * min(proj), b0 + d * max(proj)
            meio = base.lerp(ponta, 0.5)
            seg = []
            for c, i in cents:
                seg.append((obs[i], 1 if (c - base).dot(d) < (meio - base).dot(d) else 2))
            planos.append((lado, g, base, meio, ponta, seg))
    arm.data.pose_position = "POSE"
    for lado, g, base, meio, ponta, seg in planos:
        adicionar_osso(arm, f"{g}_1.{lado}", base, meio, f"mao.{lado}")
        adicionar_osso(arm, f"{g}_2.{lado}", meio, ponta, f"{g}_1.{lado}")
    bpy.context.view_layer.update()
    for lado, g, base, meio, ponta, seg in planos:
        for ob, k in seg:
            E.prender_no_osso(ob, arm, f"{g}_{k}.{lado}")
    print(f"[v2] ossos dos dedos: {len(planos) * 2}")


def mao_v2(mt, lado, escala=1.0, dedos=3, mat="pelo_sujo"):
    """Luva de mascote: palma (osso da mão) + cada dedo em 2 pedaços, um por osso do dedo."""
    n = f"mao.{lado}"
    h, _t, L, u, s, f = mt.B(n)
    cima = mt.eixo_cima(n)
    f = cima.cross(u).normalized()
    ps = mt.pontos_endo(n)
    A_ = max((p - h).dot(u) for p in ps)
    larg = max(abs((p - h).dot(f)) for p in ps) + 0.02
    esp = max(abs((p - h).dot(cima)) for p in ps) + 0.025
    larg, esp, A_ = larg * escala, esp * escala, A_ * escala
    m = Massa(0.0085)
    palma_c = h + u * (A_ * 0.3)
    m.elipse(palma_c, A_ * 0.36, larg * 0.85, esp * 0.82, Matrix((u, f, cima)).transposed())
    bm = m.malha(700)
    for face in bm.faces:
        p = face.calc_center_median()
        if face.normal.dot(cima) < -0.55 and ((p - palma_c).dot(u) / (A_ * 0.22)) ** 2 + ((p - palma_c).dot(f) / (larg * 0.5)) ** 2 < 1:
            face.material_index = 1  # almofada da palma
    nl = "Esq" if lado == "L" else "Dir"
    mt.peca(f"{mt.N}_Mao_{nl}", bm, [mt.M[mat], mt.M["claro_sujo"]], n)
    rd = larg * 0.36
    for g in GRUPOS_DEDOS:
        for k in (1, 2):
            osso = f"{g}_{k}.{lado}"
            if osso not in mt.arm.data.bones:
                continue
            hd, td, Ld, ud, *_ = mt.B(osso)
            r = rd * (0.95 if k == 1 else 0.88) * (1.1 if g == "polegar" else 1.0)
            md = Massa(0.0065)
            ini = hd + ud * (0.004 if k == 2 else -0.01)
            fim = td + ud * (0.012 if k == 2 else -0.004)
            md.capsula(ini, fim, r)
            bd = md.malha(260)
            if k == 2:
                for face in bd.faces:
                    if face.normal.dot(cima) < -0.5 and (face.calc_center_median() - hd).dot(ud) > Ld * 0.45:
                        face.material_index = 1  # almofadinha na ponta do dedo
            nome_d = {"dedo_meio": "Dedo_Meio", "dedo_a": "Dedo_A", "dedo_b": "Dedo_B", "polegar": "Polegar"}[g]
            mt.peca(f"{mt.N}_{nome_d}_{k}_{nl}", bd, [mt.M[mat], mt.M["claro_sujo"]], osso)


def mao_v2_antiga(mt, lado, escala=1.0, dedos=3, mat="pelo_sujo"):
    """Mão de mascote com dedos gordos (3 + polegar) e almofadinhas na palma (região de material)."""
    n = f"mao.{lado}"
    h, _t, L, u, s, f = mt.B(n)
    ps = mt.pontos_endo(n)
    cima = mt.eixo_cima(n)
    f = cima.cross(u).normalized()  # largura da mão (onde os dedos se abrem)
    A_ = max((p - h).dot(u) for p in ps)
    larg = max(abs((p - h).dot(f)) for p in ps) + 0.025
    esp = max(abs((p - h).dot(cima)) for p in ps) + 0.025
    larg, esp, A_ = larg * escala, esp * escala, A_ * escala
    m = Massa(0.0085)
    palma_c = h + u * (A_ * 0.36)
    eixos = Matrix((u, f, cima)).transposed()
    m.elipse(palma_c, A_ * 0.4, larg * 0.82, esp * 0.8, eixos)
    rd = larg / (dedos + 0.9)
    for i in range(dedos):
        off = (-1 + 2 * (i + 0.5) / dedos) * larg * 0.8
        comp = A_ * (1.12 if i == dedos // 2 else 1.02)
        m.capsula(h + u * (A_ * 0.5) + f * off * 0.85, h + u * comp + f * off * 1.1 - cima * esp * 0.2, rd * 0.95)
    # polegar (para a frente do corpo)
    pf = f if f.dot(FRENTE) > 0 else -f
    m.capsula(h + u * (A_ * 0.3) + pf * larg * 0.6, h + u * (A_ * 0.62) + pf * larg * 1.15 - cima * esp * 0.2, rd * 1.0)
    bm = m.malha(1100)
    # almofadinhas: palma e pontas dos dedos (lado de baixo na pose T = palma)
    for face in bm.faces:
        p = face.calc_center_median()
        if face.normal.dot(cima) < -0.55:
            dpalma = ((p - palma_c).dot(u) / (A_ * 0.25)) ** 2 + ((p - palma_c).dot(f) / (larg * 0.55)) ** 2
            ponta = (p - h).dot(u) > A_ * 0.78
            if dpalma < 1 or ponta:
                face.material_index = 1
    return mt.peca(f"{mt.N}_Mao_{'Esq' if lado == 'L' else 'Dir'}", bm, [mt.M[mat], mt.M["claro_sujo"]], n)


def pe_v2(mt, lado, comprimento, largura, altura, dedos=3, coelho=False):
    """Pata com sola e dedos (região de material: sola e almofadas)."""
    n = f"pe.{lado}"
    h, _t, L, u, s, f = mt.B(n)
    ps = mt.pontos_endo(n)
    a0 = min((p - h).dot(u) for p in ps) - 0.05
    a1 = max((p - h).dot(u) for p in ps) * comprimento + 0.03
    zchao = min(p.z for p in ps)
    m = Massa(0.012)
    frente_h = Vector((u.x, u.y, 0)).normalized()
    lado_h = frente_h.cross(CIMA)
    base = Vector((h.x, h.y, zchao + altura * 0.85))
    meio = base + frente_h * ((a0 + a1) / 2)
    eixos = Matrix((frente_h, lado_h, CIMA)).transposed()
    m.elipse(meio, (a1 - a0) / 2, largura, altura, eixos)
    m.bola(base + frente_h * (a0 + 0.04) + CIMA * altura * 0.4, altura * 1.05)  # calcanhar/tornozelo
    for i in range(dedos):
        off = (-1 + 2 * (i + 0.5) / dedos) * largura * 0.62
        m.bola(base + frente_h * (a1 - altura * 0.55) + lado_h * off - CIMA * altura * 0.2, altura * (0.62 if not coelho else 0.5))
    bm = m.malha(900)
    for face in bm.faces:
        if face.normal.z < -0.6:
            face.material_index = 1
    return mt.peca(f"{mt.N}_Pe_{'Esq' if lado == 'L' else 'Dir'}", bm, [mt.M["pelo_sujo"], mt.M["claro_sujo"]], n)


def acessorios_tito(mt, corpo_bm, cab):
    M = mt.M
    c, (Rx, Ry, Rz), W = cab["c"], cab["raios"], cab["W"]
    hb = cab["bm"]
    # orelhas redondas (osso próprio) no alto da cabeça
    for lado, sx in (("L", 1), ("R", -1)):
        base, nrm = na_superficie(hb, c, Vector((sx * 0.62, 0.05, 0.78)))
        dirc = (nrm + Vector((0, 0, 0.3))).normalized()
        adicionar_osso(mt.arm, f"orelha.{lado}", base - dirc * 0.02, base + dirc * W * 0.5, "cabeca")
        eix = Matrix((dirc.cross(FRENTE).normalized(), -FRENTE, dirc)).transposed()
        ce = base + dirc * W * 0.22
        nl = "Esq" if lado == "L" else "Dir"
        mt.peca(f"Tito_Orelha_{nl}", elipsoide(ce, W * 0.36, W * 0.16, W * 0.33, eix, 24, 12), [M["pelo"]], f"orelha.{lado}")
        mt.peca(f"Tito_Orelha_Dentro_{nl}", elipsoide(ce + FRENTE * W * 0.1, W * 0.22, W * 0.07, W * 0.2, eix, 20, 10),
                [M["claro"]], f"orelha.{lado}")
    # fenda atrás da orelha esquerda com cabos saindo
    pf, nf = na_superficie(hb, c, Vector((0.55, 0.7, 0.45)))
    mt.peca("Tito_Fenda_Orelha", elipsoide(pf - nf * 0.004, 0.032, 0.012, 0.014,
                                           Matrix((nf.cross(CIMA).normalized(), nf, CIMA)).transposed(), 16, 8), [M["forro"]], "cabeca")
    for i, cor in enumerate(("cabo_vermelho", "cabo_amarelo", "cabo_preto")):
        ini = pf - nf * 0.01 + Vector((0, 0, (i - 1) * 0.008))
        pts = [ini, ini + nf * 0.03 + Vector((0, 0.01, -0.01 * i)), ini + nf * 0.05 + Vector((0.01 * i, 0.03, -0.04 - 0.01 * i)),
               ini + nf * 0.045 + Vector((0.01 * i, 0.05, -0.08 - 0.012 * i))]
        mt.peca(f"Tito_Cabo_{i + 1}", tubo(pts, 0.0035, 6), [M[cor]], "cabeca")
    # chapéu de pizzaiolo (um pouco torto)
    topo, _n = na_superficie(hb, c, Vector((0.05, 0.02, 1)))
    ct = Matrix.Rotation(math.radians(-8), 3, "Y")
    uc = ct @ CIMA
    _u, sc, fc = base_osso(uc)
    topo -= uc * 0.03
    faixa = [(0.0, 0.0, 0), (0.0, W * 0.62, 0), (W * 0.34, W * 0.66, 0), (W * 0.36, 0.0, 0)]
    mt.peca("Tito_Chapeu_Faixa", torno(topo, uc, sc, fc, faixa, 1.0, 0.95), [M["chapeu_sujo"]], "cabeca")
    copa = [(W * 0.3, 0.0, 0), (W * 0.3, W * 0.6, 0), (W * 0.45, W * 0.78, 0), (W * 0.7, W * 0.86, 0),
            (W * 0.92, W * 0.78, 0), (W * 1.05, W * 0.5, 0), (W * 1.08, 0.0, 0)]
    mt.peca("Tito_Chapeu", torno(topo, uc, sc, fc, copa, 1.0, 0.95, segs=32, onda=lambda th: 1 + 0.05 * math.cos(6 * th)),
            [M["chapeu"]], "cabeca")
    # lenço xadrez e gravata-borboleta na base do pescoço (presos no tronco)
    hp, tp, Lp, up, sp, fp = mt.B("pescoco")
    base_p = hp + up * 0.0
    pr, _nr = na_superficie(corpo_bm, base_p, FRENTE)
    rg = max(abs(pr.y - base_p.y), 0.08) * 1.05
    rn = 0.125  # raio do pescoço de pelúcia
    gola = [(-0.05, 0.0, 0.0), (-0.05, rn + 0.1, 0.0), (-0.035, rn + 0.105, 0.0), (0.0, rn + 0.05, 0.0),
            (0.03, rn + 0.012, 0.0), (0.04, rn + 0.008, 0.0), (0.04, 0.0, 0.0)]
    _u, s2, f2 = base_osso(up)
    mt.peca("Tito_Lenco", torno(base_p, up, s2, f2, gola, 1.0, 0.95, segs=32), [M["lenco"]], "tronco")
    rg = rn + 0.08
    pfr, nfr = na_superficie(corpo_bm, base_p - up * 0.07, FRENTE)
    tri = bmesh.new()
    ini = pfr + nfr * 0.01
    vs = [tri.verts.new(p) for p in (ini + sp * rg * 0.55, ini - sp * rg * 0.55, ini - up * rg * 0.75 + nfr * 0.02,
                                     ini + sp * rg * 0.55 - nfr * 0.015, ini - sp * rg * 0.55 - nfr * 0.015,
                                     ini - up * rg * 0.75)]
    tri.faces.new((vs[0], vs[1], vs[2]))
    tri.faces.new((vs[5], vs[4], vs[3]))
    for a, b in ((0, 1), (1, 2), (2, 0)):
        tri.faces.new((vs[a], vs[b], vs[b + 3], vs[a + 3]))
    bmesh.ops.recalc_face_normals(tri, faces=tri.faces)
    mt.peca("Tito_Lenco_Ponta", tri, [M["lenco"]], "tronco", liso=False)
    cg = pfr + nfr * 0.035 + up * 0.03
    eixos = Matrix((sp, -nfr, up)).transposed()
    gr = rg * 0.28
    partes = [elipsoide(cg, gr * 0.38, gr * 0.35, gr * 0.38, eixos, 16, 8)]
    for sx in (-1, 1):
        rot = eixos @ Matrix.Rotation(math.radians(sx * 10), 3, "Y")
        partes.append(elipsoide(cg + sp * (sx * gr * 0.95), gr * 0.9, gr * 0.28, gr * 0.6, rot, 20, 10))
    mt.peca("Tito_Gravata", A.juntar(*partes), [M["gravata"]], "tronco")
    # placa de acesso nas costas, com rebites e fecho
    ht, tt, Lt, ut, st, ft = mt.B("tronco")
    pc, nc = na_superficie(corpo_bm, ht + ut * (Lt * 0.62), -FRENTE)
    eix = Matrix((nc.cross(CIMA).normalized(), nc, CIMA)).transposed()
    mt.peca("Tito_Placa_Acesso", elipsoide(pc + nc * 0.002, 0.11, 0.012, 0.085, eix, 24, 8), [M["placa"]], "tronco")
    lado_v = nc.cross(CIMA).normalized()
    rebites = [elipsoide(pc + nc * 0.012 + lado_v * dx + CIMA * dz, 0.008, 0.008, 0.008, None, 8, 4)
               for dx in (-0.085, 0.085) for dz in (-0.06, 0.06)]
    rebites.append(caixa(pc + nc * 0.014 + CIMA * 0.0, 0.03, 0.01, 0.02, eix))
    mt.peca("Tito_Placa_Rebites", A.juntar(*rebites), [M["metal_claro"]], "tronco", liso=False)


def montar_tito(mt):
    corpo_bm, S = corpo_tito(mt)
    criar_ossos_dedos(mt)
    for lado in ("L", "R"):
        mao_v2(mt, lado, escala=1.25, dedos=3)
        pe_v2(mt, lado, 1.15, 0.12, 0.075)
    cab = rosto(mt, dict(cranio=(1.42, 1.25, 1.36), olhos_acima=0.12, saltado=0.38, focinho=(0.62, 0.5, 0.38),
                         focinho_sai=0.95, bochecha=(0.66, 0.12, 0.36), pescoco_r=0.12, palpebra_sup=0.3,
                         palpebra_inf=-0.42, sobrancelha_r=0.011, sobrancelha_arco=0.2, sobrancelha_inclina=-0.25,
                         nariz_r=0.15, tris_cabeca=5000))
    acessorios_tito(mt, corpo_bm, cab)


# ---------------------------------------------------------------------------------------------
# Pipoca

def corpo_pipoca(mt):
    M = mt.M
    hq, tq, Lq, uq, sq, fq = mt.B("quadril")
    ht, tt, Lt, ut, st, ft = mt.B("tronco")
    S = abs(mt.B("braco.L")[0].x)
    m = Massa(0.017)
    # tronco esguio em forma de gota, peito estreito e cintura fina
    m.elipse(ht + ut * (Lt * 0.4) + ft * 0.012, S * 0.86, S * 0.66, Lt * 0.5)
    m.elipse(ht + ut * (Lt * 0.8), S * 0.78, S * 0.55, Lt * 0.3)
    for lado in ("L", "R"):
        m.bola(mt.B(f"braco.{lado}")[0] - Vector((math.copysign(0.02, mt.B(f"braco.{lado}")[0].x), 0, 0)), 0.065)
    m.elipse(hq + uq * (Lq * 0.35), S * 0.85, S * 0.62, Lq * 0.75)
    # pescoço comprido e fino (peça própria, com fresta em cima e embaixo)
    hp, tp, Lp, up, *_ = mt.B("pescoco")
    m.capsula(hp - up * 0.02, tp + up * 0.01, 0.042)
    for lado in ("L", "R"):
        h1, t1, _L, u1, *_ = mt.B(f"braco.{lado}")
        h2, t2, *_ = mt.B(f"antebraco.{lado}")
        m.tubo([(h1, 0.062), (h1.lerp(t1, 0.45), 0.056), (t1, 0.046), (h2.lerp(t2, 0.4), 0.05), (t2 + u1 * 0.015, 0.036)])
    for lado in ("L", "R"):
        h1, t1, *_ = mt.B(f"coxa.{lado}")
        h2, t2, *_ = mt.B(f"canela.{lado}")
        m.tubo([(h1 + Vector((0, 0, -0.02)), 0.085), (h1.lerp(t1, 0.5), 0.075), (t1, 0.058), (h2.lerp(t2, 0.35), 0.062),
                (t2 + Vector((0, 0, -0.025)), 0.042)])
    bm = m.malha(7500)
    endo = [ob.matrix_world @ v.co for ob in mt.endo if ob["osso"] in ("tronco", "quadril", "braco.L", "braco.R", "antebraco.L",
                                                                          "antebraco.R", "coxa.L", "coxa.R", "canela.L", "canela.R")
            for v in ob.data.vertices]
    print(f"[v2] Pipoca: {len(fora_do_volume(bm, endo))} de {len(endo)} pontos do metal fora do corpo (antes de cortar)")
    cb = ht + ut * (Lt * 0.4)
    for f in bm.faces:
        p = f.calc_center_median()
        if ((p.x - cb.x) / (S * 0.6)) ** 2 + ((p.z - cb.z) / (Lt * 0.36)) ** 2 < 1 and p.y < cb.y - S * 0.3:
            f.material_index = 1
        for lado in ("L", "R"):
            joelho = mt.B(f"canela.{lado}")[0]
            if (p - joelho).length < 0.06 and p.y < joelho.y:
                f.material_index = 2
    costura = costura_entre(bm, 0, 1)
    if costura:
        mt.peca("Pipoca_Costura_Barriga", costura, [M["linha"]], "tronco")
    bm_ref = bm.copy()
    cortes = juntas_padrao(mt, S, quadril_desce=0.1, raio_ombro=0.14, raio_quadril=0.13, raio_joelho=0.1, pescoco_r=0.08,
                           raio_cotovelo=0.1)
    pecas = mt.pecas_de_volume(bm, cortes, ["quadril", "tronco", "pescoco", "braco.L", "braco.R", "antebraco.L", "antebraco.R",
                                            "coxa.L", "coxa.R", "canela.L", "canela.R"], "Corpo",
                               [M["pelo"], M["claro_sujo"], M["pelo_sujo"], M["forro"]])
    return bm_ref, S, pecas


def rasgo_coxa(mt, peca):
    """Rasgo na frente da coxa esquerda (a peça já tem casca): buraco irregular + cabos aparecendo."""
    h, t, L, u, s, f = mt.B("coxa.L")
    centro = h + u * (L * 0.45)
    pc, nc = na_superficie_obj(peca, centro, FRENTE)
    me = peca.data
    bm = bmesh.new()
    bm.from_mesh(me)
    mw = peca.matrix_world
    inv = mw.inverted()
    rnd = random.Random(4)
    pts_borda = [(math.radians(a), rnd.uniform(0.7, 1.25)) for a in range(0, 360, 30)]

    def dentro(p):
        d = p - pc
        if d.dot(nc) < -0.03:
            return False
        lado_v = u.cross(nc).normalized()
        x, y = d.dot(lado_v), d.dot(u)
        ang = math.atan2(y, x) % (2 * math.pi)
        k = min(pts_borda, key=lambda a: abs(a[0] - ang))[1]
        return (x / (0.03 * k)) ** 2 + (y / (0.05 * k)) ** 2 < 1
    apagar = [fc for fc in bm.faces if dentro(mw @ fc.calc_center_median())]
    bmesh.ops.delete(bm, geom=apagar, context="FACES")
    # fundo do rasgo: borda gasta e um "bolso" escuro (o enchimento) onde aparece o pistão
    nl = inv.to_3x3() @ nc
    ja_abertas = {e for e in bm.edges if e.is_boundary}
    fechar_aberturas(bm, lambda centro: -nl.normalized(), 2, 3, profundidade=0.045, bainha=0.004)
    bm.to_mesh(me)
    bm.free()
    # pedaço do pistão do endoesqueleto aparecendo no fundo do rasgo
    mt.peca("Pipoca_Rasgo_Pistao", torno(pc - nc * 0.03 - u * 0.04, u, *base_osso(u)[1:],
                                         [(0, 0, 0), (0, 0.011, 0), (0.08, 0.011, 0), (0.08, 0, 0)], 1, 1, 10),
            [mt.M["metal_claro"]], "coxa.L")
    for i, cor in enumerate(("cabo_vermelho", "cabo_amarelo", "cabo_preto")):
        ini = pc - nc * 0.03 + u * ((i - 1) * 0.015)
        pts = [ini, ini + nc * 0.02 + u * 0.01, ini + nc * 0.035 + u * (0.02 + 0.01 * i) + s * 0.01 * (i - 1),
               ini + nc * 0.03 + u * (0.045 + 0.01 * i)]
        mt.peca(f"Pipoca_Cabo_Coxa_{i + 1}", tubo(pts, 0.003, 6), [mt.M[cor]], "coxa.L")


def na_superficie_obj(ob, origem, direcao):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.transform(ob.matrix_world)
    r = na_superficie(bm, origem, direcao)
    bm.free()
    return r


def acessorios_pipoca(mt, corpo_bm, cab):
    M = mt.M
    c, (Rx, Ry, Rz), W = cab["c"], cab["raios"], cab["W"]
    hb = cab["bm"]
    # orelhas compridas e grossas saindo do topo; a esquerda dobrada para a frente, com o arame à mostra
    for lado, sx in (("L", 1), ("R", -1)):
        nl = "Esq" if lado == "L" else "Dir"
        base, nrm = na_superficie(hb, c, Vector((sx * 0.38, 0.05, 0.92)))
        d1 = Vector((sx * 0.16, 0.06, 1)).normalized()
        meio = base + d1 * W * 1.2
        if lado == "L":
            d2 = Vector((sx * 0.5, -0.55, -0.55)).normalized()   # dobrada para a frente e para baixo
            ponta = meio + d2 * W * 1.05
        else:
            d2 = Vector((sx * 0.12, 0.08, 1)).normalized()
            ponta = meio + d2 * W * 1.3
        adicionar_osso(mt.arm, f"orelha.{lado}", base - d1 * 0.02, meio, "cabeca")
        adicionar_osso(mt.arm, f"orelha_ponta.{lado}", meio, ponta, f"orelha.{lado}")
        lo = W * 0.36
        for nome_o, a, b, osso, r0, r1 in ((f"Orelha_{nl}", base - d1 * 0.03, meio, f"orelha.{lado}", 0.7, 1.0),
                                           (f"Orelha_Ponta_{nl}", meio, ponta, f"orelha_ponta.{lado}", 1.0, 0.72)):
            uo = (b - a).normalized()
            fo = FRENTE - uo * FRENTE.dot(uo)
            if fo.length < 0.2:
                fo = CIMA - uo * CIMA.dot(uo)
            fo.normalize()
            so = fo.cross(uo).normalized()
            Lo = (b - a).length
            ponta_rasgada = lado == "L" and "Ponta" in nome_o
            fim = Lo * (0.8 if ponta_rasgada else 1.0)
            ini = 0.012 if "Ponta" in nome_o else 0.0
            if "Ponta" in nome_o:
                perfil = capsula(ini, fim, lo * r0, lo * r1, lo * 0.12, n=10, ponta=0.3, ponta_fim=0.9)
            else:
                perfil = capsula(ini, fim, lo * r0, lo * r1, lo * 0.12, n=10, ponta=0.6, ponta_fim=0.3)
            cortes = ()
            if ponta_rasgada:
                cc = a + uo * fim
                corte = elipsoide(cc, lo * 1.6, lo * 1.6, lo * 0.4, Matrix((so, fo, uo)).transposed(), 16, 8)
                rnd = random.Random(11)
                for v in corte.verts:
                    v.co += uo * rnd.uniform(-0.015, 0.015)
                cortes = (corte,)
            mt.peca(f"Pipoca_{nome_o}", torno(a, uo, so, fo, perfil, 1.0, 0.45), [M["pelo"]], osso, cortes=cortes)
            dentro = capsula(ini + 0.012, fim - 0.02, lo * r0 * 0.68, lo * r1 * 0.68, ponta=0.4)
            mt.peca(f"Pipoca_{nome_o}_Dentro", torno(a + fo * lo * 0.36, uo, so, fo, dentro, 1.0, 0.12), [M["rosa"]], osso)
        # haste de metal da orelha aparecendo na base (fresta)
        mt.peca(f"Pipoca_Orelha_Haste_{nl}", torno(base - d1 * 0.035, d1, *base_osso(d1)[1:], [(0, 0, 0), (0, 0.012, 0), (0.03, 0.012, 0), (0.03, 0, 0)], 1, 1, 10),
                [M["metal_claro"]], f"orelha.{lado}")
        # dobradiça de metal entre a base e a ponta da orelha
        eixo_d = (meio - base).normalized().cross(FRENTE).normalized()
        mt.peca(f"Pipoca_Orelha_Dobradica_{nl}", torno(meio - eixo_d * lo * 0.55, eixo_d, *base_osso(eixo_d)[1:],
                                                       [(0, 0, 0), (0, 0.009, 0), (lo * 1.1, 0.009, 0), (lo * 1.1, 0, 0)], 1, 1, 10),
                [M["metal_claro"]], f"orelha.{lado}")
        if lado == "L":
            Lp = (ponta - meio).length
            pts = [meio + d2 * (Lp * t) for t in (0.2, 0.45, 0.7, 0.82, 0.92)]
            pts.append(pts[-1] + d2 * 0.035 + Vector((sx * 0.02, -0.01, 0.0)))
            pts.append(pts[-1] + Vector((sx * 0.01, -0.02, 0.025)))
            mt.peca("Pipoca_Orelha_Arame", tubo(pts, 0.0042, 6), [M["arame"]], f"orelha_ponta.{lado}")
    # laço rosa de bolinhas na frente das orelhas
    cl, nl_ = na_superficie(hb, c, Vector((0.0, -0.35, 1)))
    eix = Matrix.Rotation(math.radians(-25), 3, "X")
    partes = [elipsoide(cl + nl_ * 0.01, W * 0.16, W * 0.14, W * 0.14, eix, 12, 6)]
    for sx in (-1, 1):
        rot = eix @ Matrix.Rotation(math.radians(sx * 12), 3, "Y")
        partes.append(elipsoide(cl + nl_ * 0.015 + Vector((sx * W * 0.36, 0, 0.01)), W * 0.36, W * 0.11, W * 0.24, rot, 18, 9))
    mt.peca("Pipoca_Laco", A.juntar(*partes), [M["laco"]], "cabeca")
    # rabinho de pompom (no lugar do tutu, que não aparece nas artes)
    hq, tq, Lq, uq, sq, fq = mt.B("quadril")
    pr, nr = na_superficie(corpo_bm, hq + uq * (Lq * 0.3), -FRENTE)
    mr = Massa(0.006)
    rnd = random.Random(5)
    for _ in range(9):
        mr.bola(pr + nr * 0.05 + Vector((rnd.uniform(-1, 1), rnd.uniform(-0.5, 0.5), rnd.uniform(-1, 1))) * 0.03, 0.045)
    mt.peca("Pipoca_Rabo", mr.malha(700), [M["claro_sujo"]], "quadril")
    # zíper nas costas (do pescoço até a cintura)
    ht, tt, Lt, ut, st, ft = mt.B("tronco")
    pts = []
    for i in range(10):
        t = 0.1 + 0.8 * i / 9
        pz, pn = na_superficie(corpo_bm, ht + ut * (Lt * t), -FRENTE)
        pts.append(pz + pn * 0.002)
    mt.peca("Pipoca_Ziper", tubo(pts, 0.0045, 4), [M["metal_claro"]], "tronco", liso=False)
    pz, pn = pts[0], (pts[0] - (ht + ut * (Lt * 0.1))).normalized()
    mt.peca("Pipoca_Ziper_Puxador", caixa(pz + pn * 0.006 - ut * 0.02, 0.012, 0.004, 0.03), [M["metal_claro"]], "tronco", liso=False)


def tutu(mt, corpo_bm):
    """Saia de tule em 2 camadas, com babados, presa no osso "saia" (filho do quadril). Barra puída e encardida."""
    M = mt.M
    hq, tq, Lq, uq, *_ = mt.B("quadril")
    centro = Vector((hq.x, hq.y, tq.z - 0.015))
    rs = []
    for i in range(12):
        a = 2 * math.pi * i / 12
        pnt, _n = na_superficie(corpo_bm, centro, Vector((math.cos(a), math.sin(a), 0)))
        rs.append(math.hypot(pnt.x - centro.x, pnt.y - centro.y))
    r0 = max(rs) + 0.012
    adicionar_osso(mt.arm, "saia", centro, centro - CIMA * 0.2, "quadril")
    baixo = -CIMA
    _u, s, f = base_osso(baixo)
    rnd = random.Random(21)
    for i, (L, r1) in enumerate(((0.17, r0 * 1.95), (0.13, r0 * 1.7))):
        perfil = [(0.0, r0, 0), (0.025, r0 * 1.06, 0), (L * 0.55, r1 * 0.82, 0), (L, r1, 0),
                  (L + 0.007, r1 * 0.985, 0), (L * 0.55, r1 * 0.8, 0), (0.025, r0 * 1.01, 0), (0.0, r0 * 0.97, 0)]
        bm = torno(centro - baixo * (0.005 * i), baixo, s, f, perfil, 1.0, 0.92, segs=64,
                   onda=lambda th, i=i: 1 + 0.06 * math.cos(16 * th + i * 0.7))
        # barra puída: a borda de baixo fica irregular (fios soltos, pedaços mais curtos)
        bainha = [v for v in bm.verts if (v.co - centro).dot(baixo) > L * 0.97]
        for v in bainha:
            k = rnd.uniform(-0.018, 0.012)
            v.co += baixo * k
        for face in bm.faces:
            if (face.calc_center_median() - centro).dot(baixo) > L * 0.7:
                face.material_index = 1
        mt.peca(f"Pipoca_Saia_{i + 1}", bm, [M["tutu"], M["tutu_sujo"]], "saia")


def montar_pipoca(mt):
    corpo_bm, S, pecas = corpo_pipoca(mt)
    rasgo_coxa(mt, pecas["coxa.L"])
    criar_ossos_dedos(mt)
    for lado in ("L", "R"):
        mao_v2(mt, lado, escala=1.0, dedos=3)
        pe_v2(mt, lado, 1.7, 0.065, 0.05, dedos=3, coelho=True)
    cab = rosto(mt, dict(cranio=(1.28, 1.12, 1.3), olhos_acima=0.05, saltado=0.42, focinho=(0.56, 0.4, 0.33),
                         focinho_sai=0.9, bochecha=(0.62, 0.05, 0.3), blush=True, pescoco_r=0.055,
                         palpebra_sup=0.58, palpebra_inf=-0.45, sobrancelha_r=0.006, sobrancelha_arco=0.35,
                         sobrancelha_inclina=-0.35, nariz_r=0.12, dentinhos=True, queixo_plastico=True, tris_cabeca=4800))
    acessorios_pipoca(mt, corpo_bm, cab)
    tutu(mt, corpo_bm)


# ---------------------------------------------------------------------------------------------

ALTURA_V2 = {"tito": 1.78, "pipoca": 1.86}


def montar(chave):
    A.PERSONAGENS[chave]["altura"] = ALTURA_V2[chave]
    for n, v in PROPORCOES_V2[chave].items():
        A.PERSONAGENS[chave]["ossos"][n] = v
    arm, endo, escala = A.preparar_rig(chave)
    M = materiais_v2(chave)
    A.materiais_endo(endo, M)
    mt = MontadorV2(chave, arm, endo, M)
    # a fantasia é modelada na pose de exibição (braços abaixados): ombro e braço se fundem nessa pose
    pose_descanso(arm, chave)
    bpy.context.view_layer.update()
    (montar_tito if chave == "tito" else montar_pipoca)(mt)
    # quinas vivas (bainhas, fundos, dentes): sem isso o sombreado suave "escorre" em listras escuras
    for ob in mt.pecas:
        ob.data.set_sharp_from_angle(angle=math.radians(50))
    bpy.context.view_layer.update()
    zmin = min((ob.matrix_world @ v.co).z for ob in mt.pecas for v in ob.data.vertices)
    arm.location.z -= zmin
    bpy.context.view_layer.update()
    tris = sum(sum(len(p.vertices) - 2 for p in ob.data.polygons) for ob in endo + mt.pecas)
    tris_fant = sum(sum(len(p.vertices) - 2 for p in ob.data.polygons) for ob in mt.pecas)
    pesos = sorted(((sum(len(p.vertices) - 2 for p in ob.data.polygons), ob.name) for ob in mt.pecas), reverse=True)
    print("[v2] peças mais pesadas:", ", ".join(f"{n} {k}" for k, n in pesos[:12]))
    zmax = max((ob.matrix_world @ v.co).z for ob in endo + mt.pecas for v in ob.data.vertices)
    print(f"[anim] {chave} v2: {len(endo)} peças de metal, {len(mt.pecas)} peças de fantasia ({tris_fant} triângulos), "
          f"{tris} triângulos no total, {len(arm.data.bones)} ossos, altura {zmax:.2f} m")
    return arm, endo, mt


ANGULO_BRACOS = {"tito": 46, "pipoca": 70}


def pose_descanso(arm, chave):
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
    ang = ANGULO_BRACOS[chave]
    A.girar(arm, "braco.L", (0, 1, 0), ang)
    A.girar(arm, "braco.R", (0, 1, 0), -ang)
    A.girar(arm, "antebraco.L", (0, 0, 1), -12)
    A.girar(arm, "antebraco.R", (0, 0, 1), 12)
    A.girar(arm, "mao.L", (0, 1, 0), 15)
    A.girar(arm, "mao.R", (0, 1, 0), -15)


def pose_teste(arm, chave):
    """Cotovelos, joelhos e pescoço dobrados (o documento pede que as juntas continuem bonitas assim)."""
    pose_descanso(arm, chave)
    A.girar(arm, "pescoco", (1, 0, 0), -14)
    A.girar(arm, "pescoco", (0, 0, 1), -20)
    A.girar(arm, "cabeca", (0, 1, 0), 10)
    A.girar(arm, "mandibula", (1, 0, 0), -24)
    A.girar(arm, "braco.R", (1, 0, 0), 70)
    A.girar(arm, "antebraco.R", (0, 0, 1), 65)
    A.girar(arm, "antebraco.L", (1, 0, 0), 85)
    A.girar(arm, "coxa.R", (1, 0, 0), 42)
    A.girar(arm, "canela.R", (1, 0, 0), -75)
    A.girar(arm, "pe.R", (1, 0, 0), 25)
    A.girar(arm, "coxa.L", (1, 0, 0), -12)
    A.girar(arm, "canela.L", (1, 0, 0), -22)
    A.girar(arm, "palpebra_sup.L", (1, 0, 0), 18)
    if chave == "pipoca":
        A.girar(arm, "orelha.R", (0, 1, 0), -15)
        A.girar(arm, "orelha_ponta.R", (1, 0, 0), 35)


def renders(chave, arm, pasta):
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    cam = A.estudio()
    pose_descanso(arm, chave)
    bpy.context.view_layer.update()
    altura = max((ob.matrix_world @ v.co).z for ob in bpy.context.scene.objects if ob.type == "MESH"
                 and not ob.name.startswith("Estudio") for v in ob.data.vertices)
    meio = (0, 0, altura * 0.5)
    dist = altura * 2.15
    for nome, ang in (("frente", 0), ("tres_quartos", 35), ("lado", 90)):
        A.fotografar(cam, pasta / f"{chave}_{nome}.png", meio, dist, ang)
    cab = arm.matrix_world @ arm.data.bones["cabeca"].head_local
    alvo = cab + Vector((0, 0, 0.13 if chave == "tito" else 0.1))
    A.fotografar(cam, pasta / f"{chave}_rosto.png", alvo, 1.2, 22, 5, 60, (1200, 1200))
    A.fotografar(cam, pasta / f"{chave}_rosto_frente.png", alvo, 1.2, 0, 3, 60, (1200, 1200))
    pose_teste(arm, chave)
    bpy.context.view_layer.update()
    A.fotografar(cam, pasta / f"{chave}_pose.png", meio, dist, 40, 10)
    pose_descanso(arm, chave)


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["tito"]
    chave = args[0]
    opcoes = dict(a.split("=", 1) if "=" in a else (a, True) for a in args[1:])
    arm, endo, mt = montar(chave)
    if not opcoes.get("sem_salvar"):
        destino = RAIZ / "personagens" / f"{chave}_final.blend"
        pose_descanso(arm, chave)
        bpy.ops.wm.save_as_mainfile(filepath=str(destino))
        print("[anim] salvo", destino)
    if opcoes.get("renders"):
        renders(chave, arm, opcoes["renders"])


if __name__ == "__main__":
    main()
