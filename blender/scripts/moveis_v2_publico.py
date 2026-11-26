"""
moveis_v2_publico.py — móveis e set dressing das áreas do PÚBLICO da V2.4.

Cômodos deste arquivo (retângulos em planta_v2.COMODOS):
  Salao (com o palco), Recepcao, Corredor_Principal, Corredor_Festas,
  Festa_Estrelas, Festa_Piratas, Festa_Princesas.

O que sai daqui:
  - blender/v2_publico.blend
  - godot/assets/cenario/v2_publico.glb

Rodar sozinho (a partir da pasta TurnoDaNoite):
  blender --background --python blender/scripts/moveis_v2_publico.py

Ideia geral (igual à da V1): cada móvel é montado "em casa" (na origem, de frente
para -Y) e depois levado para o lugar dele com montar(). As peças pequenas de um
mesmo material são juntadas numa malha só (copos, confetes, lâmpadas...), porque
cada objeto a mais pesa no PC fraco do laboratório.
Paredes, pisos, tetos, portas e a plataforma do palco vêm do gerador do prédio:
aqui só entra o que fica DENTRO dos cômodos.
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
PONTOS = planta_v2.PONTOS
COMODOS_DO_GRUPO = ["Salao", "Recepcao", "Corredor_Principal", "Corredor_Festas",
                    "Festa_Estrelas", "Festa_Piratas", "Festa_Princesas"]
RET = {c[0]: c[2:6] for c in planta_v2.COMODOS}       # nome -> (x0, x1, z0, z1)
TETO = {c[0]: c[6] for c in planta_v2.COMODOS}         # nome -> pé-direito
ALTURA_PALCO = 0.6                                     # plataforma feita pelo gerador do prédio

FONTES = comum.RAIZ / "godot" / "assets" / "fontes"
ARQ_BUNGEE = FONTES / "Bungee" / "Bungee-Regular.ttf"
ARQ_FREDOKA = FONTES / "Fredoka" / "Fredoka-Variable.ttf"
ARQ_GOCHI = FONTES / "GochiHand" / "GochiHand-Regular.ttf"

# ---------------------------------------------------------------------------
# Cores lisas só deste grupo ("Nome": ("#RRGGBB", emissão)).
# As texturizadas (madeira, metal, veludo...) vêm de materiais_v2.py.
# ---------------------------------------------------------------------------
CORES_PUBLICO = {
    "Mat_Papel_Branco": ("#e8e4d6", 0.0),          # padrão do comum.plano_arte
    "Mat_Papel_Amarelado": ("#d6c693", 0.0),
    "Mat_Teia": ("#d8d8d0", 0.0),
    "Mat_Texto_Preto": ("#141414", 0.0),
    "Mat_Texto_Branco": ("#f0ede4", 0.0),
    "Mat_Texto_Vermelho": ("#b8262a", 0.0),
    "Mat_Letreiro_Arco": ("#7a1c22", 0.0),
    "Mat_Letreiro_Dourado": ("#e8c341", 0.5),      # letras do arco: brilham de leve
    "Mat_Franja_Dourada": ("#c9a03a", 0.0),
    "Mat_Gel_Vermelho": ("#d0302a", 0.3),
    "Mat_Gel_Azul": ("#2a5ad0", 0.3),
    "Mat_Gel_Ambar": ("#e09a2a", 0.3),
    "Mat_Vidro_Sujo": ("#6f8288", 0.0),
    "Mat_Vidro_Porta": ("#5f7f9a", 0.25),          # portas da frente: luar batendo no vidro
    "Mat_Vidro_Bilheteria": ("#9fb4b8", 0.0),
    "Mat_Estrela_Recortada": ("#d9b84a", 0.0),
    "Mat_Estrela_Fosforescente": ("#b8f0a8", 1.2),
    "Mat_Placa_Saida": ("#1f9e4a", 1.5),
    "Mat_Letra_Saida": ("#f2fff2", 2.0),
    "Mat_Letra_Apagada": ("#26362a", 0.0),
    "Mat_Bolo_Rosa": ("#e8a0b8", 0.0),
    "Mat_Bolo_Creme": ("#f0e0c0", 0.0),
    "Mat_Vela_Azul": ("#7fb0e0", 0.0),
    "Mat_Planta_Seca": ("#6b5236", 0.0),
    "Mat_Vaso_Terracota": ("#9c5a3a", 0.0),
    "Mat_Cortica": ("#a5794a", 0.0),
    "Mat_Toalha_Azul_Noite": ("#1f2c5a", 0.0),
    "Mat_Toalha_Pirata": ("#5a1f1f", 0.0),
    "Mat_Toalha_Rosa": ("#e0a0c0", 0.0),
    "Mat_Tecido_Preto": ("#1c1c1c", 0.0),
    "Mat_Tule_Rosa": ("#f0c8dc", 0.0),
    "Mat_Ouro": ("#d4a832", 0.2),
    "Mat_Fio": ("#1e1e1e", 0.0),
    "Mat_Faixa_Papel": ("#f0e2a8", 0.0),
    "Mat_Vidro_Escuro": ("#1b2a30", 0.0),
    "Mat_Tela_Alto_Falante": ("#2a2622", 0.0),
    "Mat_Papelao_Pintado_Cinza": ("#8e98a8", 0.0),
    "Mat_Corda": ("#b89a6a", 0.0),
}

# Direção (na planta) para onde a FRENTE aponta, e rotação Z correspondente.
FRENTES = {
    "sul": (comum.ROT_OLHA_SUL, (0.0, 1.0)),
    "leste": (comum.ROT_OLHA_LESTE, (1.0, 0.0)),
    "norte": (comum.ROT_OLHA_NORTE, (0.0, -1.0)),
    "oeste": (comum.ROT_OLHA_OESTE, (-1.0, 0.0)),
}

CONTADOR = {}  # numeração dos marcadores por tipo (Luz__holofote_01, _02...)


# ---------------------------------------------------------------------------
# Geometria "solta": cada função devolve (vértices, faces) já posicionados.
# Assim várias peças pequenas viram UMA malha (menos objetos no Godot).
# ---------------------------------------------------------------------------

def _vf(bm):
    bm.verts.index_update()
    vs = [v.co.copy() for v in bm.verts]
    fs = [tuple(v.index for v in f.verts) for f in bm.faces]
    bm.free()
    return vs, fs


def _matriz(base, rot):
    """Translação até 'base' + rotação (graus, XYZ) em volta de 'base'."""
    return Matrix.Translation(V(base)) @ Euler([math.radians(a) for a in rot], "XYZ").to_matrix().to_4x4()


def _aplicar(vf, m):
    vs, fs = vf
    return [m @ V(v) for v in vs], fs


def g_caixa(tam, base=(0, 0, 0), rot=(0, 0, 0)):
    """Caixa com a origem no centro da face de baixo."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    sx, sy, sz = tam
    for v in bm.verts:
        v.co = V((v.co.x * sx, v.co.y * sy, (v.co.z + 0.5) * sz))
    return _aplicar(_vf(bm), _matriz(base, rot))


def g_cil(raio, alt, base=(0, 0, 0), rot=(0, 0, 0), seg=8, raio_topo=None):
    """Cilindro (ou cone) em pé, origem no centro da base."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=raio,
                          radius2=raio if raio_topo is None else raio_topo, depth=alt)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, alt / 2))
    return _aplicar(_vf(bm), _matriz(base, rot))


def g_esf(raio, centro=(0, 0, 0), seg=8, aneis=5, escala=(1, 1, 1), rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=aneis, radius=raio)
    for v in bm.verts:
        v.co = V((v.co.x * escala[0], v.co.y * escala[1], v.co.z * escala[2]))
    return _aplicar(_vf(bm), _matriz(centro, rot))


def g_tubo(pontos, raio, seg=4):
    """Tubo fino passando por uma lista de pontos (cabos, fios, cordas). Um cilindro por trecho."""
    pecas = []
    for a, b in zip(pontos[:-1], pontos[1:]):
        a, b = V(a), V(b)
        d = b - a
        if d.length < 1e-4:
            continue
        rot = d.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
        vs, fs = g_cil(raio, d.length, (0, 0, 0), seg=seg)
        m = Matrix.Translation(a) @ rot
        pecas.append(([m @ v for v in vs], fs))
    return pecas


def g_estrela(r_ext, r_int, espessura=0.02, pontas=5):
    """Estrela recortada (prisma), em pé no plano XZ, centrada na origem, frente -Y."""
    n = pontas * 2
    vs, fs = [], []
    for lado in (-1, 1):
        for i in range(n):
            a = math.radians(90 + i * 180 / pontas)
            r = r_ext if i % 2 == 0 else r_int
            vs.append(V((r * math.cos(a), lado * espessura / 2, r * math.sin(a))))
        vs.append(V((0, lado * espessura / 2, 0)))
    c0, c1 = n, 2 * n + 1
    for i in range(n):
        j = (i + 1) % n
        fs.append((c0, j, i))                         # frente
        fs.append((c1, n + 1 + i, n + 1 + j))         # trás
        fs.append((i, j, n + 1 + j, n + 1 + i))       # lateral
    return vs, fs


def g_estrela_plana(r_ext, r_int, centro, para_baixo=True):
    """Estrela plana deitada (para colar no teto, virada para baixo)."""
    vs, fs = [], []
    for i in range(10):
        a = math.radians(90 + i * 36)
        r = r_ext if i % 2 == 0 else r_int
        vs.append(V(centro) + V((r * math.cos(a), r * math.sin(a), 0)))
    vs.append(V(centro))
    for i in range(10):
        j = (i + 1) % 10
        fs.append((10, i, j) if para_baixo else (10, j, i))
    return vs, fs


def g_plano(cantos, dois_lados=True):
    """Quadrilátero (ou triângulo) pelos cantos dados; com as duas faces se pedido."""
    vs = [V(c) for c in cantos]
    n = len(vs)
    fs = [tuple(range(n))]
    if dois_lados:
        vs += [V(c) for c in cantos]
        fs.append(tuple(range(2 * n - 1, n - 1, -1)))
    return vs, fs


def malha(nome, pecas, mat, col, suave=False, origem=None, recalc=False):
    """
    Junta várias peças (vértices, faces) num objeto só.
    origem=None: a origem fica em (0,0,0) das peças (peça montada "em casa").
    origem="auto": a origem vai para o centro da base da caixa envolvente (peças já no mundo).
    """
    vs, fs = [], []
    for pv, pf in pecas:
        k = len(vs)
        vs += [V(v) for v in pv]
        fs += [tuple(i + k for i in f) for f in pf]
    desloc = V((0, 0, 0))
    if origem == "auto" and vs:
        xs, ys, zs = [v.x for v in vs], [v.y for v in vs], [v.z for v in vs]
        desloc = V(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs)))
    elif origem is not None:
        desloc = V(origem)
    me = bpy.data.meshes.new(nome)
    me.from_pydata([v - desloc for v in vs], [], fs)
    if recalc:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
    me.update()
    if suave:
        for p in me.polygons:
            p.use_smooth = True
    obj = bpy.data.objects.new(nome, me)
    col.objects.link(obj)
    obj.data.materials.append(M(mat))
    obj.location = desloc
    return obj


def M(nome):
    return comum.material(nome)


# ---------------------------------------------------------------------------
# Texto 3D com fonte OFL do projeto (convertido em malha)
# ---------------------------------------------------------------------------
_FONTES_CARREGADAS = {}


def fonte(caminho):
    chave = str(caminho)
    if chave not in _FONTES_CARREGADAS:
        _FONTES_CARREGADAS[chave] = bpy.data.fonts.load(chave, check_existing=True)
    return _FONTES_CARREGADAS[chave]


def texto_vf(corpo, tamanho, arq_fonte=ARQ_BUNGEE, extrude=0.0, resolucao=1, centrar_altura=True):
    """
    Devolve (vértices, faces) do texto em pé, virado para -Y, centrado na origem.
    centrar_altura=False: centra só na horizontal e mantém a altura da linha da fonte. Use ao montar
    uma palavra LETRA POR LETRA: centrando cada letra pela própria caixa, a letra com acento
    (o "Í" de SAÍDA) descia em relação às outras.
    """
    curva = bpy.data.curves.new("Texto_Temp", type="FONT")
    curva.body = corpo
    curva.size = tamanho
    curva.font = fonte(arq_fonte)
    curva.align_x = "CENTER"
    curva.align_y = "CENTER"
    curva.resolution_u = resolucao   # poucas subdivisões nas curvas = poucos triângulos
    curva.extrude = extrude
    temp = bpy.data.objects.new("Texto_Temp", curva)
    bpy.context.scene.collection.objects.link(temp)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(temp.evaluated_get(dg))
    bpy.data.objects.remove(temp)
    bpy.data.curves.remove(curva)
    rot = Matrix.Rotation(math.radians(90), 4, "X")  # deita o texto de pé, de frente para -Y
    vs = [rot @ v.co for v in me.vertices]
    fs = [tuple(p.vertices) for p in me.polygons]
    bpy.data.meshes.remove(me)
    if vs:
        # centraliza de verdade (a caixa da fonte nem sempre bate com o desenho)
        cx = (min(v.x for v in vs) + max(v.x for v in vs)) / 2
        cz = (min(v.z for v in vs) + max(v.z for v in vs)) / 2 if centrar_altura else 0.0
        vs = [v - V((cx, 0, cz)) for v in vs]
    return vs, fs


def largura_vf(vf):
    xs = [v.x for v in vf[0]]
    return (max(xs) - min(xs)) if xs else 0.0


def texto(nome, corpo, tamanho, mat, col, centro=(0, 0, 0), largura_max=None, arq_fonte=ARQ_BUNGEE,
          extrude=0.0, rot=(0, 0, 0)):
    """Objeto de texto (malha) com a origem no centro do texto."""
    vs, fs = texto_vf(corpo, tamanho, arq_fonte, extrude)
    larg = largura_vf((vs, fs))
    if largura_max is not None and larg > largura_max:
        k = largura_max / larg
        vs = [v * k for v in vs]
    m = _matriz(centro, rot)
    obj = malha(nome, [([m @ v for v in vs], fs)], mat, col)
    marcar_texto(obj, corpo, arq_fonte)
    return obj


def marcar_texto(obj, corpo, arq_fonte):
    """
    Guarda no objeto o que está escrito e com qual fonte (propriedades personalizadas).
    Elas vão para o .glb como "extras" e o Godot (dev/validar_artes.gd) usa para conferir
    acentos, tamanho e posição de todos os textos 3D do mapa.
    """
    obj["texto_3d"] = corpo
    obj["texto_fonte"] = pathlib.Path(arq_fonte).name
    return obj


# ---------------------------------------------------------------------------
# Ajudantes de montagem e marcadores
# ---------------------------------------------------------------------------

def caixas(nome, itens, mat, col):
    """Várias caixas num objeto. itens = [((larg, prof, alt), (x, y, z_base)[, (rx, ry, rz)]), ...]"""
    pecas = [g_caixa(i[0], i[1], i[2] if len(i) > 2 else (0, 0, 0)) for i in itens]
    return malha(nome, pecas, mat, col)


def vazio(nome, col, tamanho=0.3, tipo="PLAIN_AXES"):
    obj = bpy.data.objects.new(nome, None)
    obj.empty_display_type = tipo
    obj.empty_display_size = tamanho
    col.objects.link(obj)
    return obj


def montar(principal, filhos, x, z, h=0.0, frente="sul", giro=0.0, incl=0.0, rot=None):
    """
    Prende as peças na principal e leva o conjunto para (x, z) da planta, olhando para 'frente'.
    giro = desvio extra em Z (graus), para nada ficar perfeitamente alinhado;
    incl = inclinação em volta do eixo da frente (quadro torto).
    """
    for f in filhos:
        f.parent = principal
    principal.location = comum.p2(x, z, h)
    if rot is not None:
        principal.rotation_euler = [math.radians(a) for a in rot]
    else:
        principal.rotation_euler = (0.0, math.radians(incl), math.radians(FRENTES[frente][0] + giro))
    return principal


def colisao(nome_base, tamanho, base_local, col):
    """Caixa de colisão filha do móvel (base_local = centro da face de baixo, coordenadas do móvel)."""
    return comum.colisao_caixa(nome_base, tamanho, V(base_local), col)


def na_parede(x, z, frente, afastamento):
    dx, dz = FRENTES[frente][1]
    return x + dx * afastamento, z + dz * afastamento


def prender(filho, pai):
    """
    Faz 'filho' ser filho de 'pai' sem mudar a posição no mundo. Usa matrix_basis (e não
    matrix_world), porque a matrix_world só é recalculada quando a cena atualiza.
    Vale para peças que ainda não têm pai.
    """
    filho.parent = pai
    filho.matrix_parent_inverse = pai.matrix_basis.inverted()
    return filho


def giro_para(cx, cz, x, z):
    """Giro (graus) que faz a frente (-Y) de um objeto em (cx, cz) olhar para (x, z) da planta."""
    return math.degrees(math.atan2(x - cx, z - cz))


def numero(tipo):
    CONTADOR[tipo] = CONTADOR.get(tipo, 0) + 1
    return CONTADOR[tipo]


def marcador(prefixo, tipo, col, pos, rot=None, escala=None, nn=None):
    """Empty que o Godot troca pela coisa certa (Luz__, Som__, Decal__, Esconderijo__...)."""
    n = nn if nn is not None else numero(prefixo + tipo)
    obj = vazio(f"{prefixo}__{tipo}_{n:02d}", col, 0.25, "ARROWS" if prefixo == "Luz" else "PLAIN_AXES")
    obj.location = V(pos)
    if rot is not None:
        obj.rotation_euler = rot
    if escala is not None:
        obj.scale = escala
    return obj


def rot_mirar(origem, alvo):
    """Rotação que faz o -Z local apontar de 'origem' para 'alvo' (holofotes)."""
    d = (V(alvo) - V(origem)).normalized()
    return d.to_track_quat("-Z", "Y").to_euler()


def luz(tipo, col, x, z, h, alvo=None, nn=None):
    pos = comum.p2(x, z, h)
    rot = rot_mirar(pos, comum.p2(*alvo)) if alvo is not None else None
    return marcador("Luz", tipo, col, pos, rot, nn=nn)


def som(tipo, col, x, z, h):
    return marcador("Som", tipo, col, comum.p2(x, z, h))


def decal(tipo, col, x, z, tam=(1.0, 1.0, 0.3), h=0.0, parede=None):
    """
    Mancha projetada. Sem rotação projeta para baixo (chão).
    parede = "norte"/"sul"/"leste"/"oeste": a parede para onde a mancha projeta (gira 90° em X).
    """
    rot = None
    if parede is not None:
        rz = {"norte": 0.0, "sul": 180.0, "leste": -90.0, "oeste": 90.0}[parede]
        rot = Euler((math.radians(90), 0, math.radians(rz)), "XYZ")
    return marcador("Decal", tipo, col, comum.p2(x, z, h), rot, escala=tam)


def esconderijo(tipo, col, x, z, h=0.0, nn=None):
    return marcador("Esconderijo", tipo, col, comum.p2(x, z, h), nn=nn)


def teia(nome, col, x, z, h, dx, dz, tam=0.45):
    """Teia de aranha num canto do teto: (dx, dz) apontam do canto para dentro do cômodo."""
    c = comum.p2(x, z, h - 0.01)
    a = comum.p2(x + dx * tam, z, h - 0.01)
    b = comum.p2(x, z + dz * tam, h - 0.01)
    d = comum.p2(x + dx * 0.03, z + dz * 0.03, h - tam * 0.85)
    pecas = [g_plano([a, b, d]), g_plano([a, c, d]), g_plano([b, d, c])]
    return malha(nome, pecas, "Mat_Teia", col, origem="auto")


def teias_cantos(prefixo, col, comodo, cantos="todos", tam=0.45):
    x0, x1, z0, z1 = RET[comodo]
    h = TETO[comodo]
    lista = [(x0 + 0.1, z0 + 0.1, 1, 1), (x1 - 0.1, z0 + 0.1, -1, 1),
             (x0 + 0.1, z1 - 0.1, 1, -1), (x1 - 0.1, z1 - 0.1, -1, -1)]
    if cantos != "todos":
        lista = [lista[i] for i in cantos]
    for i, (x, z, dx, dz) in enumerate(lista):
        teia(f"{prefixo}_Teia_{i + 1:02d}", col, x, z, h, dx, dz, tam * (0.8 + 0.15 * (i % 3)))


# ---------------------------------------------------------------------------
# Peças reutilizáveis (montadas na origem, frente -Y)
# ---------------------------------------------------------------------------

def cadeira(nome, col, mat, crianca=False):
    """Cadeira de festa de plástico com pés de metal. Devolve o objeto principal (já com filhos)."""
    k = 0.72 if crianca else 1.0
    a = 0.42 * k
    corpo = malha(nome, [g_caixa((0.4 * k, 0.4 * k, 0.04), (0, 0, a)),
                         g_caixa((0.4 * k, 0.04, 0.4 * k), (0, 0.18 * k, a + 0.04))], mat, col)
    pes = malha(nome + "_Pes", [g_cil(0.014, a, (sx * 0.17 * k, sy * 0.17 * k, 0), seg=4)
                                for sx in (-1, 1) for sy in (-1, 1)], "Mat_Metal_Escuro", col)
    pes.parent = corpo
    return corpo


def por_cadeira(corpo, x, z, giro, caida=None):
    """Põe a cadeira no mundo. caida = None, 'costas' ou 'lado' (cadeira virada no chão)."""
    if caida == "costas":
        corpo.location = comum.p2(x, z, 0.2)
        corpo.rotation_euler = (math.radians(-90), 0, math.radians(giro))
    elif caida == "lado":
        corpo.location = comum.p2(x, z, 0.2)
        corpo.rotation_euler = (0, math.radians(90), math.radians(giro))
    else:
        corpo.location = comum.p2(x, z, 0.0)
        corpo.rotation_euler = (0, 0, math.radians(giro))
    return corpo


def mesa_redonda(nome, col, mat_toalha, x, z, rng, cores_cad, caidas=(), giro_mesa=0.0, itens=True):
    """Mesa redonda com toalha e 4 cadeiras desalinhadas (algumas viradas)."""
    toalha = malha(nome, [g_cil(0.74, 0.4, (0, 0, 0.36), seg=14, raio_topo=0.64),
                          g_cil(0.64, 0.02, (0, 0, 0.76), seg=14)], mat_toalha, col)
    pe = malha(nome + "_Pe", [g_cil(0.05, 0.4, (0, 0, 0), seg=6), g_cil(0.3, 0.03, (0, 0, 0), seg=10)],
               "Mat_Metal_Escuro", col)
    filhos = [pe, colisao(nome, (1.3, 1.3, 0.78), (0, 0, 0), col)]
    if itens:
        loucas, chapeus = [], []
        for i in range(rng.randint(2, 4)):
            a = rng.uniform(0, 2 * math.pi)
            r = rng.uniform(0.15, 0.45)
            px, py = r * math.cos(a), r * math.sin(a)
            if rng.random() < 0.5:
                loucas.append(g_cil(0.09, 0.008, (px, py, 0.78), seg=10))            # prato de papel
            else:
                tomb = 90 if rng.random() < 0.4 else 0
                loucas.append(g_cil(0.035, 0.1, (px, py, 0.78 + (0.035 if tomb else 0)),
                                    rot=(tomb, 0, rng.uniform(0, 360)), seg=6))       # copo
        for i in range(rng.randint(1, 2)):
            a = rng.uniform(0, 2 * math.pi)
            chapeus.append(g_cil(0.06, 0.17, (0.4 * math.cos(a), 0.4 * math.sin(a), 0.84),
                                 rot=(rng.choice((0, 80)), 0, rng.uniform(0, 360)), seg=6, raio_topo=0.0))
        filhos.append(malha(nome + "_Loucas", loucas, "Mat_Plastico_Branco", col))
        filhos.append(malha(nome + "_Chapeus", chapeus, rng.choice(["Mat_Plastico_Azul", "Mat_Plastico_Amarelo",
                                                                    "Mat_Plastico_Verde"]), col))
    montar(toalha, filhos, x, z, 0.0, "sul", giro_mesa)
    # Cadeiras em volta, fora do lugar (não são filhas: cada uma tem o seu desvio)
    for i, ang in enumerate((0, 90, 180, 270)):
        if rng.random() < 0.15:
            continue  # uma cadeira sumiu
        a = math.radians(ang + giro_mesa + rng.uniform(-18, 18))
        r = rng.uniform(0.85, 1.15)
        cx, cz = x + r * math.sin(a), z - r * math.cos(a)
        corpo = cadeira(f"{nome}_Cadeira_{i + 1:02d}", col, cores_cad[i % len(cores_cad)])
        giro = giro_para(cx, cz, x, z) + rng.uniform(-35, 35)
        por_cadeira(corpo, cx, cz, giro, "costas" if i in caidas else None)


def presente(nome, col, tam, mat_papel, mat_fita, rot=(0, 0, 0)):
    """Caixa de presente com fita em cruz e laço (montada na origem)."""
    lx, ly, lz = tam
    caixa = malha(nome, [g_caixa(tam)], mat_papel, col)
    fita = malha(nome + "_Fita", [g_caixa((lx + 0.01, 0.04, lz + 0.005)), g_caixa((0.04, ly + 0.01, lz + 0.005)),
                                  g_esf(0.05, (-0.04, 0, lz + 0.02), 6, 4, (1, 0.5, 0.6)),
                                  g_esf(0.05, (0.04, 0, lz + 0.02), 6, 4, (1, 0.5, 0.6))], mat_fita, col)
    fita.parent = caixa
    caixa.rotation_euler = [math.radians(a) for a in rot]
    return caixa


def balao_murcho_vf(x, z, h, rng, raio=0.15):
    """Balão murcho no chão: esfera achatada e torta (devolve as peças já no mundo)."""
    c = comum.p2(x, z, h + raio * 0.25)
    return g_esf(raio, c, 7, 4, (1.0, 0.75, 0.3), (rng.uniform(-10, 10), rng.uniform(-10, 10), rng.uniform(0, 360)))


def baloes_murchos(nome, col, pontos, rng, h=0.0):
    """Vários balões murchos no chão, um objeto por cor."""
    cores = ["Mat_Plastico_Vermelho", "Mat_Plastico_Azul", "Mat_Plastico_Amarelo", "Mat_Plastico_Rosa",
             "Mat_Plastico_Verde"]
    por_cor = {}
    for i, (x, z) in enumerate(pontos):
        por_cor.setdefault(cores[(i + rng.randint(0, 4)) % len(cores)], []).append(
            balao_murcho_vf(x, z, h, rng, rng.uniform(0.12, 0.18)))
    for cor, pecas in por_cor.items():
        malha(f"{nome}_{cor.split('_')[-1]}", pecas, cor, col, suave=True, origem="auto")


def balao_meio_murcho(nome, col, mat, x, z, h_amarra, altura, rng):
    """Balão que perdeu o gás: pendurado baixo, meio enrugado, com barbante."""
    topo = comum.p2(x + rng.uniform(-0.1, 0.1), z + rng.uniform(-0.1, 0.1), h_amarra + altura)
    bola = malha(nome, [g_esf(0.16, topo + V((0, 0, 0.12)), 8, 5, (1, 1, 0.8),
                              (rng.uniform(-25, 25), rng.uniform(-25, 25), 0))], mat, col, suave=True, origem="auto")
    malha(nome + "_Barbante", g_tubo([comum.p2(x, z, h_amarra), topo], 0.004, 3), "Mat_Plastico_Branco", col,
          origem="auto")
    return bola


def lixo(prefixo, col, retangulos, n, rng, h=0.0):
    """
    Lixo de festa espalhado no chão: copos, pratos de papel, guardanapos, chapéus
    amassados, fichas e latinhas. Um objeto por material (pouca coisa para o Godot).
    retangulos = [(x0, x1, z0, z1), ...] onde pode cair coisa.
    """
    grupos = {"Copos": [], "Pratos": [], "Guardanapos": [], "Chapeus": [], "Fichas": [], "Latas": []}
    pesos = list(grupos)
    areas = [(r, (r[1] - r[0]) * (r[3] - r[2])) for r in retangulos]
    total = sum(a for _, a in areas)
    for _ in range(n):
        alvo = rng.uniform(0, total)
        for r, a in areas:
            alvo -= a
            if alvo <= 0:
                break
        x, z = rng.uniform(r[0], r[1]), rng.uniform(r[2], r[3])
        tipo = rng.choice(pesos)
        base = comum.p2(x, z, h)
        giro = rng.uniform(0, 360)
        if tipo == "Copos":
            grupos[tipo].append(g_cil(0.035, 0.1, base + V((0, 0, 0.035)), (90, 0, giro), 6, 0.045))
        elif tipo == "Pratos":
            grupos[tipo].append(g_cil(0.09, 0.006, base, (rng.uniform(-4, 4), 0, giro), 10))
        elif tipo == "Guardanapos":
            grupos[tipo].append(g_caixa((0.14, 0.12, 0.006), base, (rng.uniform(-6, 6), 0, giro)))
        elif tipo == "Chapeus":
            grupos[tipo].append(g_cil(0.06, 0.15, base + V((0, 0, 0.05)), (75, 0, giro), 6, 0.0))
        elif tipo == "Fichas":
            for _k in range(rng.randint(1, 3)):
                grupos[tipo].append(g_cil(0.015, 0.004, base + V((rng.uniform(-0.1, 0.1), rng.uniform(-0.1, 0.1), 0)),
                                          (0, 0, 0), 6))
        else:
            grupos[tipo].append(g_cil(0.033, 0.12, base + V((0, 0, 0.033)), (90, 0, giro), 8))
    mats = {"Copos": "Mat_Plastico_Branco", "Pratos": "Mat_Papel_Branco", "Guardanapos": "Mat_Papel_Amarelado",
            "Chapeus": "Mat_Plastico_Azul", "Fichas": "Mat_Ouro", "Latas": "Mat_Plastico_Vermelho"}
    for tipo, pecas in grupos.items():
        if pecas:
            malha(f"{prefixo}_Lixo_{tipo}", pecas, mats[tipo], col, origem="auto")


def moldura_arte(nome, col, arquivo, larg, alt, x, z, h, frente, incl=0.0, mat_moldura="Mat_Madeira_Escura",
                 borda=0.05):
    """
    Quadro de parede: moldura atrás + plano_arte na frente. (x, z) = ponto na face da parede.
    A arte fica 6 mm na frente da moldura: com 2 mm (antes) as duas superfícies "brigavam" no
    buffer de profundidade (z-fighting) em placas de vídeo e distâncias maiores.
    """
    moldura = caixas(nome, [((larg + 2 * borda, 0.03, alt + 2 * borda), (0, -0.015, -borda))], mat_moldura, col)
    arte = comum.plano_arte(arquivo, larg, alt, V((0, -0.036, 0)), col)
    montar(moldura, [arte], x, z, h, frente, incl=incl)
    return moldura


def placa_texto(nome, col, corpo, larg, alt, x, z, h, frente, mat_fundo, mat_txt, arq=ARQ_BUNGEE, incl=0.0,
                tam=None):
    """Placa de parede com texto 3D. (x, z) na face da parede; h = altura da borda de baixo."""
    placa = caixas(nome, [((larg, 0.025, alt), (0, -0.0125, 0))], mat_fundo, col)
    t = texto(nome + "_Texto", corpo, tam or alt * 0.55, mat_txt, col, (0, -0.028, alt / 2), larg * 0.9, arq)
    montar(placa, [t], x, z, h, frente, incl=incl)
    return placa


def cortina_vf(a, b, h0, h1, dobras, amplitude, desloc=0.0):
    """
    Cortina pregueada (zigue-zague) entre os pontos a e b da planta, de h0 a h1.
    Tem as duas faces (fica bonita dos dois lados). Devolve peças no mundo.
    """
    pa, pb = comum.p2(a[0], a[1]), comum.p2(b[0], b[1])
    eixo = pb - pa
    normal = V((-eixo.y, eixo.x, 0)).normalized()
    n = dobras * 2
    frente, tras = [], []
    for i in range(n + 1):
        t = i / n
        p = pa + eixo * t + normal * ((amplitude if i % 2 else -amplitude) + desloc)
        frente += [V((p.x, p.y, h0)), V((p.x, p.y, h1))]
    fs = [(2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1) for i in range(n)]
    tras = [v.copy() for v in frente]
    fs_t = [tuple(reversed(f)) for f in fs]
    return [(frente, fs), (tras, fs_t)]


def franja_vf(a, b, h_topo, comprimento=0.1, passo=0.07, desloc=0.0):
    """Franja dourada em dente de serra ao longo de a->b (planta), pendurada de h_topo para baixo."""
    pa, pb = comum.p2(a[0], a[1]), comum.p2(b[0], b[1])
    eixo = pb - pa
    normal = V((-eixo.y, eixo.x, 0)).normalized() * desloc
    n = max(2, int(eixo.length / passo))
    pecas = []
    for i in range(n):
        p0 = pa + eixo * (i / n) + normal
        p1 = pa + eixo * ((i + 1) / n) + normal
        pm = (p0 + p1) / 2
        pecas.append(g_plano([V((p0.x, p0.y, h_topo)), V((p1.x, p1.y, h_topo)),
                              V((pm.x, pm.y, h_topo - comprimento))]))
    return pecas


def franja_vertical_vf(x, z, h0, h1, dir_xz, comprimento=0.08, passo=0.07):
    """Franja na borda vertical de uma cortina (dentes apontando para dir_xz)."""
    base = comum.p2(x, z)
    d = V((dir_xz[0], -dir_xz[1], 0)).normalized() * comprimento
    n = max(2, int((h1 - h0) / passo))
    pecas = []
    for i in range(n):
        za, zb = h0 + (h1 - h0) * i / n, h0 + (h1 - h0) * (i + 1) / n
        pecas.append(g_plano([V((base.x, base.y, za)), V((base.x, base.y, zb)),
                              V((base.x + d.x, base.y + d.y, (za + zb) / 2))]))
    return pecas


def papel_descascando(nome, col, x, z, h, frente, rng, larg=0.5, alt=0.6):
    """Folha/pedaço de papel de parede soltando: metade colada, metade dobrada para fora."""
    meia = larg / 2
    dobra = rng.uniform(25, 50)
    a = math.radians(dobra)
    corte = alt * 0.55
    pecas = [g_plano([(-meia, -0.005, 0), (meia, -0.005, 0), (meia, -0.005, corte), (-meia, -0.005, corte)]),
             g_plano([(-meia, -0.005, corte), (meia, -0.005, corte),
                      (meia * 0.8, -0.005 - (alt - corte) * math.sin(a), corte + (alt - corte) * math.cos(a)),
                      (-meia, -0.005 - (alt - corte) * math.sin(a), corte + (alt - corte) * math.cos(a))])]
    obj = malha(nome, pecas, "Mat_Papel_Amarelado", col)
    montar(obj, [], x, z, h, frente, incl=rng.uniform(-8, 8))
    return obj


def extintor(nome, col, x, z, frente):
    suporte = caixas(nome, [((0.14, 0.04, 0.22), (0, -0.02, 0.3))], "Mat_Metal_Escuro", col)
    filhos = [malha(nome + "_Cilindro", [g_cil(0.085, 0.5, (0, -0.13, 0.12), seg=10),
                                         g_esf(0.085, (0, -0.13, 0.62), 10, 4, (1, 1, 0.5))],
                    "Mat_Plastico_Vermelho", col),
              malha(nome + "_Bico", [g_caixa((0.06, 0.05, 0.08), (0, -0.13, 0.64)),
                                     g_caixa((0.03, 0.14, 0.03), (0, -0.2, 0.68))], "Mat_Plastico_Preto", col),
              colisao(nome, (0.3, 0.3, 0.8), (0, -0.15, 0.1), col)]
    montar(suporte, filhos, x, z, 0.4, frente)


def luz_emergencia_caixa(nome, col, x, z, h, frente):
    """Caixinha da luz de emergência (o Godot põe a luz no marcador Luz__emergencia_NN)."""
    corpo = caixas(nome, [((0.32, 0.08, 0.14), (0, -0.04, -0.07))], "Mat_Metal_Escuro", col)
    lente = caixas(nome + "_Lente", [((0.1, 0.03, 0.06), (sx * 0.09, -0.09, -0.03)) for sx in (-1, 1)],
                   "Mat_Luz_Emergencia", col)
    montar(corpo, [lente], x, z, h, frente)
    dx, dz = FRENTES[frente][1]
    luz("emergencia", col, x + dx * 0.15, z + dz * 0.15, h - 0.05)


# ---------------------------------------------------------------------------
# SALÃO + PALCO
# ---------------------------------------------------------------------------

def palco(col, rng):
    x0p, x1p, z0p, z1p = PONTOS["palco"]
    hp = ALTURA_PALCO
    xc = (x0p + x1p) / 2  # 27
    teto = TETO["Salao"]

    # --- Painel pintado (ARTE-01, 21:9) encostado na parede norte, acima do piso do palco.
    # O pé-direito é 3,6 m e o palco tem 0,6 m: sobra 3 m de altura, então o painel fica com
    # 6,7 x 2,87 m (21:9), e não 11 x 4,7 m, que atravessaria o teto.
    larg_painel = 6.7
    alt_painel = larg_painel * 9 / 21
    moldura = caixas("Palco_Painel_Moldura", [((larg_painel + 0.16, 0.05, alt_painel + 0.12), (0, 0, 0))],
                     "Mat_Madeira_Escura", col)
    montar(moldura, [], xc, z0p + 0.13, hp + 0.0)
    comum.plano_arte("painel_palco.jpg", larg_painel, alt_painel, comum.p2(xc, z0p + 0.163, hp + 0.06), col)  # 8 mm da moldura

    # --- Cortinas do fundo, nos dois lados do painel (encostadas na parede)
    pecas = []
    for xa, xb in ((x0p + 1.45, xc - larg_painel / 2 - 0.05), (xc + larg_painel / 2 + 0.05, x1p - 1.45)):
        pecas += cortina_vf((xa, 0.22), (xb, 0.22), hp, teto - 0.05, 6, 0.07)
    malha("Palco_Cortina_Fundo", pecas, "Mat_Cortina_Vermelha", col, origem="auto")

    # --- Esconderijos "cortina_palco": nicho atrás das cortinas laterais, nos cantos do fundo.
    # Cortina dupla: uma na borda do palco (fecha para o salão) e outra para dentro (fecha para
    # o palco). A entrada fica aberta para o sul (frente do palco).
    for i, (ex, ez) in enumerate([e[1:] for e in PONTOS["esconderijos"] if e[0] == "cortina_palco"]):
        lado = -1 if ex < xc else 1
        x_borda = (x0p + 0.12) if lado < 0 else (x1p - 0.12)
        x_dentro = (x0p + 1.45) if lado < 0 else (x1p - 1.45)
        z_fim = 2.45
        nome = f"Palco_Cortina_Lateral_{'Esq' if lado < 0 else 'Dir'}"
        pecas = cortina_vf((x_borda, 0.15), (x_borda, z_fim), hp, teto - 0.05, 5, 0.06)
        pecas += cortina_vf((x_dentro, 0.15), (x_dentro, z_fim), hp, teto - 0.05, 5, 0.06)
        cort = malha(nome, pecas, "Mat_Cortina_Vermelha", col, origem="auto")
        franja = malha(nome + "_Franja",
                       franja_vf((x_dentro, z_fim), (x_borda, z_fim), hp + 0.12, 0.1)
                       + franja_vertical_vf(x_dentro, z_fim, hp + 0.1, teto - 0.1, (0, 1)),
                       "Mat_Franja_Dourada", col, origem="auto")
        prender(franja, cort)
        for xx in (x_borda, x_dentro):
            c = colisao(f"{nome}_{'Borda' if xx == x_borda else 'Dentro'}", (0.14, z_fim - 0.12, teto - hp - 0.1),
                        comum.p2(xx, (0.12 + z_fim) / 2, hp), col)
            prender(c, cort)
        esconderijo("cortina_palco", col, ex, ez, hp, nn=i + 1)

    # --- Letreiro em ARCO na frente do palco: "O SHOW DO TITO & AMIGOS"
    z_arco = z1p - 0.28
    meia = (x1p - x0p) / 2 - 0.25          # meia corda do arco
    h_topo = teto - 0.12 - hp              # topo do arco (local, acima do piso do palco)
    flecha = 0.95
    r_ext = (meia ** 2 + flecha ** 2) / (2 * flecha)
    r_int = r_ext - 0.45
    zc = h_topo - r_ext                    # centro do círculo (local)
    th = math.asin(meia / r_ext)
    n = 28
    prof = 0.06
    vs, fs = [], []
    for i in range(n + 1):
        a = -th + 2 * th * i / n
        s, c = math.sin(a), math.cos(a)
        for y in (-prof, prof):
            vs += [V((r_int * s, y, zc + r_int * c)), V((r_ext * s, y, zc + r_ext * c))]
    for i in range(n):
        k, j = 4 * i, 4 * (i + 1)
        fs += [(k, j, j + 1, k + 1),            # frente
               (k + 3, j + 3, j + 2, k + 2),    # trás
               (k + 1, j + 1, j + 3, k + 3),    # topo
               (k + 2, j + 2, j, k)]            # baixo
    fs += [(0, 1, 3, 2), (4 * n, 4 * n + 2, 4 * n + 3, 4 * n + 1)]
    arco = malha("Palco_Letreiro_Arco", [(vs, fs)], "Mat_Letreiro_Arco", col, recalc=True)
    # Postes que seguram o arco
    h_ponta = zc + r_int * math.cos(th)
    postes = malha("Palco_Letreiro_Postes", [g_caixa((0.2, 0.2, h_ponta + 0.05), (sx * r_int * math.sin(th), 0, 0))
                                              for sx in (-1, 1)], "Mat_Madeira_Escura", col)
    # Lâmpadas em volta (algumas queimadas)
    acesas, apagadas = [], []
    for raio, qtd in ((r_ext - 0.05, 46), (r_int + 0.05, 42)):
        for i in range(qtd):
            a = -th + 0.01 + (2 * th - 0.02) * i / (qtd - 1)
            p = V((raio * math.sin(a), -prof - 0.02, zc + raio * math.cos(a)))
            (apagadas if (i * 7 + qtd) % 9 == 0 or i in (5, 6) else acesas).append(g_esf(0.035, p, 6, 4))
    lamp_on = malha("Palco_Letreiro_Lampadas_Acesas", acesas, "Mat_Lampada_Acesa", col, suave=True)
    lamp_off = malha("Palco_Letreiro_Lampadas_Queimadas", apagadas, "Mat_Lampada_Apagada", col, suave=True)
    # Letras seguindo a curva (uma por uma, todas numa malha só)
    frase = "O SHOW DO TITO & AMIGOS"
    tam = 0.3
    r_meio = (r_ext + r_int) / 2
    letras = []
    for ch in frase:
        if ch == " ":
            letras.append((None, tam * 0.45))
        else:
            vf = texto_vf(ch, tam, ARQ_BUNGEE, extrude=0.012, centrar_altura=False)
            letras.append((vf, largura_vf(vf) + tam * 0.1))
    total = sum(w for _, w in letras)
    s = -total / 2
    pecas = []
    for vf, w in letras:
        if vf is not None:
            a = (s + w / 2) / r_meio
            m = (Matrix.Translation(V((r_meio * math.sin(a), -prof - 0.015, zc + r_meio * math.cos(a))))
                 @ Matrix.Rotation(a, 4, "Y"))
            pecas.append(_aplicar(vf, m))
        s += w
    txt = malha("Palco_Letreiro_Texto", pecas, "Mat_Letreiro_Dourado", col)
    marcar_texto(txt, frase, ARQ_BUNGEE)
    montar(arco, [postes, lamp_on, lamp_off, txt], xc, z_arco, hp)

    # --- Sanefa (barra de veludo) atrás do arco, com franja, e cortinas laterais da boca de cena
    z_boca = z1p - 0.45
    pecas = cortina_vf((x0p + 0.12, z_boca), (x1p - 0.12, z_boca), teto - 0.55, teto - 0.04, 34, 0.05)
    sanefa = malha("Palco_Sanefa", pecas, "Mat_Cortina_Vermelha", col, origem="auto")
    fr = malha("Palco_Sanefa_Franja", franja_vf((x0p + 0.12, z_boca + 0.07), (x1p - 0.12, z_boca + 0.07),
                                                 teto - 0.53, 0.12), "Mat_Franja_Dourada", col, origem="auto")
    prender(fr, sanefa)
    for lado, xa, xb in (("Esq", x0p + 0.2, x0p + 1.35), ("Dir", x1p - 0.2, x1p - 1.35)):
        pecas = cortina_vf((xa, z_boca - 0.05), (xb, z_boca - 0.05), hp, teto - 0.5, 4, 0.08)
        cort = malha(f"Palco_Cortina_Boca_{lado}", pecas, "Mat_Cortina_Vermelha", col, origem="auto")
        fr = malha(f"Palco_Cortina_Boca_{lado}_Franja",
                   franja_vertical_vf(xb, z_boca, hp + 0.05, teto - 0.55, (1 if lado == "Esq" else -1, 0))
                   + franja_vf((xa, z_boca + 0.05), (xb, z_boca + 0.05), hp + 0.1, 0.08),
                   "Mat_Franja_Dourada", col, origem="auto")
        amarra = malha(f"Palco_Cortina_Boca_{lado}_Amarra",
                       [g_cil(0.03, (xb - xa) * (1 if lado == "Esq" else -1) + 0.1,
                              comum.p2(xa, z_boca - 0.05, hp + 1.3), (0, 90 if lado == "Esq" else -90, 0), 6)],
                       "Mat_Franja_Dourada", col, origem="auto")
        prender(fr, cort)
        prender(amarra, cort)

    # --- Estrelas recortadas penduradas por fios na frente do painel
    estrelas, fios = [], []
    for i, (ex, eh, er) in enumerate([(24.2, 1.95, 0.26), (25.3, 2.3, 0.2), (26.2, 1.8, 0.32), (27.9, 2.15, 0.22),
                                      (28.8, 1.9, 0.3), (29.8, 2.25, 0.24), (30.3, 1.75, 0.2)]):
        ez = 0.55 + 0.08 * (i % 3)
        centro = comum.p2(ex, ez, hp + eh)
        m = Matrix.Translation(centro) @ Euler((0, math.radians(rng.uniform(-14, 14)),
                                                 math.radians(rng.uniform(-20, 20))), "XYZ").to_matrix().to_4x4()
        estrelas.append(_aplicar(g_estrela(er, er * 0.45, 0.02), m))
        fios += g_tubo([centro + V((0, 0, er * 0.95)), comum.p2(ex, ez, teto - 0.01)], 0.003, 3)
    # uma caiu no chão do palco
    m = Matrix.Translation(comum.p2(25.4, 1.4, hp + 0.012)) @ Euler((math.radians(90), 0, 0.6), "XYZ").to_matrix().to_4x4()
    estrelas.append(_aplicar(g_estrela(0.24, 0.11, 0.02), m))
    fios += g_tubo([comum.p2(25.4, 0.95, teto - 0.01), comum.p2(25.4, 0.95, hp + 1.6),
                    comum.p2(25.5, 1.0, hp + 1.3)], 0.003, 3)
    est = malha("Palco_Estrelas_Recortadas", estrelas, "Mat_Estrela_Recortada", col, origem="auto", recalc=True)
    f = malha("Palco_Estrelas_Fios", fios, "Mat_Fio", col, origem="auto")
    prender(f, est)

    # --- Caixas de som antigas (duas no palco, duas pilhas no chão do salão)
    def caixa_som(nome, larg, prof, alt):
        corpo = caixas(nome, [((larg, prof, alt), (0, 0, 0))], "Mat_Madeira_Escura", col)
        tela = caixas(nome + "_Tela", [((larg - 0.08, 0.01, alt - 0.1), (0, -prof / 2 - 0.004, 0.05))],
                      "Mat_Tela_Alto_Falante", col)
        cones = malha(nome + "_Cones", [g_cil(larg * 0.32, 0.03, (0, -prof / 2 - 0.01, alt * 0.33), (90, 0, 0), 12),
                                        g_cil(larg * 0.16, 0.03, (0, -prof / 2 - 0.01, alt * 0.75), (90, 0, 0), 10)],
                      "Mat_Plastico_Preto", col)
        return corpo, [tela, cones]

    for i, (sx, sz, giro) in enumerate([(x0p + 1.95, z1p - 0.95, 8), (x1p - 1.95, z1p - 0.95, -10)]):
        nome = f"Palco_Caixa_Som_{i + 1:02d}"
        corpo, filhos = caixa_som(nome, 0.55, 0.45, 0.95)
        filhos.append(colisao(nome, (0.55, 0.45, 0.95), (0, 0, 0), col))
        montar(corpo, filhos, sx, sz, hp, "sul", giro)
    for i, (sx, sz, giro) in enumerate([(x0p - 1.3, 0.9, 12), (x1p + 1.3, 0.9, -9)]):
        nome = f"Salao_Caixa_Som_{i + 1:02d}"
        corpo, filhos = caixa_som(nome, 0.7, 0.55, 0.8)
        de_cima, f2 = caixa_som(nome + "_Cima", 0.6, 0.5, 0.7)
        for p_ in f2:
            p_.parent = de_cima
        de_cima.location = V((0.03, 0.02, 0.8))
        de_cima.rotation_euler = (0, 0, math.radians(-7))
        filhos += [de_cima, colisao(nome, (0.7, 0.55, 1.5), (0, 0, 0), col)]
        montar(corpo, filhos, sx, sz, 0.0, "sul", giro)

    # --- Microfone no centro (sem colisão; a pilha arriscada fica atrás, no ponto livre)
    mic = malha("Palco_Microfone", [g_cil(0.14, 0.02, (0, 0, 0), seg=10), g_cil(0.012, 1.35, (0, 0, 0.02), seg=5)],
                "Mat_Metal_Escuro", col)
    cab = malha("Palco_Microfone_Cabeca", [g_esf(0.04, (0, -0.03, 1.4), 8, 5),
                                           g_cil(0.008, 0.25, (0, 0, 1.25), (35, 0, 0), 4)], "Mat_Metal_Cinza", col)
    montar(mic, [cab], xc, 3.7, hp, "sul", 0, rot=(6, -4, 0))

    # --- Cabos pelo chão (do palco para as caixas e para a tomada)
    cabos = []
    cabos += g_tubo([comum.p2(x0p - 1.3, 1.25, 0.012), comum.p2(x0p - 0.6, 2.0, 0.012), comum.p2(x0p - 0.05, 2.2, 0.012),
                     comum.p2(x0p - 0.02, 2.25, hp + 0.012), comum.p2(x0p + 0.7, 3.2, hp + 0.012),
                     comum.p2(x0p + 1.7, 3.9, hp + 0.012)], 0.012)
    cabos += g_tubo([comum.p2(xc, 3.75, hp + 0.012), comum.p2(xc + 1.2, 4.2, hp + 0.012),
                     comum.p2(xc + 3.0, 4.35, hp + 0.012), comum.p2(x1p - 2.0, 4.3, hp + 0.012)], 0.012)
    cabos += g_tubo([comum.p2(x1p + 1.3, 1.25, 0.012), comum.p2(x1p + 2.5, 1.9, 0.012), comum.p2(x1p + 4.0, 1.4, 0.012),
                     comum.p2(39.85, 1.6, 0.012), comum.p2(39.85, 1.6, 0.35)], 0.012)
    cabos += g_tubo([comum.p2(xc - 0.4, 3.8, hp + 0.012), comum.p2(xc - 1.6, 4.5, hp + 0.012),
                     comum.p2(xc - 1.9, 4.97, hp + 0.012), comum.p2(xc - 1.95, 5.02, 0.012),
                     comum.p2(xc - 2.6, 6.2, 0.012)], 0.012)
    malha("Palco_Cabos", cabos, "Mat_Fio", col, origem="auto")

    # --- Faixa "FELIZ ANIVERSÁRIO, LUCAS!" meio caída: presa só na ponta esquerda.
    # Ela fica NA FRENTE do arco (z_arco + prof + lâmpadas = 0,15 m): antes ela ficava na mesma
    # linha do arco (z1p - 0,32 a - 0,25) e a ponta de cima sumia dentro da espessura do letreiro.
    z_faixa = z_arco + 0.2
    pa = comum.p2(x0p + 1.7, z_faixa, hp + 2.4)
    pb = comum.p2(x0p + 5.6, z_faixa + 0.04, hp + 0.26)
    eixo = pb - pa
    comp = eixo.length
    ang = math.atan2(eixo.z, eixo.x)
    faixa = malha("Palco_Faixa_Aniversario", [g_plano([(0, 0, -0.24), (comp, 0, -0.24), (comp, 0, 0.24), (0, 0, 0.24)])],
                  "Mat_Faixa_Papel", col)
    txt = texto("Palco_Faixa_Aniversario_Texto", "FELIZ ANIVERSÁRIO, LUCAS!", 0.24, "Mat_Texto_Vermelho", col,
                (comp / 2, -0.006, 0), comp * 0.9, ARQ_FREDOKA)
    txt.parent = faixa
    faixa.location = pa
    faixa.rotation_euler = (0, -ang, 0)  # sem giro em Z: a faixa inteira fica paralela ao arco, na frente dele
    barbante = malha("Palco_Faixa_Barbante", g_tubo([pa, comum.p2(x0p + 1.3, z_arco + 0.08, hp + 2.55)], 0.005, 3),
                     "Mat_Corda", col, origem="auto")
    prender(barbante, faixa)

    # --- Balões murchos no palco e um cacho meio vazio preso no poste do arco
    baloes_murchos("Palco_Baloes_Murchos", col, [(x0p + 2.6, 4.4), (x0p + 3.2, 3.9), (x1p - 2.9, 3.6),
                                                 (x1p - 2.4, 4.5), (xc + 1.5, 1.6)], rng, hp)
    for i, (mat, alt) in enumerate((("Mat_Plastico_Vermelho", 0.9), ("Mat_Plastico_Azul", 0.6),
                                    ("Mat_Plastico_Amarelo", 0.35))):
        balao_meio_murcho(f"Palco_Balao_Poste_{i + 1:02d}", col, mat, x1p - 0.4, z1p - 0.15, hp + 1.2, alt, rng)

    # --- Holofotes numa barra presa no teto, apontando para o palco (com gel colorido)
    z_barra = z1p + 2.6
    h_barra = teto - 0.3
    barra = malha("Palco_Holofotes_Barra", [g_cil(0.035, 12.0, (-6.0, 0, 0), (0, 90, 0), 6)] +
                  [g_cil(0.012, 0.3, (sx, 0, 0), seg=4) for sx in (-5.5, 5.5)], "Mat_Metal_Escuro", col)
    montar(barra, [], xc, z_barra, h_barra)
    alvos = [(23.5, 2.5, hp + 1.2), (xc, 1.8, hp + 1.0), (30.5, 2.5, hp + 1.2)]
    geis = ["Mat_Gel_Ambar", "Mat_Gel_Azul", "Mat_Gel_Vermelho"]
    for i, (hx, alvo, gel) in enumerate(zip((23.5, xc, 30.5), alvos, geis)):
        pos = comum.p2(hx, z_barra, h_barra - 0.22)
        rot = rot_mirar(pos, comum.p2(*alvo))
        nome = f"Palco_Holofote_{i + 1:02d}"
        corpo = malha(nome, [g_cil(0.13, 0.36, (0, 0, -0.06), seg=10, raio_topo=0.11),
                             g_cil(0.15, 0.03, (0, 0, -0.08), seg=10)], "Mat_Metal_Escuro", col)
        lente = malha(nome + "_Gel", [g_cil(0.115, 0.012, (0, 0, -0.095), seg=10)], gel, col)
        lente.parent = corpo
        corpo.location = pos
        corpo.rotation_euler = rot
        # o corpo foi feito ao longo de +Z; o -Z local aponta para o palco, então a lente fica em -Z
        garfo = malha(nome + "_Garfo", [g_caixa((0.34, 0.03, 0.03), (0, 0, 0.2)),
                                         g_caixa((0.03, 0.03, 0.22), (0, 0, 0))], "Mat_Metal_Escuro", col)
        garfo.location = pos
        luz("holofote", col, hx, z_barra, h_barra - 0.22, alvo)


def mesa_festa_lucas(col, rng):
    """A festa abandonada no meio do salão: bolo de plástico, presentes, cadeiras viradas."""
    x, z = 27.0, 10.5
    toalha = malha("Festa_Lucas_Mesa", [g_caixa((2.5, 1.1, 0.04), (0, 0, 0.74)),
                                        g_caixa((2.5, 0.01, 0.32), (0, -0.555, 0.46)),
                                        g_caixa((2.5, 0.01, 0.32), (0, 0.555, 0.46)),
                                        g_caixa((0.01, 1.1, 0.32), (-1.255, 0, 0.46)),
                                        g_caixa((0.01, 1.1, 0.25), (1.255, 0, 0.53), (0, 0, 0))],
                   "Mat_Toalha_Xadrez_Vermelha", col)
    pernas = malha("Festa_Lucas_Mesa_Pernas", [g_cil(0.03, 0.74, (sx * 1.1, sy * 0.45, 0), seg=6)
                                               for sx in (-1, 1) for sy in (-1, 1)], "Mat_Metal_Escuro", col)
    bolo = malha("Festa_Lucas_Bolo", [g_cil(0.26, 0.16, (0.1, 0.05, 0.78), seg=14),
                                      g_cil(0.18, 0.13, (0.1, 0.05, 0.94), seg=12)], "Mat_Bolo_Rosa", col)
    cobertura = malha("Festa_Lucas_Bolo_Cobertura", [g_cil(0.265, 0.03, (0.1, 0.05, 0.92), seg=14),
                                                     g_cil(0.185, 0.03, (0.1, 0.05, 1.06), seg=12),
                                                     g_cil(0.3, 0.012, (0.1, 0.05, 0.78), seg=14)],
                      "Mat_Bolo_Creme", col)
    velas = malha("Festa_Lucas_Bolo_Velas", [g_cil(0.008, 0.08, (0.1 + 0.09 * math.cos(a), 0.05 + 0.09 * math.sin(a), 1.07),
                                                   seg=4) for a in [i * 2 * math.pi / 7 for i in range(7)]],
                  "Mat_Vela_Azul", col)
    loucas = []
    for i in range(7):
        px, py = -1.05 + i * 0.33, (-0.35 if i % 2 else 0.35)
        if abs(px - 0.1) < 0.35:
            continue
        loucas.append(g_cil(0.1, 0.008, (px, py, 0.78), seg=10))
        if i % 3 == 0:
            loucas.append(g_cil(0.035, 0.1, (px + 0.12, py * 0.6, 0.78 + 0.035), (90, 0, i * 40), 6))
    loucas_obj = malha("Festa_Lucas_Pratos_Copos", loucas, "Mat_Papel_Branco", col)
    chapeus = malha("Festa_Lucas_Chapeus", [g_cil(0.06, 0.17, (-0.8, -0.2, 0.78), seg=6, raio_topo=0.0),
                                            g_cil(0.06, 0.17, (0.75, 0.3, 0.84), (80, 0, 30), 6, 0.0),
                                            g_cil(0.06, 0.17, (-0.3, 0.4, 0.84), (80, 0, 200), 6, 0.0)],
                    "Mat_Plastico_Azul", col)
    cartao = caixas("Festa_Lucas_Cartao", [((0.18, 0.01, 0.12), (-0.45, -0.1, 0.78), (-15, 0, 10))], "Mat_Papel_Branco", col)
    # (sem a idade: a idade do Lucas é o 3º dígito da senha, sorteado a cada partida e escrito no pôster)
    cartao_txt = texto("Festa_Lucas_Cartao_Texto", "PARABÉNS,\nLUCAS!", 0.035, "Mat_Texto_Vermelho",
                       col, (-0.45, -0.108, 0.84), 0.15, ARQ_GOCHI, rot=(-15, 0, 10))
    filhos = [pernas, bolo, cobertura, velas, loucas_obj, chapeus, cartao, cartao_txt,
              colisao("Festa_Lucas_Mesa", (2.5, 1.1, 0.8), (0, 0, 0), col)]
    montar(toalha, filhos, x, z, 0.0, "sul", 4)

    # Cadeiras em volta: metade virada no chão
    cores = ["Mat_Plastico_Vermelho", "Mat_Plastico_Amarelo", "Mat_Plastico_Azul", "Mat_Plastico_Verde"]
    for i, (cx, cz, giro, caida) in enumerate([(25.9, 9.55, 10, None), (27.1, 9.3, 160, "costas"),
                                               (28.2, 9.6, -20, None), (25.7, 11.6, 200, "lado"),
                                               (27.0, 11.75, 175, None), (28.4, 11.9, 120, "costas"),
                                               (24.9, 10.6, -95, None)]):
        corpo = cadeira(f"Festa_Lucas_Cadeira_{i + 1:02d}", col, cores[i % 4])
        por_cadeira(corpo, cx, cz, giro_para(cx, cz, x, z) + giro * 0.25, caida)
    # Presentes: alguns em cima de uma cadeira, outros no chão (um rasgado)
    papeis = [("Mat_Plastico_Azul", "Mat_Plastico_Amarelo"), ("Mat_Plastico_Rosa", "Mat_Plastico_Branco"),
              ("Mat_Plastico_Verde", "Mat_Plastico_Vermelho"), ("Mat_Plastico_Amarelo", "Mat_Plastico_Azul"),
              ("Mat_Plastico_Lilas", "Mat_Plastico_Amarelo")]
    for i, (px, pz, tam, giro, h) in enumerate([(28.9, 10.1, (0.35, 0.3, 0.25), 20, 0.0),
                                                 (29.1, 10.6, (0.25, 0.25, 0.2), -15, 0.0),
                                                 (28.95, 10.4, (0.22, 0.2, 0.15), 40, 0.25),
                                                 (25.3, 9.4, (0.4, 0.3, 0.3), 5, 0.0),
                                                 (26.4, 12.3, (0.3, 0.3, 0.18), 70, 0.0)]):
        p = presente(f"Festa_Lucas_Presente_{i + 1:02d}", col, tam, *papeis[i])
        montar(p, [], px, pz, h, "sul", giro, rot=(0, 0, giro) if i != 4 else (0, 75, giro))
    papel_rasgado = malha("Festa_Lucas_Papel_Rasgado", [g_plano([comum.p2(26.1, 12.5, 0.01), comum.p2(26.5, 12.45, 0.02),
                                                                comum.p2(26.4, 12.8, 0.01), comum.p2(26.0, 12.7, 0.03)])],
                          "Mat_Plastico_Rosa", col, origem="auto")
    _ = papel_rasgado
    # Cacho de balões murchando amarrado numa cadeira
    for i, (mat, alt) in enumerate((("Mat_Plastico_Vermelho", 0.6), ("Mat_Plastico_Azul", 0.85),
                                    ("Mat_Plastico_Verde", 0.4))):
        balao_meio_murcho(f"Festa_Lucas_Balao_{i + 1:02d}", col, mat, 28.25, 9.55, 0.85, alt, rng)


def salao(col, rng):
    palco(col, rng)
    mesa_festa_lucas(col, rng)
    teto = TETO["Salao"]

    # 8 mesas com toalha e cadeiras desalinhadas
    toalhas = ["Mat_Toalha_Xadrez_Vermelha", "Mat_Toalha_Branca"]
    cores = [["Mat_Plastico_Vermelho", "Mat_Plastico_Amarelo"], ["Mat_Plastico_Azul", "Mat_Plastico_Verde"],
             ["Mat_Plastico_Laranja", "Mat_Plastico_Azul"]]
    mesas = [(16.8, 7.4, ()), (17.0, 13.1, (2,)), (22.0, 9.0, ()), (21.9, 13.3, (1,)),
             (32.1, 8.9, (3,)), (32.3, 13.4, ()), (37.4, 6.1, (0,)), (37.6, 13.2, ())]
    for i, (mx, mz, caidas) in enumerate(mesas):
        mesa_redonda(f"Salao_Mesa_{i + 1:02d}", col, toalhas[i % 2], mx, mz, rng, cores[i % 3], caidas,
                     rng.uniform(-25, 25))

    # Biombos (divisórias sanfonadas) que quebram a visão de quem entra pelas portas do corredor
    for nome, bx, z0b, z1b in (("Salao_Biombo_01", 19.4, 10.8, 12.9), ("Salao_Biombo_02", 34.9, 10.9, 12.9)):
        n = 3
        pecas, molduras = [], []
        for i in range(n):
            za, zb = z0b + (z1b - z0b) * i / n, z0b + (z1b - z0b) * (i + 1) / n
            xa = bx + (0.13 if i % 2 else -0.13)
            xb_ = bx + (-0.13 if i % 2 else 0.13)
            pa, pb = comum.p2(xa, za, 0.12), comum.p2(xb_, zb, 0.12)
            pecas.append(g_plano([pa, pb, V((pb.x, pb.y, 1.75)), V((pa.x, pa.y, 1.75))]))
            molduras += g_tubo([V((pa.x, pa.y, 0.0)), V((pa.x, pa.y, 1.8))], 0.02, 4)
            molduras += g_tubo([V((pa.x, pa.y, 1.78)), V((pb.x, pb.y, 1.78))], 0.015, 4)
        molduras += g_tubo([V((pb.x, pb.y, 0.0)), V((pb.x, pb.y, 1.8))], 0.02, 4)
        b = malha(nome, molduras, "Mat_Madeira_Escura", col, origem="auto")
        tecido = malha(nome + "_Tecido", pecas, "Mat_Plastico_Lilas" if nome.endswith("1") else "Mat_Plastico_Laranja",
                       col, origem="auto")
        prender(tecido, b)
        c = colisao(nome, (0.4, z1b - z0b, 1.8), comum.p2(bx, (z0b + z1b) / 2, 0.0), col)
        prender(c, b)

    # Balcão de doces e bebidas: quebra a linha de visão entre a porta oeste e o centro
    balc = caixas("Salao_Balcao", [((0.7, 2.4, 1.0), (0, 0, 0))], "Mat_Madeira_Envernizada", col)
    filhos = [caixas("Salao_Balcao_Tampo", [((0.8, 2.5, 0.05), (0, 0, 1.0))], "Mat_Madeira_Escura", col),
              malha("Salao_Balcao_Potes", [g_cil(0.12, 0.28, (0, -0.7, 1.05), seg=10), g_cil(0.1, 0.22, (0.05, -0.35, 1.05), seg=10),
                                           g_cil(0.12, 0.3, (0, 0.6, 1.05), seg=10)], "Mat_Vidro_Escuro", col),
              malha("Salao_Balcao_Copos", [g_cil(0.04, 0.12, (-0.2 + 0.1 * (i % 3), 0.1 + 0.12 * (i // 3), 1.05), seg=6)
                                           for i in range(6)], "Mat_Plastico_Branco", col),
              caixas("Salao_Balcao_Placa", [((0.02, 1.4, 0.3), (-0.36, 0, 0.55))], "Mat_Plastico_Amarelo", col),
              texto("Salao_Balcao_Placa_Texto", "DOCES & REFRIS", 0.12, "Mat_Texto_Vermelho", col,
                    (-0.375, 0, 0.7), 1.3, ARQ_BUNGEE, rot=(0, 0, -90)),
              colisao("Salao_Balcao", (0.8, 2.5, 1.05), (0, 0, 0), col)]
    montar(balc, filhos, 25.0, 13.5, 0.0, "sul", 0)

    # Canto noroeste: mesa de presentes esquecida; canto nordeste: mesa de som velha e caixas
    mp = caixas("Salao_Mesa_Presentes", [((1.6, 0.7, 0.04), (0, 0, 0.72))] +
                [((0.04, 0.04, 0.72), (sx * 0.75, sy * 0.3, 0)) for sx in (-1, 1) for sy in (-1, 1)],
                "Mat_Madeira_Clara", col)
    filhos = [colisao("Salao_Mesa_Presentes", (1.6, 0.7, 0.76), (0, 0, 0), col)]
    for i, (px, tam, cores_p) in enumerate([(-0.5, (0.35, 0.3, 0.3), ("Mat_Plastico_Verde", "Mat_Plastico_Amarelo")),
                                            (0.05, (0.3, 0.3, 0.22), ("Mat_Plastico_Azul", "Mat_Plastico_Vermelho")),
                                            (0.5, (0.25, 0.25, 0.35), ("Mat_Plastico_Rosa", "Mat_Plastico_Branco"))]):
        p = presente(f"Salao_Mesa_Presentes_Presente_{i + 1:02d}", col, tam, *cores_p, rot=(0, 0, 15 * i - 10))
        p.location = V((px, 0, 0.76))
        filhos.append(p)
    montar(mp, filhos, 16.5, 0.65, 0.0, "sul", 3)
    ms = caixas("Salao_Mesa_Som", [((1.2, 0.6, 0.8), (0, 0, 0))], "Mat_Madeira_Escura", col)
    filhos = [caixas("Salao_Mesa_Som_Console", [((1.0, 0.45, 0.08), (0, -0.02, 0.8), (-12, 0, 0))], "Mat_Metal_Escuro", col),
              malha("Salao_Mesa_Som_Botoes", [g_cil(0.015, 0.03, (-0.4 + 0.1 * (i % 9), -0.1 + 0.12 * (i // 9), 0.86), seg=5)
                                              for i in range(18)], "Mat_Plastico_Branco", col),
              colisao("Salao_Mesa_Som", (1.2, 0.6, 0.9), (0, 0, 0), col)]
    montar(ms, filhos, 38.3, 1.4, 0.0, "oeste", 6)
    pilha = caixas("Salao_Caixas_Canto", [((0.7, 0.6, 0.5), (0, 0, 0)), ((0.6, 0.5, 0.45), (0.05, 0.03, 0.5), (0, 0, 8)),
                                          ((0.5, 0.45, 0.4), (0.7, 0.1, 0.0), (0, 0, -12))], "Mat_Papelao_Caixa", col)
    montar(pilha, [colisao("Salao_Caixas_Canto", (1.3, 0.7, 0.95), (0.3, 0.05, 0), col)], 38.8, 3.6, 0.0, "oeste")

    # Pilha de cadeiras empilhadas no canto sudoeste e cadeirão de bebê
    empilhadas = []
    for i in range(5):
        empilhadas += [g_caixa((0.42, 0.42, 0.04), (0.01 * i, 0.012 * i, 0.42 + 0.09 * i), (0, 0, 2 * i)),
                       g_caixa((0.42, 0.04, 0.42), (0.01 * i, 0.2 + 0.012 * i, 0.46 + 0.09 * i), (0, 0, 2 * i))]
    emp = malha("Salao_Cadeiras_Empilhadas", empilhadas, "Mat_Plastico_Vermelho", col)
    montar(emp, [colisao("Salao_Cadeiras_Empilhadas", (0.5, 0.5, 1.3), (0, 0, 0), col)], 14.55, 15.4, 0.0, "norte", 7)
    cad_bebe = malha("Salao_Cadeirao", [g_caixa((0.4, 0.4, 0.05), (0, 0, 0.75)), g_caixa((0.4, 0.05, 0.4), (0, 0.18, 0.8)),
                                        g_caixa((0.45, 0.3, 0.03), (0, -0.25, 0.92))], "Mat_Plastico_Branco", col)
    pes = malha("Salao_Cadeirao_Pes", [g_cil(0.015, 0.78, (sx * 0.2, sy * 0.2, 0), (sy * 8, -sx * 8, 0), 4)
                                       for sx in (-1, 1) for sy in (-1, 1)], "Mat_Metal_Cinza", col)
    montar(cad_bebe, [pes], 15.1, 9.3, 0.0, "leste", 25)

    # Claraboia suja no teto, bem em cima da festa do meio (ilha de luar)
    clar = caixas("Salao_Claraboia", [((1.8, 0.1, 0.12), (0, sy * 0.85, -0.12)) for sy in (-1, 1)] +
                  [((0.1, 1.6, 0.12), (sx * 0.85, 0, -0.12)) for sx in (-1, 1)] +
                  [((0.06, 1.6, 0.06), (0, 0, -0.08))], "Mat_Metal_Escuro", col)
    vidro = malha("Salao_Claraboia_Vidro", [g_plano([(-0.82, -0.82, -0.03), (0.82, -0.82, -0.03), (0.82, 0.82, -0.03),
                                                    (-0.82, 0.82, -0.03)])], "Mat_Vidro_Sujo", col)
    montar(clar, [vidro], 27.0, 10.5, teto)
    luz("claraboia", col, 27.0, 10.5, teto - 0.15, nn=1)

    # Placa do forro caída no chão e fios pendurados do buraco
    malha("Salao_Placa_Forro_Caida", [g_caixa((0.62, 0.62, 0.02), comum.p2(23.6, 6.9, 0.0), (4, -3, 27)),
                                      g_caixa((0.3, 0.25, 0.02), comum.p2(24.3, 7.3, 0.0), (0, 6, 70))],
          "Mat_Teto_Escuro", col, origem="auto")
    malha("Salao_Fios_Pendurados", g_tubo([comum.p2(23.4, 6.6, teto), comum.p2(23.45, 6.65, teto - 0.7),
                                           comum.p2(23.6, 6.7, teto - 1.0)], 0.008)
          + g_tubo([comum.p2(23.6, 6.5, teto), comum.p2(23.7, 6.55, teto - 0.45)], 0.006), "Mat_Fio", col, origem="auto")

    # Goteira com balde
    balde = malha("Salao_Balde_Goteira", [g_cil(0.15, 0.3, (0, 0, 0), seg=10, raio_topo=0.18)], "Mat_Plastico_Azul", col)
    montar(balde, [], 35.6, 7.7)
    som("goteira", col, 35.6, 7.7, teto - 0.1)
    decal("mancha_agua", col, 35.6, 7.7, (1.6, 1.4, 0.3))

    # Bandeirinhas: uma linha inteira e outra arrebentada (pendurada até quase o chão)
    for linha, (xa, za, xb, zb, quebrada) in enumerate([(14.2, 7.0, 39.8, 7.0, False), (14.2, 12.2, 39.8, 12.2, True)]):
        por_cor = {"Mat_Plastico_Vermelho": [], "Mat_Plastico_Amarelo": [], "Mat_Plastico_Azul": []}
        cores_b = list(por_cor)
        corda = []
        if not quebrada:
            pts = [comum.p2(xa + (xb - xa) * t / 10, za, teto - 0.25 - 0.25 * math.sin(math.pi * t / 10)) for t in range(11)]
        else:
            # arrebentou perto de x=27: uma metade cai até o chão, a outra fica pendurada de lado
            pts = [comum.p2(xa, za, teto - 0.25), comum.p2(20.0, za, teto - 0.55), comum.p2(25.0, za + 0.2, teto - 1.4),
                   comum.p2(26.4, za + 0.3, 0.05), comum.p2(27.6, za + 0.6, 0.01)]
        corda += g_tubo(pts, 0.005, 3)
        for a, b in zip(pts[:-1], pts[1:]):
            d = b - a
            n = int(d.length / 0.45)
            for i in range(n):
                p = a + d * (i / max(n, 1))
                if p.z < 0.25:
                    continue
                q = p + d.normalized() * 0.28
                cor = cores_b[(i + linha) % 3]
                por_cor[cor].append(g_plano([p, q, (p + q) / 2 + V((0, 0, -0.28))]))
        for cor, pecas in por_cor.items():
            if pecas:
                malha(f"Salao_Bandeirinhas_{linha + 1}_{cor.split('_')[-1]}", pecas, cor, col, origem="auto")
        malha(f"Salao_Bandeirinhas_{linha + 1}_Corda", corda, "Mat_Plastico_Branco", col, origem="auto")
    # bandeirinhas caídas no chão
    malha("Salao_Bandeirinhas_Caidas", [g_plano([comum.p2(26.8 + 0.35 * i, 12.9 + 0.1 * (i % 2), 0.01),
                                                 comum.p2(27.1 + 0.35 * i, 12.95, 0.01),
                                                 comum.p2(26.95 + 0.35 * i, 13.2 + 0.05 * i, 0.01)]) for i in range(4)],
          "Mat_Plastico_Amarelo", col, origem="auto")

    # Balões murchos e lixo de festa espalhados
    baloes_murchos("Salao_Baloes_Murchos", col, [(15.2, 5.6), (19.0, 6.4), (23.2, 11.4), (30.4, 6.9), (33.9, 14.9),
                                                 (36.6, 9.0), (39.2, 14.9), (20.9, 15.3), (29.9, 12.2), (18.4, 14.8),
                                                 (35.8, 3.9), (15.4, 3.6)], rng)
    lixo("Salao", col, [(14.4, 39.6, 5.3, 15.6), (14.4, 19.6, 0.4, 5.0), (34.4, 39.6, 0.4, 5.0)], 70, rng)

    # Confete e outras manchas (bastante nos cantos e rodapés)
    for (cx, cz, sx, sz) in [(27.0, 10.5, 3.2, 2.4), (22.0, 9.0, 2.0, 2.0), (32.3, 13.4, 2.0, 2.0), (17.0, 13.1, 1.8, 1.8),
                             (27.0, 6.9, 2.5, 1.2)]:
        decal("confete", col, cx, cz, (sx, sz, 0.4))
    decal("refrigerante", col, 32.6, 9.6, (0.9, 0.7, 0.3))
    decal("pegadas", col, 20.0, 14.0, (0.8, 3.0, 0.3))
    decal("pegadas", col, 34.0, 13.5, (0.8, 3.5, 0.3))
    decal("rachadura", col, 39.9, 11.0, (1.2, 1.0, 0.3), 1.6, "leste")
    decal("marca_mao", col, 14.1, 12.0, (0.4, 0.4, 0.3), 1.2, "oeste")
    for (cx, cz) in [(14.4, 0.4), (39.6, 0.4), (14.4, 15.6), (39.6, 15.6), (27.0, 15.7)]:
        decal("mancha_agua", col, cx, cz, (1.2, 1.2, 0.3))
    teias_cantos("Salao", col, "Salao")


# ---------------------------------------------------------------------------
# RECEPÇÃO
# ---------------------------------------------------------------------------

def banco(nome, col, larg, mat="Mat_Plastico_Vermelho"):
    b = caixas(nome, [((larg, 0.45, 0.06), (0, 0, 0.42)), ((larg, 0.06, 0.45), (0, 0.2, 0.47), (-8, 0, 0))], mat, col)
    pes = caixas(nome + "_Pes", [((0.05, 0.4, 0.42), (sx * (larg / 2 - 0.1), 0, 0)) for sx in (-1, 1)],
                 "Mat_Metal_Escuro", col)
    return b, [pes, colisao(nome, (larg, 0.5, 0.95), (0, 0, 0), col)]


def planta_seca(nome, col, x, z, rng):
    vaso = malha(nome, [g_cil(0.2, 0.4, (0, 0, 0), seg=10, raio_topo=0.25)], "Mat_Vaso_Terracota", col)
    galhos = []
    for i in range(6):
        a = i * 60 + rng.uniform(-20, 20)
        galhos += g_tubo([(0, 0, 0.35), (0.25 * math.cos(math.radians(a)), 0.25 * math.sin(math.radians(a)),
                                         0.9 + rng.uniform(-0.2, 0.2)),
                          (0.4 * math.cos(math.radians(a + 20)), 0.4 * math.sin(math.radians(a + 20)), 0.6)], 0.012, 4)
    folhas = [g_caixa((0.12, 0.06, 0.005), (0.3 * math.cos(math.radians(a)), 0.3 * math.sin(math.radians(a)), 0.01),
                      (0, 0, a)) for a in range(0, 360, 70)]
    g = malha(nome + "_Galhos", galhos, "Mat_Planta_Seca", col)
    f = malha(nome + "_Folhas_Caidas", folhas, "Mat_Planta_Seca", col)
    montar(vaso, [g, f, colisao(nome, (0.5, 0.5, 0.9), (0, 0, 0), col)], x, z, 0.0, "sul", rng.uniform(0, 90))


def standee_tito(col):
    """
    Figura de papelão (standee) do Tito em tamanho real, na recepção (ARTE-26).
    - Arte__standee_tito: plano com a imagem (fundo verde chapado). No Godot o verde é apagado
      (chroma key + alpha scissor) e o jogo empilha camadas recortadas atrás dela, formando a
      espessura do papelão. Sem a imagem, o jogo desenha uma silhueta simples do urso.
    - Base de papelão no chão, apoio (perna) atrás e a placa "BEM-VINDO!" no pé.
    A frente olha para as portas do fliperama e do corredor das festas (quem entra dá de cara com ele).
    """
    alt = 1.8
    larg = alt * 9 / 16
    base = caixas("Recepcao_Standee_Tito_Base", [((0.8, 0.55, 0.03), (0, 0.15, 0))], "Mat_Papelao_Caixa", col)
    arte = comum.plano_arte("standee_tito.jpg", larg, alt, V((0, 0, 0.03)), col)
    # perna de apoio: uma tira de papelão dobrada, do meio das costas até o chão
    apoio = caixas("Recepcao_Standee_Tito_Apoio", [((0.12, 0.012, 0.95), (0, 0.42, 0.0), (24, 0, 0))],
                   "Mat_Papelao_Caixa", col)
    placa = caixas("Recepcao_Standee_Tito_Placa", [((0.66, 0.025, 0.2), (0, -0.09, 0.03))], "Mat_Plastico_Amarelo", col)
    txt = texto("Recepcao_Standee_Tito_Placa_Texto", "BEM-VINDO!", 0.11, "Mat_Texto_Vermelho", col,
                (0, -0.109, 0.13), 0.58, ARQ_BUNGEE)
    # 120°: entre a porta larga do fliperama (150°) e a do corredor das festas (87°)
    montar(base, [arte, apoio, placa, txt, colisao("Recepcao_Standee_Tito", (0.8, 0.6, 1.85), (0, 0.15, 0), col)],
           19.3, 39.4, 0.0, "sul", 120)
    return base


def recepcao(col, rng):
    x0, x1, z0, z1 = RET["Recepcao"]
    teto = TETO["Recepcao"]

    # --- Portas da frente (decorativas, trancadas com corrente), no vão da parede sul
    porta = [e for e in planta_v2.PORTAS if e[4] == "catraca"][0]
    xp, larg_vao = porta[2], porta[3]
    folha = larg_vao / 2 - 0.03
    batente = caixas("Recepcao_Porta_Frente", [((larg_vao, 0.12, 0.1), (0, 0, 2.2)),
                                               ((0.08, 0.12, 2.3), (-larg_vao / 2 + 0.04, 0, 0)),
                                               ((0.08, 0.12, 2.3), (larg_vao / 2 - 0.04, 0, 0)),
                                               ((0.06, 0.12, 2.2), (0, 0, 0))], "Mat_Metal_Escuro", col)
    filhos = []
    for lado, sx in (("Esq", -1), ("Dir", 1)):
        cx = sx * (folha / 2 + 0.03)
        filhos.append(caixas(f"Recepcao_Porta_Frente_Folha_{lado}",
                             [((folha, 0.05, 0.12), (cx, 0, 0)), ((folha, 0.05, 0.12), (cx, 0, 2.06)),
                              ((0.08, 0.05, 2.2), (cx - sx * (folha / 2 - 0.04), 0, 0))], "Mat_Metal_Escuro", col))
        filhos.append(malha(f"Recepcao_Porta_Frente_Vidro_{lado}",
                            [g_plano([(cx - folha / 2 + 0.08, 0, 0.12), (cx + folha / 2, 0, 0.12),
                                      (cx + folha / 2, 0, 2.06), (cx - folha / 2 + 0.08, 0, 2.06)])],
                            "Mat_Vidro_Porta", col))
        filhos.append(caixas(f"Recepcao_Porta_Frente_Puxador_{lado}", [((0.03, 0.05, 0.5), (sx * 0.12, -0.06, 0.8))],
                             "Mat_Inox", col))
    # corrente enrolada nos puxadores + cadeado
    elos = [g_caixa((0.07, 0.02, 0.035) if i % 2 == 0 else (0.07, 0.035, 0.02),
                    (-0.2 + i * 0.05, -0.1, 1.02 + 0.08 * math.sin(i * 0.5)), (0, 0, 0)) for i in range(9)]
    elos += [g_caixa((0.02, 0.035, 0.07), (0.25, -0.1, 1.0 - 0.06 * i)) for i in range(5)]
    filhos.append(malha("Recepcao_Porta_Frente_Corrente", elos, "Mat_Metal_Cinza", col))
    filhos.append(caixas("Recepcao_Porta_Frente_Cadeado", [((0.08, 0.04, 0.1), (0.25, -0.12, 0.62))], "Mat_Ouro", col))
    filhos.append(caixas("Recepcao_Porta_Frente_Aviso", [((0.42, 0.005, 0.3), (-0.55, -0.03, 1.5), (0, 0, 0))],
                         "Mat_Papel_Branco", col))
    filhos.append(texto("Recepcao_Porta_Frente_Aviso_Texto", "FECHADO\nPOR TEMPO\nINDETERMINADO", 0.05, "Mat_Texto_Vermelho",
                        col, (-0.55, -0.036, 1.65), 0.38, ARQ_BUNGEE))
    filhos.append(colisao("Recepcao_Porta_Frente", (larg_vao, 0.25, 2.3), (0, 0, 0), col))
    montar(batente, filhos, xp, z1, 0.0, "norte")
    # luar entrando pelas portas de vidro
    luz("claraboia", col, xp, z1 - 0.6, 2.4, nn=2)
    som("vento", col, xp, z1 - 0.3, 1.2)
    decal("pegadas", col, xp + 0.5, z1 - 1.5, (1.0, 2.5, 0.3))

    # --- Placa SAÍDA verde em cima da porta. Antes uma letra ficava "queimada" (escura), de
    # propósito, mas no jogo isso parecia defeito de fonte (o playtest leu o "Í" como uma letra
    # preta): agora todas acendem. As letras ficam 6 mm na frente da placa (sem z-fighting).
    placa = caixas("Recepcao_Placa_Saida", [((0.8, 0.1, 0.28), (0, -0.05, 0))], "Mat_Placa_Saida", col)
    tam = 0.17
    vfs = [texto_vf(ch, tam, ARQ_BUNGEE, centrar_altura=False) for ch in "SAÍDA"]
    # todas as letras na mesma linha de base: sobe o conjunto para o meio da placa
    base_y = (min(v.z for vf in vfs for v in vf[0]) + max(v.z for vf in vfs for v in vf[0])) / 2
    vfs = [([v - V((0, 0, base_y)) for v in vf[0]], vf[1]) for vf in vfs]
    larguras = [largura_vf(v) + 0.025 for v in vfs]
    s = -sum(larguras) / 2
    acesas = []
    for vf, w in zip(vfs, larguras):
        acesas.append(_aplicar(vf, Matrix.Translation(V((s + w / 2, -0.106, 0.13)))))
        s += w
    la = malha("Recepcao_Placa_Saida_Letras", acesas, "Mat_Letra_Saida", col)
    marcar_texto(la, "SAÍDA", ARQ_BUNGEE)
    montar(placa, [la], xp, z1 - 0.1, 2.45, "norte")

    # --- Catraca com grades (barra a entrada; as pontas ficam abertas para circular)
    z_cat = z1 - 2.3
    cat = caixas("Recepcao_Catraca", [((0.25, 0.35, 0.95), (sx, 0, 0)) for sx in (-0.75, 0.75)], "Mat_Inox", col)
    bracos = []
    for sx in (-0.75, 0.75):
        for k in range(3):
            a = k * 120 + (20 if sx > 0 else 0)
            bracos.append(g_cil(0.02, 0.5, (sx + 0.13, 0, 0.85), (a, 90, 0), 5))
    bracos.append(g_cil(0.02, 0.45, (0.88, 0.05, 0.02), (90, 0, 30), 5))   # braço quebrado no chão
    br = malha("Recepcao_Catraca_Bracos", bracos, "Mat_Inox", col)
    grades = []
    for xa, xb in ((-3.2, -1.0), (1.0, 3.2)):
        grades += g_tubo([(xa, 0, 0.95), (xb, 0, 0.95)], 0.025, 6)
        grades += g_tubo([(xa, 0, 0.5), (xb, 0, 0.5)], 0.02, 6)
        for xx in (xa, (xa + xb) / 2, xb):
            grades += g_tubo([(xx, 0, 0), (xx, 0, 0.97)], 0.03, 6)
    gr = malha("Recepcao_Catraca_Grades", grades, "Mat_Metal_Cinza", col)
    montar(cat, [br, gr, colisao("Recepcao_Catraca", (6.4, 0.4, 1.0), (0, 0, 0), col)], xp, z_cat, 0.0, "sul")

    # --- Bilheteria com vidro (canto sudoeste)
    bx0, bx1, bz0, bz1 = x0 + 1.0, x0 + 4.8, z1 - 3.8, z1 - 0.15
    bl, bp = bx1 - bx0, bz1 - bz0
    bil = caixas("Recepcao_Bilheteria", [((bl, 0.08, 1.0), (0, -bp / 2, 0)), ((0.08, bp, 1.0), (bl / 2, 0, 0)),
                                         ((0.08, bp, 2.4), (-bl / 2, 0, 0)), ((bl, 0.08, 2.4), (0, bp / 2, 0)),
                                         ((bl + 0.2, bp + 0.2, 0.1), (0, 0, 2.4)),
                                         ((bl, 0.35, 0.05), (0, -bp / 2 + 0.12, 1.0)),
                                         ((0.35, bp, 0.05), (bl / 2 - 0.12, 0, 1.0))], "Mat_Madeira_Envernizada", col)
    vidros = malha("Recepcao_Bilheteria_Vidro", [
        g_plano([(-bl / 2, -bp / 2, 1.05), (bl / 2, -bp / 2, 1.05), (bl / 2, -bp / 2, 2.4), (-bl / 2, -bp / 2, 2.4)]),
        g_plano([(bl / 2, -bp / 2, 1.05), (bl / 2, bp / 2, 1.05), (bl / 2, bp / 2, 2.4), (bl / 2, -bp / 2, 2.4)])],
        "Mat_Vidro_Bilheteria", col)
    caixilhos = malha("Recepcao_Bilheteria_Caixilhos", g_tubo([(-bl / 2, -bp / 2, 1.7), (bl / 2, -bp / 2, 1.7)], 0.02, 4)
                      + g_tubo([(0, -bp / 2, 1.05), (0, -bp / 2, 2.4)], 0.02, 4)
                      + g_tubo([(bl / 2, 0, 1.05), (bl / 2, 0, 2.4)], 0.02, 4), "Mat_Metal_Escuro", col)
    letreiro = placa_texto("Recepcao_Bilheteria_Letreiro", col, "BILHETERIA", 2.0, 0.32, 0, 0, 0, "sul",
                           "Mat_Plastico_Amarelo", "Mat_Texto_Vermelho")
    letreiro.parent = bil
    letreiro.location = V((0, -bp / 2 - 0.08, 2.5))
    letreiro.rotation_euler = (0, 0, 0)
    banquinho = malha("Recepcao_Bilheteria_Banco", [g_cil(0.18, 0.05, (-0.3, 0.4, 0.65), seg=10),
                                                    g_cil(0.03, 0.65, (-0.3, 0.4, 0), seg=5)], "Mat_Metal_Escuro", col)
    registradora = caixas("Recepcao_Bilheteria_Registradora", [((0.4, 0.3, 0.2), (0.6, -bp / 2 + 0.3, 1.05))],
                          "Mat_Metal_Escuro", col)
    rolos = malha("Recepcao_Bilheteria_Rolos_Ingresso", [g_cil(0.08, 0.06, (-0.6, -bp / 2 + 0.2, 1.05), seg=10),
                                                         g_cil(0.08, 0.06, (bl / 2 - 0.15, 0.5, 1.05), seg=10)],
                  "Mat_Plastico_Vermelho", col)
    ingressos = malha("Recepcao_Bilheteria_Ingressos", [g_caixa((0.05, 0.6, 0.002), (-0.62, -bp / 2 - 0.25, 0.0), (0, 0, 15)),
                                                        g_caixa((0.05, 0.4, 0.002), (bl / 2 + 0.3, 0.7, 0.0), (0, 0, 70))],
                      "Mat_Plastico_Vermelho", col)
    montar(bil, [vidros, caixilhos, banquinho, registradora, rolos, ingressos,
                 colisao("Recepcao_Bilheteria", (bl + 0.1, bp + 0.1, 2.5), (0, 0, 0), col)],
           (bx0 + bx1) / 2, (bz0 + bz1) / 2, 0.0, "sul")

    # --- Balcão de atendimento na parede leste, com o cardápio (ARTE-18) atrás e o porta-retrato
    balc = caixas("Recepcao_Balcao", [((3.3, 0.7, 1.0), (0, 0, 0))], "Mat_Madeira_Escura", col)
    pr = caixas("Recepcao_Porta_Retrato", [((0.36, 0.03, 0.26), (0, 0, 0))], "Mat_Madeira_Envernizada", col)
    foto = comum.plano_arte("foto_festa_antiga.jpg", 0.3, 0.2, V((0, -0.021, 0.03)), col)  # 6 mm do porta-retrato
    pe_pr = caixas("Recepcao_Porta_Retrato_Pe", [((0.04, 0.12, 0.2), (0, 0.06, 0), (-25, 0, 0))], "Mat_Madeira_Envernizada", col)
    for f_ in (foto, pe_pr):
        f_.parent = pr
    pr.location = V((-0.9, -0.12, 1.05))
    pr.rotation_euler = (math.radians(-10), 0, math.radians(-15))
    filhos = [caixas("Recepcao_Balcao_Tampo", [((3.4, 0.8, 0.05), (0, 0, 1.0))], "Mat_Madeira_Clara", col),
              caixas("Recepcao_Caixa_Registradora", [((0.4, 0.35, 0.22), (0.7, 0.05, 1.05)),
                                                     ((0.3, 0.05, 0.15), (0.7, 0.2, 1.27))], "Mat_Metal_Escuro", col),
              malha("Recepcao_Sino_Balcao", [g_cil(0.05, 0.05, (-0.3, -0.2, 1.05), seg=8, raio_topo=0.02)], "Mat_Ouro", col),
              malha("Recepcao_Balcao_Pote_Pirulitos", [g_cil(0.1, 0.22, (0.1, -0.1, 1.05), seg=10)], "Mat_Vidro_Escuro", col),
              caixas("Recepcao_Balcao_Gaveta_Aberta", [((0.5, 0.4, 0.15), (1.2, 0.45, 0.7))], "Mat_Madeira_Clara", col),
              pr,
              colisao("Recepcao_Balcao", (3.4, 0.8, 1.05), (0, 0, 0), col)]
    montar(balc, filhos, x1 - 2.4, 36.0, 0.0, "oeste")
    moldura_arte("Recepcao_Cardapio", col, "cardapio.jpg", 0.9, 1.2, x1 - 0.1, 36.0, 1.25, "oeste")
    cad = cadeira("Recepcao_Cadeira_Atendente", col, "Mat_Plastico_Preto")
    por_cadeira(cad, x1 - 1.2, 35.3, giro_para(x1 - 1.2, 35.3, x1 - 2.4, 35.6))

    # --- Bancos de espera
    for nome, bx, bz, frente, larg in (("Recepcao_Banco_01", x0 + 0.42, 35.0, "leste", 2.0),
                                       ("Recepcao_Banco_02", 16.6, z0 + 0.42, "sul", 2.0),
                                       ("Recepcao_Banco_03", 27.5, z0 + 0.42, "sul", 2.0),
                                       ("Recepcao_Banco_04", 27.6, z1 - 0.42, "norte", 2.0)):
        b, filhos = banco(nome, col, larg)
        montar(b, filhos, bx, bz, 0.0, frente, rng.uniform(-4, 4))
    # mochila esquecida no banco (detalhe de história) e uma revista
    malha("Recepcao_Mochila_Esquecida", [g_caixa((0.3, 0.18, 0.38), comum.p2(16.1, 33.55, 0.48), (0, -10, 12))],
          "Mat_Plastico_Azul", col, origem="auto")
    malha("Recepcao_Revistas", [g_caixa((0.22, 0.3, 0.01), comum.p2(27.9, 33.5, 0.48), (0, 0, 20)),
                                g_caixa((0.22, 0.3, 0.01), comum.p2(28.1, 33.9, 0.0), (0, 0, -35))],
          "Mat_Papel_Branco", col, origem="auto")

    # --- Plantas secas
    planta_seca("Recepcao_Planta_Seca_01", col, x0 + 0.4, 40.75, rng)
    planta_seca("Recepcao_Planta_Seca_02", col, x1 - 0.45, z1 - 0.45, rng)
    planta_seca("Recepcao_Planta_Seca_03", col, 25.7, z0 + 0.45, rng)

    # --- Bebedouro, placa de boas-vindas, display de papelão do Tito, fila com cordão
    beb = caixas("Recepcao_Bebedouro", [((0.4, 0.35, 0.9), (0, 0, 0))], "Mat_Inox", col)
    montar(beb, [caixas("Recepcao_Bebedouro_Bacia", [((0.36, 0.3, 0.06), (0, -0.02, 0.9))], "Mat_Metal_Cinza", col),
                 colisao("Recepcao_Bebedouro", (0.4, 0.35, 0.96), (0, 0, 0), col)], 19.6, z0 + 0.3, 0.0, "sul")
    placa_texto("Recepcao_Placa_Boas_Vindas", col, "BEM-VINDO À\nPIZZARIA DO TITO", 2.6, 0.55, 23.0, z0 + 0.1, 2.5,
                "sul", "Mat_Plastico_Vermelho", "Mat_Texto_Branco", tam=0.18)
    standee_tito(col)
    for i, (px, pz, caido) in enumerate([(26.8, 41.0, False), (26.8, 39.6, False), (28.2, 38.6, True)]):
        poste = malha(f"Recepcao_Poste_Fila_{i + 1:02d}", [g_cil(0.15, 0.03, (0, 0, 0), seg=10),
                                                           g_cil(0.025, 0.9, (0, 0, 0.03), seg=6),
                                                           g_esf(0.04, (0, 0, 0.95), 6, 4)], "Mat_Ouro", col)
        if caido:
            montar(poste, [], px, pz, 0.15, rot=(90, 0, 50))
        else:
            montar(poste, [], px, pz)
    malha("Recepcao_Cordao_Fila", g_tubo([comum.p2(26.8, 41.0, 0.9), comum.p2(26.8, 40.3, 0.65), comum.p2(26.8, 39.6, 0.9)], 0.015, 4)
          + g_tubo([comum.p2(26.8, 39.6, 0.9), comum.p2(27.3, 39.2, 0.3), comum.p2(27.7, 38.9, 0.02)], 0.015, 4),
          "Mat_Cortina_Vermelha", col, origem="auto")
    # caixa de achados e perdidos com brinquedos
    ach = caixas("Recepcao_Achados_Perdidos", [((0.5, 0.4, 0.35), (0, 0, 0))], "Mat_Papelao_Caixa", col)
    brinq = malha("Recepcao_Achados_Brinquedos", [g_esf(0.09, (-0.1, 0, 0.38), 8, 5), g_esf(0.07, (0.12, 0.05, 0.36), 8, 5),
                                                  g_caixa((0.12, 0.08, 0.1), (0.25, -0.3, 0.0), (0, 0, 30))],
                  "Mat_Plastico_Amarelo", col)
    rot_ach = texto("Recepcao_Achados_Perdidos_Texto", "ACHADOS E\nPERDIDOS", 0.06, "Mat_Texto_Preto", col, (0, -0.205, 0.2),
                    0.45, ARQ_GOCHI)
    montar(ach, [brinq, rot_ach], 20.4, z1 - 0.5, 0.0, "norte", 8)

    # --- Lixo, papéis, decals, teias
    lixo("Recepcao", col, [(x0 + 0.5, x1 - 0.6, z0 + 0.6, z1 - 2.8), (25.0, x1 - 0.5, z1 - 2.4, z1 - 0.3)], 40, rng)
    baloes_murchos("Recepcao_Baloes_Murchos", col, [(21.0, 36.5), (29.5, 42.5), (15.2, 37.0)], rng)
    decal("mancha_agua", col, x0 + 0.5, z0 + 0.5, (1.2, 1.2, 0.3))
    decal("mancha_agua", col, x1 - 0.6, z1 - 0.6, (1.4, 1.2, 0.3))
    decal("pegadas", col, 23.0, 37.0, (1.0, 4.0, 0.3))
    decal("refrigerante", col, 25.5, 38.0, (0.8, 0.6, 0.3))
    decal("rachadura", col, x0 + 0.1, 42.0, (1.0, 1.2, 0.3), 2.0, "oeste")
    decal("giz_cera", col, 18.0, z0 + 0.1, (0.8, 0.5, 0.3), 0.6, "norte")
    teias_cantos("Recepcao", col, "Recepcao")


# ---------------------------------------------------------------------------
# CORREDOR PRINCIPAL (só coisas encostadas nas paredes, até 0,4 m)
# ---------------------------------------------------------------------------

def corredor_principal(col, rng):
    x0, x1, z0, z1 = RET["Corredor_Principal"]
    teto = TETO["Corredor_Principal"]
    zn, zs = z0 + 0.1, z1 - 0.1           # faces das paredes norte e sul

    # Pôsteres ARTE-12 a 15, com moldura (alguns tortos)
    for nome, arq, x, z, frente, incl in (("Corredor_Poster_01", "poster_seja_feliz.jpg", 13.5, zn, "sul", 3),
                                          ("Corredor_Poster_02", "poster_pipoca_pular.jpg", 23.0, zs, "norte", -6),
                                          ("Corredor_Poster_03", "poster_pizza_dobro.jpg", 27.0, zn, "sul", 0),
                                          ("Corredor_Poster_04", "poster_aniversario.jpg", 38.0, zs, "norte", 9)):
        moldura_arte(nome, col, arq, 0.6, 0.9, x, z, 1.2, frente, incl)

    # Extintores
    extintor("Corredor_Extintor_01", col, 2.8, zn, "sul")
    extintor("Corredor_Extintor_02", col, 51.0, zs, "norte")

    # Carrinho de limpeza fino, balde com esfregão e a placa "CUIDADO: PISO MOLHADO"
    car = caixas("Corredor_Carrinho_Limpeza", [((0.9, 0.36, 0.04), (0, 0, 0.12)), ((0.9, 0.36, 0.04), (0, 0, 0.55)),
                                               ((0.9, 0.36, 0.03), (0, 0, 0.9))], "Mat_Plastico_Amarelo", col)
    filhos = [malha("Corredor_Carrinho_Limpeza_Estrutura",
                    [g_cil(0.015, 0.92, (sx * 0.43, sy * 0.16, 0.0), seg=4) for sx in (-1, 1) for sy in (-1, 1)] +
                    [g_cil(0.04, 0.03, (sx * 0.4, sy * 0.14, 0.0), (90, 0, 0), 6) for sx in (-1, 1) for sy in (-1, 1)],
                    "Mat_Metal_Escuro", col),
              malha("Corredor_Carrinho_Limpeza_Frascos", [g_cil(0.04, 0.22, (-0.3 + 0.12 * i, 0.02 * (i % 2), 0.59), seg=6)
                                                         for i in range(4)] +
                    [g_caixa((0.3, 0.25, 0.25), (0.25, 0, 0.16))], "Mat_Plastico_Azul", col),
              malha("Corredor_Carrinho_Limpeza_Saco", [g_cil(0.17, 0.45, (0.0, 0, 0.93), seg=8, raio_topo=0.15)],
                    "Mat_Plastico_Preto", col),
              colisao("Corredor_Carrinho_Limpeza", (0.92, 0.38, 1.0), (0, 0, 0), col)]
    montar(car, filhos, 40.6, zs - 0.21, 0.0, "norte", 2)
    balde = malha("Corredor_Balde_Esfregao", [g_cil(0.15, 0.28, (0, 0, 0), seg=10, raio_topo=0.17)], "Mat_Plastico_Amarelo", col)
    esf = malha("Corredor_Esfregao", [g_cil(0.012, 1.3, (0, 0.02, 0.1), (-12, 0, 0), 5),
                                      g_cil(0.08, 0.12, (0, 0, 0.12), seg=6)], "Mat_Madeira_Clara", col)
    montar(balde, [esf], 41.6, zs - 0.2, 0.0, "norte")
    pm = malha("Corredor_Placa_Piso_Molhado", [g_caixa((0.3, 0.02, 0.62), (0, -0.07, 0), (-10, 0, 0)),
                                               g_caixa((0.3, 0.02, 0.62), (0, 0.07, 0), (10, 0, 0))],
               "Mat_Plastico_Amarelo", col)
    pm_txt = texto("Corredor_Placa_Piso_Molhado_Texto", "CUIDADO:\nPISO\nMOLHADO", 0.055, "Mat_Texto_Preto", col,
                   (0, -0.13, 0.36), 0.26, ARQ_BUNGEE, rot=(-10, 0, 0))
    montar(pm, [pm_txt], 42.5, zs - 0.25, 0.0, "norte", -10)
    decal("refrigerante", col, 42.2, 17.9, (1.4, 1.0, 0.3))   # a poça do piso molhado

    # Papéis descascando nas paredes
    for i, (x, z, fr, h) in enumerate([(10.0, zn, "sul", 1.3), (31.0, zn, "sul", 1.7), (50.0, zn, "sul", 1.1),
                                       (3.5, zs, "norte", 1.5), (32.5, zs, "norte", 1.2), (53.0, zs, "norte", 1.8),
                                       (15.5, zs, "norte", 2.0)]):
        papel_descascando(f"Corredor_Papel_Descascando_{i + 1:02d}", col, x, z, h, fr, rng,
                          rng.uniform(0.4, 0.7), rng.uniform(0.5, 0.8))

    # Bebedouro, lixeira, quadro de avisos e caixas encostadas
    beb = caixas("Corredor_Bebedouro", [((0.4, 0.34, 0.9), (0, 0, 0))], "Mat_Inox", col)
    montar(beb, [caixas("Corredor_Bebedouro_Bacia", [((0.36, 0.3, 0.06), (0, -0.02, 0.9))], "Mat_Metal_Cinza", col),
                 colisao("Corredor_Bebedouro", (0.4, 0.34, 0.96), (0, 0, 0), col)], 12.0, zs - 0.19, 0.0, "norte")
    lix = malha("Corredor_Lixeira", [g_cil(0.17, 0.6, (0, 0, 0), seg=10)], "Mat_Metal_Escuro", col)
    montar(lix, [colisao("Corredor_Lixeira", (0.36, 0.36, 0.6), (0, 0, 0), col)], 24.0, zn + 0.2, 0.0, "sul")
    quadro = caixas("Corredor_Quadro_Avisos", [((1.2, 0.03, 0.8), (0, -0.015, 0))], "Mat_Cortica", col)
    papeis = malha("Corredor_Quadro_Avisos_Papeis", [g_caixa((0.22, 0.005, 0.3), (-0.4, -0.033, 0.4), (0, 5, 0)),
                                                     g_caixa((0.25, 0.005, 0.3), (0.3, -0.033, 0.12), (0, -8, 0)),
                                                     g_caixa((0.2, 0.005, 0.2), (0.0, -0.033, 0.5)),
                                                     g_caixa((0.2, 0.005, 0.28), (0.12, -0.04, -0.25), (0, 40, 0))],
                   "Mat_Papel_Branco", col)
    titulo = texto("Corredor_Quadro_Avisos_Texto", "AVISOS", 0.08, "Mat_Texto_Preto", col, (0, -0.04, 0.72))
    montar(quadro, [papeis, titulo], 40.0, zn, 1.1, "sul")
    pilha = caixas("Corredor_Caixas", [((0.6, 0.36, 0.45), (0, 0, 0)), ((0.5, 0.33, 0.35), (0.05, 0.01, 0.45), (0, 0, 6)),
                                       ((0.45, 0.35, 0.4), (0.6, 0, 0), (0, 0, -4))], "Mat_Papelao_Caixa", col)
    montar(pilha, [colisao("Corredor_Caixas", (1.1, 0.38, 0.8), (0.28, 0, 0), col)], 48.6, zs - 0.21, 0.0, "norte")
    cone = malha("Corredor_Cone", [g_cil(0.15, 0.55, (0, 0, 0), seg=8, raio_topo=0.03), g_caixa((0.34, 0.34, 0.03))],
                 "Mat_Plastico_Laranja", col)
    montar(cone, [], 52.5, zn + 0.22, 0.17, rot=(90, 0, 95))

    # Placas de direção em cima das portas
    for nome, txt, x, z, fr in (("Oficina", "OFICINA", 7, zn, "sul"), ("Salao_Oeste", "SALÃO", 20, zn, "sul"),
                                ("Salao_Leste", "SALÃO", 34, zn, "sul"), ("Cozinha", "COZINHA", 46, zn, "sul"),
                                ("Banheiros", "BANHEIROS", 56, zn, "sul"), ("Deposito", "DEPÓSITO", 7, zs, "norte"),
                                ("Fliperama_Oeste", "FLIPERAMA", 18, zs, "norte"),
                                ("Fliperama_Leste", "FLIPERAMA", 28, zs, "norte"),
                                ("Funcionarios", "SOMENTE\nFUNCIONÁRIOS", 45.5, zs, "norte"),
                                ("Gerencia", "GERÊNCIA", 57, zs, "norte")):
        alt = 0.34 if "\n" in txt else 0.24
        placa_texto(f"Corredor_Placa_{nome}", col, txt, 1.1, alt, x, z, 2.42, fr, "Mat_Plastico_Branco", "Mat_Texto_Preto",
                    incl=rng.choice((0, 0, 0, 4, -3)), tam=0.11 if "\n" in txt else 0.13)

    # Luminárias do teto: só uma fluorescente funciona (pisca); as outras estão apagadas.
    lum = []
    for x in (10.0, 20.0, 40.0, 50.0):
        lum += [g_caixa((1.25, 0.32, 0.07), comum.p2(x, 17.5, teto - 0.07))]
    malha("Corredor_Luminarias_Apagadas", lum, "Mat_Lampada_Apagada", col, origem="auto")
    fl = caixas("Corredor_Fluorescente_01", [((1.25, 0.32, 0.07), (0, 0, -0.07))], "Mat_Metal_Escuro", col)
    tubo = malha("Corredor_Fluorescente_01_Tubo", [g_cil(0.025, 1.15, (-0.575, sy * 0.07, -0.1), (0, 90, 0), 6)
                                                   for sy in (-1, 1)], "Mat_Lampada_Acesa", col)
    corr = malha("Corredor_Fluorescente_01_Correntes", g_tubo([(0.55, 0, 0), (0.55, 0, 0.12)], 0.006, 3)
                 + g_tubo([(-0.55, 0, 0), (-0.55, 0, 0.22)], 0.006, 3), "Mat_Metal_Cinza", col)
    # uma corrente arrebentou: a luminária pende torta
    montar(fl, [tubo, corr], 30.0, 17.5, teto - 0.45, rot=(0, -12, 0))
    luz("fluorescente", col, 30.0, 17.5, teto - 0.35, nn=1)
    som("zumbido", col, 30.0, 17.5, teto - 0.3)

    # Luzes de emergência nas pontas
    luz_emergencia_caixa("Corredor_Emergencia_01", col, 2.0, zn, 2.6, "sul")
    luz_emergencia_caixa("Corredor_Emergencia_02", col, x1 - 0.1, 17.5, 2.6, "oeste")

    # Placa do forro caída, encostada na parede, e fios saindo do forro
    malha("Corredor_Placa_Forro_Caida", [g_caixa((0.6, 0.6, 0.02), comum.p2(33.3, zs - 0.16, 0.0), (75, 0, 3))],
          "Mat_Teto_Escuro", col, origem="auto")
    malha("Corredor_Fios_Pendurados", g_tubo([comum.p2(33.0, 18.3, teto), comum.p2(33.1, 18.35, teto - 0.6),
                                              comum.p2(33.3, 18.4, teto - 0.8)], 0.008), "Mat_Fio", col, origem="auto")

    # Sujeira nos rodapés e cantos
    for x in (1.0, 9.5, 16.0, 25.0, 36.5, 43.0, 49.0, 58.5):
        decal("mancha_agua", col, x, zn + 0.3 if int(x) % 2 else zs - 0.3, (1.4, 0.7, 0.3))
    decal("pegadas", col, 30.0, 17.5, (12.0, 1.4, 0.3))
    decal("marca_mao", col, 44.0, zs, (0.5, 0.5, 0.3), 1.1, "sul")
    decal("rachadura", col, 22.0, zn, (1.0, 1.2, 0.3), 2.2, "norte")
    lixo("Corredor", col, [(x0 + 0.4, x1 - 0.4, zn + 0.05, zn + 0.45), (x0 + 0.4, x1 - 0.4, zs - 0.45, zs - 0.05)], 30, rng)
    teias_cantos("Corredor", col, "Corredor_Principal")
    teia("Corredor_Teia_05", col, 30.0, zn, teto, 1, 1, 0.35)


# ---------------------------------------------------------------------------
# CORREDOR DAS FESTAS
# ---------------------------------------------------------------------------

def corredor_festas(col, rng):
    x0, x1, z0, z1 = RET["Corredor_Festas"]
    teto = TETO["Corredor_Festas"]
    xo, xl = x0 + 0.1, x1 - 0.1          # faces das paredes oeste e leste

    # Foto da inauguração (ARTE-22) num quadro torto
    moldura_arte("Corredor_Festas_Foto_Inauguracao", col, "foto_inauguracao.jpg", 0.75, 0.5, xo, 30.0, 1.4, "leste", 7)

    # Placas das salas em cima das portas e cartazes ao lado
    for txt, zp, mat in (("ESTRELAS", 23, "Mat_Toalha_Azul_Noite"), ("PIRATAS", 32, "Mat_Toalha_Pirata"),
                         ("PRINCESAS", 40, "Mat_Plastico_Rosa")):
        placa_texto(f"Corredor_Festas_Placa_{txt.capitalize()}", col, txt, 1.2, 0.26, xl, zp, 2.35, "oeste", mat,
                    "Mat_Plastico_Amarelo", tam=0.14, incl=rng.choice((0, 3, -2)))
    for nome, arq, zp, incl in (("Estrelas", "cartaz_festa_estrelas", 20.6, -4), ("Piratas", "cartaz_festa_piratas", 34.6, 2),
                                ("Princesas", "cartaz_festa_princesas", 42.6, 0)):
        moldura_arte(f"Corredor_Festas_Cartaz_{nome}", col, arq, 0.5, 0.75, xl, zp, 1.2, "oeste", incl,
                     "Mat_Plastico_Amarelo", 0.03)
    moldura_arte("Corredor_Festas_Cartaz_Regras", col, "cartaz_regras_festa", 0.5, 0.75, xo, 35.2, 1.25, "leste", -3,
                 "Mat_Plastico_Azul", 0.03)
    moldura_arte("Corredor_Festas_Cartaz_Parabens", col, "cartaz_parabens", 0.6, 0.9, xo, 21.8, 1.2, "leste", 5,
                 "Mat_Plastico_Vermelho", 0.03)

    # Cadeira de criança encostada na parede (sem lugar)
    cad = cadeira("Corredor_Festas_Cadeira_Crianca", col, "Mat_Plastico_Verde", crianca=True)
    c = colisao("Corredor_Festas_Cadeira_Crianca", (0.32, 0.32, 0.6), (0, 0, 0), col)
    c.parent = cad
    por_cadeira(cad, xl - 0.24, 36.4, -75)

    # Cabideiro com um casaco de criança esquecido e um baú de fantasias
    cab = malha("Corredor_Festas_Cabideiro", [g_cil(0.17, 0.03, (0, 0, 0), seg=8), g_cil(0.02, 1.6, (0, 0, 0.03), seg=5)] +
                [g_cil(0.012, 0.18, (0, 0, 1.45), (60, 0, a), 4) for a in (0, 120, 240)], "Mat_Madeira_Escura", col)
    casaco = malha("Corredor_Festas_Casaco", [g_caixa((0.28, 0.08, 0.4), (0.0, -0.15, 1.08), (8, 0, 0))],
                   "Mat_Plastico_Vermelho", col)
    montar(cab, [casaco, colisao("Corredor_Festas_Cabideiro", (0.35, 0.35, 1.6), (0, 0, 0), col)], xo + 0.21, 19.8, 0.0, "leste")
    bau = caixas("Corredor_Festas_Bau", [((0.8, 0.38, 0.45), (0, 0, 0))], "Mat_Madeira_Velha", col)
    tampa = caixas("Corredor_Festas_Bau_Tampa", [((0.8, 0.04, 0.38), (0, 0.17, 0.45), (-20, 0, 0))], "Mat_Madeira_Velha", col)
    serp = malha("Corredor_Festas_Bau_Serpentinas", g_tubo([(-0.2, -0.05, 0.45), (-0.3, -0.25, 0.3), (-0.25, -0.35, 0.01),
                                                             (0.1, -0.45, 0.01)], 0.012)
                 + g_tubo([(0.15, 0.0, 0.45), (0.3, -0.2, 0.2), (0.45, -0.3, 0.01)], 0.012), "Mat_Plastico_Rosa", col)
    montar(bau, [tampa, serp, colisao("Corredor_Festas_Bau", (0.8, 0.38, 0.5), (0, 0, 0), col)], xo + 0.21, 37.0, 0.0,
           "leste")

    # Balões murchos, lixo, sujeira
    baloes_murchos("Corredor_Festas_Baloes_Murchos", col, [(32.6, 28.0), (34.3, 25.5), (33.0, 43.8), (34.5, 38.2)], rng)
    lixo("Corredor_Festas", col, [(xo + 0.1, xl - 0.1, z0 + 0.3, z1 - 0.3)], 22, rng)
    decal("confete", col, 33.5, 22.0, (2.4, 2.0, 0.3))
    decal("confete", col, 33.5, 41.5, (2.4, 2.0, 0.3))
    decal("giz_cera", col, xo, 28.0, (1.0, 0.6, 0.3), 0.55, "oeste")
    decal("mancha_agua", col, 33.5, z0 + 0.4, (2.6, 0.8, 0.3))
    decal("mancha_agua", col, 33.5, z1 - 0.4, (2.6, 0.8, 0.3))
    luz_emergencia_caixa("Corredor_Festas_Emergencia", col, 33.5, z0 + 0.1, 2.45, "sul")
    som("goteira", col, 33.5, 33.0, teto - 0.1)
    teias_cantos("Corredor_Festas", col, "Corredor_Festas")


# ---------------------------------------------------------------------------
# SALAS DE FESTA
# ---------------------------------------------------------------------------

def mesa_toalha_longa(nome, col, mat_toalha, x, z, entrada, rng, giro=0.0, mats_cadeira=("Mat_Plastico_Branco",),
                      n_esc=1):
    """
    Mesa comprida com toalha até o chão: o esconderijo 'mesa_toalha'.
    Colisão no tampo e nos 3 lados fechados; o lado da 'entrada' ("sul" ou "norte" ou "leste")
    fica aberto (a toalha desse lado está levantada e amassada).
    """
    L, P, H = 2.3, 1.15, 0.78
    pecas = [g_caixa((L, P, 0.03), (0, 0, H - 0.03))]
    lados = {"sul": ((L, 0.01), (0, -P / 2)), "norte": ((L, 0.01), (0, P / 2)),
             "oeste": ((0.01, P), (-L / 2, 0)), "leste": ((0.01, P), (L / 2, 0))}
    for lado, ((sx, sy), (bx, by)) in lados.items():
        if lado == entrada:
            # aba levantada: termina mais alto e dobrada para fora
            pecas.append(g_caixa((sx, sy, 0.42), (bx, by, H - 0.42),
                                 (12 if lado == "sul" else -12 if lado == "norte" else 0, 0, 0)))
        else:
            pecas.append(g_caixa((sx, sy, H - 0.01), (bx * 1.02, by * 1.02, 0.01)))
    toalha = malha(nome, pecas, mat_toalha, col)
    filhos = [colisao(nome + "_Tampo", (L, P, 0.06), (0, 0, H - 0.06), col)]
    for lado, ((sx, sy), (bx, by)) in lados.items():
        if lado != entrada:
            filhos.append(colisao(f"{nome}_{lado.capitalize()}", (max(sx, 0.06), max(sy, 0.06), H - 0.06), (bx, by, 0), col))
    pecas_itens = [g_cil(0.1, 0.008, (-0.8 + 0.4 * i, (-0.3 if i % 2 else 0.3), H), seg=10) for i in range(5)]
    pecas_itens += [g_cil(0.035, 0.1, (-0.6 + 0.5 * i, 0.05, H + (0.035 if i == 1 else 0)), ((90 if i == 1 else 0), 0, 30), 6)
                    for i in range(3)]
    filhos.append(malha(nome + "_Pratos_Copos", pecas_itens, "Mat_Papel_Branco", col))
    montar(toalha, filhos, x, z, 0.0, "sul", giro)
    # cadeiras pequenas em volta (fora da entrada)
    pos = [(-0.7, -0.95), (0.4, -1.0), (-0.5, 1.0), (0.6, 0.95), (-1.55, 0.1), (1.6, -0.1)]
    for i, (dx, dz) in enumerate(pos):
        if (entrada == "sul" and dz > 0 and abs(dx) < 1.2) or (entrada == "norte" and dz < 0 and abs(dx) < 1.2) or \
                (entrada == "leste" and dx > 1.2):
            continue
        cx, cz = x + dx + rng.uniform(-0.1, 0.1), z + dz + rng.uniform(-0.1, 0.1)
        corpo = cadeira(f"{nome}_Cadeira_{i + 1:02d}", col, mats_cadeira[i % len(mats_cadeira)], crianca=True)
        giro_c = giro_para(cx, cz, x, z) + rng.uniform(-30, 30)
        por_cadeira(corpo, cx, cz, giro_c, "costas" if i == n_esc else None)


def convites(nome, col, x, z, h, rng, mat="Mat_Papel_Branco"):
    pecas = [g_caixa((0.16, 0.11, 0.004), comum.p2(x + rng.uniform(-0.15, 0.15), z + rng.uniform(-0.1, 0.1), h + 0.004 * i),
                     (0, 0, rng.uniform(0, 360))) for i in range(6)]
    return malha(nome, pecas, mat, col, origem="auto")


def aparador(nome, col, x, z, frente, larg=1.2, mat="Mat_Madeira_Clara"):
    a = caixas(nome, [((larg, 0.4, 0.04), (0, 0, 0.8))] + [((0.04, 0.04, 0.8), (sx * (larg / 2 - 0.04), sy * 0.16, 0))
                                                            for sx in (-1, 1) for sy in (-1, 1)], mat, col)
    montar(a, [colisao(nome, (larg, 0.4, 0.84), (0, 0, 0), col)], x, z, 0.0, frente)
    return a


def festa_estrelas(col, rng):
    x0, x1, z0, z1 = RET["Festa_Estrelas"]
    teto = TETO["Festa_Estrelas"]
    ex, ez = [e[1:] for e in PONTOS["esconderijos"] if e[0] == "mesa_toalha"][0]
    mesa_toalha_longa("Estrelas_Mesa", col, "Mat_Toalha_Azul_Noite", ex, ez, "sul", rng,
                      mats_cadeira=("Mat_Plastico_Azul", "Mat_Plastico_Amarelo"))
    esconderijo("mesa_toalha", col, ex, ez, nn=1)
    # estrelinhas pintadas na toalha
    malha("Estrelas_Mesa_Estampa", [_aplicar(g_estrela(0.07, 0.03, 0.004),
                                             Matrix.Translation(comum.p2(ex - 1.0 + 0.4 * i, ez - 0.585, 0.25 + 0.2 * (i % 2))))
                                    for i in range(6)], "Mat_Estrela_Recortada", col, origem="auto")

    # Pista do código: pôster de aniversário com a data
    px, pz, _ = PONTOS["pista_aniversario"]
    moldura_arte("Estrelas_Poster_Pista", col, "pista_aniversario", 0.6, 0.9, px, z0 + 0.1, 1.2, "sul", 0,
                 "Mat_Plastico_Amarelo", 0.04)
    marcador("Pista", "aniversario", col, comum.p2(px, pz, 1.65), nn=0).name = "Pista__aniversario"

    # Estrelas fosforescentes no teto (a "ilha de luz" fraca da sala)
    pecas = []
    for i in range(26):
        sx, sz = rng.uniform(x0 + 0.4, x1 - 0.4), rng.uniform(z0 + 0.4, z1 - 0.4)
        r = rng.uniform(0.05, 0.12)
        pecas.append(g_estrela_plana(r, r * 0.45, comum.p2(sx, sz, teto - 0.01)))
    malha("Estrelas_Teto_Fosforescente", pecas, "Mat_Estrela_Fosforescente", col, origem="auto")
    # Lua de papelão na parede leste, móbile de planetas e foguete de papelão
    lua = malha("Estrelas_Lua_Papelao", [g_cil(0.45, 0.03, (0, 0, 0), (90, 0, 0), 14)], "Mat_Papel_Amarelado", col)
    sombra = malha("Estrelas_Lua_Papelao_Sombra", [g_cil(0.4, 0.03, (0.18, -0.01, 0.08), (90, 0, 0), 14)],
                   "Mat_Toalha_Azul_Noite", col)
    montar(lua, [sombra], x1 - 0.12, 25.6, 1.9, "oeste", incl=10)
    mob = []
    fios = []
    for i, (dx, dz, dh, r) in enumerate([(-0.35, 0, 0.7, 0.12), (0.3, 0.2, 0.55, 0.09), (0.0, -0.3, 0.9, 0.15),
                                         (0.25, -0.15, 1.05, 0.07)]):
        c = comum.p2(37.4 + dx, 25.6 + dz, teto - dh)
        mob.append(g_esf(r, c, 8, 5))
        fios += g_tubo([c + V((0, 0, r)), comum.p2(37.4 + dx, 25.6 + dz, teto - 0.35)], 0.003, 3)
    fios += g_tubo([comum.p2(37.0, 25.6, teto - 0.35), comum.p2(37.8, 25.6, teto - 0.35)], 0.006, 3)
    fios += g_tubo([comum.p2(37.4, 25.6, teto - 0.35), comum.p2(37.4, 25.6, teto)], 0.004, 3)
    mobile = malha("Estrelas_Mobile_Planetas", mob, "Mat_Plastico_Laranja", col, suave=True, origem="auto")
    fio_m = malha("Estrelas_Mobile_Fios", fios, "Mat_Fio", col, origem="auto")
    prender(fio_m, mobile)
    fog = malha("Estrelas_Foguete_Papelao", [g_cil(0.3, 1.6, (0, 0, 0.3), seg=10), g_cil(0.3, 0.5, (0, 0, 1.9), seg=10, raio_topo=0.0)],
                "Mat_Papelao_Pintado_Cinza", col)
    aletas = malha("Estrelas_Foguete_Aletas", [g_caixa((0.04, 0.4, 0.5), (0, 0.3, 0.0), (0, 0, a)) for a in (0, 120, 240)] +
                   [g_cil(0.1, 0.02, (0, -0.3, 1.4), (90, 0, 0), 10)], "Mat_Plastico_Vermelho", col)
    montar(fog, [aletas, colisao("Estrelas_Foguete", (0.8, 0.8, 2.4), (0, 0, 0), col)], x1 - 0.6, z0 + 0.6, 0.0, "sul", 20)

    # Aparador com os convites e o presente que nunca foi aberto
    aparador("Estrelas_Aparador", col, 37.5, z1 - 0.32, "norte")
    convites("Estrelas_Convites", col, 37.2, z1 - 0.32, 0.84, rng)
    p = presente("Estrelas_Presente_Fechado", col, (0.35, 0.3, 0.28), "Mat_Toalha_Azul_Noite", "Mat_Ouro")
    montar(p, [], 37.85, z1 - 0.33, 0.84, "norte", 12)
    etiqueta = texto("Estrelas_Presente_Etiqueta", "PARA: LUCAS", 0.03, "Mat_Texto_Preto", col, (0, 0, 0), 0.2, ARQ_GOCHI)
    montar(etiqueta, [], 37.85, z1 - 0.495, 1.02, "norte", 12)
    # baú de brinquedos e balões
    bau = caixas("Estrelas_Bau_Brinquedos", [((0.9, 0.5, 0.5), (0, 0, 0))], "Mat_Plastico_Azul", col)
    br = malha("Estrelas_Bau_Brinquedos_Itens", [g_esf(0.1, (-0.2, 0, 0.55), 8, 5), g_esf(0.08, (0.15, 0.05, 0.52), 8, 5),
                                                 g_caixa((0.15, 0.1, 0.1), (0.5, -0.4, 0), (0, 0, 25))], "Mat_Plastico_Amarelo", col)
    montar(bau, [br, colisao("Estrelas_Bau", (0.9, 0.5, 0.55), (0, 0, 0), col)], x0 + 0.6, 26.6, 0.0, "leste")
    baloes_murchos("Estrelas_Baloes_Murchos", col, [(36.0, 20.0), (42.6, 26.4), (38.2, 25.6), (41.2, 20.3)], rng)
    for i, (mat, alt) in enumerate((("Mat_Plastico_Azul", 0.7), ("Mat_Plastico_Amarelo", 0.45))):
        balao_meio_murcho(f"Estrelas_Balao_{i + 1:02d}", col, mat, x0 + 0.5, z0 + 0.5, 0.05, alt, rng)
    lixo("Estrelas", col, [(x0 + 0.4, x1 - 0.4, z0 + 0.4, z1 - 0.4)], 20, rng)
    decal("confete", col, ex, ez, (3.2, 2.2, 0.3))
    decal("giz_cera", col, 41.0, z0 + 0.1, (0.8, 0.6, 0.3), 0.5, "norte")
    decal("mancha_agua", col, x0 + 0.5, z1 - 0.5, (1.0, 1.0, 0.3))
    som("ventilacao", col, 40.0, 25.0, teto - 0.1)
    teias_cantos("Estrelas", col, "Festa_Estrelas", (0, 1, 3))


def festa_piratas(col, rng):
    x0, x1, z0, z1 = RET["Festa_Piratas"]
    teto = TETO["Festa_Piratas"]
    ex, ez = [e[1:] for e in PONTOS["esconderijos"] if e[0] == "mesa_toalha"][1]
    mesa_toalha_longa("Piratas_Mesa", col, "Mat_Toalha_Pirata", ex, ez, "leste", rng,
                      mats_cadeira=("Mat_Plastico_Preto", "Mat_Plastico_Vermelho"))
    esconderijo("mesa_toalha", col, ex, ez, nn=2)

    # Grade do duto (só a grade): na parede norte, baixa, na linha x do ponto DUTO_GRADES
    gx, gz = [(d[1], d[2]) for d in planta_v2.DUTO_GRADES if d[0] == "Festa_Piratas"][0]
    grade = caixas("Duto_Grade_Piratas", [((0.7, 0.03, 0.5), (0, -0.015, 0))] +
                   [((0.62, 0.02, 0.025), (0, -0.04, 0.06 + 0.055 * i)) for i in range(7)], "Mat_Metal_Escuro", col)
    montar(grade, [], gx, z0 + 0.1, 0.15, "sul")

    # Fachada de navio pirata de compensado na parede leste
    nav = caixas("Piratas_Navio_Fachada", [((3.2, 0.12, 1.3), (0, 0, 0)), ((3.4, 0.16, 0.12), (0, -0.02, 1.3))],
                 "Mat_Madeira_Velha", col)
    escot = malha("Piratas_Navio_Escotilhas", [g_cil(0.15, 0.02, (x, -0.07, 0.75), (90, 0, 0), 10) for x in (-1.0, 0.0, 1.0)],
                  "Mat_Metal_Escuro", col)
    mastro = malha("Piratas_Navio_Mastro", [g_cil(0.06, 1.4, (0.6, 0, 1.4), seg=8)], "Mat_Madeira_Escura", col)
    bandeira = malha("Piratas_Navio_Bandeira", [g_plano([(0.66, 0, 2.2), (1.36, -0.05, 2.25), (1.3, -0.05, 2.7), (0.66, 0, 2.75)])],
                     "Mat_Tecido_Preto", col)
    caveira = malha("Piratas_Navio_Bandeira_Desenho", [g_esf(0.09, (1.0, -0.06, 2.5), 6, 4, (1, 0.2, 1)),
                                                      g_caixa((0.28, 0.01, 0.03), (1.0, -0.06, 2.36), (0, 30, 0)),
                                                      g_caixa((0.28, 0.01, 0.03), (1.0, -0.06, 2.36), (0, -30, 0))],
                    "Mat_Plastico_Branco", col)
    montar(nav, [escot, mastro, bandeira, caveira, colisao("Piratas_Navio", (3.4, 0.25, 1.4), (0, 0, 0), col)],
           x1 - 0.22, 31.6, 0.0, "oeste", 0)
    # Timão na parede sul e mapa do tesouro
    tim = malha("Piratas_Timao", [g_cil(0.4, 0.04, (0, 0, 0), (90, 0, 0), 12)] +
                [g_cil(0.02, 0.95, (0, -0.03, 0), (0, a, 0), 4) for a in range(0, 180, 45)], "Mat_Madeira_Escura", col)
    assar_obj(tim)
    montar(tim, [], 40.6, z1 - 0.15, 1.6, "norte")
    moldura_arte("Piratas_Mapa_Tesouro", col, "mapa_tesouro", 0.9, 0.6, 37.6, z1 - 0.1, 1.35, "norte", -4,
                 "Mat_Madeira_Velha", 0.04)
    # Baú do tesouro com moedas, barris, rede de pesca no canto e papagaio de papelão
    bau = caixas("Piratas_Bau_Tesouro", [((0.8, 0.5, 0.45), (0, 0, 0))], "Mat_Madeira_Velha", col)
    tampa = caixas("Piratas_Bau_Tesouro_Tampa", [((0.8, 0.06, 0.45), (0, 0.24, 0.45), (-25, 0, 0))], "Mat_Madeira_Velha", col)
    moedas = malha("Piratas_Bau_Moedas", [g_esf(0.33, (0, 0, 0.4), 8, 4, (1.1, 0.65, 0.25))] +
                   [g_cil(0.03, 0.006, (-0.5 + 0.12 * i, -0.4 - 0.05 * (i % 3), 0.0), seg=6) for i in range(7)], "Mat_Ouro", col)
    montar(bau, [tampa, moedas, colisao("Piratas_Bau", (0.8, 0.5, 0.6), (0, 0, 0), col)], x1 - 0.7, z1 - 3.2, 0.0, "norte", -15)  # longe do ponto da pilha
    p = presente("Piratas_Presente_Fechado", col, (0.3, 0.3, 0.25), "Mat_Tecido_Preto", "Mat_Plastico_Vermelho")
    montar(p, [], x1 - 1.55, z1 - 0.4, 0.0, "norte", 25)
    for i, (bx, bz) in enumerate([(x0 + 0.55, z0 + 0.55), (x0 + 1.3, z0 + 0.45), (x0 + 0.5, z1 - 0.55)]):
        bar = malha(f"Piratas_Barril_{i + 1:02d}", [g_cil(0.3, 0.8, (0, 0, 0), seg=10)], "Mat_Madeira_Velha", col)
        aros = malha(f"Piratas_Barril_{i + 1:02d}_Aros", [g_cil(0.31, 0.04, (0, 0, h), seg=10) for h in (0.12, 0.64)],
                     "Mat_Metal_Escuro", col)
        montar(bar, [aros, colisao(f"Piratas_Barril_{i + 1:02d}", (0.6, 0.6, 0.8), (0, 0, 0), col)], bx, bz)
    rede = []
    for i in range(6):
        rede += g_tubo([comum.p2(x1 - 0.12, z0 + 0.12 + 0.25 * i, teto - 0.02),
                        comum.p2(x1 - 0.5 - 0.05 * i, z0 + 0.2 + 0.25 * i, teto - 0.9 - 0.08 * i)], 0.006, 3)
        rede += g_tubo([comum.p2(x1 - 0.12 - 0.25 * i, z0 + 0.12, teto - 0.02),
                        comum.p2(x1 - 0.25 - 0.3 * i, z0 + 0.5, teto - 0.8 - 0.06 * i)], 0.006, 3)
    malha("Piratas_Rede_Pesca", rede, "Mat_Corda", col, origem="auto")
    pap = malha("Piratas_Papagaio_Papelao", [g_esf(0.15, (0, 0, 0.2), 8, 5, (1, 0.15, 1.4)), g_esf(0.09, (0.02, 0, 0.46), 6, 4, (1, 0.2, 1))],
                "Mat_Plastico_Verde", col)
    bico = malha("Piratas_Papagaio_Bico", [g_cil(0.03, 0.08, (0.1, 0, 0.44), (0, 90, 0), 5, 0.0)], "Mat_Plastico_Amarelo", col)
    montar(pap, [bico], x0 + 0.12, 29.6, 1.7, "leste")
    convites("Piratas_Convites", col, ex - 0.4, ez - 0.1, 0.78, rng, "Mat_Papel_Amarelado")
    baloes_murchos("Piratas_Baloes_Murchos", col, [(36.6, 30.0), (42.0, 34.9), (38.0, 35.2)], rng)
    lixo("Piratas", col, [(x0 + 0.4, x1 - 0.5, z0 + 0.4, z1 - 0.4)], 18, rng)
    decal("refrigerante", col, 37.5, 33.6, (0.8, 0.7, 0.3))
    decal("marca_mao", col, x0, 34.8, (0.5, 0.5, 0.3), 0.9, "oeste")
    decal("mancha_agua", col, x1 - 0.5, z0 + 0.5, (1.0, 1.0, 0.3))
    som("rangido", col, 40.0, 32.0, 1.5)
    teias_cantos("Piratas", col, "Festa_Piratas", (0, 2, 3))


def assar_obj(obj):
    """Grava a rotação/posição na malha (para peças feitas com rotação própria)."""
    obj.data.transform(obj.matrix_basis)
    obj.matrix_basis = Matrix.Identity(4)
    return obj


def festa_princesas(col, rng):
    x0, x1, z0, z1 = RET["Festa_Princesas"]
    teto = TETO["Festa_Princesas"]
    ex, ez = [e[1:] for e in PONTOS["esconderijos"] if e[0] == "mesa_toalha"][2]
    mesa_toalha_longa("Princesas_Mesa", col, "Mat_Toalha_Rosa", ex, ez, "norte", rng,
                      mats_cadeira=("Mat_Plastico_Rosa", "Mat_Plastico_Lilas"))
    esconderijo("mesa_toalha", col, ex, ez, nn=3)
    malha("Princesas_Mesa_Coroa", [g_cil(0.09, 0.07, comum.p2(ex + 0.5, ez + 0.2, 0.78), seg=8, raio_topo=0.11)],
          "Mat_Ouro", col, origem="auto")

    # Castelo de papelão na parede sul
    cast = caixas("Princesas_Castelo", [((4.0, 0.12, 1.6), (0, 0, 0)), ((1.2, 0.12, 0.5), (0, 0, 1.6))] +
                  [((0.5, 0.12, 0.2), (x, 0, 1.6)) for x in (-1.75, -1.0)] +
                  [((0.5, 0.12, 0.2), (x, 0, 1.6)) for x in (1.0, 1.75)], "Mat_Papelao_Pintado_Cinza", col)
    torres = malha("Princesas_Castelo_Torres", [g_cil(0.3, 2.1, (sx * 2.0, -0.1, 0), seg=10) for sx in (-1, 1)],
                   "Mat_Papelao_Pintado_Cinza", col)
    tetos = malha("Princesas_Castelo_Telhados", [g_cil(0.36, 0.6, (sx * 2.0, -0.1, 2.1), seg=10, raio_topo=0.0) for sx in (-1, 1)],
                  "Mat_Plastico_Rosa", col)
    porta = malha("Princesas_Castelo_Porta", [g_caixa((0.9, 0.02, 1.1), (0, -0.07, 0)),
                                              g_cil(0.45, 0.02, (0, -0.07, 1.1), (90, 0, 0), 10)], "Mat_Madeira_Escura", col)
    montar(cast, [torres, tetos, porta, colisao("Princesas_Castelo", (4.7, 0.55, 2.1), (0, -0.12, 0), col)],
           39.5, z1 - 0.3, 0.0, "norte")

    # Trono, penteadeira com espelho e abajur de princesa (ilha de luz quente e fraca)
    trono = caixas("Princesas_Trono", [((0.7, 0.6, 0.45), (0, 0, 0)), ((0.7, 0.12, 1.1), (0, 0.25, 0.45))], "Mat_Plastico_Rosa", col)
    det = malha("Princesas_Trono_Detalhes", [g_esf(0.07, (sx * 0.33, 0.25, 1.6), 6, 4) for sx in (-1, 1)] +
                [g_caixa((0.08, 0.5, 0.25), (sx * 0.33, 0, 0.45)) for sx in (-1, 1)], "Mat_Ouro", col)
    montar(trono, [det, colisao("Princesas_Trono", (0.75, 0.65, 1.2), (0, 0, 0), col)], x0 + 0.6, z0 + 0.6, 0.0, "sul", -35)
    pent = caixas("Princesas_Penteadeira", [((1.0, 0.42, 0.75), (0, 0, 0))], "Mat_Plastico_Branco", col)
    esp = malha("Princesas_Penteadeira_Espelho", [g_cil(0.32, 0.02, (0, 0.12, 1.2), (90, 0, 0), 12)], "Mat_Espelho", col)
    mold = malha("Princesas_Penteadeira_Moldura", [g_cil(0.36, 0.02, (0, 0.14, 1.2), (90, 0, 0), 12)], "Mat_Ouro", col)
    pent_itens = malha("Princesas_Penteadeira_Itens", [g_cil(0.03, 0.1, (-0.35, -0.05, 0.75), seg=6),
                                                      g_cil(0.03, 0.14, (-0.25, 0.0, 0.75), seg=6),
                                                      g_caixa((0.15, 0.1, 0.05), (0.3, -0.05, 0.75), (0, 0, 20))],
                       "Mat_Plastico_Lilas", col)
    montar(pent, [esp, mold, pent_itens, colisao("Princesas_Penteadeira", (1.0, 0.42, 0.8), (0, 0, 0), col)],
           42.5, z0 + 0.33, 0.0, "sul", 0)
    criado = caixas("Princesas_Criado_Mudo", [((0.45, 0.4, 0.6), (0, 0, 0))], "Mat_Plastico_Branco", col)
    abajur = malha("Princesas_Abajur", [g_cil(0.06, 0.05, (0, 0, 0.6), seg=8), g_cil(0.015, 0.3, (0, 0, 0.65), seg=5)],
                   "Mat_Ouro", col)
    cupula = malha("Princesas_Abajur_Cupula", [g_cil(0.18, 0.22, (0, 0, 0.88), seg=10, raio_topo=0.1)], "Mat_Tule_Rosa", col)
    montar(criado, [abajur, cupula, colisao("Princesas_Criado_Mudo", (0.45, 0.4, 0.62), (0, 0, 0), col)],
           x1 - 0.35, z0 + 0.4, 0.0, "oeste", 0)
    luz("abajur", col, x1 - 0.35, z0 + 0.4, 0.98, nn=1)

    # Cortinas de tule na parede norte e guirlanda de flores
    pecas = cortina_vf((x0 + 1.6, z0 + 0.18), (x0 + 3.6, z0 + 0.18), 0.6, teto - 0.1, 7, 0.05)
    malha("Princesas_Tule", pecas, "Mat_Tule_Rosa", col, origem="auto")
    flores = [g_esf(0.06, comum.p2(x0 + 0.3 + 0.35 * i, z0 + 0.13, teto - 0.35 - 0.25 * math.sin(math.pi * i / 24)), 6, 4)
              for i in range(25) if i not in (17, 18)]
    malha("Princesas_Guirlanda", flores, "Mat_Plastico_Rosa", col, suave=True, origem="auto")
    malha("Princesas_Flores_Caidas", [g_esf(0.06, comum.p2(41.0 + 0.2 * i, z0 + 0.35 + 0.1 * i, 0.03), 6, 4) for i in range(3)],
          "Mat_Plastico_Rosa", col, suave=True, origem="auto")

    convites("Princesas_Convites", col, ex - 0.6, ez + 0.2, 0.78, rng, "Mat_Toalha_Rosa")
    p = presente("Princesas_Presente_Fechado", col, (0.32, 0.32, 0.3), "Mat_Plastico_Lilas", "Mat_Plastico_Rosa")
    montar(p, [], 36.2, 43.9, 0.0, "norte", -18)
    baloes_murchos("Princesas_Baloes_Murchos", col, [(36.3, 38.6), (42.8, 42.0), (41.0, 38.0), (37.5, 41.5)], rng)
    for i, (mat, alt) in enumerate((("Mat_Plastico_Rosa", 0.8), ("Mat_Plastico_Lilas", 0.5), ("Mat_Plastico_Rosa", 0.3))):
        balao_meio_murcho(f"Princesas_Balao_{i + 1:02d}", col, mat, x0 + 0.65, z0 + 0.95, 0.5, alt, rng)
    lixo("Princesas", col, [(x0 + 0.4, x1 - 0.4, z0 + 0.6, z1 - 0.8)], 18, rng)
    decal("confete", col, ex, ez, (3.0, 2.2, 0.3))
    decal("giz_cera", col, x0, 43.0, (0.9, 0.6, 0.3), 0.5, "oeste")
    decal("mancha_agua", col, x1 - 0.5, z1 - 0.5, (1.0, 1.0, 0.3))
    som("radio", col, x1 - 0.35, z0 + 0.4, 0.8)
    teias_cantos("Princesas", col, "Festa_Princesas", (1, 2, 3))


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------

def contar_triangulos():
    total = 0
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and not obj.name.endswith("-colonly"):
            total += sum(len(p.vertices) - 2 for p in obj.data.polygons)
    return total


def conferir_teto():
    """Nada pode passar do pé-direito do cômodo (olha a Collection de cada objeto)."""
    erros = []
    for nome in COMODOS_DO_GRUPO:
        col = bpy.data.collections[nome]
        for obj in col.objects:
            if obj.type != "MESH":
                continue
            topo = max((obj.matrix_world @ V(c)).z for c in obj.bound_box)
            if topo > TETO[nome] + 0.005:
                erros.append(f"{obj.name} passa do teto de {nome} ({topo:.2f} > {TETO[nome]})")
    return erros


def gerar():
    comum.limpar_cena()
    CONTADOR.clear()
    _FONTES_CARREGADAS.clear()
    for nome, (cor, em) in CORES_PUBLICO.items():
        comum.material(nome, cor, em)
    # vidro da bilheteria meio transparente (dá para ver o banquinho lá dentro)
    vidro = M("Mat_Vidro_Bilheteria")
    bsdf = next(n for n in vidro.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    bsdf.inputs["Alpha"].default_value = 0.35
    if hasattr(vidro, "surface_render_method"):
        vidro.surface_render_method = "BLENDED"

    cols = {nome: comum.colecao(nome) for nome in COMODOS_DO_GRUPO}
    salao(cols["Salao"], random.Random(11))
    recepcao(cols["Recepcao"], random.Random(22))
    corredor_principal(cols["Corredor_Principal"], random.Random(33))
    corredor_festas(cols["Corredor_Festas"], random.Random(44))
    festa_estrelas(cols["Festa_Estrelas"], random.Random(55))
    festa_piratas(cols["Festa_Piratas"], random.Random(66))
    festa_princesas(cols["Festa_Princesas"], random.Random(77))

    bpy.context.view_layer.update()
    problemas = comum.conferir_areas_livres_v2(permitidos=())
    problemas += conferir_teto()
    for p in problemas:
        print("PROBLEMA:", p)
    if problemas:
        raise RuntimeError(f"{len(problemas)} problema(s) de área livre/teto; veja acima.")
    print("[publico] áreas livres OK")

    tri = contar_triangulos()
    objs = list(bpy.context.scene.objects)
    print(f"[publico] objetos: {len(objs)} ({sum(1 for o in objs if o.type == 'EMPTY')} Empties, "
          f"{sum(1 for o in objs if o.name.endswith('-colonly'))} colisões)")
    print(f"[publico] triângulos: {tri}")
    if tri > 50000:
        raise RuntimeError("Passou de 50 mil triângulos; simplifique.")

    comum.salvar_blend(comum.PASTA_BLENDER / "v2_publico.blend")
    comum.exportar_glb(comum.PASTA_CENARIO / "v2_publico.glb")


if __name__ == "__main__":
    gerar()
