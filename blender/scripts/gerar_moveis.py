"""
gerar_moveis.py — cria todos os móveis, props e os 4 disjuntores da Pizzaria do Tito.

O que sai daqui:
  - blender/moveis.blend                    (tudo, organizado em Collections por cômodo)
  - godot/assets/cenario/moveis.glb         (móveis e props, sem os disjuntores)
  - godot/assets/cenario/disjuntores.glb    (só os 4 disjuntores, com a alavanca separada)

Como rodar sozinho (a partir da pasta TurnoDaNoite):
  blender --background --python blender/scripts/gerar_moveis.py

Ideia geral: cada móvel é montado "em casa" (na origem, de frente para -Y)
e depois levado para o lugar dele na planta com montar(). As peças são filhas
da peça principal; assim, no Blender, mover a peça principal (tecla G) leva
o móvel inteiro junto, inclusive a caixa de colisão.
"""

import math
import pathlib
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import comum  # noqa: E402

V = Vector

# ---------------------------------------------------------------------------
# Cores que só os móveis usam (as gerais ficam em comum.CORES)
# Formato igual ao do comum: "Nome": ("#RRGGBB", emissao)
# ---------------------------------------------------------------------------
CORES_MOVEIS = {
    "Mat_Tijolo_Vermelho": ("#8a3b26", 0.0),
    "Mat_Cortica": ("#a5794a", 0.0),
    "Mat_Papel_Branco": ("#e8e4d6", 0.0),
    "Mat_Papel_Amarelo": ("#e3cf6a", 0.0),
    "Mat_Texto_Preto": ("#141414", 0.0),
    "Mat_Texto_Branco": ("#f0ede4", 0.0),
    "Mat_Massa_Pizza": ("#e0c08a", 0.0),
    "Mat_Brasa": ("#ff6a1a", 0.4),
    "Mat_Planta_Verde": ("#2f5e2c", 0.0),
    "Mat_Vaso_Terracota": ("#9c5a3a", 0.0),
    "Mat_Vidro_Escuro": ("#1b2a30", 0.0),
    "Mat_Letreiro_Amarelo": ("#e8c341", 0.6),
    "Mat_Letreiro_Rosa": ("#e0458f", 0.8),
    "Mat_Poster_Amarelo": ("#d9b23a", 0.0),
    "Mat_Poster_Lilas": ("#9078b8", 0.0),
    "Mat_Poster_Vermelho": ("#b8423a", 0.0),
    "Mat_Poster_Azul": ("#3a6fb8", 0.0),
    "Mat_Poster_Verde": ("#4a9a52", 0.0),
    "Mat_Poster_Laranja": ("#d9822f", 0.0),
    "Mat_Poster_Cinza": ("#8f8a80", 0.0),
    "Mat_Poster_Creme": ("#e8dcbc", 0.0),
}

COMODOS = [
    "Sala_Seguranca", "Salao", "Cozinha", "Deposito", "Corredor_Principal",
    "Fliperama", "Banheiros", "Recepcao", "Corredor_Fundos",
]

# Direção (na planta) para onde a FRENTE de cada orientação aponta
FRENTES = {
    "sul": (comum.ROT_OLHA_SUL, (0.0, 1.0)),
    "leste": (comum.ROT_OLHA_LESTE, (1.0, 0.0)),
    "norte": (comum.ROT_OLHA_NORTE, (0.0, -1.0)),
    "oeste": (comum.ROT_OLHA_OESTE, (-1.0, 0.0)),
}


# ---------------------------------------------------------------------------
# Ajudantes
# ---------------------------------------------------------------------------

def M(nome):
    """Material pelo nome (os da paleta do comum ou os de CORES_MOVEIS, já criados)."""
    return comum.material(nome)


def assar(obj):
    """Grava a posição/rotação dentro da malha e zera o objeto: a origem vira (0,0,0)."""
    obj.data.transform(obj.matrix_basis)
    obj.matrix_basis = Matrix.Identity(4)
    return obj


def caixas(nome, itens, mat, col):
    """
    Várias caixas num objeto só (ex.: as 4 pernas de uma cadeira).
    itens = [((largura, profundidade, altura), (x, y, z_da_base)), ...]
    A origem do objeto fica em (0,0,0).
    """
    bm = bmesh.new()
    for (sx, sy, sz), (bx, by, bz) in itens:
        r = bmesh.ops.create_cube(bm, size=1.0)
        for v in r["verts"]:
            v.co = V((v.co.x * sx + bx, v.co.y * sy + by, (v.co.z + 0.5) * sz + bz))
    malha = bpy.data.meshes.new(nome)
    bm.to_mesh(malha)
    bm.free()
    obj = bpy.data.objects.new(nome, malha)
    col.objects.link(obj)
    obj.data.materials.append(M(mat))
    return obj


def cilindros(nome, itens, mat, col, vertices=10):
    """Vários cilindros em pé num objeto só. itens = [(raio, altura, (x, y, z_base)), ...]"""
    bm = bmesh.new()
    for raio, altura, (bx, by, bz) in itens:
        r = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=vertices,
                                  radius1=raio, radius2=raio, depth=altura)
        bmesh.ops.translate(bm, verts=r["verts"], vec=(bx, by, bz + altura / 2))
    malha = bpy.data.meshes.new(nome)
    bm.to_mesh(malha)
    bm.free()
    obj = bpy.data.objects.new(nome, malha)
    col.objects.link(obj)
    obj.data.materials.append(M(mat))
    return obj


def esferas(nome, itens, mat, col, segmentos=8, aneis=6):
    """Várias esferas num objeto só. itens = [(raio, (x, y, z_centro)), ...]"""
    bm = bmesh.new()
    for raio, (cx, cy, cz) in itens:
        r = bmesh.ops.create_uvsphere(bm, u_segments=segmentos, v_segments=aneis, radius=raio)
        bmesh.ops.translate(bm, verts=r["verts"], vec=(cx, cy, cz))
    malha = bpy.data.meshes.new(nome)
    bm.to_mesh(malha)
    bm.free()
    for poligono in malha.polygons:
        poligono.use_smooth = True
    obj = bpy.data.objects.new(nome, malha)
    col.objects.link(obj)
    obj.data.materials.append(M(mat))
    return obj


def vazio(nome, col):
    """Objeto vazio (Empty): serve só de 'pai' para agrupar peças. Vira um Node3D no Godot."""
    obj = bpy.data.objects.new(nome, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = 0.3
    col.objects.link(obj)
    return obj


def quad(nome, largura, altura, centro, mat, col):
    """
    Retângulo plano virado para -Y (a 'frente'), com UV de 0 a 1.
    Usado em telas: o Godot pode trocar o material e mostrar uma imagem nele.
    """
    w, h = largura / 2, altura / 2
    verts = [(-w, 0, -h), (w, 0, -h), (w, 0, h), (-w, 0, h)]
    obj = comum.malha_de_pontos(nome, verts, [(0, 1, 2, 3)], centro, mat, col)
    uv = obj.data.uv_layers.new(name="UVMap")
    cantos_uv = [(0, 0), (1, 0), (1, 1), (0, 1)]
    for i, loop in enumerate(obj.data.loops):
        uv.data[i].uv = cantos_uv[loop.vertex_index]
    return obj


def texto(nome, corpo, tamanho, mat, col, centro=(0, 0, 0), largura_max=None):
    """
    Texto 3D plano (fonte padrão do Blender), convertido em malha para exportar.
    Fica de pé, virado para -Y (a frente), centralizado em 'centro'.
    """
    curva = bpy.data.curves.new(nome + "_Curva", type="FONT")
    curva.body = corpo
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
            # Encolhe a malha (não o objeto), para a escala do objeto continuar 1
            malha.transform(Matrix.Scale(largura_max / largura, 4))
    # Deita o texto de pé, de frente para -Y
    malha.transform(Matrix.Rotation(math.radians(90), 4, "X"))
    malha.materials.clear()
    malha.materials.append(M(mat))
    obj = bpy.data.objects.new(nome, malha)
    col.objects.link(obj)
    obj.location = V(centro)
    return obj


def montar(principal, filhos, x, z, h=0.0, frente="sul"):
    """Prende as peças na principal e leva o conjunto para (x, z) da planta, olhando para 'frente'."""
    for f in filhos:
        f.parent = principal
    principal.location = comum.p(x, z, h)
    principal.rotation_euler = (0.0, 0.0, math.radians(FRENTES[frente][0]))
    return principal


def colisao(nome_base, tamanho, base_local, col):
    """Caixa de colisão (filha do móvel). base_local = centro da face de baixo, em coordenadas do móvel."""
    return comum.colisao_caixa(nome_base, tamanho, V(base_local), col)


def na_parede(x, z, frente, afastamento):
    """Ponto (x, z) empurrado 'afastamento' metros para a frente (para objetos encostados na parede)."""
    dx, dz = FRENTES[frente][1]
    return x + dx * afastamento, z + dz * afastamento


# ---------------------------------------------------------------------------
# Peças reutilizáveis (montadas na origem, frente para -Y)
# ---------------------------------------------------------------------------

def cadeira(nome, col, mat):
    assento = caixas(nome, [((0.42, 0.42, 0.05), (0, 0, 0.42))], mat, col)
    encosto = caixas(nome + "_Encosto", [((0.42, 0.05, 0.45), (0, 0.185, 0.47))], mat, col)
    pes = caixas(nome + "_Pes", [((0.03, 0.03, 0.42), (sx * 0.18, sy * 0.18, 0))
                                 for sx in (-1, 1) for sy in (-1, 1)], "Mat_Metal_Escuro", col)
    return assento, [encosto, pes]


def balao(nome, col, mat, x, y, altura_corda, z_base):
    """Balão com barbante; z_base = onde o barbante está amarrado."""
    bola = comum.esfera(nome, 0.17, V((x, y, z_base + altura_corda + 0.2)), mat, col,
                        segmentos=10, aneis=6, escala=(1, 1, 1.2))
    corda = comum.cilindro(nome + "_Barbante", 0.004, altura_corda, V((x, y, z_base)),
                           "Mat_Plastico_Branco", col, vertices=3)
    return [bola, corda]


def mesa_festa(nome, col, mat_toalha, cores_cadeiras, n_baloes, cor_balao, chapeus):
    tampo = assar(comum.cilindro(nome, 0.6, 0.04, V((0, 0, 0.72)), "Mat_Madeira_Escura", col, vertices=16))
    filhos = [
        comum.cilindro(nome + "_Toalha", 0.72, 0.37, V((0, 0, 0.4)), mat_toalha, col,
                       vertices=16, raio_topo=0.62),
        comum.cilindro(nome + "_Perna", 0.06, 0.72, V((0, 0, 0)), "Mat_Metal_Escuro", col, vertices=8),
        comum.cilindro(nome + "_Base", 0.3, 0.03, V((0, 0, 0)), "Mat_Metal_Escuro", col, vertices=12),
        colisao(nome, (1.44, 1.44, 0.78), (0, 0, 0), col),
    ]
    # 4 cadeiras em volta, viradas para o centro da mesa
    for i, ang in enumerate((0, 90, 180, 270)):
        a = math.radians(ang)
        cx, cy = 0.95 * math.sin(a), -0.95 * math.cos(a)
        assento, partes = cadeira(f"Cadeira_{nome[-2:]}_{i + 1:02d}", col, cores_cadeiras[i % len(cores_cadeiras)])
        for prt in partes:
            prt.parent = assento
        # A frente da cadeira (-Y) tem que apontar para o centro da mesa
        assento.rotation_euler = (0, 0, math.atan2(cx, -cy) + math.pi)
        assento.location = V((cx, cy, 0))
        filhos.append(assento)
    for i in range(chapeus):
        a = math.radians(40 + i * 130)
        filhos.append(comum.cilindro(f"{nome}_Chapeu_{i + 1:02d}", 0.07, 0.2,
                                     V((0.35 * math.cos(a), 0.35 * math.sin(a), 0.77)),
                                     ["Mat_Plastico_Azul", "Mat_Plastico_Amarelo", "Mat_Plastico_Verde"][i % 3],
                                     col, vertices=8, raio_topo=0.0))
    for i in range(n_baloes):
        filhos += balao(f"{nome}_Balao_{i + 1:02d}", col, cor_balao if i == 0 else "Mat_Plastico_Amarelo",
                        -0.45 + i * 0.9, 0.45, 1.0 + 0.25 * i, 0.77)
    return tampo, filhos


def estante(nome, col, largura, prof, altura, n_prat, mat, mat_itens="Mat_Papelao", itens_por_prat=3):
    """Estante encostada na parede de trás (+Y local), aberta na frente (-Y)."""
    tabuas = [((0.04, prof, altura), (sx * (largura / 2 - 0.02), 0, 0)) for sx in (-1, 1)]
    tabuas.append(((largura, 0.02, altura), (0, prof / 2 - 0.01, 0)))
    passo = (altura - 0.1) / n_prat
    for i in range(n_prat + 1):
        tabuas.append(((largura, prof, 0.03), (0, 0, 0.08 + i * passo if i < n_prat else altura - 0.03)))
    frame = caixas(nome, tabuas, mat, col)
    itens = []
    for i in range(n_prat):
        z0 = 0.11 + i * passo
        for j in range(itens_por_prat):
            larg = largura / itens_por_prat
            x = -largura / 2 + larg * (j + 0.5)
            alt = min(passo - 0.08, 0.25 + 0.1 * ((i + j) % 3))
            itens.append(((larg * 0.7, prof * 0.75, alt), (x, 0.02, z0)))
    filhos = [caixas(nome + "_Itens", itens, mat_itens, col)]
    filhos.append(colisao(nome, (largura, prof, altura), (0, 0, 0), col))
    return frame, filhos


def poster(nome, col, titulo, mat_fundo, mat_texto, desenho):
    """Pôster de parede: moldura, fundo colorido, um desenho simples e um texto inventado."""
    moldura = caixas(nome, [((0.86, 0.03, 1.16), (0, -0.015, 0))], "Mat_Madeira_Escura", col)
    filhos = [caixas(nome + "_Fundo", [((0.78, 0.01, 1.08), (0, -0.035, 0.04))], mat_fundo, col)]
    y = -0.042

    def circulo(n, r, x, zc, mat):
        return comum.cilindro(n, r, 0.004, V((x, y, zc)), mat, col, vertices=14, rot=(90, 0, 0))

    if desenho == "urso":
        filhos += [circulo(nome + "_Desenho_Rosto", 0.2, 0, 0.78, "Mat_Tito_Marrom"),
                   circulo(nome + "_Desenho_Orelha_Esq", 0.08, -0.17, 0.95, "Mat_Tito_Marrom"),
                   circulo(nome + "_Desenho_Orelha_Dir", 0.08, 0.17, 0.95, "Mat_Tito_Marrom"),
                   comum.cilindro(nome + "_Desenho_Focinho", 0.08, 0.004, V((0, y - 0.004, 0.72)),
                                  "Mat_Tito_Bege", col, vertices=12, rot=(90, 0, 0))]
    elif desenho == "coelha":
        filhos += [circulo(nome + "_Desenho_Rosto", 0.18, 0, 0.72, "Mat_Pipoca_Branco"),
                   caixas(nome + "_Desenho_Orelhas", [((0.07, 0.004, 0.26), (-0.08, y, 0.86)),
                                                      ((0.07, 0.004, 0.26), (0.08, y, 0.86))],
                          "Mat_Pipoca_Branco", col)]
    elif desenho == "pizza":
        filhos.append(comum.malha_de_pontos(nome + "_Desenho_Pizza",
                                            [(-0.22, y, 0.95), (0.22, y, 0.95), (0, y, 0.55)],
                                            [(0, 2, 1)], (0, 0, 0), "Mat_Massa_Pizza", col))
        filhos.append(circulo(nome + "_Desenho_Calabresa", 0.04, 0.0, 0.85, "Mat_Plastico_Vermelho"))
    elif desenho == "baloes":
        for i, (bx, bz, m) in enumerate([(-0.15, 0.85, "Mat_Plastico_Vermelho"),
                                         (0.0, 0.92, "Mat_Plastico_Amarelo"),
                                         (0.15, 0.82, "Mat_Plastico_Verde")]):
            filhos.append(circulo(f"{nome}_Desenho_Balao_{i + 1}", 0.09, bx, bz, m))
    elif desenho == "estrela":
        pts = []
        for i in range(10):
            a = math.radians(90 + i * 36)
            r = 0.2 if i % 2 == 0 else 0.08
            pts.append((r * math.cos(a), y, 0.78 + r * math.sin(a)))
        centro = len(pts)
        pts.append((0, y, 0.78))
        faces = [(centro, i, (i + 1) % 10) for i in range(10)]
        filhos.append(comum.malha_de_pontos(nome + "_Desenho_Estrela", pts, faces, (0, 0, 0),
                                            "Mat_Plastico_Amarelo", col))
    elif desenho == "moldura_vazia":
        filhos.append(caixas(nome + "_Desenho_Foto", [((0.4, 0.004, 0.45), (0, y, 0.55))],
                             "Mat_Poster_Creme", col))
    filhos.append(texto(nome + "_Texto", titulo, 0.085, mat_texto, col, (0, y - 0.006, 0.3),
                        largura_max=0.7))
    return moldura, filhos


def luminaria(nome, col, x, z):
    """Luminária de teto: a origem fica no teto (3,2 m) e a peça fica pendurada para baixo."""
    corpo = caixas(nome, [((0.6, 0.6, 0.06), (0, 0, -0.06))], "Mat_Metal_Escuro", col)
    lamp = caixas(nome + "_Lampada", [((0.5, 0.5, 0.02), (0, 0, -0.08))], "Mat_Lampada_Apagada", col)
    return montar(corpo, [lamp], x, z, 3.2)


def luz_emergencia(nome, col, x, z, frente):
    """Caixinha vermelha de emergência na parede, com o centro a 2,6 m de altura."""
    corpo = caixas(nome, [((0.28, 0.08, 0.12), (0, -0.04, -0.06))], "Mat_Metal_Escuro", col)
    lente = caixas(nome + "_Lente", [((0.22, 0.01, 0.07), (0, -0.085, -0.035))], "Mat_Luz_Emergencia", col)
    return montar(corpo, [lente], x, z, 2.6, frente)


# ---------------------------------------------------------------------------
# Cômodos
# ---------------------------------------------------------------------------

def sala_seguranca(col):
    # Mesa encostada na parede oeste, de frente para o leste (para quem está na sala)
    mesa = caixas("Mesa_Seguranca", [((3.0, 0.9, 0.05), (0, 0, 0.7)),
                                     ((0.05, 0.85, 0.7), (-1.45, 0, 0)),
                                     ((0.05, 0.85, 0.7), (1.45, 0, 0)),
                                     ((2.9, 0.03, 0.5), (0, 0.4, 0.2))], "Mat_Madeira_Escura", col)
    filhos = [colisao("Mesa_Seguranca", (3.0, 0.9, 0.75), (0, 0, 0), col),
              caixas("Mesa_Seguranca_Teclado", [((0.45, 0.15, 0.03), (0, -0.33, 0.75))], "Mat_Plastico_Preto", col),
              caixas("Mesa_Seguranca_Prancheta", [((0.25, 0.32, 0.015), (1.25, -0.3, 0.75))], "Mat_Papel_Branco", col)]
    # Copos de café (cilindro branco + tampinha de café)
    for i, (cx, cy) in enumerate([(-1.2, -0.25), (-0.55, -0.3), (1.25, 0.15)]):
        copo = comum.cilindro(f"Copo_Cafe_{i + 1:02d}", 0.04, 0.11, V((cx, cy, 0.75)), "Mat_Plastico_Branco", col, vertices=8)
        cafe = comum.cilindro(f"Copo_Cafe_{i + 1:02d}_Cafe", 0.036, 0.005, V((0, 0, 0.1)), "Mat_Madeira_Escura", col, vertices=8)
        cafe.parent = copo
        filhos.append(copo)
    montar(mesa, filhos, 22.55, 21.5, 0.0, "leste")

    # Monitores CRT em cima da mesa (o do meio é o principal, com a tela separada)
    for nome, z_pl in [("Monitor_Principal", 21.5), ("Monitor_Esquerdo", 22.35), ("Monitor_Direito", 20.65)]:
        corpo = caixas(nome, [((0.5, 0.45, 0.42), (0, 0, 0)), ((0.36, 0.25, 0.3), (0, 0.33, 0.05))],
                       "Mat_Plastico_Branco", col)
        nome_tela = "Monitor_Tela" if nome == "Monitor_Principal" else nome + "_Tela"
        tela = quad(nome_tela, 0.38, 0.29, (0, -0.227, 0.22), "Mat_Tela_Monitor", col)
        montar(corpo, [tela], 22.6, z_pl, 0.75, "leste")

    # Ventilador de mesa
    base = comum.cilindro("Ventilador", 0.1, 0.03, V((0, 0, 0)), "Mat_Metal_Escuro", col, vertices=10)
    filhos = [comum.cilindro("Ventilador_Haste", 0.015, 0.22, V((0, 0, 0.03)), "Mat_Metal_Escuro", col, vertices=6),
              comum.esfera("Ventilador_Motor", 0.06, V((0, 0.03, 0.27)), "Mat_Metal_Escuro", col, segmentos=8, aneis=6),
              comum.cilindro("Ventilador_Grade", 0.16, 0.02, V((0, -0.03, 0.27)), "Mat_Metal_Cinza", col,
                             vertices=12, rot=(90, 0, 0))]
    montar(base, filhos, 22.55, 22.85, 0.75, "leste")

    # Cadeira de escritório (sem colisão, porque fica colada no ponto de início do jogador)
    assento = caixas("Cadeira_Seguranca", [((0.5, 0.5, 0.08), (0, 0, 0.45))], "Mat_Plastico_Preto", col)
    filhos = [caixas("Cadeira_Seguranca_Encosto", [((0.48, 0.06, 0.55), (0, 0.24, 0.55))], "Mat_Plastico_Preto", col),
              comum.cilindro("Cadeira_Seguranca_Coluna", 0.03, 0.45, V((0, 0, 0)), "Mat_Metal_Escuro", col, vertices=6),
              caixas("Cadeira_Seguranca_Rodas", [((0.6, 0.06, 0.05), (0, 0, 0)), ((0.06, 0.6, 0.05), (0, 0, 0))],
                     "Mat_Metal_Escuro", col)]
    montar(assento, filhos, 24.2, 21.5, 0.0, "oeste")

    # Painel de avisos na parede leste
    px, pz = na_parede(29.9, 23.5, "oeste", 0.0)
    painel = caixas("Painel_Avisos", [((1.2, 0.03, 0.8), (0, -0.015, 0))], "Mat_Cortica", col)
    filhos = [caixas("Painel_Avisos_Papeis_Brancos", [((0.22, 0.005, 0.3), (-0.4, -0.033, 0.4)),
                                                      ((0.25, 0.005, 0.32), (0.3, -0.033, 0.12))], "Mat_Papel_Branco", col),
              caixas("Painel_Avisos_Papeis_Amarelos", [((0.2, 0.005, 0.2), (0.0, -0.033, 0.48)),
                                                       ((0.18, 0.005, 0.18), (-0.15, -0.033, 0.1))], "Mat_Papel_Amarelo", col),
              texto("Painel_Avisos_Texto", "AVISOS", 0.09, "Mat_Texto_Preto", col, (0, -0.04, 0.72))]
    montar(painel, filhos, px, pz, 1.1, "oeste")

    # Armário de arquivos no canto nordeste
    arm = caixas("Armario_Arquivos", [((0.6, 0.5, 1.4), (0, 0, 0))], "Mat_Metal_Cinza", col)
    filhos = [caixas("Armario_Arquivos_Puxadores", [((0.15, 0.02, 0.03), (0, -0.26, 0.3 + 0.35 * i)) for i in range(3)],
                     "Mat_Metal_Escuro", col),
              colisao("Armario_Arquivos", (0.6, 0.5, 1.4), (0, 0, 0), col)]
    montar(arm, filhos, 29.45, 17.2, 0.0, "oeste")

    # Relógio de parede acima da mesa e uma lixeira
    rel = comum.cilindro("Relogio_Parede", 0.18, 0.04, V((0, 0, 0)), "Mat_Plastico_Branco", col, vertices=16, rot=(90, 0, 0))
    assar(rel)
    ponteiros = caixas("Relogio_Parede_Ponteiros", [((0.02, 0.005, 0.13), (0, -0.045, 0)), ((0.1, 0.005, 0.02), (0.05, -0.045, -0.01))],
                       "Mat_Texto_Preto", col)
    montar(rel, [ponteiros], 22.1, 21.5, 2.3, "leste")
    lixo = comum.cilindro("Lixeira_Seguranca", 0.15, 0.35, V((0, 0, 0)), "Mat_Metal_Escuro", col, vertices=10)
    montar(lixo, [], 23.2, 25.6)


def cortina_ondulada(nome, x0, x1, z_plan, h0, h1, ondas, amplitude, mat, col):
    """Cortina em zigue-zague (parece tecido pregueado com poucos polígonos), virada para o sul."""
    n = ondas * 2
    verts, faces = [], []
    centro = comum.p((x0 + x1) / 2, z_plan, h0)
    for i in range(n + 1):
        x = comum.p(x0 + (x1 - x0) * i / n, z_plan).x - centro.x
        dy = amplitude if i % 2 else -amplitude
        verts += [(x, dy, 0.0), (x, dy, h1 - h0)]
    for i in range(n):
        a, b = 2 * i, 2 * (i + 1)
        faces.append((a, b, b + 1, a + 1))
    return comum.malha_de_pontos(nome, verts, faces, centro, mat, col)


def salao(col):
    # 8 mesas de festa (posições escolhidas para deixar portas e pontos de patrulha livres)
    mesas = [(12.5, 5.0), (17.5, 8.0), (22.5, 8.0), (27.5, 5.0),
             (12.5, 10.8), (17.5, 11.0), (22.5, 11.0), (27.5, 10.8)]
    toalhas = ["Mat_Toalha_Xadrez_Vermelha", "Mat_Toalha_Branca"]
    cores_cad = [["Mat_Plastico_Vermelho", "Mat_Plastico_Amarelo"], ["Mat_Plastico_Azul", "Mat_Plastico_Verde"]]
    baloes = ["Mat_Plastico_Vermelho", "Mat_Plastico_Azul", "Mat_Plastico_Verde", "Mat_Plastico_Vermelho"]
    for i, (mx, mz) in enumerate(mesas):
        tampo, filhos = mesa_festa(f"Mesa_{i + 1:02d}", col, toalhas[i % 2], cores_cad[i % 2],
                                   1 + (i % 2), baloes[i % 4], 2 if i % 3 else 3)
        montar(tampo, filhos, mx, mz)

    # Palco: cortina do fundo (até 2,4 m, para a luz de emergência acima dela aparecer),
    # cortinas laterais na frente e a sanefa em cima.
    cortina_ondulada("Palco_Cortina", 14.0, 26.0, 0.3, 0.5, 2.4, 14, 0.08, "Mat_Cortina_Vermelha", col)
    esq = cortina_ondulada("Palco_Cortina_Esq", 14.1, 15.0, 3.8, 0.5, 3.1, 2, 0.07, "Mat_Cortina_Vermelha", col)
    dir_ = cortina_ondulada("Palco_Cortina_Dir", 25.0, 25.9, 3.8, 0.5, 3.1, 2, 0.07, "Mat_Cortina_Vermelha", col)
    esq_col = comum.colisao_caixa("Palco_Cortina_Esq", (0.9, 0.3, 2.6), comum.p(14.55, 3.8, 0.5), col)
    dir_col = comum.colisao_caixa("Palco_Cortina_Dir", (0.9, 0.3, 2.6), comum.p(25.45, 3.8, 0.5), col)
    comum.parentar(esq_col, esq)
    comum.parentar(dir_col, dir_)
    cortina_ondulada("Palco_Sanefa", 14.0, 26.0, 3.95, 2.65, 3.15, 16, 0.05, "Mat_Cortina_Vermelha", col)

    # Barra de holofotes acima da frente do palco, com 4 holofotes apontando para o palco
    barra = assar(comum.cilindro("Holofotes_Barra", 0.04, 12.0, V((-6.0, 0, 0)), "Mat_Metal_Escuro", col,
                                 vertices=6, rot=(0, 90, 0)))
    filhos = []
    for i, hx in enumerate((-4.5, -1.5, 1.5, 4.5)):
        filhos.append(comum.cilindro(f"Holofote_{i + 1:02d}", 0.12, 0.28, V((hx, 0, -0.05)), "Mat_Metal_Escuro", col,
                                     vertices=10, raio_topo=0.09, rot=(-143, 0, 0)))
    montar(barra, filhos, 20.0, 4.6, 2.95)
    for nome, hx in [("Holofote_Chao_Esq", 15.4), ("Holofote_Chao_Dir", 24.6)]:
        h = comum.cilindro(nome, 0.1, 0.22, V((0, 0, 0)), "Mat_Metal_Escuro", col, vertices=10, rot=(-35, 0, 0))
        assar(h)
        montar(h, [], hx, 3.4, 0.5, "sul")

    # Suportes dos animatrônicos (atrás das posições deles no palco) e plaquinhas com os nomes
    for nome, sx in [("Suporte_Tito", 17.0), ("Suporte_Pipoca", 23.0)]:
        base = comum.cilindro(nome, 0.25, 0.03, V((0, 0, 0)), "Mat_Metal_Escuro", col, vertices=12)
        poste = comum.cilindro(nome + "_Poste", 0.04, 1.5, V((0, 0, 0.03)), "Mat_Metal_Cinza", col, vertices=8)
        trava = caixas(nome + "_Trava", [((0.3, 0.08, 0.08), (0, -0.05, 1.45))], "Mat_Metal_Escuro", col)
        montar(base, [poste, trava], sx, 0.65, 0.5)
    for nome, px, txt in [("Placa_Tito", 17.0, "TITO"), ("Placa_Pipoca", 23.0, "PIPOCA")]:
        placa = caixas(nome, [((0.7, 0.02, 0.2), (0, -0.01, 0))], "Mat_Plastico_Amarelo", col)
        letras = texto(nome + "_Texto", txt, 0.12, "Mat_Plastico_Vermelho", col, (0, -0.022, 0.1), largura_max=0.6)
        montar(placa, [letras], px, 4.0, 0.15, "sul")
    mic = comum.cilindro("Microfone", 0.15, 0.02, V((0, 0, 0)), "Mat_Metal_Escuro", col, vertices=10)
    filhos = [comum.cilindro("Microfone_Haste", 0.012, 1.4, V((0, 0, 0.02)), "Mat_Metal_Cinza", col, vertices=6),
              comum.esfera("Microfone_Cabeca", 0.04, V((0, -0.02, 1.45)), "Mat_Metal_Escuro", col, segmentos=8, aneis=6)]
    montar(mic, filhos, 20.0, 2.8, 0.5)

    # Faixa decorativa na parede sul do salão, de frente para o palco
    fx, fz = na_parede(20.0, 12.9, "norte", 0.0)
    faixa = caixas("Faixa_Decorativa", [((6.4, 0.02, 0.5), (0, -0.01, 0))], "Mat_Plastico_Amarelo", col)
    letras = texto("Faixa_Decorativa_Texto", "SEJA FELIZ NA PIZZARIA DO TITO!", 0.3, "Mat_Plastico_Vermelho", col,
                   (0, -0.022, 0.25), largura_max=6.1)
    montar(faixa, [letras], fx, fz, 2.35, "norte")

    # Bandeirinhas atravessando o salão (um objeto por cor; cada triângulo tem as duas faces)
    for linha, zl in enumerate((6.5, 10.0)):
        por_cor = {"Mat_Plastico_Vermelho": [], "Mat_Plastico_Amarelo": [], "Mat_Plastico_Azul": []}
        cores = list(por_cor)
        x = 10.6
        i = 0
        while x + 0.3 < 29.5:
            por_cor[cores[i % 3]].append(x)
            x += 0.5
            i += 1
        for cor, xs in por_cor.items():
            verts, faces = [], []
            for xi in xs:
                b = comum.p(xi, zl, 2.95)
                k = len(verts)
                tri = [(b.x, b.y, 2.95), (b.x + 0.3, b.y, 2.95), (b.x + 0.15, b.y, 2.65)]
                verts += tri + tri  # cópia para a face de trás ter normais próprias
                faces += [(k, k + 2, k + 1), (k + 3, k + 4, k + 5)]
            nome = f"Bandeirinhas_{linha + 1}_{cor.split('_')[-1]}"
            comum.malha_de_pontos(nome, verts, faces, (0, 0, 0), cor, col)
        corda = comum.cilindro(f"Bandeirinhas_{linha + 1}_Corda", 0.006, 19.0, comum.p(10.5, zl, 2.95),
                               "Mat_Plastico_Branco", col, vertices=4, rot=(0, 90, 0))
        corda.name = f"Bandeirinhas_{linha + 1}_Corda"

    # Cachos de balões nos cantos do salão
    for i, (bx, bz) in enumerate([(10.7, 0.7), (29.3, 0.7), (10.7, 12.3), (29.3, 12.3)]):
        peso = comum.cilindro(f"Baloes_Canto_{i + 1:02d}", 0.06, 0.08, V((0, 0, 0)), "Mat_Metal_Escuro", col, vertices=8)
        filhos = []
        for j, (dx, dy, m) in enumerate([(-0.15, 0, "Mat_Plastico_Vermelho"), (0.15, 0.05, "Mat_Plastico_Azul"),
                                         (0, -0.15, "Mat_Plastico_Amarelo")]):
            filhos += balao(f"Baloes_Canto_{i + 1:02d}_{j + 1}", col, m, dx, dy, 1.5 + 0.2 * j, 0.08)
        montar(peso, filhos, bx, bz)


def cozinha(col):
    # Fogão encostado na parede norte
    fog = caixas("Fogao", [((1.0, 0.7, 0.9), (0, 0, 0))], "Mat_Metal_Cinza", col)
    filhos = [caixas("Fogao_Porta", [((0.8, 0.02, 0.45), (0, -0.36, 0.2))], "Mat_Metal_Escuro", col),
              cilindros("Fogao_Bocas", [(0.1, 0.02, (sx * 0.25, sy * 0.15, 0.9)) for sx in (-1, 1) for sy in (-1, 1)],
                        "Mat_Plastico_Preto", col),
              comum.cilindro("Panela_01", 0.15, 0.15, V((-0.25, -0.15, 0.92)), "Mat_Metal_Escuro", col, vertices=10),
              comum.cilindro("Panela_02", 0.12, 0.22, V((0.25, 0.15, 0.92)), "Mat_Metal_Cinza", col, vertices=10),
              colisao("Fogao", (1.0, 0.7, 0.9), (0, 0, 0), col)]
    montar(fog, filhos, 1.6, 0.45)

    # Forno de pizza de tijolos, com cúpula, chaminé e brasa fraquinha
    forno = caixas("Forno_Pizza", [((2.0, 1.5, 1.0), (0, 0, 0))], "Mat_Tijolo_Vermelho", col)
    filhos = [comum.esfera("Forno_Pizza_Cupula", 1.0, V((0, 0, 1.0)), "Mat_Tijolo_Vermelho", col,
                           segmentos=12, aneis=6, escala=(0.95, 0.72, 0.6)),
              caixas("Forno_Pizza_Boca", [((0.7, 0.02, 0.4), (0, -0.76, 0.45))], "Mat_Plastico_Preto", col),
              caixas("Forno_Pizza_Brasa", [((0.5, 0.01, 0.12), (0, -0.775, 0.47))], "Mat_Brasa", col),
              comum.cilindro("Forno_Pizza_Chamine", 0.15, 1.0, V((0, 0.3, 1.5)), "Mat_Metal_Escuro", col, vertices=8),
              colisao("Forno_Pizza", (2.0, 1.5, 1.6), (0, 0, 0), col)]
    montar(forno, filhos, 5.2, 0.85)

    # Geladeira no canto nordeste
    gel = caixas("Geladeira", [((0.9, 0.7, 1.9), (0, 0, 0))], "Mat_Plastico_Branco", col)
    filhos = [caixas("Geladeira_Puxadores", [((0.03, 0.04, 0.3), (0.35, -0.37, 1.3)), ((0.03, 0.04, 0.4), (0.35, -0.37, 0.5))],
                     "Mat_Metal_Cinza", col),
              caixas("Geladeira_Divisao", [((0.9, 0.01, 0.02), (0, -0.355, 1.15))], "Mat_Metal_Escuro", col),
              colisao("Geladeira", (0.9, 0.7, 1.9), (0, 0, 0), col)]
    montar(gel, filhos, 9.35, 0.45)

    # Bancada central de preparo
    banc = caixas("Bancada_Central", [((3.0, 1.0, 0.85), (0, 0, 0)), ((3.05, 1.05, 0.05), (0, 0, 0.85))],
                  "Mat_Metal_Cinza", col)
    filhos = [caixas("Tabua_Corte", [((0.5, 0.35, 0.03), (-0.8, 0, 0.9))], "Mat_Madeira_Clara", col),
              comum.cilindro("Massa_Pizza", 0.2, 0.03, V((-0.8, 0, 0.93)), "Mat_Massa_Pizza", col, vertices=12),
              comum.cilindro("Panela_03", 0.16, 0.18, V((0.9, 0.1, 0.9)), "Mat_Metal_Escuro", col, vertices=10),
              comum.cilindro("Rolo_Massa", 0.03, 0.4, V((-0.1, 0.25, 0.93)), "Mat_Madeira_Clara", col,
                             vertices=8, rot=(0, 90, 0)),
              colisao("Bancada_Central", (3.0, 1.0, 0.9), (0, 0, 0), col)]
    montar(banc, filhos, 5.0, 4.1)

    # Bancada com pia na parede leste (de frente para o oeste)
    pia = caixas("Bancada_Pia", [((3.0, 0.6, 0.9), (0, 0, 0))], "Mat_Metal_Cinza", col)
    filhos = [caixas("Bancada_Pia_Cuba", [((0.6, 0.4, 0.02), (0.3, 0, 0.9))], "Mat_Metal_Escuro", col),
              caixas("Bancada_Pia_Torneira", [((0.04, 0.04, 0.25), (0.3, 0.22, 0.9)), ((0.04, 0.18, 0.04), (0.3, 0.14, 1.12))],
                     "Mat_Metal_Cinza", col),
              cilindros("Pratos_Empilhados", [(0.13, 0.12, (-0.9, 0, 0.9))], "Mat_Louca_Branca", col, vertices=12),
              colisao("Bancada_Pia", (3.0, 0.6, 0.9), (0, 0, 0), col)]
    montar(pia, filhos, 9.6, 3.0, 0.0, "oeste")

    # Prateleiras na parede oeste, com potes
    for nome, z_pl, larg in [("Prateleira_Cozinha_01", 3.25, 2.5), ("Prateleira_Cozinha_02", 5.8, 1.6)]:
        frame, filhos = estante(nome, col, larg, 0.4, 2.0, 4, "Mat_Madeira_Clara", "Mat_Louca_Branca", 4)
        montar(frame, filhos, 0.3, z_pl, 0.0, "leste")

    lixo = comum.cilindro("Lixeira_Cozinha", 0.22, 0.6, V((0, 0, 0)), "Mat_Plastico_Verde", col, vertices=10)
    montar(lixo, [], 2.5, 12.4)


def deposito(col):
    for nome, x, z, larg, frente in [("Estante_Deposito_01", 32.5, 0.45, 3.0, "sul"),
                                     ("Estante_Deposito_02", 35.9, 0.45, 2.2, "sul"),
                                     ("Estante_Deposito_03", 39.55, 4.3, 2.6, "oeste")]:
        frame, filhos = estante(nome, col, larg, 0.7, 2.2, 4, "Mat_Metal_Escuro", "Mat_Papelao", 3)
        montar(frame, filhos, x, z, 0.0, frente)

    # Pilhas de caixas de papelão
    for nome, x, z, alturas in [("Caixas_Deposito_01", 32.0, 3.6, (0.6, 0.5, 0.4)),
                                ("Caixas_Deposito_02", 35.8, 3.4, (0.55, 0.45)),
                                ("Caixas_Deposito_03", 33.0, 11.2, (0.6, 0.5))]:
        itens, z0 = [], 0.0
        for i, alt in enumerate(alturas):
            lado = 1.0 - 0.15 * i
            itens.append(((lado, lado, alt), (0.03 * i, -0.02 * i, z0)))
            z0 += alt
        caixa_obj = caixas(nome, itens, "Mat_Papelao", col)
        montar(caixa_obj, [colisao(nome, (1.0, 1.0, z0), (0, 0, 0), col)], x, z)

    # Bancada de peças antigas: cabeças e braços de animatrônicos velhos (só metal e plástico)
    banc = caixas("Bancada_Pecas", [((2.5, 0.9, 0.05), (0, 0, 0.85)), ((0.05, 0.85, 0.85), (-1.2, 0, 0)),
                                    ((0.05, 0.85, 0.85), (1.2, 0, 0))], "Mat_Madeira_Escura", col)
    urso = comum.esfera("Cabeca_Antiga_Urso", 0.25, V((-0.7, 0.05, 1.15)), "Mat_Metal_Escuro", col, segmentos=10, aneis=7)
    urso_orelhas = esferas("Cabeca_Antiga_Urso_Orelhas", [(0.08, (-0.18, 0, 0.2)), (0.08, (0.18, 0, 0.2))],
                           "Mat_Metal_Escuro", col)
    urso_focinho = comum.esfera("Cabeca_Antiga_Urso_Focinho", 0.1, V((0, -0.22, -0.05)), "Mat_Plastico_Branco", col,
                                segmentos=8, aneis=6, escala=(1.2, 0.8, 0.8))
    urso_orelhas.parent = urso
    urso_focinho.parent = urso
    coelho = comum.esfera("Cabeca_Antiga_Coelho", 0.22, V((0.35, 0.05, 1.12)), "Mat_Plastico_Branco", col, segmentos=10, aneis=7)
    coelho_orelhas = esferas("Cabeca_Antiga_Coelho_Orelhas", [(0.06, (-0.08, 0, 0.3)), (0.06, (0.08, 0, 0.3))],
                             "Mat_Plastico_Branco", col)
    for v in coelho_orelhas.data.vertices:  # estica as esferinhas para virarem orelhas compridas
        v.co.z = 0.3 + (v.co.z - 0.3) * 3.0
    coelho_orelhas.parent = coelho
    braco = comum.cilindro("Braco_Mecanico", 0.03, 0.6, V((0.75, -0.15, 0.92)), "Mat_Metal_Cinza", col,
                           vertices=8, rot=(0, 90, 0))
    junta = comum.esfera("Braco_Mecanico_Junta", 0.05, V((0, 0, 0.0)), "Mat_Metal_Escuro", col, segmentos=8, aneis=6)
    junta.parent = braco
    engr = comum.cilindro("Engrenagem", 0.12, 0.03, V((-0.15, -0.25, 0.9)), "Mat_Metal_Cinza", col, vertices=10)
    ferr = caixas("Caixa_Ferramentas", [((0.4, 0.2, 0.18), (1.0, 0.22, 0.9))], "Mat_Plastico_Vermelho", col)
    filhos = [urso, coelho, braco, engr, ferr, colisao("Bancada_Pecas", (2.5, 0.9, 0.9), (0, 0, 0), col)]
    montar(banc, filhos, 30.55, 10.25, 0.0, "leste")

    barril = comum.cilindro("Barril_Deposito", 0.35, 0.9, V((0, 0, 0)), "Mat_Plastico_Azul", col, vertices=12)
    montar(barril, [colisao("Barril_Deposito", (0.7, 0.7, 0.9), (0, 0, 0), col)], 38.5, 12.2)


def arcade(nome, col, mat_corpo, mat_tela, titulo):
    corpo = caixas(nome, [((0.7, 0.75, 0.95), (0, 0, 0)), ((0.7, 0.5, 0.9), (0, 0.125, 0.95))], mat_corpo, col)
    filhos = [quad(nome + "_Tela", 0.54, 0.4, (0, -0.13, 1.3), mat_tela, col),
              quad(nome + "_Letreiro", 0.62, 0.17, (0, -0.13, 1.71), "Mat_Letreiro_Amarelo", col),
              texto(nome + "_Letreiro_Texto", titulo, 0.1, "Mat_Texto_Preto", col, (0, -0.136, 1.71), largura_max=0.55),
              caixas(nome + "_Painel", [((0.7, 0.3, 0.1), (0, -0.25, 0.9))], "Mat_Plastico_Preto", col),
              cilindros(nome + "_Controle", [(0.012, 0.08, (-0.15, -0.3, 1.0))], "Mat_Metal_Cinza", col, vertices=6),
              cilindros(nome + "_Botoes", [(0.025, 0.015, (0.08, -0.3, 1.0)), (0.025, 0.015, (0.17, -0.3, 1.0))],
                        "Mat_Plastico_Vermelho", col, vertices=8),
              comum.cilindro(nome + "_Banco", 0.18, 0.05, V((0, -0.9, 0.5)), "Mat_Plastico_Vermelho", col, vertices=10),
              comum.cilindro(nome + "_Banco_Haste", 0.03, 0.5, V((0, -0.9, 0.0)), "Mat_Metal_Escuro", col, vertices=6),
              colisao(nome, (0.7, 0.75, 1.85), (0, 0, 0), col)]
    return corpo, filhos


def fliperama(col):
    corpos = ["Mat_Plastico_Preto", "Mat_Plastico_Azul", "Mat_Plastico_Vermelho", "Mat_Plastico_Preto", "Mat_Plastico_Verde"]
    telas = ["Mat_Tela_Arcade_Azul", "Mat_Tela_Arcade_Rosa", "Mat_Tela_Arcade_Verde"]
    titulos = ["TURBO", "ESTRELA", "PULO", "PIZZA", "FOGUETE"]
    for i, z_pl in enumerate((17.6, 19.0, 20.4, 21.8, 23.2)):
        c, filhos = arcade(f"Arcade_{i + 1:02d}", col, corpos[i], telas[i % 3], titulos[i])
        montar(c, filhos, 13.525, z_pl, 0.0, "oeste")

    # Máquina de prêmios (garra) no canto noroeste
    maq = caixas("Maquina_Premios", [((1.0, 1.0, 0.8), (0, 0, 0)), ((1.0, 1.0, 0.25), (0, 0, 1.8))],
                 "Mat_Plastico_Vermelho", col)
    filhos = [caixas("Maquina_Premios_Colunas", [((0.05, 0.05, 1.0), (sx * 0.475, sy * 0.475, 0.8))
                                                 for sx in (-1, 1) for sy in (-1, 1)], "Mat_Metal_Cinza", col),
              esferas("Maquina_Premios_Pelucias_Azuis", [(0.1, (-0.25, 0.1, 0.9)), (0.09, (0.2, -0.2, 0.9)), (0.1, (0.0, 0.25, 1.0))],
                      "Mat_Plastico_Azul", col),
              esferas("Maquina_Premios_Pelucias_Amarelas", [(0.1, (0.25, 0.2, 0.9)), (0.09, (-0.2, -0.2, 0.9)), (0.08, (0.05, 0.0, 1.05))],
                      "Mat_Plastico_Amarelo", col),
              caixas("Maquina_Premios_Garra", [((0.02, 0.02, 0.4), (0, 0, 1.4)), ((0.12, 0.12, 0.06), (0, 0, 1.34))],
                     "Mat_Metal_Cinza", col),
              texto("Maquina_Premios_Texto", "PRÊMIOS", 0.13, "Mat_Plastico_Amarelo", col, (0, -0.505, 1.925), largura_max=0.9),
              colisao("Maquina_Premios", (1.0, 1.0, 2.05), (0, 0, 0), col)]
    montar(maq, filhos, 2.0, 16.62)

    # Letreiro na parede norte
    lx, lz = na_parede(10.5, 16.1, "sul", 0.0)
    placa = caixas("Letreiro_Fliperama", [((2.2, 0.03, 0.5), (0, -0.015, 0))], "Mat_Plastico_Preto", col)
    letras = texto("Letreiro_Fliperama_Texto", "FLIPERAMA", 0.3, "Mat_Letreiro_Rosa", col, (0, -0.035, 0.25), largura_max=2.0)
    montar(placa, [letras], lx, lz, 2.3, "sul")

    # Balcão de troca de tickets na parede sul
    balc = caixas("Balcao_Premios", [((2.0, 0.8, 1.0), (0, 0, 0))], "Mat_Plastico_Amarelo", col)
    filhos = [cilindros("Balcao_Premios_Potes", [(0.12, 0.25, (-0.5, 0, 1.0)), (0.12, 0.2, (0.5, 0, 1.0))],
                        "Mat_Vidro_Escuro", col, vertices=10),
              texto("Balcao_Premios_Texto", "TROQUE SEUS TICKETS", 0.09, "Mat_Plastico_Vermelho", col, (0, -0.41, 0.75),
                    largura_max=1.8),
              colisao("Balcao_Premios", (2.0, 0.8, 1.0), (0, 0, 0), col)]
    montar(balc, filhos, 10.5, 26.5, 0.0, "norte")


def banheiros(col):
    # Bancada com 3 pias e espelho na parede oeste
    banc = caixas("Bancada_Pias", [((2.8, 0.6, 0.85), (0, 0, 0))], "Mat_Plastico_Branco", col)
    filhos = [cilindros("Pias", [(0.18, 0.06, (x, -0.02, 0.85)) for x in (-0.9, 0, 0.9)], "Mat_Louca_Branca", col, vertices=12),
              caixas("Torneiras", [((0.04, 0.12, 0.12), (x, 0.2, 0.85)) for x in (-0.9, 0, 0.9)], "Mat_Metal_Cinza", col),
              quad("Espelho_Banheiro", 2.6, 0.8, (0, 0.285, 1.6), "Mat_Espelho", col),
              colisao("Bancada_Pias", (2.8, 0.6, 0.85), (0, 0, 0), col)]
    montar(banc, filhos, 14.4, 19.2, 0.0, "leste")

    # Bloco de 4 cabines na parede leste (de frente para o oeste)
    bloco = vazio("Cabines_Banheiro", col)
    filhos = [caixas("Cabine_Divisorias", [((0.04, 1.5, 1.8), (x, 0, 0.15)) for x in (-2.4, -1.2, 0.0, 1.2, 2.4)],
                     "Mat_Plastico_Azul", col),
              colisao("Cabines_Banheiro", (4.8, 1.5, 2.0), (0, 0, 0), col)]
    for i, x in enumerate((-1.8, -0.6, 0.6, 1.8)):
        filhos.append(caixas(f"Cabine_Porta_{i + 1:02d}", [((1.08, 0.04, 1.8), (x, -0.73, 0.15))], "Mat_Plastico_Azul", col))
        vaso = comum.cilindro(f"Vaso_Sanitario_{i + 1:02d}", 0.2, 0.4, V((x, 0.3, 0)), "Mat_Louca_Branca", col, vertices=10)
        caixa_d = caixas(f"Vaso_Sanitario_{i + 1:02d}_Caixa", [((0.4, 0.18, 0.35), (0, 0.32, 0.4))], "Mat_Louca_Branca", col)
        caixa_d.parent = vaso
        filhos.append(vaso)
    montar(bloco, filhos, 21.15, 22.0, 0.0, "oeste")

    sec = caixas("Secador_Maos", [((0.3, 0.18, 0.3), (0, -0.09, 0))], "Mat_Metal_Cinza", col)
    montar(sec, [], 21.9, 17.6, 1.2, "oeste")
    lixo = comum.cilindro("Lixeira_Banheiro", 0.18, 0.5, V((0, 0, 0)), "Mat_Metal_Escuro", col, vertices=10)
    montar(lixo, [], 14.45, 21.2)


def recepcao(col):
    balc = caixas("Balcao_Recepcao", [((3.0, 0.7, 1.0), (0, 0, 0))], "Mat_Madeira_Escura", col)
    filhos = [caixas("Balcao_Recepcao_Tampo", [((3.1, 0.8, 0.05), (0, 0, 1.0))], "Mat_Madeira_Clara", col),
              caixas("Caixa_Registradora", [((0.4, 0.35, 0.22), (0.8, 0.05, 1.05)), ((0.3, 0.05, 0.15), (0.8, 0.2, 1.27))],
                     "Mat_Metal_Escuro", col),
              comum.cilindro("Sino_Balcao", 0.05, 0.05, V((-0.9, -0.2, 1.05)), "Mat_Plastico_Amarelo", col,
                             vertices=8, raio_topo=0.02),
              colisao("Balcao_Recepcao", (3.1, 0.8, 1.05), (0, 0, 0), col)]
    montar(balc, filhos, 32.5, 19.35)

    px, pz = na_parede(32.0, 16.1, "sul", 0.0)
    placa = caixas("Placa_Boas_Vindas", [((3.0, 0.03, 0.6), (0, -0.015, 0))], "Mat_Plastico_Vermelho", col)
    letras = texto("Placa_Boas_Vindas_Texto", "BEM-VINDO À\nPIZZARIA DO TITO", 0.2, "Mat_Texto_Branco", col,
                   (0, -0.035, 0.3), largura_max=2.8)
    montar(placa, [letras], px, pz, 2.2, "sul")

    # Porta da frente (só decoração): trancada com corrente e cadeado
    batente = caixas("Porta_Frente", [((1.8, 0.08, 0.08), (0, -0.04, 2.2)),
                                      ((0.08, 0.08, 2.28), (-0.86, -0.04, 0)),
                                      ((0.08, 0.08, 2.28), (0.86, -0.04, 0))], "Mat_Batente_Madeira", col)
    filhos = []
    for lado, sx in (("Esq", -1), ("Dir", 1)):
        filhos.append(caixas(f"Porta_Frente_Folha_{lado}", [((0.8, 0.05, 2.2), (sx * 0.41, -0.03, 0))], "Mat_Porta_Metal", col))
        filhos.append(quad(f"Porta_Frente_Vidro_{lado}", 0.5, 0.8, (sx * 0.41, -0.057, 1.45), "Mat_Vidro_Escuro", col))
        filhos.append(caixas(f"Porta_Frente_Puxador_{lado}", [((0.03, 0.04, 0.4), (sx * 0.08, -0.08, 0.9))], "Mat_Metal_Cinza", col))
    elos = [((0.07, 0.02, 0.035) if i % 2 == 0 else (0.07, 0.035, 0.02), (-0.24 + i * 0.06, -0.12, 1.08)) for i in range(9)]
    filhos.append(caixas("Porta_Frente_Corrente", elos, "Mat_Metal_Cinza", col))
    filhos.append(caixas("Porta_Frente_Cadeado", [((0.08, 0.04, 0.09), (0, -0.14, 0.97))], "Mat_Plastico_Amarelo", col))
    filhos.append(caixas("Porta_Frente_Placa", [((0.4, 0.01, 0.15), (-0.41, -0.065, 1.95))], "Mat_Papel_Branco", col))
    filhos.append(texto("Porta_Frente_Placa_Texto", "FECHADO", 0.08, "Mat_Plastico_Vermelho", col, (-0.41, -0.072, 2.025),
                        largura_max=0.36))
    montar(batente, filhos, 39.9, 22.0, 0.0, "oeste")

    for nome, x, z, frente in [("Banco_Recepcao_01", 39.6, 26.0, "oeste"), ("Banco_Recepcao_02", 34.3, 29.6, "norte")]:
        banco = caixas(nome, [((2.0, 0.5, 0.08), (0, 0, 0.4))], "Mat_Plastico_Vermelho", col)
        filhos = [caixas(nome + "_Encosto", [((2.0, 0.08, 0.5), (0, 0.21, 0.45))], "Mat_Plastico_Vermelho", col),
                  caixas(nome + "_Pes", [((0.05, 0.45, 0.4), (sx * 0.9, 0, 0)) for sx in (-1, 1)], "Mat_Metal_Escuro", col),
                  colisao(nome, (2.0, 0.5, 0.95), (0, 0, 0), col)]
        montar(banco, filhos, x, z, 0.0, frente)

    vaso = comum.cilindro("Planta_Recepcao", 0.25, 0.45, V((0, 0, 0)), "Mat_Vaso_Terracota", col, vertices=10, raio_topo=0.3)
    folhas = esferas("Planta_Recepcao_Folhas", [(0.3, (0, 0, 0.75)), (0.22, (0.12, 0.1, 1.0)), (0.2, (-0.1, -0.08, 1.05))],
                     "Mat_Planta_Verde", col)
    montar(vaso, [folhas, colisao("Planta_Recepcao", (0.6, 0.6, 1.2), (0, 0, 0), col)], 31.0, 16.8)


def corredor_principal(col):
    posters = [
        (10.0, 13.1, "sul", "SEJA FELIZ NA\nPIZZARIA DO TITO!", "Mat_Poster_Amarelo", "Mat_Texto_Preto", "urso"),
        (20.0, 13.1, "sul", "PIPOCA ADORA\nPULAR!", "Mat_Poster_Lilas", "Mat_Texto_Branco", "coelha"),
        (30.0, 13.1, "sul", "PIZZA EM DOBRO\nTODA SEXTA", "Mat_Poster_Vermelho", "Mat_Texto_Branco", "pizza"),
        (3.0, 15.9, "norte", "FESTA DE\nANIVERSÁRIO", "Mat_Poster_Azul", "Mat_Texto_Branco", "baloes"),
        (12.5, 15.9, "norte", "LAVE AS MÃOS\nANTES DE COMER", "Mat_Poster_Verde", "Mat_Texto_Branco", "estrela"),
        (22.0, 15.9, "norte", "NÃO CORRA\nNOS CORREDORES", "Mat_Poster_Laranja", "Mat_Texto_Preto", "estrela"),
        (32.0, 15.9, "norte", "FUNCIONÁRIO\nDO MÊS", "Mat_Poster_Cinza", "Mat_Texto_Preto", "moldura_vazia"),
        (38.0, 15.9, "norte", "SORRIA!\nA FESTA NÃO PARA", "Mat_Poster_Creme", "Mat_Texto_Preto", "urso"),
    ]
    for i, (x, z, frente, titulo, fundo, cor_txt, desenho) in enumerate(posters):
        moldura, filhos = poster(f"Poster_{i + 1:02d}", col, titulo, fundo, cor_txt, desenho)
        montar(moldura, filhos, x, z, 1.15, frente)

    for nome, x, z, frente in [("Extintor_01", 29.5, 15.9, "norte"), ("Extintor_02", 2.5, 13.1, "sul")]:
        suporte = caixas(nome, [((0.12, 0.04, 0.2), (0, -0.02, 0.35))], "Mat_Metal_Escuro", col)
        filhos = [comum.cilindro(nome + "_Cilindro", 0.09, 0.5, V((0, -0.13, 0.15)), "Mat_Plastico_Vermelho", col, vertices=10),
                  caixas(nome + "_Bico", [((0.06, 0.05, 0.08), (0, -0.13, 0.65)), ((0.03, 0.12, 0.03), (0, -0.2, 0.68))],
                         "Mat_Plastico_Preto", col)]
        montar(suporte, filhos, x, z, 0.5, frente)


def corredor_fundos(col):
    # Canos correndo pela parede sul, perto do teto
    cano1 = comum.cilindro("Cano_Fundos_01", 0.06, 29.0, comum.p(0.5, 29.75, 2.95), "Mat_Metal_Cinza", col,
                           vertices=8, rot=(0, 90, 0))
    cano2 = comum.cilindro("Cano_Fundos_02", 0.04, 29.0, comum.p(0.5, 29.8, 2.8), "Mat_Metal_Escuro", col,
                           vertices=6, rot=(0, 90, 0))
    for nome, x in [("Cano_Fundos_Descida_01", 3.0), ("Cano_Fundos_Descida_02", 27.0)]:
        comum.cilindro(nome, 0.04, 2.8, comum.p(x, 29.8, 0.0), "Mat_Metal_Escuro", col, vertices=6)
    _ = (cano1, cano2)
    for nome, x in [("Caixas_Fundos_01", 10.5), ("Caixas_Fundos_02", 21.0)]:
        cx = caixas(nome, [((0.8, 0.35, 0.6), (0, 0, 0)), ((0.5, 0.3, 0.35), (0.1, 0, 0.6))], "Mat_Papelao", col)
        montar(cx, [colisao(nome, (0.8, 0.35, 0.95), (0, 0, 0), col)], x, 29.7, 0.0, "norte")


def luminarias_e_emergencia(cols):
    luminarias = {
        "Salao": [(14, 6), (20, 6), (26, 6), (14, 10.5), (20, 10.5), (26, 10.5)],
        "Corredor_Principal": [(4, 14.5), (12, 14.5), (20, 14.5), (28, 14.5), (36, 14.5)],
        "Cozinha": [(5, 4), (5, 9.5)],
        "Deposito": [(35, 4), (35, 9.5)],
        "Fliperama": [(4, 21.5), (10, 21.5)],
        "Banheiros": [(18, 21.5)],
        "Sala_Seguranca": [(26, 21.5)],
        "Recepcao": [(35, 21), (35, 27)],
        "Corredor_Fundos": [(5, 28.5), (15, 28.5), (25, 28.5)],
    }
    for comodo, pontos in luminarias.items():
        for i, (x, z) in enumerate(pontos):
            luminaria(f"Luminaria_{comodo}_{i + 1:02d}", cols[comodo], x, z)
    emergencias = [((0.1, 14.5), "leste", "Corredor_Principal"), ((39.9, 14.5), "oeste", "Corredor_Principal"),
                   ((15, 29.9), "norte", "Corredor_Fundos"), ((29.9, 21.5), "oeste", "Sala_Seguranca"),
                   ((20, 0.1), "sul", "Salao")]
    for i, ((x, z), frente, comodo) in enumerate(emergencias):
        luz_emergencia(f"Luz_Emergencia_{i + 1:02d}", cols[comodo], x, z, frente)


def disjuntores(col):
    """
    4 caixas de disjuntor. A origem fica no centro da face de trás (encostada na parede),
    com o centro da caixa a 1,3 m de altura. A alavanca é um objeto filho com a origem no
    eixo de giro: desligada = -40° no X local (para baixo); o jogo gira até +40° (para cima).
    Truque: a alavanca está virada 180° em Z dentro da caixa, para que girar o X local
    no sentido positivo levante a ponta (que fica para fora da caixa).
    """
    dados = [("Disjuntor_Cozinha", 0.1, 9.5, "leste", "COZINHA"),
             ("Disjuntor_Deposito", 39.9, 9.5, "oeste", "DEPÓSITO"),
             ("Disjuntor_Fliperama", 0.1, 21.5, "leste", "FLIPERAMA"),
             ("Disjuntor_Banheiros", 18.0, 26.9, "norte", "BANHEIROS")]
    objetos = []
    for nome, x, z, frente, rotulo in dados:
        cx = caixas(nome, [((0.45, 0.15, 0.6), (0, -0.075, -0.3))], "Mat_Disjuntor_Caixa", col)
        alav = caixas(nome + "_Alavanca", [((0.12, 0.04, 0.04), (0, 0, -0.02)),
                                           ((0.03, 0.14, 0.03), (0, 0.07, -0.015)),
                                           ((0.09, 0.04, 0.04), (0, 0.15, -0.02))], "Mat_Disjuntor_Alavanca", col)
        alav.parent = cx
        alav.location = V((0, -0.15, 0))
        alav.rotation_euler = (math.radians(-40), 0, math.radians(180))
        led = caixas(nome + "_Led", [((0.03, 0.01, 0.03), (0.16, -0.155, 0.2))], "Mat_Led_Disjuntor", col)
        led.parent = cx
        placa = texto(nome + "_Placa", rotulo, 0.05, "Mat_Texto_Branco", col, (-0.03, -0.152, 0.22), largura_max=0.3)
        placa.parent = cx
        cx.location = comum.p(x, z, 1.3)
        cx.rotation_euler = (0, 0, math.radians(FRENTES[frente][0]))
        objetos += [cx, alav, led, placa]
    return objetos


# ---------------------------------------------------------------------------
# Checagens automáticas
# ---------------------------------------------------------------------------

def _dist_ret(px, pz, ret):
    x0, x1, z0, z1 = ret
    dx = max(x0 - px, 0.0, px - x1)
    dz = max(z0 - pz, 0.0, pz - z1)
    return math.hypot(dx, dz)


def verificar_areas_livres():
    """Falha se alguma caixa de colisão invadir portas, pontos de jogo ou corredores (seção 4 do contrato)."""
    bpy.context.view_layer.update()
    pontos = []
    portas = [(10, 6.5), (30, 6.5), (30, 28.5), (5, 13), (15, 13), (25, 13), (35, 13),
              (7, 16), (18, 16), (26, 16), (35, 16), (7, 27), (26, 27)]
    pontos += [(f"porta {p}", p[0], p[1], 1.5) for p in portas]
    patrulha = [(14, 8), (26, 8), (5, 7), (35, 7), (3, 14.5), (37, 14.5), (7, 21.5), (15, 28.5), (35, 23)]
    pontos += [(f"patrulha {p}", p[0], p[1], 1.0) for p in patrulha]
    pilhas = [(28.8, 26), (8.8, 11.8), (38.8, 1.2), (1.2, 25.8), (38.8, 29), (1.2, 28.5)]
    pontos += [(f"pilha {p}", p[0], p[1], 1.0) for p in pilhas]
    pontos += [("animatrônico (17,2)", 17, 2, 1.0), ("animatrônico (23,2)", 23, 2, 1.0),
               ("spawn (25.5,21.5)", 25.5, 21.5, 1.2)]
    # Frente dos disjuntores: um círculo de 1 m centrado 1 m à frente (cobre 0 a 2 m)
    pontos += [("frente disjuntor cozinha", 1.1, 9.5, 1.0), ("frente disjuntor depósito", 38.9, 9.5, 1.0),
               ("frente disjuntor fliperama", 1.1, 21.5, 1.0), ("frente disjuntor banheiros", 18.0, 25.9, 1.0)]

    erros = []
    for obj in bpy.context.scene.objects:
        if not obj.name.endswith("-colonly"):
            continue
        cantos = [obj.matrix_world @ V(c) for c in obj.bound_box]
        xs = [c.x + 20 for c in cantos]
        zs = [15 - c.y for c in cantos]
        ret = (min(xs), max(xs), min(zs), max(zs))
        for nome, px, pz, raio in pontos:
            d = _dist_ret(px, pz, ret)
            if d < raio - 1e-4:
                erros.append(f"{obj.name} invade {nome} (distância {d:.2f} < {raio})")
        # Escada do palco
        if ret[0] < 21 and ret[1] > 19 and ret[2] < 5.5 and ret[3] > 4:
            erros.append(f"{obj.name} invade a escada do palco")
        # Corredores: só coisas encostadas na parede, com até 0,4 m de profundidade
        for (cx0, cx1, cz0, cz1, nome_c) in [(0, 40, 13, 16, "corredor principal"), (0, 30, 27, 30, "corredor dos fundos")]:
            if ret[1] > cx0 + 0.11 and ret[0] < cx1 - 0.11 and ret[3] > cz0 + 0.11 and ret[2] < cz1 - 0.11:
                encostado = ret[3] <= cz0 + 0.1 + 0.4 + 1e-4 or ret[2] >= cz1 - 0.1 - 0.4 - 1e-4
                if not encostado:
                    erros.append(f"{obj.name} ocupa o meio do {nome_c}")
    for e in erros:
        print("AVISO:", e)
    if erros:
        raise RuntimeError(f"{len(erros)} problema(s) de área livre; veja os AVISOS acima.")
    print("[moveis] áreas livres OK")


def contar_triangulos(objetos):
    total = 0
    for obj in objetos:
        if obj.type == "MESH" and not obj.name.endswith("-colonly"):
            total += sum(len(p.vertices) - 2 for p in obj.data.polygons)
    return total


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------

def gerar():
    comum.limpar_cena()
    for nome, (cor, em) in CORES_MOVEIS.items():
        comum.material(nome, cor, em)

    cols = {nome: comum.colecao(nome) for nome in COMODOS}
    col_disj = comum.colecao("Disjuntores")

    sala_seguranca(cols["Sala_Seguranca"])
    salao(cols["Salao"])
    cozinha(cols["Cozinha"])
    deposito(cols["Deposito"])
    fliperama(cols["Fliperama"])
    banheiros(cols["Banheiros"])
    recepcao(cols["Recepcao"])
    corredor_principal(cols["Corredor_Principal"])
    corredor_fundos(cols["Corredor_Fundos"])
    luminarias_e_emergencia(cols)
    objs_disj = disjuntores(col_disj)

    verificar_areas_livres()

    todos = list(bpy.context.scene.objects)
    moveis = [o for o in todos if o.name not in {d.name for d in objs_disj}]
    tri_moveis = contar_triangulos(moveis)
    tri_disj = contar_triangulos(objs_disj)
    print(f"[moveis] objetos: {len(moveis)} móveis/props + {len(objs_disj)} de disjuntores")
    print(f"[moveis] triângulos: {tri_moveis} (móveis) + {tri_disj} (disjuntores) = {tri_moveis + tri_disj}")
    if tri_moveis + tri_disj > 60000:
        raise RuntimeError("Passou de 60 mil triângulos; simplifique.")

    comum.salvar_blend(comum.PASTA_BLENDER / "moveis.blend")
    # Cada .glb só deve levar as suas Collections; as outras são tiradas da cena
    # temporariamente (senão elas viram nós vazios no Godot).
    exportar_so(comum.PASTA_CENARIO / "moveis.glb", moveis, set(COMODOS))
    exportar_so(comum.PASTA_CENARIO / "disjuntores.glb", objs_disj, {"Disjuntores"})


def exportar_so(caminho, objetos, colecoes_incluidas):
    """
    Exporta só as Collections pedidas. As outras são desligadas da cena
    temporariamente (senão o exportador cria nós vazios com o nome delas).
    """
    raiz = bpy.context.scene.collection
    tiradas = [c for c in raiz.children if c.name not in colecoes_incluidas]
    for c in tiradas:
        raiz.children.unlink(c)
    bpy.context.view_layer.update()  # a cena precisa "perceber" a mudança antes de exportar
    try:
        comum.exportar_glb(caminho, [o for o in objetos if o.name in bpy.context.view_layer.objects])
    finally:
        for c in tiradas:
            raiz.children.link(c)
        bpy.context.view_layer.update()


if __name__ == "__main__":
    gerar()
