"""
comum.py — funções e materiais compartilhados por todos os scripts do Blender.

Por que existe: assim todos os scripts usam os MESMOS nomes de material, a mesma
escala (1 unidade = 1 metro) e a mesma conversão de coordenadas da planta.
Para mudar uma cor do jogo inteiro, basta mudar o valor em CORES aqui e rodar
o gerar_tudo.py de novo (ou mudar a Base Color do material direto no Blender).
"""

import json
import math
import sys
from datetime import datetime
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import materiais_v2  # noqa: E402  (mapa de texturas, compartilhado com o Godot)

# ---------------------------------------------------------------------------
# Caminhos do projeto
# ---------------------------------------------------------------------------
# Este arquivo fica em TurnoDaNoite/blender/scripts/, então a raiz está 2 níveis acima.
RAIZ = Path(__file__).resolve().parents[2]
PASTA_BLENDER = RAIZ / "blender"
PASTA_CENARIO = RAIZ / "godot" / "assets" / "cenario"
PASTA_PERSONAGENS = RAIZ / "godot" / "assets" / "personagens"
PASTA_IMAGENS = RAIZ / "docs" / "progresso" / "imagens"
PASTA_TEXTURAS = RAIZ / "godot" / "assets" / "texturas"

# ---------------------------------------------------------------------------
# Paleta de cores (hex sRGB, como aparece no seletor de cor do Blender)
# Um material por cor: para mudar a cor de algo, troque só a Base Color
# do material correspondente.
# Formato: "Nome_do_Material": ("#RRGGBB", forca_de_emissao)
# ---------------------------------------------------------------------------
CORES = {
    # --- Prédio ---
    "Mat_Piso_Quadriculado": ("#8a8680", 0.0),
    "Mat_Carpete_Fliperama": ("#2a2340", 0.0),
    "Mat_Papel_Parede_Festa": ("#7a3a3a", 0.0),
    "Mat_Chapa_Antiderrapante": ("#8a8d90", 0.0),
    "Mat_Piso_Preto": ("#1c1c1e", 0.0),
    "Mat_Piso_Branco": ("#cfcabb", 0.0),
    "Mat_Piso_Azulejo_Azul": ("#7f9fae", 0.0),
    "Mat_Piso_Concreto": ("#5a5752", 0.0),
    "Mat_Piso_Carpete_Roxo": ("#3b2a4d", 0.0),
    "Mat_Teto_Escuro": ("#1e1b1a", 0.0),
    "Mat_Parede_Creme": ("#b9ab8c", 0.0),
    "Mat_Parede_Concreto": ("#6e6a63", 0.0),
    "Mat_Parede_Externa": ("#3a3633", 0.0),
    "Mat_Faixa_Vermelha": ("#8e2b2b", 0.0),
    "Mat_Faixa_Azul_Petroleo": ("#2c5560", 0.0),
    "Mat_Faixa_Azulejo_Branco": ("#d8d6cf", 0.0),
    "Mat_Faixa_Roxa": ("#5a3474", 0.0),
    "Mat_Faixa_Azul_Claro": ("#7fb2c7", 0.0),
    "Mat_Faixa_Verde_Oliva": ("#555d33", 0.0),
    "Mat_Faixa_Amarela": ("#b58d2c", 0.0),
    "Mat_Faixa_Cinza": ("#4a4845", 0.0),
    "Mat_Palco_Madeira": ("#5b3a22", 0.0),
    "Mat_Batente_Madeira": ("#4a3020", 0.0),
    "Mat_Porta_Metal": ("#5d6266", 0.0),
    # --- Uso geral (móveis, props) ---
    "Mat_Madeira_Clara": ("#9a7048", 0.0),
    "Mat_Madeira_Escura": ("#4b3221", 0.0),
    "Mat_Metal_Cinza": ("#8a8d90", 0.0),
    "Mat_Metal_Escuro": ("#3b3d40", 0.0),
    "Mat_Plastico_Preto": ("#161616", 0.0),
    "Mat_Plastico_Branco": ("#d9d6cc", 0.0),
    "Mat_Plastico_Vermelho": ("#a3262a", 0.0),
    "Mat_Plastico_Amarelo": ("#d1a326", 0.0),
    "Mat_Plastico_Azul": ("#2d5fa3", 0.0),
    "Mat_Plastico_Verde": ("#3d8a46", 0.0),
    "Mat_Toalha_Xadrez_Vermelha": ("#b13a3a", 0.0),
    "Mat_Toalha_Branca": ("#e0dccf", 0.0),
    "Mat_Cortina_Vermelha": ("#6e1418", 0.0),
    "Mat_Papelao": ("#8b6a43", 0.0),
    "Mat_Espelho": ("#cfe0e6", 0.0),
    "Mat_Louca_Branca": ("#e6e4dc", 0.0),
    # --- Emissivos (brilham fraco no escuro) ---
    "Mat_Tela_Monitor": ("#1d3b2a", 0.6),
    "Mat_Tela_Arcade_Azul": ("#1f4f9e", 1.2),
    "Mat_Tela_Arcade_Rosa": ("#9e1f6b", 1.2),
    "Mat_Tela_Arcade_Verde": ("#1f9e4a", 1.2),
    "Mat_Lampada_Apagada": ("#d9d2b8", 0.0),
    "Mat_Luz_Emergencia": ("#ff2a1a", 2.0),
    "Mat_Led_Disjuntor": ("#ff3b1f", 1.5),
    # --- Disjuntores ---
    "Mat_Disjuntor_Caixa": ("#6b7071", 0.0),
    "Mat_Disjuntor_Alavanca": ("#c22d22", 0.0),
    # --- Genéricos da V2 (cor de prévia; a cor real vem da tinta em materiais_v2.py) ---
    "Mat_Madeira_Velha": ("#8f7258", 0.0),
    "Mat_Madeira_Envernizada": ("#7a5230", 0.0),
    "Mat_Inox": ("#c8cacc", 0.0),
    "Mat_Metal_Enferrujado": ("#7a4a30", 0.0),
    "Mat_Metal_Pintado_Verde": ("#6f8f6a", 0.0),
    "Mat_Metal_Pintado_Azul": ("#5a76a0", 0.0),
    "Mat_Metal_Pintado_Amarelo": ("#d8b04a", 0.0),
    "Mat_Papelao_Caixa": ("#b4895a", 0.0),
    "Mat_Lencol_Branco": ("#e8e4da", 0.0),
    "Mat_Tecido_Figurino_Vermelho": ("#b03a3a", 0.0),
    "Mat_Tecido_Figurino_Azul": ("#3a5fb0", 0.0),
    "Mat_Tecido_Figurino_Amarelo": ("#d8b84a", 0.0),
    "Mat_Azulejo_Cozinha": ("#f2efe6", 0.0),
    "Mat_Concreto_Sujo": ("#8a857c", 0.0),
    "Mat_Tijolo_Aparente": ("#9a4a38", 0.0),
    "Mat_Plastico_Rosa": ("#e07aa8", 0.0),
    "Mat_Plastico_Lilas": ("#b08ae0", 0.0),
    "Mat_Plastico_Laranja": ("#e8873a", 0.0),
    "Mat_Carpete_Fliperama_Gasto": ("#2a2340", 0.0),
    "Mat_Vidro_Aramado": ("#9fb4b8", 0.0),
    "Mat_Faixa_Rosa": ("#d88aa8", 0.0),
    "Mat_Faixa_Marrom": ("#8a5a3a", 0.0),
    "Mat_Porta_Aco": ("#5d6266", 0.0),
    "Mat_Botao_Vermelho": ("#d8302a", 1.5),
    "Mat_Luz_Porta_Verde": ("#3fe060", 2.0),
    "Mat_Neon_Rosa": ("#ff3fa0", 4.0),
    "Mat_Neon_Ciano": ("#3fe8ff", 4.0),
    "Mat_Neon_Amarelo": ("#ffd23f", 4.0),
    "Mat_Lampada_Acesa": ("#fff1c8", 3.0),
    "Mat_Tela_Arcade_Desligada": ("#0c1410", 0.2),
    # --- Personagens (placeholders) ---
    "Mat_Tito_Marrom": ("#6b4226", 0.0),
    "Mat_Tito_Bege": ("#c9a77c", 0.0),
    "Mat_Tito_Gravata": ("#d9a520", 0.0),   # amarelo-mostarda
    "Mat_Tito_Chapeu": ("#e8e4da", 0.0),    # chapéu de pizzaiolo branco
    "Mat_Tito_Focinho": ("#2a1a12", 0.0),
    "Mat_Olho_Tito": ("#ffd27a", 3.0),
    "Mat_Pipoca_Lilas": ("#9b7fc4", 0.0),
    "Mat_Pipoca_Branco": ("#ece6f2", 0.0),
    "Mat_Pipoca_Laco": ("#d8457f", 0.0),
    "Mat_Pipoca_Bochecha": ("#e98fb2", 0.0),
    "Mat_Olho_Pipoca": ("#9ff0ff", 3.0),
}


def hex_para_linear(hex_cor):
    """Converte '#RRGGBB' (sRGB) para cor linear RGBA, que é o que o Blender usa por dentro."""
    hex_cor = hex_cor.lstrip("#")
    rgb = [int(hex_cor[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]

    def s2l(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return (s2l(rgb[0]), s2l(rgb[1]), s2l(rgb[2]), 1.0)


def material(nome, cor_hex=None, emissao=None):
    """
    Devolve o material com esse nome, criando se não existir.
    Se o nome estiver em CORES, usa a cor da paleta.
    """
    mat = bpy.data.materials.get(nome)
    if mat is not None:
        return mat
    if cor_hex is None:
        if nome not in CORES:
            raise KeyError(f"Material '{nome}' não está em CORES; passe cor_hex.")
        cor_hex, emissao_padrao = CORES[nome]
        if emissao is None:
            emissao = emissao_padrao
    emissao = emissao or 0.0
    cor = hex_para_linear(cor_hex)

    mat = bpy.data.materials.new(nome)
    # diffuse_color é a cor usada nas prévias (Workbench); a Base Color vai para o jogo.
    mat.diffuse_color = cor
    if mat.node_tree is None:
        mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = cor
    bsdf.inputs["Roughness"].default_value = 0.8
    if emissao > 0:
        bsdf.inputs["Emission Color"].default_value = cor
        bsdf.inputs["Emission Strength"].default_value = emissao
    _ligar_texturas(mat, bsdf)
    return mat


def _ligar_texturas(mat, bsdf):
    """
    Se o material está em materiais_v2.TEXTURIZADOS, liga as imagens:
    cor x tinta -> Base Color, normal -> Normal, aspereza -> Roughness.
    A tinta multiplica a textura: trocar a tinta muda a cor sem perder o desenho.
    """
    dados = materiais_v2.TEXTURIZADOS.get(mat.name)
    if not dados:
        return
    pasta, _metros, tinta_hex = dados
    base = PASTA_TEXTURAS / pasta / pasta
    cor_img = Path(str(base) + "_cor.jpg")
    if not cor_img.exists():
        print(f"[comum] AVISO: textura {cor_img.name} não encontrada; {mat.name} fica com cor lisa")
        return
    nos, ligacoes = mat.node_tree.nodes, mat.node_tree.links
    tinta = hex_para_linear(tinta_hex)
    mat.diffuse_color = tinta  # cor usada nas prévias sem textura

    def imagem(caminho, nao_cor, x):
        no = nos.new("ShaderNodeTexImage")
        no.image = bpy.data.images.load(str(caminho), check_existing=True)
        if nao_cor:
            no.image.colorspace_settings.name = "Non-Color"
        no.location = (x, 0)
        return no

    cor = imagem(cor_img, False, -700)
    mistura = nos.new("ShaderNodeMix")
    mistura.data_type = "RGBA"
    mistura.blend_type = "MULTIPLY"
    mistura.inputs["Factor"].default_value = 1.0
    mistura.inputs["B"].default_value = tinta
    ligacoes.new(cor.outputs["Color"], mistura.inputs["A"])
    ligacoes.new(mistura.outputs["Result"], bsdf.inputs["Base Color"])
    normal_img = Path(str(base) + "_normal.jpg")
    if normal_img.exists():
        mapa = nos.new("ShaderNodeNormalMap")
        ligacoes.new(imagem(normal_img, True, -700).outputs["Color"], mapa.inputs["Color"])
        ligacoes.new(mapa.outputs["Normal"], bsdf.inputs["Normal"])
    asp_img = Path(str(base) + "_aspereza.jpg")
    if asp_img.exists():
        ligacoes.new(imagem(asp_img, True, -700).outputs["Color"], bsdf.inputs["Roughness"])


def aplicar_uv_mundo(objetos=None):
    """
    Cria coordenadas UV em ESCALA DE MUNDO REAL (projeção em caixa): cada face usa os
    dois eixos do mundo mais 'deitados' nela, dividido pelo tamanho de 1 repetição da
    textura do material. Assim nada fica esticado, e uma parede de 4 m mostra 2 repetições
    de uma textura de 2 m, por exemplo.
    """
    for obj in objetos if objetos is not None else bpy.context.scene.objects:
        if obj.type != "MESH" or obj.name.endswith("-colonly"):
            continue
        # Telas e planos de arte precisam da imagem inteira (UV de 0 a 1): não mexemos neles.
        if obj.name.startswith("Arte__") or obj.name.endswith("_Tela") or obj.name == "Monitor_Tela" or obj.get("uv_propria"):
            continue
        malha = obj.data
        if not malha.uv_layers:
            malha.uv_layers.new(name="UVMap")
        uv = malha.uv_layers.active.data
        m = obj.matrix_world
        rot = m.to_3x3().normalized()
        nomes = [s.name if s else "" for s in malha.materials]
        for poligono in malha.polygons:
            nome_mat = nomes[poligono.material_index] if poligono.material_index < len(nomes) else ""
            metros = materiais_v2.metros_por_repeticao(nome_mat)
            n = rot @ poligono.normal
            eixo = max(range(3), key=lambda i: abs(n[i]))
            for li in poligono.loop_indices:
                co = m @ malha.vertices[malha.loops[li].vertex_index].co
                if eixo == 2:   # chão/teto: X e Y do mundo
                    u, v = co.x, co.y
                elif eixo == 0: # parede virada para X: Y e Z
                    u, v = co.y, co.z
                else:           # parede virada para Y: X e Z
                    u, v = co.x, co.z
                uv[li].uv = (u / metros, v / metros)


# ---------------------------------------------------------------------------
# Coordenadas
# ---------------------------------------------------------------------------
# A planta do GDD usa (x, z): x de 0 a 40 (oeste -> leste), z de 0 a 30 (norte -> sul).
# No Blender: X = x - 20 e Y = 15 - z (o Y do Blender aponta para o norte).
# Depois de exportar, o Godot vê: X = x - 20, Z = z - 15.

def p(x, z, altura=0.0):
    """Converte um ponto da planta (x, z) + altura para coordenadas do Blender."""
    return Vector((x - 20.0, 15.0 - z, altura))


def p2(x, z, altura=0.0):
    """V2 (mapa 60 x 45 m): planta (x, z) + altura -> Blender. Godot: X = x - 30, Z = z - 22,5."""
    return Vector((x - 30.0, 22.5 - z, altura))


def bbox_planta(obj):
    """Retângulo (x0, x1, z0, z1) que o objeto ocupa na planta da V2 (pela caixa envolvente)."""
    cantos = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    xs = [c.x + 30.0 for c in cantos]
    zs = [22.5 - c.y for c in cantos]
    return min(xs), max(xs), min(zs), max(zs)


def conferir_areas_livres_v2(permitidos=()):
    """
    Confere se algum objeto de colisão (-colonly) invade:
      - os vãos de porta (1,2 m de cada lado do vão);
      - os pontos de jogo da planta_v2 (início, palco, patrulha, pilhas, fichas): raio de 0,8 m.
    'permitidos' = nomes (ou começos de nome) de objetos que podem ficar num ponto de propósito
    (ex.: a máquina de garra no ponto "maquina_garra"). Devolve a lista de problemas.
    """
    import planta_v2
    problemas = []
    circulos = []
    P = planta_v2.PONTOS
    for chave in ("spawn_jogador", "palco_tito", "palco_pipoca"):
        circulos.append((chave, P[chave][0], P[chave][1], 0.8))
    for nome_lista in ("patrulha", "pilhas", "fichas"):
        for i, (x, z) in enumerate(P[nome_lista]):
            circulos.append((f"{nome_lista}_{i + 1}", x, z, 0.8))
    for eixo, fixo, centro, larg, tipo, _ in planta_v2.PORTAS:
        if tipo == "catraca":
            continue
        meia = larg / 2
        if eixo == "z":
            circulos.append((f"porta_z{fixo}_x{centro}", centro, fixo, max(meia, 0.7) + 0.5))
        else:
            circulos.append((f"porta_x{fixo}_z{centro}", fixo, centro, max(meia, 0.7) + 0.5))
    for obj in bpy.context.scene.objects:
        if not obj.name.endswith("-colonly") or any(obj.name.startswith(p) for p in permitidos):
            continue
        x0, x1, z0, z1 = bbox_planta(obj)
        for nome, cx, cz, r in circulos:
            # distância do centro do círculo até o retângulo
            dx = max(x0 - cx, 0.0, cx - x1)
            dz = max(z0 - cz, 0.0, cz - z1)
            if dx * dx + dz * dz < r * r:
                problemas.append(f"{obj.name} invade {nome}")
    return problemas


# Rotações (em graus, em torno do Z do Blender) para um objeto cuja FRENTE é -Y
ROT_OLHA_SUL = 0.0      # frente para +z da planta (Blender -Y)
ROT_OLHA_LESTE = 90.0   # frente para +x da planta
ROT_OLHA_NORTE = 180.0  # frente para -z da planta (Blender +Y)
ROT_OLHA_OESTE = -90.0  # frente para -x da planta


# ---------------------------------------------------------------------------
# Cena e coleções
# ---------------------------------------------------------------------------

def limpar_cena():
    """Começa de uma cena vazia, sem o cubo/câmera/luz padrão."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    cena = bpy.context.scene
    cena.unit_settings.system = "METRIC"
    cena.unit_settings.scale_length = 1.0  # 1 unidade = 1 metro


def colecao(nome, pai=None):
    """Devolve (ou cria) uma Collection. Usamos uma por cômodo para organizar."""
    col = bpy.data.collections.get(nome)
    if col is None:
        col = bpy.data.collections.new(nome)
        (pai or bpy.context.scene.collection).children.link(col)
    return col


def _novo_objeto(nome, malha, colecao_destino):
    obj = bpy.data.objects.new(nome, malha)
    (colecao_destino or bpy.context.scene.collection).objects.link(obj)
    return obj


def _mover_para(obj, base, rot_z_graus=0.0, rot=None):
    obj.location = Vector(base)
    if rot is not None:
        obj.rotation_euler = [math.radians(a) for a in rot]
    else:
        obj.rotation_euler = (0.0, 0.0, math.radians(rot_z_graus))


# ---------------------------------------------------------------------------
# Primitivas (todas com origem num ponto lógico e escala 1)
# ---------------------------------------------------------------------------

def caixa(nome, tamanho, base, mat=None, col=None, rot_z=0.0, origem="base"):
    """
    Cria uma caixa. tamanho = (largura X, profundidade Y, altura Z) em metros.
    origem="base": a origem fica no centro da face de baixo (bom para móveis).
    origem="centro": a origem fica no centro da caixa.
    """
    sx, sy, sz = tamanho
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    desloc_z = 0.5 if origem == "base" else 0.0
    for v in bm.verts:
        v.co = Vector((v.co.x * sx, v.co.y * sy, (v.co.z + desloc_z) * sz))
    malha = bpy.data.meshes.new(nome)
    bm.to_mesh(malha)
    bm.free()
    obj = _novo_objeto(nome, malha, col)
    if mat is not None:
        obj.data.materials.append(material(mat) if isinstance(mat, str) else mat)
    _mover_para(obj, base, rot_z)
    return obj


def cilindro(nome, raio, altura, base, mat=None, col=None, vertices=12, rot=None, rot_z=0.0, raio_topo=None):
    """Cilindro (ou tronco de cone, se raio_topo for diferente) com origem no centro da base."""
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=False, segments=vertices,
        radius1=raio, radius2=raio if raio_topo is None else raio_topo, depth=altura,
    )
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, altura / 2))
    malha = bpy.data.meshes.new(nome)
    bm.to_mesh(malha)
    bm.free()
    obj = _novo_objeto(nome, malha, col)
    if mat is not None:
        obj.data.materials.append(material(mat) if isinstance(mat, str) else mat)
    _mover_para(obj, base, rot_z, rot)
    return obj


def esfera(nome, raio, centro, mat=None, col=None, segmentos=12, aneis=8, escala=(1, 1, 1), rot=None):
    """Esfera low poly com origem no centro. 'escala' deforma a malha (a escala do objeto fica 1)."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segmentos, v_segments=aneis, radius=raio)
    for v in bm.verts:
        v.co = Vector((v.co.x * escala[0], v.co.y * escala[1], v.co.z * escala[2]))
    malha = bpy.data.meshes.new(nome)
    bm.to_mesh(malha)
    bm.free()
    for poligono in malha.polygons:
        poligono.use_smooth = True
    obj = _novo_objeto(nome, malha, col)
    if mat is not None:
        obj.data.materials.append(material(mat) if isinstance(mat, str) else mat)
    _mover_para(obj, centro, 0.0, rot)
    return obj


def malha_de_pontos(nome, vertices, faces, base=(0, 0, 0), mat=None, col=None, rot_z=0.0):
    """Cria um objeto a partir de uma lista de vértices e faces (para formas especiais)."""
    malha = bpy.data.meshes.new(nome)
    malha.from_pydata([Vector(v) for v in vertices], [], faces)
    malha.update()
    obj = _novo_objeto(nome, malha, col)
    if mat is not None:
        obj.data.materials.append(material(mat) if isinstance(mat, str) else mat)
    _mover_para(obj, base, rot_z)
    return obj


def parentar(filho, pai):
    """Faz 'filho' ser filho de 'pai' sem mudar a posição dele no mundo."""
    # Atualiza as matrizes antes de ler: logo depois de mudar location/rotation, matrix_world
    # ainda está velha e o filho perdia a própria posição (a porta da cabine girava em volta
    # do centro da cabine em vez da dobradiça).
    bpy.context.view_layer.update()
    mundo = filho.matrix_world.copy()
    filho.parent = pai
    filho.matrix_parent_inverse = pai.matrix_world.inverted()
    filho.matrix_world = mundo


def plano_arte(arquivo, largura, altura, base, col=None, rot_z=0.0, mat="Mat_Papel_Branco"):
    """
    Plano que recebe uma arte (pôster, letreiro, painel...). Nome: "Arte__<arquivo sem extensão>".
    A frente é -Y (como todo objeto do projeto) e a UV cobre a imagem inteira (0 a 1).
    No Godot, o script ArteExterna troca o material pela imagem do Gemini (com envelhecimento)
    ou por uma versão feita por código, se a imagem não existir.
    'base' = centro da borda de BAIXO do plano (fica em pé, encostado na parede).
    """
    meia = largura / 2
    verts = [(-meia, 0, 0), (meia, 0, 0), (meia, 0, altura), (-meia, 0, altura)]
    obj = malha_de_pontos(f"Arte__{Path(arquivo).stem}", verts, [(0, 1, 2, 3)], base, mat, col, rot_z)
    uv = obj.data.uv_layers.new(name="UVMap").data
    for i, (u, v) in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv[i].uv = (u, v)
    obj["uv_propria"] = True
    return obj


def colisao_caixa(nome_base, tamanho, base, col=None, rot_z=0.0):
    """
    Cria uma caixa SÓ de colisão para o Godot.
    O sufixo '-colonly' faz o Godot criar um StaticBody3D invisível no lugar da malha.
    No Blender ela aparece como arame e não sai nos renders.
    """
    obj = caixa(f"{nome_base}_Colisao-colonly", tamanho, base, None, col, rot_z)
    obj.display_type = "WIRE"
    obj.hide_render = True
    return obj


# ---------------------------------------------------------------------------
# Salvar e exportar
# ---------------------------------------------------------------------------

def salvar_blend(caminho):
    aplicar_uv_mundo()  # toda malha sai com UV em escala real antes de salvar
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(caminho), compress=False)
    print(f"[comum] salvo: {caminho}")


def exportar_glb(caminho, objetos=None):
    """
    Exporta para .glb (glTF binário), que o Godot importa sozinho.
    objetos=None exporta todos os objetos da cena.
    As Collections viram nós no Godot (ex.: Salao/Mesa_01), para ficar organizado.
    """
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    for obj in bpy.context.scene.objects:
        obj.select_set(False)
    alvo = objetos if objetos is not None else list(bpy.context.scene.objects)
    for obj in alvo:
        obj.hide_set(False)
        obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(caminho),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_cameras=False,
        export_lights=False,
        # Propriedades personalizadas (ex.: obj["texto_3d"]) viram metadado "extras" no Godot:
        # é assim que os validadores de dev/ sabem o que está escrito em cada texto 3D.
        export_extras=True,
        export_animations=True,
        export_hierarchy_full_collections=True,
        # As imagens NÃO vão dentro do .glb: no Godot cada material é um arquivo .tres
        # (godot/assets/materiais/) que aponta para as texturas de godot/assets/texturas/.
        export_image_format="NONE",
    )
    print(f"[comum] exportado: {caminho}")


def registrar_imagem(caminho_png, legenda, fase):
    """
    Escreve, ao lado da imagem, um .json com legenda/horário/fase.
    A página docs/progresso lê esses arquivos (via gerar_dados.py) para montar a galeria.
    """
    caminho_png = Path(caminho_png)
    dados = {
        "arquivo": caminho_png.name,
        "legenda": legenda,
        "fase": fase,
        "horario": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    caminho_png.with_suffix(".json").write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def argumentos_do_script():
    """Argumentos passados depois de '--' na linha de comando do Blender."""
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
