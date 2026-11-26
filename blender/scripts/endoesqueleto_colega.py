"""
endoesqueleto_colega.py — prepara o endoesqueleto do colega (blender/personagens_colega/animatronic.blend)
para receber a fantasia do Tito e da Pipoca. NUNCA salva por cima do arquivo do colega.

O arquivo dele tem as peças do endoesqueleto prontas (pistões, juntas, cabeça com dentes, olhos e
pálpebras, dedos), mas sem armature: as peças estão juntas em poucos objetos (com espelhamento).
Aqui:
  1. aplica os modificadores (espelho) e separa cada peça solta (ilha) num objeto próprio;
  2. corta as hastes que atravessam o cotovelo (senão elas não dobram);
  3. cria a armature (um osso por parte que se move) e prende cada peça no osso mais perto,
     do jeito "rígido" (cada peça segue um osso, sem deformar), que é como um animatrônico funciona;
  4. muda as proporções por personagem (Tito largo e baixo, Pipoca alta e fina) movendo as juntas.
A fantasia vem depois (animatronicos_finais.py).

Coordenadas do arquivo do colega: frente para +Y, ~21 unidades de altura. No fim giramos 180° (frente
para −Y, padrão do projeto) e escalamos para metros.
"""

import math

import bmesh
import bpy
from mathutils import Vector

ARQUIVO_COLEGA = "personagens_colega/animatronic.blend"

# Materiais da fantasia que o colega começou (substituída pela nossa) e objetos de cena.
MATERIAIS_DESCARTADOS = {"YellowFur", "BeigeFur"}

# Juntas no arquivo do colega (frente +Y). s = lado: +1 = x positivo (lado DIREITO do boneco).
JUNTAS = {
    "quadril": ((0, 0, -2.0), (0, 0, 0.0)),
    "tronco": ((0, 0, 0.0), (0, 0, 7.8)),
    "pescoco": ((0, 0, 7.8), (0, 0, 8.75)),
    "cabeca": ((0, 0, 8.75), (0, 0, 11.7)),
    "mandibula": ((0, 0.15, 9.12), (0, 1.15, 9.0)),
}
JUNTAS_LADO = {
    "braco": ((3.3, 0, 6.48), (5.87, 0, 6.48)),
    "antebraco": ((5.87, 0, 6.48), (8.43, 0, 6.48)),
    "mao": ((8.43, 0, 6.48), (11.5, 0, 6.48)),
    "coxa": ((1.48, 0, -1.95), (1.48, 0, -5.33)),
    "canela": ((1.48, 0, -5.33), (1.48, 0, -8.9)),
    "pe": ((1.48, 0, -8.9), (1.48, 2.6, -9.1)),
    "olho": ((0.8, 0.71, 10.73), (0.8, 1.4, 10.73)),
    "palpebra_sup": ((0.8, 0.70, 10.73), (0.8, 0.70, 11.5)),
    "palpebra_inf": ((0.8, 0.69, 10.73), (0.8, 0.69, 10.0)),
}
PAIS = {
    "tronco": "quadril", "pescoco": "tronco", "cabeca": "pescoco", "mandibula": "cabeca",
    "braco": "tronco", "antebraco": "braco", "mao": "antebraco",
    "coxa": "quadril", "canela": "coxa", "pe": "canela",
    "olho": "cabeca", "palpebra_sup": "cabeca", "palpebra_inf": "cabeca",
}
# Peças com dono fixo (pelo nome do objeto original do colega)
DONO_FIXO = {
    "Cube.051": "olho", "Cube.052": "olho",
    "Cube.054": "palpebra_sup", "Cube.055": "palpebra_sup",
    "Cube.056": "palpebra_inf", "Cube.057": "palpebra_inf",
    "Cube.053": "mandibula",
}
# Peças que só podem ir para alguns ossos (pelo nome do objeto original)
DONO_GRUPO = {"Cube.002": ("quadril", "tronco")}
# Ossos que recebem peça por proximidade
OSSOS_CORPO = ["quadril", "tronco", "pescoco", "cabeca", "braco", "antebraco", "mao", "coxa", "canela", "pe"]


def nome_osso(base, s):
    if base in JUNTAS:
        return base
    return f"{base}.{'R' if s > 0 else 'L'}"


def lista_ossos():
    """[(nome, cabeça, cauda, pai)] no espaço do colega."""
    ossos = []
    for nome, (a, b) in JUNTAS.items():
        ossos.append((nome, Vector(a), Vector(b), PAIS.get(nome)))
    for base, (a, b) in JUNTAS_LADO.items():
        for s in (1, -1):
            va, vb = Vector(a), Vector(b)
            va.x *= s
            vb.x *= s
            pai = PAIS[base]
            ossos.append((nome_osso(base, s), va, vb, nome_osso(pai, s) if pai in JUNTAS_LADO else pai))
    return ossos


def distancia_segmento(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (p - (a + ab * t)).length


def _cortar(bm_origem, plano_co, plano_no):
    """Divide uma malha em duas pelo plano (cada metade tampada). Devolve (lado -, lado +)."""
    partes = []
    for limpar_dentro in (False, True):
        bm = bm_origem.copy()
        geo = bm.verts[:] + bm.edges[:] + bm.faces[:]
        r = bmesh.ops.bisect_plane(bm, geom=geo, plane_co=plano_co, plane_no=plano_no,
                                   clear_inner=limpar_dentro, clear_outer=not limpar_dentro)
        corte = [e for e in r["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        if corte:
            bmesh.ops.holes_fill(bm, edges=corte, sides=0)
        partes.append(bm)
    return partes


def preparar(raiz_blender):
    """Abre o arquivo do colega e deixa: peças soltas (uma por ilha), cada uma com o osso dono em ["osso"]."""
    bpy.ops.wm.open_mainfile(filepath=str(raiz_blender / ARQUIVO_COLEGA))
    deps = bpy.context.evaluated_depsgraph_get()
    pecas = []  # (nome_origem, bmesh já em coordenadas de mundo, materiais)
    for obj in list(bpy.context.scene.objects):
        if obj.type != "MESH":
            continue
        mats = [m for m in obj.data.materials]
        if mats and all(m and m.name.split(".")[0] in MATERIAIS_DESCARTADOS for m in mats):
            continue
        me = bpy.data.meshes.new_from_object(obj.evaluated_get(deps))
        me.transform(obj.matrix_world)
        bm = bmesh.new()
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
        # Ilhas
        bm.verts.ensure_lookup_table()
        visto = set()
        for v in bm.verts:
            if v.index in visto:
                continue
            ilha = set()
            pilha = [v]
            while pilha:
                a = pilha.pop()
                if a.index in ilha:
                    continue
                ilha.add(a.index)
                for e in a.link_edges:
                    pilha.append(e.other_vert(a))
            visto |= ilha
            sub = bm.copy()
            sub.verts.ensure_lookup_table()
            bmesh.ops.delete(sub, geom=[sub.verts[i] for i in range(len(sub.verts)) if i not in ilha], context="VERTS")
            pecas.append((obj.name, sub, mats))
        bm.free()
    # Hastes que atravessam o cotovelo: cortar no cotovelo
    cotovelo = JUNTAS_LADO["braco"][1][0]
    final = []
    for origem, bm, mats in pecas:
        xs = [v.co.x for v in bm.verts]
        if min(xs) * max(xs) > 0 and min(abs(min(xs)), abs(max(xs))) < cotovelo - 0.3 < cotovelo + 0.3 < max(abs(min(xs)), abs(max(xs))):
            s = 1 if xs[0] > 0 else -1
            for parte in _cortar(bm, Vector((s * cotovelo, 0, 0)), Vector((1, 0, 0))):
                if parte.verts:
                    final.append((origem, parte, mats))
            bm.free()
        else:
            final.append((origem, bm, mats))
    # Apaga tudo da cena e cria um objeto por peça
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    ossos = lista_ossos()
    objetos = []
    for i, (origem, bm, mats) in enumerate(final):
        centro = sum((v.co for v in bm.verts), Vector()) / len(bm.verts)
        s = 1 if centro.x > 0 else -1
        if origem in DONO_FIXO:
            osso = nome_osso(DONO_FIXO[origem], s)
        elif origem in DONO_GRUPO:
            # peças do tronco do colega (coluna, costelas, placas e barra dos ombros) ficam no tronco
            osso = min((distancia_segmento(centro, a, b), n) for (n, a, b, _p) in ossos if n in DONO_GRUPO[origem])[1]
        else:
            candidatos = [(distancia_segmento(centro, a, b), n) for (n, a, b, _p) in ossos
                          if n.split(".")[0] in OSSOS_CORPO]
            osso = min(candidatos)[1]
        me = bpy.data.meshes.new(f"Endo_{i:03d}")
        bm.to_mesh(me)
        bm.free()
        for m in mats:
            me.materials.append(m)
        ob = bpy.data.objects.new(f"Endo_{osso}_{i:03d}", me)
        ob["osso"] = osso
        ob["origem"] = origem
        bpy.context.scene.collection.objects.link(ob)
        objetos.append(ob)
    return objetos, ossos


def mudar_proporcoes(objetos, ossos, escala_osso):
    """
    Move as juntas e as peças para as proporções de cada personagem.
    escala_osso: {nome_base: (comprimento, grossura)}. Cada osso fica com o comprimento multiplicado,
    e a cadeia é refeita a partir da raiz (os filhos acompanham a ponta do pai).
    Peças compridas (pistões) esticam ao longo do osso; peças curtas (juntas, parafusos) só mudam
    de lugar e de tamanho por igual (não ficam ovais).
    """
    info = {n: (a, b, p) for (n, a, b, p) in ossos}
    novo = {}

    def calcular(n):
        if n in novo:
            return novo[n]
        a, b, p = info[n]
        comp, _g = escala_osso.get(n.split(".")[0], (1.0, 1.0))
        if p is None:
            na = a.copy()
        else:
            pa, pb, _ = info[p]
            npa, npb = calcular(p)
            # o ponto de encaixe no pai mantém a posição relativa (ao longo e para o lado)
            eixo_p = (pb - pa)
            t = (a - pa).dot(eixo_p) / eixo_p.length_squared
            lateral = (a - pa) - eixo_p * t
            _cp, gp = escala_osso.get(p.split(".")[0], (1.0, 1.0))
            na = npa + (npb - npa) * t + lateral * gp
        nb = na + (b - a) * comp
        novo[n] = (na, nb)
        return novo[n]

    for n in info:
        calcular(n)
    for ob in objetos:
        n = ob["osso"]
        a, b, _ = info[n]
        na, nb = novo[n]
        comp, gros = escala_osso.get(n.split(".")[0], (1.0, 1.0))
        u = (b - a).normalized()
        L = (b - a).length
        vs = ob.data.vertices
        centro = sum((v.co for v in vs), Vector()) / len(vs)
        ao_longo = [(v.co - a).dot(u) for v in vs]
        extensao = max(ao_longo) - min(ao_longo)
        esticar = extensao > 0.45 * L
        dc = centro - a
        ac = dc.dot(u)
        novo_centro = na + u * (ac * comp) + (dc - u * ac) * gros
        for v in vs:
            d = v.co - a
            if esticar:
                al = d.dot(u)
                v.co = na + u * (al * comp) + (d - u * al) * gros
            else:
                v.co = novo_centro + (v.co - centro) * gros
    return [(n, novo[n][0], novo[n][1], info[n][2]) for n in info]


def criar_armature(nome, ossos, objetos, escala, giro=True):
    """Cria a armature (já em metros e virada para −Y) e prende cada peça no seu osso (parent de osso)."""
    rot = -1 if giro else 1

    def conv(v):
        return Vector((v.x * rot, v.y * rot, v.z)) * escala

    # chão: o ponto mais baixo das peças vai para z = 0
    zmin = min((ob.matrix_world @ v.co).z for ob in objetos for v in ob.data.vertices)
    deslocar = Vector((0, 0, -zmin * escala))
    arm_dados = bpy.data.armatures.new(nome)
    arm = bpy.data.objects.new(nome, arm_dados)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    for (n, a, b, _p) in ossos:
        e = arm_dados.edit_bones.new(n)
        e.head = conv(a) + deslocar
        e.tail = conv(b) + deslocar
        # rolagem: eixo Z local do osso para a frente (−Y) nos membros, para cima nos ossos verticais
        e.align_roll(Vector((0, -1, 0)) if abs(e.vector.normalized().z) > 0.7 else Vector((0, 0, 1)))
    for (n, _a, _b, p) in ossos:
        if p:
            arm_dados.edit_bones[n].parent = arm_dados.edit_bones[p]
    bpy.ops.object.mode_set(mode="OBJECT")
    for ob in objetos:
        for v in ob.data.vertices:
            v.co = conv(v.co) + deslocar
        ob.data.update()
        prender_no_osso(ob, arm, ob["osso"])
    return arm


def prender_no_osso(ob, arm, osso):
    """Parent de osso mantendo a posição no mundo (sem deformar a malha)."""
    bpy.context.view_layer.update()
    mundo = ob.matrix_world.copy()
    ob.parent = arm
    ob.parent_type = "BONE"
    ob.parent_bone = osso
    bpy.context.view_layer.update()
    ob.matrix_world = mundo
    ob["osso"] = osso


def girar_osso(arm, nome, graus_xyz):
    pb = arm.pose.bones[nome]
    pb.rotation_mode = "XYZ"
    pb.rotation_euler = [math.radians(g) for g in graus_xyz]
