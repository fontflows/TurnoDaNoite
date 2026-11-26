"""
dev_render_previews.py — FERRAMENTA DE DESENVOLVIMENTO (não faz parte do jogo).

Gera imagens de prévia do cenário e dos personagens para a página
docs/progresso, usando o motor Workbench (rápido e funciona sem placa de vídeo boa).

Uso (a partir da raiz do projeto):
  blender --background --python blender/scripts/dev_render_previews.py -- <alvos> [fase=N]
Alvos: planta, comodos, olhos, personagens   (ex.: -- planta comodos fase=2)
"""

import math
import pathlib
import sys
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import comum  # noqa: E402

CARIMBO = datetime.now().strftime("%Y-%m-%d_%H%M")


def preparar_cena():
    comum.limpar_cena()
    cena = bpy.context.scene
    # EEVEE mostra as texturas COM a tinta dos materiais (o Workbench ignoraria a tinta).
    cena.render.engine = "BLENDER_EEVEE"
    cena.eevee.taa_render_samples = 16
    mundo = bpy.data.worlds.new("Mundo_Previa")
    mundo.use_nodes = True
    fundo = mundo.node_tree.nodes.get("Background")
    fundo.inputs["Color"].default_value = (0.75, 0.75, 0.78, 1.0)
    fundo.inputs["Strength"].default_value = 1.0
    cena.world = mundo
    cena.render.resolution_x = 1600
    cena.render.resolution_y = 1000
    cena.render.film_transparent = False
    cena.view_settings.view_transform = "Standard"  # cores iguais às da paleta
    cena.view_settings.exposure = -0.4  # a luz ambiente da prévia é forte; isto evita estourar
    sh = cena.display.shading
    sh.light = "STUDIO"
    sh.color_type = "TEXTURE"  # mostra as texturas (materiais sem textura aparecem na cor deles)
    sh.show_shadows = True
    sh.shadow_intensity = 0.35
    sh.show_cavity = True
    sh.cavity_type = "WORLD"
    sh.show_object_outline = True
    sh.background_type = "VIEWPORT"
    sh.background_color = (0.04, 0.035, 0.045)
    cena.display.light_direction = (0.35, -0.45, 0.82)
    return cena


def anexar(caminho_blend):
    """Traz todos os objetos de um .blend para a cena atual (cópia, não link)."""
    caminho = comum.PASTA_BLENDER / caminho_blend
    if not caminho.exists():
        print(f"[render] AVISO: {caminho} não existe, pulando")
        return []
    with bpy.data.libraries.load(str(caminho), link=False) as (origem, destino):
        destino.objects = list(origem.objects)
    objs = [o for o in destino.objects if o is not None]
    for o in objs:
        bpy.context.scene.collection.objects.link(o)
    return objs


def esconder(objs, filtro):
    for o in objs:
        if filtro(o):
            o.hide_render = True


def camera(nome, posicao, alvo, lente=24.0, orto=None):
    cam_dados = bpy.data.cameras.new(nome)
    if orto:
        cam_dados.type = "ORTHO"
        cam_dados.ortho_scale = orto
    else:
        cam_dados.lens = lente
    cam_dados.clip_end = 500
    cam = bpy.data.objects.new(nome, cam_dados)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = Vector(posicao)
    direcao = Vector(alvo) - Vector(posicao)
    cam.rotation_euler = direcao.to_track_quat("-Z", "Y").to_euler()
    return cam


def render(cam, slug, legenda, fase):
    cena = bpy.context.scene
    cena.camera = cam
    comum.PASTA_IMAGENS.mkdir(parents=True, exist_ok=True)
    caminho = comum.PASTA_IMAGENS / f"{CARIMBO}_{slug}.png"
    cena.render.filepath = str(caminho)
    bpy.ops.render.render(write_still=True)
    comum.registrar_imagem(caminho, legenda, fase)
    print(f"[render] {caminho.name}")


def eh_teto_ou_colisao(o):
    return o.name.startswith("Teto_") or o.name.endswith("-colonly")


# Cômodos: nome bonito, retângulo (x0, x1, z0, z1) da planta
COMODOS = [
    ("Salão de festas", "salao", (10, 30, 0, 13)),
    ("Cozinha", "cozinha", (0, 10, 0, 13)),
    ("Depósito / bastidores", "deposito", (30, 40, 0, 13)),
    ("Fliperama", "fliperama", (0, 14, 16, 27)),
    ("Banheiros", "banheiros", (14, 22, 16, 27)),
    ("Sala de segurança", "sala_seguranca", (22, 30, 16, 27)),
    ("Recepção", "recepcao", (30, 40, 16, 30)),
    ("Corredor principal", "corredor", (0, 40, 13, 16)),
]


def alvo_planta(fase):
    objs = anexar("predio.blend") + anexar("moveis.blend")
    esconder(objs, eh_teto_ou_colisao)
    # A escala ortográfica vale para a largura; 1600x1000 -> altura = 52 * 10/16 = 32,5 m (prédio tem 30).
    cam = camera("Cam_Planta", comum.p(20, 15, 60), comum.p(20, 15, 0), orto=52)
    render(cam, "planta_vista_de_cima", "Planta vista de cima (sem teto), Blender", fase)
    cam = camera("Cam_Iso", comum.p(44, 44, 34), comum.p(20, 14, 0), lente=30)
    render(cam, "planta_perspectiva", "Visão geral em perspectiva (sem teto), Blender", fase)
    return objs


def alvo_v2(fase):
    """Mapa da V2: junta todos os blender/v2_*.blend que existirem."""
    objs = []
    for arq in sorted(comum.PASTA_BLENDER.glob("v2_*.blend")):
        objs += anexar(arq.name)
    esconder(objs, eh_teto_ou_colisao)
    # 60 x 45 m: escala ortográfica 74 -> 74 x 46 m na imagem 1600 x 1000
    cam = camera("Cam_Planta_V2", (0, 0, 80), (0, 0, 0), orto=74)
    render(cam, "v2_planta_vista_de_cima", "V2: planta nova vista de cima (sem teto), Blender", fase)
    cam = camera("Cam_Iso_V2", (34, -46, 44), (0, -1, 0), lente=28)
    render(cam, "v2_perspectiva", "V2: visão geral em perspectiva (sem teto), Blender", fase)


def alvo_comodos(fase):
    objs = anexar("predio.blend") + anexar("moveis.blend")
    esconder(objs, eh_teto_ou_colisao)
    for titulo, slug, (x0, x1, z0, z1) in COMODOS:
        cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        tamanho = max(x1 - x0, z1 - z0)
        # Câmera alta, no canto sudeste do cômodo, olhando para o centro (vista em corte).
        pos = comum.p(x1 + tamanho * 0.15, z1 + tamanho * 0.35, 3.0 + tamanho * 0.75)
        cam = camera(f"Cam_{slug}", pos, comum.p(cx, cz, 0.6), lente=22)
        render(cam, f"comodo_{slug}", f"{titulo}: vista em corte, Blender", fase)


def alvo_olhos(fase):
    """Vistas na altura dos olhos (com teto), como o jogador veria com tudo aceso."""
    objs = anexar("predio.blend") + anexar("moveis.blend")
    esconder(objs, lambda o: o.name.endswith("-colonly"))
    vistas = [
        ("olhos_salao_palco", "Salão visto da porta do corredor, olhando o palco", (25, 12.3), (19, 2)),
        ("olhos_sala_seguranca", "Sala de segurança: posição inicial do jogador", (27.8, 21.5), (22, 21.5)),
        ("olhos_corredor", "Corredor principal visto do oeste", (0.8, 14.5), (40, 14.5)),
        ("olhos_fliperama", "Fliperama visto da porta", (7, 16.6), (5, 25)),
    ]
    for slug, legenda, (x, z), (ax, az) in vistas:
        cam = camera(f"Cam_{slug}", comum.p(x, z, 1.65), comum.p(ax, az, 1.2), lente=18)
        render(cam, slug, legenda + ", Blender", fase)


def alvo_personagens(fase):
    objs = anexar("personagens_placeholder.blend")
    if not objs:
        return
    esconder(objs, lambda o: o.name.endswith("-colonly"))
    bpy.context.scene.render.resolution_x = 1400
    bpy.context.scene.render.resolution_y = 1000
    # Chão simples para dar referência de escala.
    comum.caixa("Chao_Referencia", (12, 12, 0.02), (0, 0, -0.02), "Mat_Piso_Concreto")

    raizes = [o for o in objs if o.parent is None and o.name in ("Tito", "Pipoca")]
    # Coloca os dois lado a lado para as fotos em grupo, guardando a posição original.
    for nome in ("Tito", "Pipoca"):
        raiz = next((o for o in raizes if o.name == nome), None)
        if raiz is None:
            continue
        outros = [o for o in raizes if o is not raiz]
        for o in outros:
            o.hide_render = True
            for f in o.children_recursive:
                f.hide_render = True
        alvo = Vector((raiz.location.x, raiz.location.y, 1.0))
        frente = camera(f"Cam_{nome}_Frente", alvo + Vector((0, -5.2, 0.3)), alvo, lente=40)
        render(frente, f"personagem_{nome.lower()}_frente", f"{nome} (placeholder) de frente, Blender", fase)
        lado = camera(f"Cam_{nome}_Lado", alvo + Vector((5.2, 0, 0.3)), alvo, lente=40)
        render(lado, f"personagem_{nome.lower()}_lado", f"{nome} (placeholder) de lado, Blender", fase)
        tres_quartos = camera(f"Cam_{nome}_34", alvo + Vector((3.2, -3.8, 0.9)), alvo, lente=40)
        render(tres_quartos, f"personagem_{nome.lower()}_tres_quartos", f"{nome} (placeholder) em 3/4, Blender", fase)
        for o in outros:
            o.hide_render = False
            for f in o.children_recursive:
                f.hide_render = False


def main():
    args = comum.argumentos_do_script()
    fase = 2
    alvos = []
    for a in args:
        if a.startswith("fase="):
            valor = a.split("=", 1)[1]
            fase = int(valor) if valor.isdigit() else valor  # "2" -> 2; "V2.3" -> "V2.3"
        else:
            alvos.append(a)
    alvos = alvos or ["planta"]
    funcoes = {"v2": alvo_v2, "planta": alvo_planta, "comodos": alvo_comodos, "olhos": alvo_olhos, "personagens": alvo_personagens}
    for alvo in alvos:
        preparar_cena()
        funcoes[alvo](fase)


if __name__ == "__main__":
    main()
