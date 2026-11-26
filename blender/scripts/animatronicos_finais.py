"""
animatronicos_finais.py — Tito e Pipoca finais: fantasia de pelúcia em peças rígidas sobre o
endoesqueleto (blender/endoesqueleto/animatronic.blend, que NÃO é alterado).

Cada peça da fantasia segue um osso (cabeça, mandíbula, peito, braço, antebraço, mão, coxa, canela,
pé, orelhas), com frestas nas juntas mostrando o metal. Ossos novos (só os essenciais que faltavam):
orelhas (Tito: 1 por lado; Pipoca: base + ponta, para a orelha comprida cair).

Rodar (na pasta TurnoDaNoite):
    blender --background --factory-startup --python blender/scripts/animatronicos_finais.py -- tito
    blender --background --factory-startup --python blender/scripts/animatronicos_finais.py -- pipoca
Opções depois do nome: renders=<pasta> (faz os renders do design), sem_salvar.
Saída: blender/personagens/<nome>_final.blend
Texturas: godot/assets/texturas/animatronicos/ (ferramentas/gerar_texturas_animatronicos.py).
"""

import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import endoesqueleto as E  # noqa: E402

TEX = RAIZ.parent / "godot" / "assets" / "texturas"
TEXA = TEX / "animatronicos"
FRENTE = Vector((0, -1, 0))
CIMA = Vector((0, 0, 1))

# ---------------------------------------------------------------------------------------------
# Proporções: (comprimento, grossura) de cada osso em relação ao endoesqueleto.
CABECA_SEGUE = ("olho", "palpebra_sup", "palpebra_inf", "mandibula")
PERSONAGENS = {
    "tito": {
        "Nome": "Tito",
        "altura": 1.78,  # endoesqueleto (sem chapéu)
        "ossos": {"quadril": (1.0, 1.25), "tronco": (1.0, 1.0), "pescoco": (0.5, 1.3), "cabeca": (1.28, 1.48),
                  "braco": (1.0, 1.3), "antebraco": (0.95, 1.3), "mao": (0.9, 1.4),
                  "coxa": (0.9, 1.35), "canela": (0.85, 1.35), "pe": (1.0, 1.4)},
    },
    "pipoca": {
        "Nome": "Pipoca",
        "altura": 2.02,
        "ossos": {"quadril": (1.0, 0.9), "tronco": (1.0, 0.72), "pescoco": (1.55, 0.85), "cabeca": (0.98, 0.98),
                  "braco": (1.25, 0.82), "antebraco": (1.3, 0.82), "mao": (1.1, 0.85),
                  "coxa": (1.3, 0.85), "canela": (1.38, 0.85), "pe": (1.2, 0.85)},
    },
}


# ---------------------------------------------------------------------------------------------
# Materiais

def _img(caminho, dados=False):
    img = bpy.data.images.load(str(caminho), check_existing=True)
    if dados:
        img.colorspace_settings.name = "Non-Color"
    return img


def material(nome, cor=(0.8, 0.8, 0.8), img_cor=None, img_normal=None, forca_normal=1.0, aspereza=0.8,
             img_aspereza=None, metal=0.0, emissao=None, forca_emissao=0.0, brilho_tecido=0.0):
    if nome in bpy.data.materials:
        return bpy.data.materials[nome]
    m = bpy.data.materials.new(nome)
    m.use_nodes = True
    nt = m.node_tree
    p = nt.nodes["Principled BSDF"]
    p.inputs["Base Color"].default_value = (*cor, 1)
    p.inputs["Roughness"].default_value = aspereza
    p.inputs["Metallic"].default_value = metal
    if img_cor:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = _img(img_cor)
        nt.links.new(t.outputs["Color"], p.inputs["Base Color"])
    if img_aspereza:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = _img(img_aspereza, True)
        nt.links.new(t.outputs["Color"], p.inputs["Roughness"])
    if img_normal:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = _img(img_normal, True)
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = forca_normal
        nt.links.new(t.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], p.inputs["Normal"])
    if emissao:
        p.inputs["Emission Color"].default_value = (*emissao, 1)
        p.inputs["Emission Strength"].default_value = forca_emissao
    if brilho_tecido:
        p.inputs["Sheen Weight"].default_value = brilho_tecido
    m["metros_por_repeticao"] = 0.35
    return m


def materiais(chave):
    """Todos os materiais de um personagem. Nomes no padrão do projeto (Mat_<Personagem>_<Parte>)."""
    N = PERSONAGENS[chave]["Nome"]
    pel = dict(img_normal=TEXA / "pelucia_normal.jpg", forca_normal=0.9, img_aspereza=TEXA / "pelucia_aspereza.jpg",
               brilho_tecido=0.2)
    M = {}
    if chave == "tito":
        M["pelo"] = material(f"Mat_{N}_Pelo", img_cor=TEXA / "tito_pelo_cor.jpg", **pel)
        M["pelo_sujo"] = material(f"Mat_{N}_Pelo_Sujo", img_cor=TEXA / "tito_pelo_sujo_cor.jpg", **pel)
        M["claro"] = material(f"Mat_{N}_Creme", img_cor=TEXA / "tito_creme_cor.jpg", **pel)
        M["claro_sujo"] = material(f"Mat_{N}_Creme_Sujo", img_cor=TEXA / "tito_creme_sujo_cor.jpg", **pel)
        M["plastico"] = material(f"Mat_{N}_Plastico", img_cor=TEXA / "plastico_creme_cor.jpg", aspereza=0.38)
        M["iris"] = material(f"Mat_Olho_{N}", cor=(1.0, 0.45, 0.04), emissao=(1.0, 0.4, 0.02), forca_emissao=2.5, aspereza=0.2)
        M["nariz"] = material(f"Mat_{N}_Nariz", cor=(0.03, 0.025, 0.025), aspereza=0.25)
        M["chapeu"] = material(f"Mat_{N}_Chapeu", img_cor=TEXA / "chapeu_cor.jpg", **pel)
        M["chapeu_sujo"] = material(f"Mat_{N}_Chapeu_Sujo", img_cor=TEXA / "chapeu_sujo_cor.jpg", **pel)
        M["gravata"] = material(f"Mat_{N}_Gravata", img_cor=TEXA / "gravata_cor.jpg",
                                img_normal=TEX / "tecido" / "tecido_normal.jpg", aspereza=0.75, brilho_tecido=0.4)
        M["lenco"] = material(f"Mat_{N}_Lenco", img_cor=TEXA / "xadrez_vermelho_cor.jpg",
                              img_normal=TEX / "tecido" / "tecido_normal.jpg", aspereza=0.8, brilho_tecido=0.4)
        M["bochecha"] = material(f"Mat_{N}_Bochecha", img_cor=TEXA / "pipoca_rosa_cor.jpg", **pel)
    else:
        M["pelo"] = material(f"Mat_{N}_Pelo", img_cor=TEXA / "pipoca_pelo_cor.jpg", **pel)
        M["pelo_sujo"] = material(f"Mat_{N}_Pelo_Sujo", img_cor=TEXA / "pipoca_pelo_sujo_cor.jpg", **pel)
        M["claro"] = material(f"Mat_{N}_Branco", img_cor=TEXA / "pipoca_branco_cor.jpg", **pel)
        M["claro_sujo"] = material(f"Mat_{N}_Branco_Sujo", img_cor=TEXA / "pipoca_branco_sujo_cor.jpg", **pel)
        M["rosa"] = material(f"Mat_{N}_Rosa", img_cor=TEXA / "pipoca_rosa_cor.jpg", **pel)
        M["plastico"] = material(f"Mat_{N}_Plastico", img_cor=TEXA / "plastico_branco_cor.jpg", aspereza=0.38)
        M["iris"] = material(f"Mat_Olho_{N}", cor=(1.0, 0.12, 0.55), emissao=(1.0, 0.08, 0.5), forca_emissao=2.5, aspereza=0.2)
        M["nariz"] = material(f"Mat_{N}_Nariz", cor=(0.85, 0.35, 0.5), aspereza=0.3)
        M["laco"] = material(f"Mat_{N}_Laco", img_cor=TEXA / "laco_bolinhas_cor.jpg",
                             img_normal=TEX / "tecido" / "tecido_normal.jpg", aspereza=0.7, brilho_tecido=0.4)
        M["tutu"] = material(f"Mat_{N}_Tutu", img_cor=TEXA / "tutu_cor.jpg",
                             img_normal=TEX / "tecido" / "tecido_normal.jpg", aspereza=0.7, brilho_tecido=0.7)
        M["bochecha"] = M["rosa"]
    M["dentes"] = material("Mat_Animatronico_Dentes", img_cor=TEXA / "dentes_cor.jpg", aspereza=0.35)
    M["olho"] = material("Mat_Animatronico_Olho", cor=(0.92, 0.91, 0.88), aspereza=0.15)
    M["pupila"] = material("Mat_Animatronico_Pupila", cor=(0.005, 0.005, 0.005), aspereza=0.1)
    M["forro"] = material("Mat_Animatronico_Forro", cor=(0.04, 0.035, 0.03), aspereza=0.95)
    M["metal_claro"] = material("Mat_Endo_Metal_Claro", img_cor=TEX / "metal_escovado" / "metal_escovado_cor.jpg",
                                img_normal=TEX / "metal_escovado" / "metal_escovado_normal.jpg",
                                img_aspereza=TEX / "metal_escovado" / "metal_escovado_aspereza.jpg", metal=1.0)
    M["metal_escuro"] = material("Mat_Endo_Metal_Escuro", img_cor=TEXA / "metal_escuro_cor.jpg",
                                 img_normal=TEX / "metal_escovado" / "metal_escovado_normal.jpg", aspereza=0.55, metal=0.85)
    M["arame"] = material("Mat_Endo_Arame", cor=(0.55, 0.5, 0.42), metal=1.0, aspereza=0.45)
    tamanhos = {"lenco": 0.3, "laco": 0.22, "plastico": 0.5, "dentes": 0.2, "metal_claro": 0.3, "metal_escuro": 0.4,
                "gravata": 0.3, "tutu": 0.4}
    for k, m in M.items():
        m["metros_por_repeticao"] = tamanhos.get(k, 0.32)
    return M


# ---------------------------------------------------------------------------------------------
# Geometria

def base_osso(u):
    """(u, lado, frente) ortonormais para um osso com direção u."""
    f = FRENTE.copy()
    if abs(u.dot(f)) > 0.7:
        f = CIMA.copy()
    s = f.cross(u).normalized()
    f = u.cross(s).normalized()
    return u, s, f


def torno(h, u, s, f, perfil, ks=1.0, kf=1.0, segs=24, onda=None):
    """
    Sólido de revolução ao longo de u a partir de h. perfil: [(a, r, desloc_frente)].
    Seção elíptica: raio r*ks no eixo s e r*kf no eixo f. onda(θ) multiplica o raio (babados).
    Raio 0 na primeira/última amostra = ponta fechada.
    """
    bm = bmesh.new()
    aneis = []
    for (a, r, df) in perfil:
        c = h + u * a + f * df
        if r < 1e-5:
            aneis.append([bm.verts.new(c)])
            continue
        anel = []
        for k in range(segs):
            th = 2 * math.pi * k / segs
            m = onda(th) if onda else 1.0
            anel.append(bm.verts.new(c + s * (math.cos(th) * r * ks * m) + f * (math.sin(th) * r * kf * m)))
        aneis.append(anel)
    for i in range(len(aneis) - 1):
        A, B = aneis[i], aneis[i + 1]
        if len(A) == 1 and len(B) > 1:
            for k in range(segs):
                bm.faces.new((A[0], B[(k + 1) % segs], B[k]))
        elif len(B) == 1 and len(A) > 1:
            for k in range(segs):
                bm.faces.new((A[k], A[(k + 1) % segs], B[0]))
        elif len(A) > 1:
            for k in range(segs):
                bm.faces.new((A[k], A[(k + 1) % segs], B[(k + 1) % segs], B[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def capsula(a0, a1, r0, r1, bojo=0.0, n=8, ponta=0.9, df=None, ponta_fim=None):
    """Perfil de cápsula (pontas arredondadas) de a0 a a1, raio r0→r1, com barriga 'bojo'."""
    df = df or (lambda t: 0.0)
    rc0 = min(r0, (a1 - a0) / 2) * ponta
    rc1 = min(r1, (a1 - a0) / 2) * (ponta if ponta_fim is None else ponta_fim)
    perfil = []
    for i in range(5):
        phi = math.pi / 2 * i / 4
        perfil.append((a0 + rc0 * (1 - math.cos(phi)), r0 * math.sin(phi), df(0.0)))
    for i in range(1, n):
        t = i / n
        a = a0 + rc0 + (a1 - rc1 - a0 - rc0) * t
        r = r0 + (r1 - r0) * t + bojo * math.sin(math.pi * t)
        perfil.append((a, r, df(t)))
    for i in range(4, -1, -1):
        phi = math.pi / 2 * i / 4
        perfil.append((a1 - rc1 * (1 - math.cos(phi)), r1 * math.sin(phi), df(1.0)))
    return perfil


def perfil_ovo(a0, a1, R, n=18, expo=0.5, assim=0.0, df=None):
    """
    Perfil liso tipo ovo de a0 a a1 (pontas fechadas). expo < 0.5 = mais "cilindro", 0.5 = elipse.
    assim > 0 deixa o fim mais largo que o começo (ex.: ombros), < 0 o contrário (ex.: barriga embaixo).
    """
    df = df or (lambda t: 0.0)
    perfil = []
    for i in range(n + 1):
        tt = i / n
        r = R * math.sin(math.pi * tt) ** expo * (1 + assim * (tt - 0.5) * 2)
        perfil.append((a0 + (a1 - a0) * tt, max(r, 0.0) if 0 < i < n else 0.0, df(tt)))
    return perfil


def elipsoide(c, rx, ry, rz, eixos=None, u_segs=32, v_segs=16):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=u_segs, v_segments=v_segs, radius=1.0)
    rot = eixos if eixos is not None else Matrix.Identity(3)
    for v in bm.verts:
        p = Vector((v.co.x * rx, v.co.y * ry, v.co.z * rz))
        v.co = c + rot @ p
    return bm


def caixa(c, tx, ty, tz, eixos=None):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    rot = eixos if eixos is not None else Matrix.Identity(3)
    for v in bm.verts:
        v.co = c + rot @ Vector((v.co.x * tx, v.co.y * ty, v.co.z * tz))
    return bm


def tubo(pontos, raio, lados=8):
    bm = bmesh.new()
    aneis = []
    for i, p in enumerate(pontos):
        t = (pontos[min(i + 1, len(pontos) - 1)] - pontos[max(i - 1, 0)]).normalized()
        a = t.cross(CIMA if abs(t.z) < 0.9 else Vector((1, 0, 0))).normalized()
        b = t.cross(a)
        aneis.append([bm.verts.new(p + (a * math.cos(k * 2 * math.pi / lados) + b * math.sin(k * 2 * math.pi / lados)) * raio)
                      for k in range(lados)])
    for i in range(len(aneis) - 1):
        for k in range(lados):
            bm.faces.new((aneis[i][k], aneis[i][(k + 1) % lados], aneis[i + 1][(k + 1) % lados], aneis[i + 1][k]))
    for anel in (aneis[0], aneis[-1]):
        bm.faces.new(anel)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def juntar(*bms):
    bm = bmesh.new()
    me = bpy.data.meshes.new("tmp")
    for b in bms:
        b.to_mesh(me)
        bm.from_mesh(me)
        b.free()
    bpy.data.meshes.remove(me)
    return bm


class Montador:
    def __init__(self, chave, arm, endo, M):
        self.chave = chave
        self.N = PERSONAGENS[chave]["Nome"]
        self.arm = arm
        self.endo = endo
        self.M = M
        self.pecas = []

    # --- ossos -------------------------------------------------------------------------------
    def osso(self, n):
        b = self.arm.data.bones[n]
        h, t = self.arm.matrix_world @ b.head_local, self.arm.matrix_world @ b.tail_local
        u = (t - h).normalized()
        return (h, t, (t - h).length) + base_osso(u)

    def pontos_endo(self, n):
        return [ob.matrix_world @ v.co for ob in self.endo if ob["osso"] == n for v in ob.data.vertices]

    def caixa_endo(self, nomes):
        ps = [p for n in nomes for p in self.pontos_endo(n)]
        mn = Vector((min(p.x for p in ps), min(p.y for p in ps), min(p.z for p in ps)))
        mx = Vector((max(p.x for p in ps), max(p.y for p in ps), max(p.z for p in ps)))
        return mn, mx

    def raio_endo(self, n, a, janela, ks=1.0, kf=1.0, df=0.0, lim_s=None):
        h, _t, _L, u, s, f = self.osso(n)
        r = 0.0
        for p in self.pontos_endo(n):
            d = p - h
            if lim_s is not None and abs(d.dot(s)) > lim_s:
                continue
            if abs(d.dot(u) - a) <= janela:
                r = max(r, math.hypot(d.dot(s) / ks, (d.dot(f) - df) / kf))
        return r

    def cobrir(self, n, perfil, ks, kf, folga, lim_s=None, nucleo=0.4):
        """Aumenta o perfil todo POR IGUAL até cobrir o metal (a forma continua lisa)."""
        rmax = max(p[1] for p in perfil)
        k = 1.0
        pior = None
        passo = abs(perfil[1][0] - perfil[0][0])
        for (a, r, df) in perfil:
            if r > nucleo * rmax:
                req = self.raio_endo(n, a, passo * 0.75, ks, kf, df, lim_s) + folga
                if req / r > k:
                    pior = (round(a, 3), round(req, 3), round(r, 3))
                k = max(k, req / r)
        print(f"[cobrir] {n}: x{k:.2f} (raio máx {rmax * k:.3f} m) pior (a, exigido, raio) = {pior}, L = {perfil[-1][0]:.3f}")
        return [(a, r * k, df) for (a, r, df) in perfil]

    def ajustar(self, n, perfil, ks, kf, folga, uniforme=False, lim_s=None):
        """
        Garante que a fantasia cubra o metal: aumenta o raio onde o endoesqueleto encosta, e depois
        SUAVIZA o perfil (senão cada junta do metal vira um "gomo" na pelúcia).
        As amostras das pontas arredondadas (as 4 primeiras e as 4 últimas) ficam como estão: ali é a fresta.
        """
        ini, fim = 4, len(perfil) - 4
        req = [0.0] * len(perfil)
        for i in range(ini, fim):
            a, r, df = perfil[i]
            req[i] = self.raio_endo(n, a, 0.03, ks, kf, df, lim_s) + folga
        # dilata (o raio exigido vale num trecho em volta) e suaviza algumas vezes
        aa = [p[0] for p in perfil]
        req2 = [max([req[j] for j in range(ini, fim) if abs(aa[j] - aa[i]) < 0.07] or [0.0]) if ini <= i < fim else 0.0
                for i in range(len(perfil))]
        if uniforme:
            # membros: o raio exigido vale no comprimento todo (a forma de "barril" se mantém)
            rmax_design = max(p[1] for p in perfil)
            rq = max(req2)
            req2 = [rq * perfil[i][1] / rmax_design if ini <= i < fim else 0.0 for i in range(len(perfil))]
        r = [max(p[1], q) if ini <= i < fim else p[1] for i, (p, q) in enumerate(zip(perfil, req2))]
        for _ in range(6):
            s = r[:]
            for i in range(ini, fim):
                s[i] = (r[i - 1] + 2 * r[i] + r[i + 1]) / 4
            r = [max(s[i], req2[i], perfil[i][1]) if ini <= i < fim else r[i] for i in range(len(r))]
        # as pontas acompanham o novo raio da primeira/última seção
        for i in range(ini):
            f0 = r[ini] / max(perfil[ini][1], 1e-6)
            r[i] = perfil[i][1] * f0
        for i in range(fim, len(perfil)):
            f1 = r[fim - 1] / max(perfil[fim - 1][1], 1e-6)
            r[i] = perfil[i][1] * f1
        return [(a, ri, df) for (a, _r, df), ri in zip(perfil, r)]

    # --- peças -------------------------------------------------------------------------------
    def peca(self, nome, bm, mats, osso, liso=True, uv_tam=None, casca=0.0, cortes=()):
        me = bpy.data.meshes.new(nome)
        bm.to_mesh(me)
        bm.free()
        for m in (mats if isinstance(mats, (list, tuple)) else [mats]):
            me.materials.append(m)
        ob = bpy.data.objects.new(nome, me)
        bpy.context.scene.collection.objects.link(ob)
        for p in me.polygons:
            p.use_smooth = liso
        if casca:
            mod = ob.modifiers.new("casca", "SOLIDIFY")
            mod.thickness = casca
            mod.offset = -1
            mod.use_rim = True
            me.materials.append(self.M["forro"])
            mod.material_offset = len(me.materials) - 1
            mod.material_offset_rim = len(me.materials) - 1
        cortadores = []
        for bmc in cortes:
            mc = bpy.data.meshes.new("corte")
            bmc.to_mesh(mc)
            bmc.free()
            oc = bpy.data.objects.new("corte", mc)
            bpy.context.scene.collection.objects.link(oc)
            oc.hide_render = True
            mod = ob.modifiers.new("corte", "BOOLEAN")
            mod.operation = "DIFFERENCE"
            mod.solver = "EXACT"
            mod.object = oc
            cortadores.append(oc)
        if ob.modifiers:
            bpy.context.view_layer.update()
            deps = bpy.context.evaluated_depsgraph_get()
            novo = bpy.data.meshes.new_from_object(ob.evaluated_get(deps))
            ob.modifiers.clear()
            velho = ob.data
            ob.data = novo
            bpy.data.meshes.remove(velho)
            for oc in cortadores:
                bpy.data.meshes.remove(oc.data)
        uv_caixa(ob)
        E.prender_no_osso(ob, self.arm, osso)
        self.pecas.append(ob)
        return ob


def uv_caixa(ob):
    """UV em escala de metro (projeção em caixa), usando o tamanho de repetição de cada material."""
    me = ob.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uv = me.uv_layers.active.data
    m = ob.matrix_world
    for p in me.polygons:
        mat = me.materials[p.material_index] if p.material_index < len(me.materials) else None
        tam = mat.get("metros_por_repeticao", 0.35) if mat else 0.35
        n = (m.to_3x3() @ p.normal)
        eixo = max(range(3), key=lambda i: abs(n[i]))
        for li in p.loop_indices:
            co = m @ me.vertices[me.loops[li].vertex_index].co
            if eixo == 2:
                a, b = co.x, co.y
            elif eixo == 0:
                a, b = co.y, co.z
            else:
                a, b = co.x, co.z
            uv[li].uv = (a / tam, b / tam)


# ---------------------------------------------------------------------------------------------
# Montagem

def preparar_rig(chave):
    cfg = PERSONAGENS[chave]
    objs, ossos = E.preparar(RAIZ)
    fatores = dict(cfg["ossos"])
    for n in CABECA_SEGUE:
        fatores[n] = fatores["cabeca"]
    ossos2 = E.mudar_proporcoes(objs, ossos, fatores)
    zs = [v.co.z for ob in objs for v in ob.data.vertices]
    escala = cfg["altura"] / (max(zs) - min(zs))
    arm = E.criar_armature(f"{cfg['Nome']}_Rig", ossos2, objs, escala)
    arm.data.display_type = "STICK"
    return arm, objs, escala


def materiais_endo(endo, M):
    troca = {"LightMetal": M["metal_claro"], "DarkMetal": M["metal_escuro"], "Teeth": M["dentes"], "Eye": M["olho"]}
    for ob in endo:
        for i, m in enumerate(ob.data.materials):
            if m and m.name.split(".")[0] in troca:
                ob.data.materials[i] = troca[m.name.split(".")[0]]
        for p in ob.data.polygons:
            p.use_smooth = False
        uv_caixa(ob)
        ob.name = f"Endo_{ob['osso']}_{ob.name.rsplit('_', 1)[-1]}"


def adicionar_osso(arm, nome, cabeca, cauda, pai):
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    e = arm.data.edit_bones.new(nome)
    e.head, e.tail = cabeca, cauda
    e.align_roll(FRENTE)
    e.parent = arm.data.edit_bones[pai]
    bpy.ops.object.mode_set(mode="OBJECT")


def membro(mt, nome_osso, nome_peca, r0, r1, folga_junta, ks=1.0, kf=1.0, bojo=0.0, mat="pelo", mat_ponta=None,
           inicio=None, fim=None, casca=0.0, cortes=()):
    h, _t, L, u, s, f = mt.osso(nome_osso)
    a0 = folga_junta if inicio is None else inicio
    a1 = L - folga_junta if fim is None else fim
    perfil = mt.cobrir(nome_osso, perfil_ovo(a0, a1, max(r0, r1) + bojo, expo=0.42, assim=(r1 - r0) / max(r0, r1)), ks, kf, 0.012)
    bm = torno(h, u, s, f, perfil, ks, kf)
    mats = [mt.M[mat]]
    if mat_ponta:
        # bordas (perto das juntas) mais sujas e gastas
        mats.append(mt.M[mat_ponta])
        for face in bm.faces:
            a = (face.calc_center_median() - h).dot(u)
            if a < a0 + 0.035 or a > a1 - 0.035:
                face.material_index = 1
    return mt.peca(f"{mt.N}_{nome_peca}", bm, mats, nome_osso, casca=casca, cortes=cortes)


def mao(mt, lado, tam_dedo, sujo="pelo_sujo"):
    n = f"mao.{lado}"
    h, _t, L, u, s, f = mt.osso(n)
    ps = mt.pontos_endo(n)
    al = [(p - h).dot(u) for p in ps]
    ss = [(p - h).dot(s) for p in ps]
    ff = [(p - h).dot(f) for p in ps]
    A = max(al)
    # eixo largo (onde os dedos se abrem) e eixo fino (espessura da mão)
    largo_s = (max(ss) - min(ss)) > (max(ff) - min(ff))
    eixo_l, eixo_e = (s, f) if largo_s else (f, s)
    lmin, lmax = (min(ss), max(ss)) if largo_s else (min(ff), max(ff))
    emin, emax = (min(ff), max(ff)) if largo_s else (min(ss), max(ss))
    centro_l, centro_e = (lmin + lmax) / 2, (emin + emax) / 2
    meia_l = (lmax - lmin) / 2 + 0.02
    meia_e = (emax - emin) / 2 + 0.02
    partes = []
    hp = h + eixo_l * centro_l + eixo_e * centro_e
    # palma
    partes.append(torno(hp, u, eixo_l, eixo_e, capsula(0.02, A * 0.62, meia_l * 0.8, meia_l, 0.0),
                        1.0, meia_e / meia_l))
    # 4 dedos gordinhos
    for i in range(4):
        off = (-0.75 + 0.5 * i) * meia_l
        comp = A * (1.0 if i in (1, 2) else 0.9) + tam_dedo
        partes.append(torno(hp + eixo_l * off, u, eixo_l, eixo_e,
                            capsula(A * 0.45, comp, meia_l * 0.27, meia_l * 0.25), 1.0, meia_e / (meia_l * 0.27) * 0.9 / 1.0 * 0.27 / 0.27))
    # polegar: sai da palma para a frente do corpo
    lado_pol = FRENTE if eixo_l.dot(FRENTE) == 0 else (eixo_l if eixo_l.dot(FRENTE) > 0 else -eixo_l)
    up = (u * 0.5 + lado_pol).normalized()
    _u2, s2, f2 = base_osso(up)
    partes.append(torno(hp + u * (A * 0.25) + lado_pol * meia_l * 0.6, up, s2, f2,
                        capsula(0.0, meia_l * 1.1, meia_e * 0.75, meia_e * 0.65)))
    return mt.peca(f"{mt.N}_Mao_{'Esq' if lado == 'L' else 'Dir'}", juntar(*partes), [mt.M[sujo]], n)


def pe(mt, lado, alongar, largura, altura, mat="pelo_sujo", mat_sola="claro_sujo"):
    n = f"pe.{lado}"
    h, _t, L, u, s, f = mt.osso(n)
    ps = mt.pontos_endo(n)
    al = [(p - h).dot(u) for p in ps]
    ss = [abs((p - h).dot(s)) for p in ps]
    fs = [(p - h).dot(f) for p in ps]
    A0, A1 = min(al), max(al)
    rs = max(max(ss) + 0.025, largura)
    rf = max((max(fs) - min(fs)) / 2 + 0.03, altura)
    centro_f = (max(fs) + min(fs)) / 2 + 0.01
    perfil = capsula(A0 - 0.06, A1 * alongar + 0.03, rf * 0.9, rf, 0.15 * rf, df=lambda t: centro_f)
    bm = torno(h, u, s, f, [(a, r, df) for (a, r, df) in perfil], rs / rf, 1.0)
    # sola mais clara (a parte de baixo, em contato com o chão)
    for face in bm.faces:
        if face.normal.z < -0.6:
            face.material_index = 1
    return mt.peca(f"{mt.N}_Pe_{'Esq' if lado == 'L' else 'Dir'}", bm, [mt.M[mat], mt.M[mat_sola]], n)


def _pontos_material(mt, osso, nome_mat):
    """Pontos (mundo) só das faces que usam o material (os objetos do endoesqueleto têm vários materiais)."""
    ps = []
    for ob in mt.endo:
        if ob["osso"] != osso:
            continue
        mats = ob.data.materials
        mw = ob.matrix_world
        for poly in ob.data.polygons:
            m = mats[poly.material_index] if poly.material_index < len(mats) else None
            if m and m.name == nome_mat:
                ps += [mw @ ob.data.vertices[i].co for i in poly.vertices]
    return ps


def frente_elipsoide(c, raios, x, z):
    """y da superfície da frente (−Y) de um elipsoide no ponto (x, z)."""
    k = 1 - ((x - c.x) / raios[0]) ** 2 - ((z - c.z) / raios[2]) ** 2
    return c.y - raios[1] * math.sqrt(max(0.0, k))


def cabeca(mt, raios, desloc):
    """
    Casca da cabeça (pelúcia com forro escuro por dentro), com buracos dos olhos e da boca.
    Devolve as medidas do rosto para o focinho, o queixo e as bochechas.
    """
    M = mt.M
    mn, mx = mt.caixa_endo(["cabeca", "olho.L", "olho.R"])
    c = (mn + mx) / 2 + Vector(desloc)
    olhos = {}
    for lado in ("L", "R"):
        ps = mt.pontos_endo(f"olho.{lado}")
        oc = sum(ps, Vector()) / len(ps)
        r = (max(p.x for p in ps) - min(p.x for p in ps)) / 2
        y_frente = min(p.y for p in ps)
        olhos[lado] = (Vector((oc.x, oc.y, oc.z)), r, y_frente)
    dsup = _pontos_material(mt, "cabeca", "Mat_Animatronico_Dentes")
    dinf = _pontos_material(mt, "mandibula", "Mat_Animatronico_Dentes")
    mand_mn, mand_mx = mt.caixa_endo(["mandibula"])
    rosto = {
        "c": c, "olhos": olhos,
        "dsup_z": (min(p.z for p in dsup), max(p.z for p in dsup)),
        "dinf_z": (min(p.z for p in dinf), max(p.z for p in dinf)),
        "dentes_y": min(p.y for p in dsup + dinf),
        "dentes_x": max(abs(p.x) for p in dsup + dinf),
        "mand": (mand_mn, mand_mx),
    }
    # a casca precisa cobrir o metal da cabeça (menos a frente, que tem olhos e boca)
    rx, ry, rz = raios
    for p in mt.pontos_endo("cabeca"):
        if p.y < c.y - ry * 0.3:
            continue
        k = ((p.x - c.x) / rx) ** 2 + ((p.y - c.y) / ry) ** 2 + ((p.z - c.z) / rz) ** 2
        if k > 0.9:
            f = math.sqrt(k / 0.9)
            rx, rz = rx * (1 + (f - 1) * abs(p.x - c.x) / max(abs(p.x - c.x) + abs(p.z - c.z), 1e-6)), \
                rz * (1 + (f - 1) * abs(p.z - c.z) / max(abs(p.x - c.x) + abs(p.z - c.z), 1e-6))
    raios = (rx, ry, rz)
    cortes = []
    for lado, (oc, r, yf) in olhos.items():
        # buraco do olho: o olho fica um pouco afundado na pelúcia
        cortes.append(elipsoide(Vector((oc.x, yf + r * 0.25, oc.z)), r * 1.05, r * 0.9, r * 1.0))
    # boca: abertura na frente, da base do queixo até os dentes de cima
    z0, z1 = mand_mn.z - 0.01, rosto["dsup_z"][1] + 0.005
    zm = (z0 + z1) / 2
    cortes.append(elipsoide(Vector((0, frente_elipsoide(c, raios, 0, zm), zm)), rosto["dentes_x"] + 0.03, 0.16, (z1 - z0) / 2,
                            None, 32, 16))
    # pescoço
    cortes.append(elipsoide(Vector((c.x, c.y, c.z - raios[2])), raios[0] * 0.42, raios[1] * 0.42, raios[2] * 0.3))
    rosto["raios"] = raios
    mt.peca(f"{mt.N}_Cabeca", elipsoide(c, *raios, u_segs=40, v_segs=22), [M["pelo"]], "cabeca", casca=0.018, cortes=cortes)
    for lado, (oc, r, yf) in olhos.items():
        nome_lado = "Esq" if lado == "L" else "Dir"
        # íris (brilha) e pupila, coladas na frente do olho do endoesqueleto e presas no osso do olho
        mt.peca(f"{mt.N}_Iris_{nome_lado}", elipsoide(Vector((oc.x, yf + r * 0.035, oc.z)), r * 0.56, r * 0.05, r * 0.56, None, 24, 12),
                [M["iris"]], f"olho.{lado}")
        mt.peca(f"{mt.N}_Pupila_{nome_lado}", elipsoide(Vector((oc.x, yf + r * 0.01, oc.z)), r * 0.22, r * 0.04, r * 0.28, None, 16, 8),
                [M["pupila"]], f"olho.{lado}")
        # pálpebras de pelúcia sobre as de metal do endoesqueleto (mesmo osso, um pouco maiores)
        for qual in ("sup", "inf"):
            for ob in [o for o in mt.endo if o["osso"] == f"palpebra_{qual}.{lado}"]:
                bmp = bmesh.new()
                bmp.from_mesh(ob.data)
                mw = ob.matrix_world
                for v in bmp.verts:
                    v.co = oc + ((mw @ v.co) - oc) * 1.08
                mt.peca(f"{mt.N}_Palpebra_{qual.capitalize()}_{nome_lado}", bmp, [M["pelo"]], f"palpebra_{qual}.{lado}")
    return rosto


def focinho(mt, rosto, larg, alt, prof, nariz_r, cor_nariz="nariz", dentinhos=False, mat_queixo="plastico"):
    """Focinho de plástico (preso na cabeça, logo acima dos dentes) e queixo (preso na mandíbula)."""
    M = mt.M
    c, raios = rosto["c"], rosto["raios"]
    zs0, zs1 = rosto["dsup_z"]
    # focinho: a base fica no meio dos dentes de cima (as pontas dos dentes aparecem embaixo)
    zf = (zs0 + zs1) / 2 + alt
    yf = frente_elipsoide(c, raios, 0, zf) - prof * 0.45
    cf = Vector((0, yf, zf))
    mt.peca(f"{mt.N}_Focinho", elipsoide(cf, larg, prof, alt), [M["plastico"]], "cabeca")
    mt.peca(f"{mt.N}_Nariz", elipsoide(cf + Vector((0, -prof * 0.88, alt * 0.45)), nariz_r * 1.3, nariz_r * 0.8, nariz_r * 0.9),
            [M[cor_nariz]], "cabeca")
    if dentinhos:
        for x in (-1, 1):
            d = caixa(Vector((x * larg * 0.12, yf - prof * 0.5, zf - alt - 0.012)), larg * 0.2, 0.01, 0.032)
            mt.peca(f"{mt.N}_Dentinho_{'Esq' if x > 0 else 'Dir'}", d, [M["dentes"]], "cabeca", liso=False)
    # queixo: embaixo dos dentes de baixo
    zi0, zi1 = rosto["dinf_z"]
    altq = alt * 0.62
    zq = zi0 + 0.004 - altq * 0.55
    yq = min(frente_elipsoide(c, raios, 0, zq), rosto["dentes_y"]) - prof * 0.15
    mt.peca(f"{mt.N}_Queixo", elipsoide(Vector((0, yq + prof * 0.35, zq)), larg * 0.85, prof * 0.8, altq), [M[mat_queixo]], "mandibula")
    # fundo da boca escuro (preso no queixo, para a boca aberta não mostrar o vazio)
    mt.peca(f"{mt.N}_Boca_Fundo", elipsoide(Vector((0, rosto["dentes_y"] + 0.05, (zi0 + zs1) / 2)), rosto["dentes_x"] + 0.01, 0.035,
                                             (zs1 - zi0) / 2 + 0.01, None, 16, 8), [M["forro"]], "mandibula")


def bochechas(mt, c_cab, raios, x, z, r):
    for lado in (-1, 1):
        p = Vector((c_cab.x + lado * x, 0, z))
        # encosta na superfície da cabeça
        dy = raios[1] * math.sqrt(max(0.0, 1 - (lado * x / raios[0]) ** 2 - ((z - c_cab.z) / raios[2]) ** 2))
        p.y = c_cab.y - dy + r * 0.25
        eixos = Matrix.Rotation(math.radians(-lado * 30), 3, "Z")
        mt.peca(f"{mt.N}_Bochecha_{'Esq' if lado > 0 else 'Dir'}", elipsoide(p, r, r * 0.35, r * 0.75, eixos, 20, 10),
                [mt.M["bochecha"]], "cabeca")


def limite_ombro(mt):
    """Até onde (para o lado) o peito da fantasia precisa cobrir o metal: o resto fica na fresta do ombro."""
    h, _t, _L, _u, s, _f = mt.osso("tronco")
    hb = mt.osso("braco.L")[0]
    return abs((hb - h).dot(s)) * 0.84


def montar_tito(mt):
    M = mt.M
    # Tronco: barrigão (o maior volume do Tito)
    h, _t, L, u, s, f = mt.osso("tronco")
    perfil = perfil_ovo(-0.01, L * 1.16, 0.33, n=22, expo=0.5, assim=-0.05,
                        df=lambda t: 0.07 * math.sin(math.pi * min(1, t * 1.3)))
    perfil = mt.cobrir("tronco", perfil, 1.12, 0.95, 0.03, lim_s=limite_ombro(mt))
    mt.peca("Tito_Tronco", torno(h, u, s, f, perfil, 1.12, 0.95), [M["pelo"]], "tronco")
    # raio do tronco perto do pescoço (a gola do lenço abraça esse ponto)
    # gola do lenço: onde o tronco encontra a cabeça
    mt.a_gola = L * 0.93
    mt.r_gola = min(perfil, key=lambda p: abs(p[0] - mt.a_gola))[1] * 1.12
    # barriga de plástico creme, encostada na frente do tronco
    ab, rb, dfb = min(perfil, key=lambda p: abs(p[0] - L * 0.4))
    cb = h + u * ab + f * (rb * 0.95 + dfb - 0.05)
    mt.peca("Tito_Barriga", elipsoide(cb, rb * 1.12 * 0.68, 0.09, L * 0.34, Matrix((s, f, u)).transposed()),
            [M["claro_sujo"]], "tronco")
    # Quadril (calção de pelúcia)
    h, _t, L, u, s, f = mt.osso("quadril")
    perfil = mt.cobrir("quadril", perfil_ovo(-0.17, L - 0.035, 0.2, expo=0.55, assim=0.15), 1.15, 0.95, 0.03,
                       nucleo=0.8)
    mt.peca("Tito_Quadril", torno(h, u, s, f, perfil, 1.2, 0.95), [M["pelo"]], "quadril")
    # Braços e pernas grossos e curtos
    for lado, ns in (("L", "Esq"), ("R", "Dir")):
        membro(mt, f"braco.{lado}", f"Braco_{ns}", 0.105, 0.095, 0.028, bojo=0.012, mat_ponta="pelo_sujo")
        membro(mt, f"antebraco.{lado}", f"Antebraco_{ns}", 0.095, 0.085, 0.026, bojo=0.008, mat_ponta="pelo_sujo")
        membro(mt, f"coxa.{lado}", f"Coxa_{ns}", 0.15, 0.13, 0.03, bojo=0.015, mat_ponta="pelo_sujo")
        membro(mt, f"canela.{lado}", f"Canela_{ns}", 0.13, 0.12, 0.03, bojo=0.012, mat_ponta="pelo_sujo")
        mao(mt, lado, 0.02)
        pe(mt, lado, 1.05, 0.13, 0.09)
    # Cabeça redonda e grande
    mn, mx = mt.caixa_endo(["cabeca", "olho.L", "olho.R"])
    larg = (mx.x - mn.x) / 2
    raios = (larg * 1.32, larg * 1.12, larg * 1.22)
    rosto = cabeca(mt, raios, (0, 0.03, -0.01))
    c, raios = rosto["c"], rosto["raios"]
    focinho(mt, rosto, larg * 0.6, larg * 0.3, larg * 0.36, larg * 0.15)
    bochechas(mt, c, raios, larg * 0.95, c.z - raios[2] * 0.2, larg * 0.2)
    # orelhas redondas pequenas (osso próprio, para tremer na animação)
    for lado, sx in (("L", 1), ("R", -1)):
        base = c + Vector((sx * raios[0] * 0.66, 0.0, raios[2] * 0.74))
        dirc = Vector((sx * 0.55, 0, 0.85)).normalized()
        adicionar_osso(mt.arm, f"orelha.{lado}", base, base + dirc * larg * 0.5, "cabeca")
        eixos = Matrix((dirc.cross(FRENTE).normalized(), -FRENTE, dirc)).transposed()
        ce = base + dirc * larg * 0.28
        mt.peca(f"Tito_Orelha_{'Esq' if lado == 'L' else 'Dir'}", elipsoide(ce, larg * 0.36, larg * 0.14, larg * 0.32, eixos, 24, 12),
                [M["pelo"]], f"orelha.{lado}")
        mt.peca(f"Tito_Orelha_Dentro_{'Esq' if lado == 'L' else 'Dir'}",
                elipsoide(ce + FRENTE * larg * 0.09, larg * 0.22, larg * 0.06, larg * 0.2, eixos, 20, 10), [M["claro"]], f"orelha.{lado}")
    # chapéu de pizzaiolo (um pouco torto)
    topo = c + Vector((0, 0.01, raios[2] * 0.86))
    ct = Matrix.Rotation(math.radians(-8), 3, "Y")
    uc = ct @ CIMA
    _u, sc, fc = base_osso(uc)
    faixa = [(0.0, 0.0, 0), (0.0, larg * 0.62, 0), (larg * 0.34, larg * 0.66, 0), (larg * 0.36, 0.0, 0)]
    mt.peca("Tito_Chapeu_Faixa", torno(topo, uc, sc, fc, faixa, 1.0, 0.95), [M["chapeu_sujo"]], "cabeca")
    copa = [(larg * 0.3, 0.0, 0), (larg * 0.3, larg * 0.6, 0), (larg * 0.45, larg * 0.78, 0), (larg * 0.7, larg * 0.86, 0),
            (larg * 0.92, larg * 0.78, 0), (larg * 1.05, larg * 0.5, 0), (larg * 1.08, 0.0, 0)]
    mt.peca("Tito_Chapeu", torno(topo, uc, sc, fc, copa, 1.0, 0.95, segs=32, onda=lambda th: 1 + 0.05 * math.cos(6 * th)),
            [M["chapeu"]], "cabeca")
    # gravata-borboleta e lenço xadrez no pescoço (presos no tronco)
    h, t, L, u, s, f = mt.osso("tronco")
    rt = mt.r_gola / 0.6
    pescoco_c = h + u * mt.a_gola
    gola = [(-0.045, 0.0, 0.0), (-0.045, rt * 0.62, 0.0), (0.0, rt * 0.66, 0.0), (0.035, rt * 0.56, 0.0), (0.035, 0.0, 0.0)]
    mt.peca("Tito_Lenco", torno(pescoco_c - u * 0.03, u, s, f, gola, 1.1, 1.0, segs=28), [M["lenco"]], "tronco")
    ponta_ini = pescoco_c - u * 0.04 + f * (rt * 0.6)
    tri = bmesh.new()
    vs = [tri.verts.new(p) for p in (ponta_ini + s * rt * 0.42, ponta_ini - s * rt * 0.42, ponta_ini - u * rt * 0.62 + f * 0.04,
                                         ponta_ini + s * rt * 0.42 - f * 0.02, ponta_ini - s * rt * 0.42 - f * 0.02,
                                         ponta_ini - u * rt * 0.62 + f * 0.02)]
    tri.faces.new((vs[0], vs[1], vs[2]))
    tri.faces.new((vs[5], vs[4], vs[3]))
    for a, b in ((0, 1), (1, 2), (2, 0)):
        tri.faces.new((vs[a], vs[b], vs[b + 3], vs[a + 3]))
    bmesh.ops.recalc_face_normals(tri, faces=tri.faces)
    mt.peca("Tito_Lenco_Ponta", tri, [M["lenco"]], "tronco", liso=False)
    cg = pescoco_c + f * (rt * 0.68) + u * 0.0
    eixos = Matrix((s, f, u)).transposed()
    gr = rt * 0.15
    partes = [elipsoide(cg, gr * 0.42, gr * 0.4, gr * 0.42, eixos, 16, 8)]
    for lado in (-1, 1):
        rot = eixos @ Matrix.Rotation(math.radians(lado * 8), 3, "Y")
        partes.append(elipsoide(cg + s * (lado * gr * 0.95), gr * 0.95, gr * 0.32, gr * 0.62, rot, 20, 10))
    mt.peca("Tito_Gravata", juntar(*partes), [M["gravata"]], "tronco")


def montar_pipoca(mt):
    M = mt.M
    h, _t, L, u, s, f = mt.osso("tronco")
    perfil = perfil_ovo(0.0, L * 1.03, 0.13, n=22, expo=0.4, assim=0.08)
    perfil = mt.cobrir("tronco", perfil, 1.15, 0.8, 0.02, lim_s=limite_ombro(mt))
    mt.peca("Pipoca_Tronco", torno(h, u, s, f, perfil, 1.15, 0.8), [M["pelo"]], "tronco")
    # barriga branca de plástico, encostada na frente do tronco
    ab, rb, dfb = min(perfil, key=lambda p: abs(p[0] - L * 0.4))
    cb = h + u * ab + f * (rb * 0.8 + dfb - 0.03)
    mt.peca("Pipoca_Barriga", elipsoide(cb, rb * 1.15 * 0.62, 0.05, L * 0.3, Matrix((s, f, u)).transposed()),
            [M["claro_sujo"]], "tronco")
    h, _t, L, u, s, f = mt.osso("quadril")
    perfil = mt.cobrir("quadril", perfil_ovo(-0.07, L - 0.03, 0.15, expo=0.45, assim=0.1), 1.2, 0.85, 0.02)
    mt.peca("Pipoca_Quadril", torno(h, u, s, f, perfil, 1.2, 0.85), [M["pelo"]], "quadril")
    # tutu de tule com babados
    rq = max(r for (_a, r, _d) in perfil)
    for i, (a, r0, r1) in enumerate(((L * 0.95, rq * 1.15, rq * 2.0), (L * 0.75, rq * 1.1, rq * 1.75))):
        tutu = [(a, 0.0, 0), (a, rq * 1.05, 0), (a - 0.03, r0, 0), (a - 0.11, r1, 0), (a - 0.135, r1 * 0.96, 0),
                (a - 0.03, rq * 0.98, 0), (a - 0.01, 0.0, 0)]
        mt.peca(f"Pipoca_Tutu_{i + 1}", torno(h, u, s, f, tutu, 1.15, 0.9, segs=48,
                                               onda=lambda th, i=i: 1 + 0.07 * math.cos(14 * th + i)), [M["tutu"]], "quadril")
    for lado, ns in (("L", "Esq"), ("R", "Dir")):
        membro(mt, f"braco.{lado}", f"Braco_{ns}", 0.058, 0.05, 0.03, mat_ponta="pelo_sujo")
        membro(mt, f"antebraco.{lado}", f"Antebraco_{ns}", 0.05, 0.046, 0.03, mat_ponta="pelo_sujo")
        cortes = ()
        if lado == "L":
            # rasgo na coxa esquerda: buraco com borda irregular mostrando o endoesqueleto
            hc, _tc, Lc, uc, sc, fc = mt.osso("coxa.L")
            centro = hc + uc * (Lc * 0.5) + fc * 0.06 + sc * 0.02
            rasgo = elipsoide(centro, 0.045, 0.07, 0.085, None, 16, 10)
            rnd = random.Random(3)
            for v in rasgo.verts:
                v.co = centro + (v.co - centro) * rnd.uniform(0.75, 1.2)
            cortes = (rasgo,)
        membro(mt, f"coxa.{lado}", f"Coxa_{ns}", 0.085, 0.07, 0.035, mat_ponta="pelo_sujo",
               casca=0.012 if cortes else 0.0, cortes=cortes)
        membro(mt, f"canela.{lado}", f"Canela_{ns}", 0.07, 0.058, 0.035, mat_ponta="pelo_sujo")
        mao(mt, lado, 0.025)
        pe(mt, lado, 1.55, 0.075, 0.06)
    # cabeça um pouco oval, focinho pequeno e dentinhos de coelha
    mn, mx = mt.caixa_endo(["cabeca", "olho.L", "olho.R"])
    larg = (mx.x - mn.x) / 2
    raios = (larg * 1.15, larg * 1.05, larg * 1.25)
    rosto = cabeca(mt, raios, (0, 0.02, 0.0))
    c, raios = rosto["c"], rosto["raios"]
    focinho(mt, rosto, larg * 0.5, larg * 0.27, larg * 0.32, larg * 0.1, dentinhos=True, mat_queixo="plastico")
    bochechas(mt, c, raios, larg * 0.82, c.z - raios[2] * 0.25, larg * 0.18)
    # orelhas compridas e caídas: base (sobe) + ponta (cai até o ombro); a esquerda rasgada com o arame
    for lado, sx in (("L", 1), ("R", -1)):
        ns = "Esq" if lado == "L" else "Dir"
        base = c + Vector((sx * raios[0] * 0.5, 0.02, raios[2] * 0.86))
        d1 = Vector((sx * 0.72, 0.08, 0.69)).normalized()
        meio = base + d1 * larg * 0.62
        d2 = Vector((sx * 0.2, 0.1, -0.97)).normalized()
        _ht, ombro, *_r = mt.osso("tronco")
        ponta = meio + d2 * ((meio.z - (ombro.z + 0.06)) / -d2.z)
        adicionar_osso(mt.arm, f"orelha.{lado}", base, meio, "cabeca")
        adicionar_osso(mt.arm, f"orelha_ponta.{lado}", meio, ponta, f"orelha.{lado}")
        larg_o = larg * 0.36
        for nome_o, a, b, osso, r0, r1 in ((f"Orelha_{ns}", base, meio, f"orelha.{lado}", 0.75, 0.95),
                                           (f"Orelha_Ponta_{ns}", meio, ponta, f"orelha_ponta.{lado}", 0.95, 0.75)):
            uo = (b - a).normalized()
            fo = FRENTE - uo * FRENTE.dot(uo)
            fo.normalize()
            so = fo.cross(uo).normalized()
            Lo = (b - a).length
            fim = Lo * (0.62 if (lado == "L" and "Ponta" in nome_o) else 1.0) + 0.02
            perfil = capsula(-0.015 if "Ponta" not in nome_o else 0.015, fim, larg_o * r0, larg_o * r1, larg_o * 0.15)
            cortes = ()
            if lado == "L" and "Ponta" in nome_o:
                # ponta rasgada: corte irregular
                cc = a + uo * fim
                corte = elipsoide(cc, larg_o * 1.6, larg_o * 1.6, larg_o * 0.5, Matrix((so, fo, uo)).transposed(), 16, 8)
                rnd = random.Random(11)
                for v in corte.verts:
                    v.co += uo * rnd.uniform(-0.02, 0.02)
                cortes = (corte,)
            mt.peca(f"Pipoca_{nome_o}", torno(a, uo, so, fo, perfil, 1.0, 0.3), [M["pelo"]], osso, cortes=cortes)
            dentro = capsula(0.03, fim - 0.04, larg_o * r0 * 0.72, larg_o * r1 * 0.72)
            mt.peca(f"Pipoca_{nome_o}_Dentro", torno(a + fo * larg_o * 0.24, uo, so, fo, dentro, 1.0, 0.07),
                    [M["rosa"]], osso, cortes=())
        if lado == "L":
            # arame da orelha aparecendo depois do rasgo
            Lp = (ponta - meio).length
            pts = [meio + d2 * (Lp * t) for t in (0.3, 0.5, 0.62, 0.75, 0.86)]
            pts.append(pts[-1] + d2 * 0.04 + FRENTE * 0.03 + Vector((sx * 0.02, 0, 0)))
            pts.append(pts[-1] + FRENTE * 0.03 + CIMA * 0.03)
            mt.peca("Pipoca_Orelha_Arame", tubo(pts, 0.0045, 6), [M["arame"]], f"orelha_ponta.{lado}")
    # laço rosa de bolinhas no alto da cabeça
    cl = c + Vector((0, -raios[1] * 0.35, raios[2] * 0.93))
    eix = Matrix.Rotation(math.radians(-15), 3, "X")
    partes = [elipsoide(cl, larg * 0.16, larg * 0.14, larg * 0.14, eix, 16, 8)]
    for lado in (-1, 1):
        rot = eix @ Matrix.Rotation(math.radians(lado * 12), 3, "Y")
        partes.append(elipsoide(cl + Vector((lado * larg * 0.36, 0, 0.01)), larg * 0.36, larg * 0.11, larg * 0.24, rot, 24, 12))
    mt.peca("Pipoca_Laco", juntar(*partes), [M["laco"]], "cabeca")


def montar(chave):
    arm, endo, escala = preparar_rig(chave)
    M = materiais(chave)
    materiais_endo(endo, M)
    mt = Montador(chave, arm, endo, M)
    (montar_tito if chave == "tito" else montar_pipoca)(mt)
    # pés no chão: a fantasia pode passar um pouco do metal por baixo
    bpy.context.view_layer.update()
    zmin = min((ob.matrix_world @ v.co).z for ob in mt.pecas for v in ob.data.vertices)
    arm.location.z -= zmin
    bpy.context.view_layer.update()
    tris = sum(sum(len(p.vertices) - 2 for p in ob.data.polygons) for ob in endo + mt.pecas)
    zmax = max((ob.matrix_world @ v.co).z for ob in endo + mt.pecas for v in ob.data.vertices)
    print(f"[anim] {chave}: {len(endo)} peças de metal, {len(mt.pecas)} peças de fantasia, {tris} triângulos, "
          f"{len(arm.data.bones)} ossos, altura {zmax:.2f} m")
    return arm, endo, mt


# ---------------------------------------------------------------------------------------------
# Poses e renders

def girar(arm, osso, eixo, graus):
    """Gira o osso em torno de um eixo do MUNDO (na pose de descanso)."""
    pb = arm.pose.bones[osso]
    rest = (arm.matrix_world.to_3x3() @ pb.bone.matrix_local.to_3x3()).normalized()
    q_mundo = Matrix.Rotation(math.radians(graus), 3, Vector(eixo))
    local = rest.inverted() @ q_mundo @ rest
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = local.to_quaternion() @ pb.rotation_quaternion


def pose_descanso(arm, chave):
    """Braços para baixo (pose de exibição, em vez do T do arquivo)."""
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
    ang = 68 if chave == "tito" else 74
    girar(arm, "braco.L", (0, 1, 0), ang)
    girar(arm, "braco.R", (0, 1, 0), -ang)
    girar(arm, "antebraco.L", (0, 0, 1), -14)
    girar(arm, "antebraco.R", (0, 0, 1), 14)


def pose_teste(arm, chave):
    pose_descanso(arm, chave)
    girar(arm, "pescoco", (0, 0, 1), -22)
    girar(arm, "cabeca", (0, 1, 0), 12)
    girar(arm, "mandibula", (1, 0, 0), -28)
    girar(arm, "braco.R", (1, 0, 0), 75)       # braço direito para a frente
    girar(arm, "antebraco.R", (0, 0, 1), 40)
    girar(arm, "mao.R", (1, 0, 0), 25)
    girar(arm, "antebraco.L", (1, 0, 0), 75)   # cotovelo esquerdo dobrado
    girar(arm, "coxa.R", (1, 0, 0), 38)        # perna direita levantada
    girar(arm, "canela.R", (1, 0, 0), -62)
    girar(arm, "pe.R", (1, 0, 0), 20)
    girar(arm, "palpebra_sup.L", (1, 0, 0), 25)
    if chave == "pipoca":
        girar(arm, "orelha.R", (0, 1, 0), 25)
        girar(arm, "orelha_ponta.R", (0, 1, 0), -35)


def estudio():
    cena = bpy.context.scene
    cena.render.engine = "BLENDER_EEVEE"
    try:
        cena.eevee.use_raytracing = True
        cena.eevee.use_shadows = True
    except AttributeError:
        pass
    cena.view_settings.view_transform = "AgX"
    cena.view_settings.look = "AgX - Punchy"
    w = bpy.data.worlds.new("Estudio")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.012, 0.012, 0.016, 1)
    cena.world = w
    bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 0))
    chao = bpy.context.active_object
    chao.name = "Estudio_Chao"
    mc = bpy.data.materials.new("Estudio_Chao")
    mc.use_nodes = True
    mc.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.025, 0.022, 0.022, 1)
    mc.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.6
    chao.data.materials.append(mc)

    def luz(nome, tipo, pos, alvo, energia, cor, tam=1.0):
        ld = bpy.data.lights.new(nome, tipo)
        ld.energy = energia
        ld.color = cor
        if tipo == "AREA":
            ld.size = tam
        ob = bpy.data.objects.new(nome, ld)
        cena.collection.objects.link(ob)
        ob.location = pos
        d = (Vector(alvo) - Vector(pos)).normalized()
        ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

    luz("Luz_Principal", "AREA", (-2.2, -3.2, 3.2), (0, 0, 1.1), 900, (1.0, 0.9, 0.78), 2.0)
    luz("Luz_Preenchimento", "AREA", (3.0, -2.5, 1.6), (0, 0, 1.0), 220, (0.75, 0.82, 1.0), 2.5)
    luz("Luz_Contorno_1", "AREA", (2.0, 2.8, 2.8), (0, 0, 1.3), 650, (0.7, 0.8, 1.0), 1.5)
    luz("Luz_Contorno_2", "AREA", (-2.4, 2.4, 2.2), (0, 0, 1.2), 450, (1.0, 0.75, 0.6), 1.5)
    cam = bpy.data.objects.new("Camera_Estudio", bpy.data.cameras.new("Camera_Estudio"))
    cena.collection.objects.link(cam)
    cena.camera = cam
    return cam


def fotografar(cam, caminho, alvo, distancia, angulo, elev=8.0, lente=50, res=(1200, 1500)):
    cena = bpy.context.scene
    cena.render.resolution_x, cena.render.resolution_y = res
    cam.data.lens = lente
    r, e = math.radians(angulo), math.radians(elev)
    d = Vector((math.sin(r) * math.cos(e), -math.cos(r) * math.cos(e), math.sin(e)))
    cam.location = Vector(alvo) + d * distancia
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    cena.render.filepath = str(caminho)
    bpy.ops.render.render(write_still=True)
    print("[render]", caminho)


def renders(chave, arm, pasta):
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    cam = estudio()
    bpy.context.view_layer.update()
    pose_descanso(arm, chave)
    bpy.context.view_layer.update()
    altura = max((ob.matrix_world @ v.co).z for ob in bpy.context.scene.objects if ob.type == "MESH"
                 and not ob.name.startswith("Estudio") for v in ob.data.vertices)
    meio = (0, 0, altura * 0.5)
    dist = altura * 2.15
    for nome, ang in (("frente", 0), ("tres_quartos", 35), ("lado", 90)):
        fotografar(cam, pasta / f"{chave}_{nome}.png", meio, dist, ang)
    cab = arm.matrix_world @ arm.data.bones["cabeca"].head_local
    fotografar(cam, pasta / f"{chave}_rosto.png", cab + Vector((0, 0, 0.12)), 1.25, 20, 4, 60, (1200, 1200))
    pose_teste(arm, chave)
    bpy.context.view_layer.update()
    fotografar(cam, pasta / f"{chave}_pose.png", meio, dist, 30)
    pose_descanso(arm, chave)


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["tito"]
    chave = args[0]
    opcoes = dict(a.split("=", 1) if "=" in a else (a, True) for a in args[1:])
    arm, endo, mt = montar(chave)
    if not opcoes.get("sem_salvar"):
        destino = RAIZ / "personagens" / f"{chave}_final.blend"
        destino.parent.mkdir(parents=True, exist_ok=True)
        pose_descanso(arm, chave)
        bpy.ops.wm.save_as_mainfile(filepath=str(destino))
        print("[anim] salvo", destino)
    if opcoes.get("renders"):
        renders(chave, arm, opcoes["renders"])


if __name__ == "__main__":
    main()
