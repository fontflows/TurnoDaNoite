"""
gerar_placeholders.py — cria os personagens provisórios (placeholders) Tito e Pipoca.

Por que existe: o jogo precisa de personagens para testar a IA e o jumpscare
antes de os modelos finais ficarem prontos. Estes bonecos são simples, mas
têm "cara de personagem" e seguem o mesmo padrão que os modelos finais devem seguir:

- cerca de 2 m de altura, com a origem (0, 0, 0) nos PÉS;
- FRENTE virada para -Y no Blender (na vista Front, tecla 1 do teclado numérico,
  o personagem olha para você);
- um Empty "Tito"/"Pipoca" na origem é o pai de tudo;
- "Esq" = lado esquerdo DO PERSONAGEM. Como ele olha para -Y, o lado esquerdo
  dele fica no +X do Blender (o seu lado direito, olhando para ele de frente);
- a cabeça ("Tito_Cabeca"/"Pipoca_Cabeca") tem a origem no pescoço e é pai de
  olhos, orelhas, focinho etc. Assim o Godot gira a cabeça inteira de uma vez;
- braços com origem no ombro e pernas com origem no quadril, para o Godot
  conseguir balançar essas partes por código (sem esqueleto/rig).

Rodar sozinho (a partir da raiz do projeto):
    blender --background --python blender/scripts/gerar_placeholders.py
"""

import math
import pathlib
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import comum  # noqa: E402


# ---------------------------------------------------------------------------
# Formas extras usadas só pelos personagens
# ---------------------------------------------------------------------------

def torno(nome, perfil, base, mat, col, segmentos=14):
    """
    Cria um sólido de revolução (como um vaso feito no torno).
    perfil = lista de (raio, altura) de baixo para cima; raio 0 fecha a ponta.
    Usamos para o corpo em barril e para o chapéu.
    """
    bm = bmesh.new()
    aneis = []
    for raio, z in perfil:
        if raio <= 0.0:
            aneis.append([bm.verts.new((0.0, 0.0, z))])
        else:
            anel = []
            for i in range(segmentos):
                a = 2.0 * math.pi * i / segmentos
                anel.append(bm.verts.new((raio * math.cos(a), raio * math.sin(a), z)))
            aneis.append(anel)
    for baixo, cima in zip(aneis, aneis[1:]):
        if len(baixo) == 1 and len(cima) == 1:
            continue
        if len(baixo) == 1:
            for i in range(segmentos):
                bm.faces.new((baixo[0], cima[(i + 1) % segmentos], cima[i]))
        elif len(cima) == 1:
            for i in range(segmentos):
                bm.faces.new((baixo[i], baixo[(i + 1) % segmentos], cima[0]))
        else:
            for i in range(segmentos):
                j = (i + 1) % segmentos
                bm.faces.new((baixo[i], baixo[j], cima[j], cima[i]))
    # Fecha as pontas que não terminam em raio 0 (ex.: aba do chapéu)
    for anel in (aneis[0], aneis[-1]):
        if len(anel) > 1:
            bm.faces.new(anel)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    malha = bpy.data.meshes.new(nome)
    bm.to_mesh(malha)
    bm.free()
    obj = bpy.data.objects.new(nome, malha)
    col.objects.link(obj)
    obj.data.materials.append(comum.material(mat))
    obj.location = Vector(base)
    return obj


def prisma_xz(nome, pontos, espessura, base, mat, col):
    """
    Cria uma peça achatada a partir de um contorno 2D no plano X-Z (visto de frente),
    com 'espessura' na direção Y. Usamos para as asas da gravata e do laço.
    """
    bm = bmesh.new()
    meio = espessura / 2.0
    frente = [bm.verts.new((x, -meio, z)) for x, z in pontos]
    tras = [bm.verts.new((x, meio, z)) for x, z in pontos]
    bm.faces.new(frente)
    bm.faces.new(list(reversed(tras)))
    n = len(pontos)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((frente[i], frente[j], tras[j], tras[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    malha = bpy.data.meshes.new(nome)
    bm.to_mesh(malha)
    bm.free()
    obj = bpy.data.objects.new(nome, malha)
    col.objects.link(obj)
    obj.data.materials.append(comum.material(mat))
    obj.location = Vector(base)
    return obj


def laco(prefixo, centro, largura, altura, espessura, mat, col):
    """
    Gravata-borboleta / laço: duas asas + um nó no meio.
    Devolve o nó do meio (que vira pai das asas).
    """
    meia = largura / 2.0
    asa = [(0.02, altura * 0.22), (meia, altura / 2.0), (meia, -altura / 2.0), (0.02, -altura * 0.22)]
    no_meio = comum.caixa(f"{prefixo}", (0.05, espessura * 1.3, altura * 0.5), centro, mat, col, origem="centro")
    asa_esq = prisma_xz(f"{prefixo}_Asa_Esq", asa, espessura, centro, mat, col)
    asa_dir = prisma_xz(f"{prefixo}_Asa_Dir", [(-x, z) for x, z in asa], espessura, centro, mat, col)
    return no_meio, [asa_esq, asa_dir]


def cabeca_com_origem_no_pescoco(nome, pescoco, raio, escala, mat, col):
    """
    Cria a esfera da cabeça já com a origem no pescoço (embaixo da cabeça).
    Assim, girar a cabeça no Godot faz ela girar em volta do pescoço, como de verdade.
    """
    cabeca = comum.esfera(nome, raio, pescoco, mat, col, segmentos=16, aneis=10, escala=escala)
    cabeca.data.transform(Matrix.Translation((0.0, 0.0, raio * escala[2] * 0.92)))
    return cabeca


def membro(nome, ombro, comprimento, raio, inclinacao_y, mat, col):
    """
    Braço ou perna: cilindro com a origem na ponta de cima (ombro/quadril)
    e descendo a partir dela. inclinacao_y abre o membro para fora (graus).
    """
    # Girar 180° em X faz o cilindro "crescer para baixo" a partir da origem.
    return comum.cilindro(nome, raio, comprimento, ombro, mat, col, vertices=10, rot=(180.0, inclinacao_y, 0.0))


def novo_empty(nome, col):
    vazio = bpy.data.objects.new(nome, None)
    vazio.empty_display_type = "PLAIN_AXES"
    vazio.empty_display_size = 0.3
    col.objects.link(vazio)
    return vazio


def ponta_do_membro(obj, comprimento):
    """Posição (no mundo) da ponta de baixo de um braço/perna criado com membro()."""
    bpy.context.view_layer.update()
    return obj.matrix_world @ Vector((0.0, 0.0, comprimento))


# ---------------------------------------------------------------------------
# Tito (urso): corpo em barril, marrom e bege
# ---------------------------------------------------------------------------

def criar_tito():
    col = comum.colecao("Tito")
    raiz = novo_empty("Tito", col)
    pais = []  # (filho, pai) — o parentesco é feito no fim, com as posições já atualizadas

    # Pernas (origem no quadril)
    for lado, x in (("Esq", 0.2), ("Dir", -0.2)):
        perna = membro(f"Tito_Perna_{lado}", (x, 0.0, 0.62), 0.52, 0.12, 0.0, "Mat_Tito_Marrom", col)
        pe = comum.caixa(f"Tito_Pe_{lado}", (0.24, 0.34, 0.12), (x, -0.06, 0.0), "Mat_Tito_Bege", col)
        pais += [(perna, raiz), (pe, perna)]

    # Corpo em barril e barriga clara
    corpo = torno("Tito_Corpo", [
        (0.0, 0.56), (0.32, 0.57), (0.41, 0.70), (0.45, 0.90),
        (0.43, 1.10), (0.36, 1.24), (0.20, 1.32), (0.0, 1.34),
    ], (0, 0, 0), "Mat_Tito_Marrom", col)
    barriga = comum.esfera("Tito_Barriga", 1.0, (0.0, -0.38, 0.92), "Mat_Tito_Bege", col, escala=(0.27, 0.08, 0.28))
    rabo = comum.esfera("Tito_Rabo", 0.09, (0.0, 0.42, 0.75), "Mat_Tito_Bege", col, segmentos=8, aneis=6)
    pais += [(corpo, raiz), (barriga, raiz), (rabo, raiz)]

    # Gravata-borboleta no peito
    gravata, asas = laco("Tito_Gravata", (0.0, -0.31, 1.25), 0.30, 0.16, 0.05, "Mat_Tito_Gravata", col)
    pais += [(gravata, raiz)] + [(a, gravata) for a in asas]

    # Braços (origem no ombro) com as mãos na ponta
    for lado, x, inclinacao in (("Esq", 0.46, -12.0), ("Dir", -0.46, 12.0)):
        braco = membro(f"Tito_Braco_{lado}", (x, 0.0, 1.18), 0.52, 0.1, inclinacao, "Mat_Tito_Marrom", col)
        mao = comum.esfera(f"Tito_Mao_{lado}", 0.12, ponta_do_membro(braco, 0.52), "Mat_Tito_Bege", col, segmentos=10, aneis=7)
        pais += [(braco, raiz), (mao, braco)]

    # Cabeça (origem no pescoço) e tudo que fica nela
    cabeca = cabeca_com_origem_no_pescoco("Tito_Cabeca", (0.0, 0.0, 1.32), 0.28, (1.0, 0.95, 0.92), "Mat_Tito_Marrom", col)
    pais.append((cabeca, raiz))
    focinho = comum.esfera("Tito_Focinho", 1.0, (0.0, -0.23, 1.50), "Mat_Tito_Bege", col, escala=(0.14, 0.11, 0.10))
    nariz = comum.esfera("Tito_Nariz", 1.0, (0.0, -0.335, 1.54), "Mat_Tito_Focinho", col, segmentos=10, aneis=6, escala=(0.05, 0.035, 0.035))
    pais += [(focinho, cabeca), (nariz, cabeca)]
    for lado, x in (("Esq", 0.1), ("Dir", -0.1)):
        olho = comum.esfera(f"Tito_Olho_{lado}", 0.045, (x, -0.235, 1.65), "Mat_Olho_Tito", col, segmentos=10, aneis=6)
        sobrancelha = comum.caixa(f"Tito_Sobrancelha_{lado}", (0.09, 0.02, 0.02), (x, -0.25, 1.715), "Mat_Tito_Focinho", col, origem="centro")
        orelha = comum.esfera(f"Tito_Orelha_{lado}", 1.0, (x * 2.0, 0.02, 1.83), "Mat_Tito_Marrom", col, escala=(0.10, 0.045, 0.10))
        orelha_dentro = comum.esfera(f"Tito_Orelha_{lado}_Dentro", 1.0, (x * 2.0, -0.02, 1.83), "Mat_Tito_Bege", col, segmentos=10, aneis=6, escala=(0.06, 0.02, 0.06))
        pais += [(olho, cabeca), (sobrancelha, cabeca), (orelha, cabeca), (orelha_dentro, orelha)]

    # Chapéu pequeno de pizzaiolo (combina com a pizzaria), um pouco torto para dar charme
    chapeu = torno("Tito_Chapeu", [
        (0.0, 0.0), (0.105, 0.0), (0.105, 0.07), (0.14, 0.10), (0.16, 0.15),
        (0.15, 0.20), (0.10, 0.235), (0.0, 0.245),
    ], (0.04, 0.0, 1.81), "Mat_Tito_Chapeu", col, segmentos=12)
    chapeu.rotation_euler = (0.0, math.radians(-10.0), 0.0)
    faixa = comum.cilindro("Tito_Chapeu_Faixa", 0.103, 0.035, (0.0, 0.0, 0.03), "Mat_Tito_Gravata", col, vertices=12)
    pais += [(chapeu, cabeca)]

    bpy.context.view_layer.update()
    # A faixa é posicionada no espaço do chapéu (já inclinado)
    faixa.parent = chapeu
    for filho, pai in pais:
        comum.parentar(filho, pai)
    return raiz, col


# ---------------------------------------------------------------------------
# Pipoca (coelha): corpo esguio, orelhas longas, lilás e branco
# ---------------------------------------------------------------------------

def criar_pipoca():
    col = comum.colecao("Pipoca")
    raiz = novo_empty("Pipoca", col)
    pais = []

    # Pernas finas (origem no quadril) e pés compridos de coelho
    for lado, x in (("Esq", 0.14), ("Dir", -0.14)):
        perna = membro(f"Pipoca_Perna_{lado}", (x, 0.0, 0.70), 0.62, 0.08, 0.0, "Mat_Pipoca_Lilas", col)
        pe = comum.caixa(f"Pipoca_Pe_{lado}", (0.16, 0.36, 0.08), (x, -0.09, 0.0), "Mat_Pipoca_Branco", col)
        pais += [(perna, raiz), (pe, perna)]

    # Corpo esguio
    corpo = torno("Pipoca_Corpo", [
        (0.0, 0.64), (0.20, 0.66), (0.27, 0.78), (0.27, 0.98),
        (0.22, 1.16), (0.14, 1.25), (0.0, 1.27),
    ], (0, 0, 0), "Mat_Pipoca_Lilas", col)
    barriga = comum.esfera("Pipoca_Barriga", 1.0, (0.0, -0.235, 0.92), "Mat_Pipoca_Branco", col, escala=(0.17, 0.06, 0.22))
    rabo = comum.esfera("Pipoca_Rabo", 0.09, (0.0, 0.27, 0.78), "Mat_Pipoca_Branco", col, segmentos=8, aneis=6)
    pais += [(corpo, raiz), (barriga, raiz), (rabo, raiz)]

    # Braços finos com mãos brancas
    for lado, x, inclinacao in (("Esq", 0.29, -8.0), ("Dir", -0.29, 8.0)):
        braco = membro(f"Pipoca_Braco_{lado}", (x, 0.0, 1.15), 0.52, 0.065, inclinacao, "Mat_Pipoca_Lilas", col)
        mao = comum.esfera(f"Pipoca_Mao_{lado}", 0.08, ponta_do_membro(braco, 0.52), "Mat_Pipoca_Branco", col, segmentos=10, aneis=7)
        pais += [(braco, raiz), (mao, braco)]

    # Cabeça (origem no pescoço)
    cabeca = cabeca_com_origem_no_pescoco("Pipoca_Cabeca", (0.0, 0.0, 1.27), 0.22, (1.0, 0.95, 1.05), "Mat_Pipoca_Lilas", col)
    pais.append((cabeca, raiz))
    focinho = comum.esfera("Pipoca_Focinho", 1.0, (0.0, -0.18, 1.43), "Mat_Pipoca_Branco", col, escala=(0.10, 0.07, 0.07))
    nariz = comum.esfera("Pipoca_Nariz", 1.0, (0.0, -0.25, 1.46), "Mat_Pipoca_Bochecha", col, segmentos=10, aneis=6, escala=(0.035, 0.025, 0.025))
    dentes = comum.caixa("Pipoca_Dentes", (0.05, 0.015, 0.04), (0.0, -0.235, 1.36), "Mat_Pipoca_Branco", col)
    pais += [(focinho, cabeca), (nariz, cabeca), (dentes, cabeca)]
    for lado, x, giro in (("Esq", 0.09, -10.0), ("Dir", -0.09, 10.0)):
        olho = comum.esfera(f"Pipoca_Olho_{lado}", 0.04, (x, -0.185, 1.55), "Mat_Olho_Pipoca", col, segmentos=10, aneis=6)
        bochecha = comum.esfera(f"Pipoca_Bochecha_{lado}", 1.0, (x * 1.4, -0.165, 1.42), "Mat_Pipoca_Bochecha", col, segmentos=10, aneis=6, escala=(0.055, 0.03, 0.04))
        # Orelhas longas, levemente abertas para os lados
        orelha = comum.esfera(f"Pipoca_Orelha_{lado}", 1.0, (x, 0.02, 1.83), "Mat_Pipoca_Lilas", col, escala=(0.07, 0.035, 0.25), rot=(0.0, giro, 0.0))
        orelha_dentro = comum.esfera(f"Pipoca_Orelha_{lado}_Dentro", 1.0, (x, -0.005, 1.83), "Mat_Pipoca_Branco", col, segmentos=10, aneis=6, escala=(0.04, 0.02, 0.19), rot=(0.0, giro, 0.0))
        pais += [(olho, cabeca), (bochecha, cabeca), (orelha, cabeca), (orelha_dentro, orelha)]

    # Laço rosa no alto da cabeça, na frente das orelhas
    no_laco, asas = laco("Pipoca_Laco", (0.0, -0.08, 1.68), 0.26, 0.13, 0.04, "Mat_Pipoca_Laco", col)
    pais += [(no_laco, cabeca)] + [(a, no_laco) for a in asas]

    bpy.context.view_layer.update()
    for filho, pai in pais:
        comum.parentar(filho, pai)
    return raiz, col


# ---------------------------------------------------------------------------

def objetos_da_hierarquia(raiz):
    return [raiz] + list(raiz.children_recursive)


def contar_triangulos(objetos):
    total = 0
    for obj in objetos:
        if obj.type == "MESH":
            obj.data.calc_loop_triangles()
            total += len(obj.data.loop_triangles)
    return total


def exportar_personagem(caminho, raiz):
    """
    Exporta só a hierarquia de um personagem.
    Diferente do cenário, aqui NÃO exportamos a Collection como nó: o Empty
    "Tito"/"Pipoca" já é o pai de tudo, e a Collection com o mesmo nome criaria
    um nó repetido ("Tito" dentro de "Tito"), deixando os caminhos no Godot confusos.
    """
    caminho.parent.mkdir(parents=True, exist_ok=True)
    for obj in bpy.context.scene.objects:
        obj.select_set(False)
    for obj in objetos_da_hierarquia(raiz):
        obj.select_set(True)
    bpy.ops.export_scene.gltf(export_image_format="NONE",  # texturas ficam fora do .glb (materiais .tres no Godot)
        filepath=str(caminho),
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
        export_cameras=False,
        export_lights=False,
        export_extras=False,
        export_animations=True,
        export_hierarchy_full_collections=False,
    )
    print(f"[placeholders] exportado: {caminho}")


def gerar():
    comum.limpar_cena()
    tito, _ = criar_tito()
    pipoca, _ = criar_pipoca()
    bpy.context.view_layer.update()

    for raiz in (tito, pipoca):
        objs = objetos_da_hierarquia(raiz)
        print(f"[placeholders] {raiz.name}: {len(objs)} objetos, {contar_triangulos(objs)} triângulos")

    comum.salvar_blend(comum.PASTA_BLENDER / "personagens_placeholder.blend")
    exportar_personagem(comum.PASTA_PERSONAGENS / "tito.glb", tito)
    exportar_personagem(comum.PASTA_PERSONAGENS / "pipoca.glb", pipoca)


if __name__ == "__main__":
    gerar()
