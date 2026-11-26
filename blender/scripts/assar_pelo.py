"""
assar_pelo.py — gera pelo curto no Blender (milhares de fios deitados sobre um plano) e "assa" o
relevo num normal map que repete sem emenda. Esse normal é somado ao da pelúcia CC0 (Fabric084)
em ferramentas/gerar_texturas_animatronicos.py, para dar a sensação de pelo no jogo (o glTF não
leva o pelo do Blender, só a imagem).

Rodar (na pasta TurnoDaNoite):
    blender --background --factory-startup --python blender/scripts/assar_pelo.py
Saída: blender/texturas_assadas/pelo_curto_normal.png (1024 px)
"""

import math
import random
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "texturas_assadas" / "pelo_curto_normal.png"
TAM = 1024
FIOS = 9000


def limpar():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)


def criar_fios():
    """Fios = cones finos deitados quase todos para o mesmo lado (pelo "penteado"), com variação."""
    rnd = random.Random(7)
    bm = bmesh.new()
    for _ in range(FIOS):
        x, y = rnd.random(), rnd.random()
        comprimento = rnd.uniform(0.035, 0.07)
        raio = rnd.uniform(0.0022, 0.0040)
        # direção: penteado para "baixo" (−Y) com ±35° de bagunça; bem deitado (12° a 30° do plano)
        ang = math.radians(-90 + rnd.gauss(0, 22))
        incl = math.radians(rnd.uniform(12, 30))
        d = Vector((math.cos(ang) * math.cos(incl), math.sin(ang) * math.cos(incl), math.sin(incl)))
        # fio levemente curvo: 3 trechos
        pontos = [Vector((x, y, 0.0))]
        for i in range(1, 4):
            dd = d.copy()
            dd.z -= 0.18 * i  # a ponta cai um pouco
            pontos.append(pontos[-1] + dd.normalized() * (comprimento / 3))
        # repete nas bordas para emendar (tile)
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                if (ox or oy) and not (-0.1 < x + ox < 1.1 and -0.1 < y + oy < 1.1):
                    continue
                off = Vector((ox, oy, 0))
                _tubo(bm, [p + off for p in pontos], raio)
    me = bpy.data.meshes.new("Fios")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("Fios", me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    return ob


def _tubo(bm, pontos, raio):
    aneis = []
    lados = 5
    for i, p in enumerate(pontos):
        t = pontos[min(i + 1, len(pontos) - 1)] - pontos[max(i - 1, 0)]
        t.normalize()
        a = t.cross(Vector((0, 0, 1)))
        if a.length < 1e-4:
            a = Vector((1, 0, 0))
        a.normalize()
        b = t.cross(a)
        r = raio * (1 - i / (len(pontos) - 1)) + 0.0003
        aneis.append([bm.verts.new(p + (a * math.cos(k * 2 * math.pi / lados) + b * math.sin(k * 2 * math.pi / lados)) * r)
                      for k in range(lados)])
    for i in range(len(aneis) - 1):
        for k in range(lados):
            bm.faces.new((aneis[i][k], aneis[i][(k + 1) % lados], aneis[i + 1][(k + 1) % lados], aneis[i + 1][k]))


def criar_alvo():
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0.5, 0.5, 0))
    alvo = bpy.context.active_object
    alvo.name = "Alvo"
    img = bpy.data.images.new("pelo_normal", TAM, TAM, float_buffer=False)
    img.colorspace_settings.name = "Non-Color"
    mat = bpy.data.materials.new("Alvo")
    mat.use_nodes = True
    no = mat.node_tree.nodes.new("ShaderNodeTexImage")
    no.image = img
    mat.node_tree.nodes.active = no
    alvo.data.materials.append(mat)
    return alvo, img


def main():
    limpar()
    cena = bpy.context.scene
    cena.render.engine = "CYCLES"
    cena.cycles.samples = 4
    cena.cycles.device = "CPU"
    fios = criar_fios()
    alvo, img = criar_alvo()
    # pele embaixo dos fios (para o normal não "furar" entre os fios)
    bpy.ops.mesh.primitive_plane_add(size=3, location=(0.5, 0.5, -0.002))
    pele = bpy.context.active_object
    bpy.ops.object.select_all(action="DESELECT")
    fios.select_set(True)
    pele.select_set(True)
    alvo.select_set(True)
    bpy.context.view_layer.objects.active = alvo
    cena.render.bake.use_selected_to_active = True
    cena.render.bake.cage_extrusion = 0.08
    cena.render.bake.max_ray_distance = 0.2
    cena.render.bake.margin = 0
    bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT")
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    img.filepath_raw = str(SAIDA)
    img.file_format = "PNG"
    img.save()
    print("[pelo] normal assado em", SAIDA)


main()
