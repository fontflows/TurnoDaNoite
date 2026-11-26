"""
moveis_v2_enchimento.py — acha os ESPAÇOS VAZIOS GRANDES do mapa da V2 e enche com grupos
de objetos que combinam com cada cômodo (regra da V2.1: um ponto de interesse a cada 4-6 m).

Como funciona:
  1. Junta os móveis já gerados (v2_publico, v2_diversao, v2_servico) só para medir.
  2. Numa grade de 1 m, mede a distância de cada ponto até a coisa mais próxima
     (móvel, decoração, arte, luz, som). Mais de 3 m = espaço vazio grande.
  3. Coloca um grupo temático no ponto mais vazio, mede de novo, repete.
  4. Grava o relatório em docs/progresso/relatorio_vazios.txt e exporta só os objetos novos
     em godot/assets/cenario/v2_enchimento.glb.
Rodar DEPOIS dos outros geradores:  blender --background --python blender/scripts/moveis_v2_enchimento.py
"""

import math
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import bpy  # noqa: E402

import comum  # noqa: E402
import moveis_v2_diversao as d  # noqa: E402
import planta_v2  # noqa: E402

LIMITE_VAZIO = 3.0       # metros até o ponto de interesse mais próximo
MARGEM_PAREDE = 0.8      # não mede (nem enche) colado na parede
NAO_ENCHER = {"Corredor_Principal", "Corredor_Festas", "Corredor_Funcionarios", "Sala_Seguranca", "Armario_Limpeza"}
SORTE = random.Random(4242)
IGNORAR = ("Piso_", "Teto_", "Parede_", "Batente", "Colisao", "Teias", "Decal__")
RELATORIO = comum.RAIZ / "docs" / "progresso" / "relatorio_vazios.txt"

# Que tipo de "bagunça" combina com cada cômodo
TEMAS = {
    "Oficina": ["tambor", "carcaca", "caixas", "pneus"],
    "Cozinha": ["sacos", "caixas_pizza", "carrinho", "lixeira"],
    "Camara_Fria": ["caixas", "sacos"],
    "Banheiros": ["lixeira", "balde"],
    "Deposito": ["caixas", "tambor", "coberto"],
    "Sala_Eletrica": ["carretel", "tambor", "caixas"],
    "Fliperama": ["cadeiras", "baloes", "caixas_premios"],
    "Recepcao": ["banco", "cone", "baloes", "display"],
    "Salao": ["cadeiras", "baloes", "presentes"],
    "Festa_Estrelas": ["baloes", "presentes"],
    "Festa_Piratas": ["barril", "presentes"],
    "Festa_Princesas": ["baloes", "presentes"],
    "Vestiario": ["caixas", "balde"],
    "Sala_Gerente": ["caixas"],
    "Arquivo": ["caixas"],
    "Copa": ["cadeiras", "caixas", "lixeira"],
}


def anexar(arquivo):
    caminho = comum.PASTA_BLENDER / arquivo
    if not caminho.exists():
        return []
    with bpy.data.libraries.load(str(caminho), link=False) as (origem, destino):
        destino.objects = list(origem.objects)
    objs = [o for o in destino.objects if o is not None]
    for o in objs:
        bpy.context.scene.collection.objects.link(o)
    return objs


def pontos_de_interesse(objetos):
    """Retângulos (x0, x1, z0, z1) na planta de tudo que conta como ponto de interesse."""
    rets = []
    for o in objetos:
        if o.name.startswith(IGNORAR) or o.name.endswith("-colonly") or o.parent is not None:
            continue
        if o.type == "EMPTY":
            if o.name.startswith(("Luz__", "Som__", "Item__", "Pista__", "Esconderijo__")):
                x, z = o.matrix_world.translation.x + 30, 22.5 - o.matrix_world.translation.y
                rets.append((x, x, z, z))
            continue
        if o.type == "MESH":
            rets.append(comum.bbox_planta(o))
    return rets


def distancia(x, z, ret):
    x0, x1, z0, z1 = ret
    dx = max(x0 - x, 0.0, x - x1)
    dz = max(z0 - z, 0.0, z - z1)
    return math.hypot(dx, dz)


def celulas_vazias(comodo, rets):
    nome, _, x0, x1, z0, z1, _ = comodo
    vazias = []
    x = x0 + MARGEM_PAREDE
    while x <= x1 - MARGEM_PAREDE:
        z = z0 + MARGEM_PAREDE
        while z <= z1 - MARGEM_PAREDE:
            dist = min((distancia(x, z, r) for r in rets), default=99.0)
            if dist > LIMITE_VAZIO:
                vazias.append((dist, x, z))
            z += 1.0
        x += 1.0
    return sorted(vazias, reverse=True)


def livre_para_encher(x, z):
    """Não enche em cima de pontos de jogo nem perto de portas (a navegação precisa passar)."""
    P = planta_v2.PONTOS
    pontos = [P["spawn_jogador"][:2], P["palco_tito"][:2], P["palco_pipoca"][:2]] + P["patrulha"] + P["pilhas"] + P["fichas"]
    if any(math.hypot(x - px, z - pz) < 2.4 for px, pz in pontos):
        return False
    for eixo, fixo, centro, larg, tipo, _ in planta_v2.PORTAS:
        cx, cz = (centro, fixo) if eixo == "z" else (fixo, centro)
        if math.hypot(x - cx, z - cz) < 2.2:
            return False
    return True


# ---------------------------------------------------------------------------
# Grupos de objetos (simples e baratos; um objeto + uma colisão por grupo)
# ---------------------------------------------------------------------------

def grupo(tipo, col, x, z, n):
    lote = d.Lote()
    alto = 0.0
    if tipo == "tambor":
        for i in range(SORTE.randint(2, 3)):
            lote.cilindro(0.3, 0.9, (i * 0.62 - 0.3, SORTE.uniform(-0.15, 0.15), 0), "Mat_Metal_Enferrujado", lados=10)
        alto = 0.9
    elif tipo in ("caixas", "caixas_premios"):
        for i in range(SORTE.randint(3, 6)):
            lote.caixa((0.55, 0.45, 0.4), (SORTE.uniform(-0.4, 0.4), SORTE.uniform(-0.3, 0.3), (i % 3) * 0.4), "Mat_Papelao_Caixa",
                       rot=(0, 0, SORTE.uniform(-20, 20)))
        alto = 1.2
    elif tipo == "carcaca":
        lote.caixa((0.7, 0.5, 0.8), (0, 0, 0), "Mat_Metal_Pintado_Verde", rot=(0, 15, 25))
        lote.esfera(0.25, (0.5, 0.2, 0.25), "Mat_Plastico_Branco", seg=8, aneis=5)
        lote.tubo([(-0.3, 0.3, 0.1), (-0.7, 0.6, 0.05), (-0.9, 0.5, 0.02)], 0.02, "Mat_Fio_Vermelho")
        alto = 0.9
    elif tipo == "pneus":
        for i in range(3):
            lote.cilindro(0.35, 0.2, (0, 0, i * 0.2), "Mat_Plastico_Preto", lados=10)
        alto = 0.6
    elif tipo == "sacos":
        for i in range(SORTE.randint(3, 5)):
            lote.esfera(0.32, (SORTE.uniform(-0.4, 0.4), SORTE.uniform(-0.2, 0.2), 0.18 + (i // 3) * 0.3), "Mat_Lencol_Branco",
                        escala=(1.2, 0.8, 0.5), seg=8, aneis=5)
        alto = 0.7
    elif tipo == "caixas_pizza":
        for i in range(SORTE.randint(5, 9)):
            lote.caixa((0.42, 0.42, 0.05), (SORTE.uniform(-0.05, 0.05), SORTE.uniform(-0.05, 0.05), i * 0.05), "Mat_Papelao_Caixa",
                       rot=(0, 0, SORTE.uniform(-15, 15)))
        alto = 0.45
    elif tipo == "carrinho":
        lote.caixa((0.9, 0.55, 0.04), (0, 0, 0.85), "Mat_Inox")
        lote.caixa((0.9, 0.55, 0.04), (0, 0, 0.3), "Mat_Inox")
        for sx in (-0.42, 0.42):
            for sy in (-0.25, 0.25):
                lote.cilindro(0.015, 0.85, (sx, sy, 0), "Mat_Metal_Cinza", lados=4)
        alto = 0.9
    elif tipo in ("lixeira", "balde"):
        lote.cilindro(0.25 if tipo == "lixeira" else 0.16, 0.65 if tipo == "lixeira" else 0.3, (0, 0, 0),
                      "Mat_Plastico_Verde" if tipo == "lixeira" else "Mat_Plastico_Azul", lados=10)
        for i in range(3):
            lote.caixa((0.15, 0.15, 0.08), (SORTE.uniform(-0.5, 0.5), SORTE.uniform(-0.4, 0.4), 0), "Mat_Papel_Branco",
                       rot=(SORTE.uniform(0, 30), 0, SORTE.uniform(0, 90)))
        alto = 0.65
    elif tipo == "coberto":
        lote.caixa((1.3, 0.8, 1.1), (0, 0, 0), "Mat_Lencol_Branco")
        lote.caixa((1.4, 0.9, 0.12), (0, 0, 0), "Mat_Lencol_Branco")
        alto = 1.1
    elif tipo == "carretel":
        lote.cilindro(0.55, 0.08, (0, 0, 0.55), "Mat_Madeira_Velha", rot=(90, 0, 0), lados=12)
        lote.cilindro(0.55, 0.08, (0, 0.6, 0.55), "Mat_Madeira_Velha", rot=(90, 0, 0), lados=12)
        lote.cilindro(0.35, 0.55, (0, 0.05, 0.55), "Mat_Plastico_Preto", rot=(-90, 0, 0), lados=12)
        alto = 1.1
    elif tipo == "cadeiras":
        for i in range(SORTE.randint(3, 5)):
            lote.caixa((0.42, 0.42, 0.04), (0, 0, 0.44 + i * 0.1), "Mat_Plastico_Vermelho", rot=(0, 0, SORTE.uniform(-8, 8)))
            lote.caixa((0.42, 0.04, 0.45), (0, 0.2, 0.46 + i * 0.1), "Mat_Plastico_Vermelho")
        lote.caixa((0.42, 0.42, 0.04), (0.9, 0.2, 0.0), "Mat_Plastico_Amarelo", rot=(80, 0, 30))   # uma tombada
        alto = 1.0
    elif tipo == "baloes":
        for i in range(SORTE.randint(3, 6)):
            mat = SORTE.choice(["Mat_Plastico_Vermelho", "Mat_Plastico_Azul", "Mat_Plastico_Amarelo", "Mat_Plastico_Verde", "Mat_Plastico_Rosa"])
            lote.esfera(0.2, (SORTE.uniform(-0.6, 0.6), SORTE.uniform(-0.5, 0.5), 0.08), mat, escala=(1, 1, 0.45), seg=8, aneis=5)
        alto = 0.0   # balões murchos no chão: sem colisão
    elif tipo == "presentes":
        for i in range(SORTE.randint(2, 4)):
            mat = SORTE.choice(["Mat_Plastico_Rosa", "Mat_Plastico_Azul", "Mat_Plastico_Amarelo", "Mat_Plastico_Lilas"])
            s = SORTE.uniform(0.25, 0.45)
            lote.caixa((s, s, s * 0.8), (SORTE.uniform(-0.4, 0.4), SORTE.uniform(-0.4, 0.4), 0), mat, rot=(0, 0, SORTE.uniform(0, 45)))
        alto = 0.0
    elif tipo == "banco":
        lote.caixa((1.6, 0.45, 0.06), (0, 0, 0.42), "Mat_Plastico_Vermelho")
        lote.caixa((1.6, 0.06, 0.4), (0, 0.2, 0.48), "Mat_Plastico_Vermelho")
        for sx in (-0.7, 0.7):
            lote.caixa((0.06, 0.4, 0.42), (sx, 0, 0), "Mat_Metal_Escuro")
        alto = 0.9
    elif tipo == "cone":
        lote.cilindro(0.18, 0.55, (0, 0, 0), "Mat_Plastico_Amarelo", lados=8, raio_topo=0.03)
        lote.caixa((0.4, 0.4, 0.03), (0, 0, 0), "Mat_Plastico_Amarelo")
        alto = 0.0
    elif tipo == "display":
        lote.caixa((0.7, 0.05, 1.5), (0, 0, 0), "Mat_Papelao_Caixa", rot=(-6, 0, 0))   # display de papelão do Tito
        lote.esfera(0.25, (0, -0.05, 1.55), "Mat_Tito_Marrom", seg=8, aneis=5)
        alto = 1.6
    elif tipo == "barril":
        lote.cilindro(0.32, 0.85, (0, 0, 0), "Mat_Madeira_Velha", lados=10)
        lote.cilindro(0.33, 0.06, (0, 0, 0.6), "Mat_Metal_Escuro", lados=10)
        alto = 0.85
    obj = lote.objeto(f"Enchimento_{tipo}_{n:02d}", col)
    filhos = []
    if alto > 0.3:
        filhos.append(d.colisao(f"Enchimento_{tipo}_{n:02d}", (1.3, 1.0, alto), (0, 0, 0), col))
    return d.montar(obj, filhos, x, z, 0.0, "sul", SORTE.uniform(0, 360))


def gerar():
    comum.limpar_cena()
    for nome, (cor, em) in d.CORES_DIVERSAO.items():
        comum.material(nome, cor, em)
    medidos = []
    for arq in ("v2_publico.blend", "v2_diversao.blend", "v2_servico.blend"):
        medidos += anexar(arq)
    bpy.context.view_layer.update()
    rets = pontos_de_interesse(medidos)
    linhas = ["Espaços vazios grandes (mais de %.0f m até o ponto de interesse mais próximo)" % LIMITE_VAZIO, ""]
    antes = {}
    for c in planta_v2.COMODOS:
        antes[c[0]] = len(celulas_vazias(c, rets))
    # Remove os objetos medidos: este arquivo só exporta o enchimento.
    for o in medidos:
        bpy.data.objects.remove(o, do_unlink=True)
    n = 0
    novos_rets = list(rets)
    for c in planta_v2.COMODOS:
        nome = c[0]
        if nome in NAO_ENCHER or nome not in TEMAS:
            continue
        col = comum.colecao(nome)
        for _ in range(12):
            vazias = [v for v in celulas_vazias(c, novos_rets) if livre_para_encher(v[1], v[2])]
            if not vazias:
                break
            _, x, z = vazias[0]
            n += 1
            obj = grupo(SORTE.choice(TEMAS[nome]), col, x, z, n)
            novos_rets.append((x - 0.7, x + 0.7, z - 0.6, z + 0.6))
    depois = {c[0]: len(celulas_vazias(c, novos_rets)) for c in planta_v2.COMODOS}
    for c in planta_v2.COMODOS:
        nome = c[0]
        obs = " (não enchido: corredor/sala pequena)" if nome in NAO_ENCHER else ""
        linhas.append(f"{nome:24s} antes: {antes[nome]:3d} m²   depois: {depois[nome]:3d} m²{obs}")
    linhas += ["", f"Grupos de enchimento criados: {n}",
               "Pontos que continuam vazios ficam perto de portas, pontos de patrulha, pilhas ou fichas (de propósito)."]
    RELATORIO.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print("\n".join(linhas))
    bpy.context.view_layer.update()
    problemas = comum.conferir_areas_livres_v2()
    for p in problemas:
        print("PROBLEMA:", p)
    if problemas:
        raise RuntimeError(f"{len(problemas)} problema(s) de área livre")
    comum.salvar_blend(comum.PASTA_BLENDER / "v2_enchimento.blend")
    comum.exportar_glb(comum.PASTA_CENARIO / "v2_enchimento.glb")


if __name__ == "__main__":
    gerar()
