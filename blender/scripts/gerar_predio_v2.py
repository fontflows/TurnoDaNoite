"""
gerar_predio_v2.py — a "casca" da pizzaria da V2 (60 x 45 m): pisos, paredes com vãos de
porta e a janela aramada, tetos (cada cômodo na sua altura), palco com escada, portas
especiais (que a lógica do Godot vai controlar) e as colisões.

Tudo vem de blender/scripts/planta_v2.py (fonte única da planta).
Saída: blender/v2_predio.blend e godot/assets/cenario/v2_predio.glb
Rodar sozinho:  blender --background --python blender/scripts/gerar_predio_v2.py
"""

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import bpy  # noqa: E402

import comum  # noqa: E402
import planta_v2  # noqa: E402
from gerar_predio import MalhaMultiMaterial  # noqa: E402  (mesma ferramenta da V1)

ESPESSURA = 0.2
ALTURA_FAIXA = 1.1
ALTURA_PORTA = 2.2
ALTURA_PALCO = 0.6

# Materiais de cada cômodo: (piso, faixa de baixo da parede, parede de cima)
VISUAL = {
    "Salao": ("Mat_Carpete_Fliperama", "Mat_Faixa_Vermelha", "Mat_Papel_Parede_Festa"),
    "Oficina": ("Mat_Concreto_Sujo", "Mat_Faixa_Cinza", "Mat_Parede_Concreto"),
    "Cozinha": ("Mat_Chapa_Antiderrapante", "Mat_Faixa_Azulejo_Branco", "Mat_Azulejo_Cozinha"),
    "Camara_Fria": ("Mat_Chapa_Antiderrapante", "Mat_Metal_Cinza", "Mat_Metal_Cinza"),
    "Banheiros": ("Mat_Piso_Azulejo_Azul", "Mat_Faixa_Azul_Claro", "Mat_Faixa_Azulejo_Branco"),
    "Corredor_Principal": ("Mat_Piso_Quadriculado", "Mat_Faixa_Azul_Petroleo", "Mat_Parede_Creme"),
    "Deposito": ("Mat_Concreto_Sujo", "Mat_Faixa_Cinza", "Mat_Tijolo_Aparente"),
    "Sala_Eletrica": ("Mat_Concreto_Sujo", "Mat_Faixa_Cinza", "Mat_Parede_Concreto"),
    "Fliperama": ("Mat_Carpete_Fliperama", "Mat_Faixa_Roxa", "Mat_Parede_Creme"),
    "Recepcao": ("Mat_Piso_Quadriculado", "Mat_Faixa_Amarela", "Mat_Parede_Creme"),
    "Corredor_Festas": ("Mat_Piso_Quadriculado", "Mat_Faixa_Vermelha", "Mat_Papel_Parede_Festa"),
    "Festa_Estrelas": ("Mat_Carpete_Fliperama_Gasto", "Mat_Faixa_Azul_Petroleo", "Mat_Papel_Parede_Festa"),
    "Festa_Piratas": ("Mat_Madeira_Envernizada", "Mat_Faixa_Marrom", "Mat_Parede_Creme"),
    "Festa_Princesas": ("Mat_Carpete_Fliperama_Gasto", "Mat_Faixa_Rosa", "Mat_Papel_Parede_Festa"),
    "Corredor_Funcionarios": ("Mat_Concreto_Sujo", "Mat_Faixa_Cinza", "Mat_Parede_Creme"),
    "Vestiario": ("Mat_Piso_Azulejo_Azul", "Mat_Faixa_Azul_Claro", "Mat_Parede_Creme"),
    "Sala_Gerente": ("Mat_Madeira_Envernizada", "Mat_Faixa_Marrom", "Mat_Parede_Creme"),
    "Sala_Seguranca": ("Mat_Piso_Quadriculado", "Mat_Faixa_Verde_Oliva", "Mat_Parede_Creme"),
    "Armario_Limpeza": ("Mat_Concreto_Sujo", "Mat_Faixa_Cinza", "Mat_Parede_Concreto"),
    "Arquivo": ("Mat_Concreto_Sujo", "Mat_Faixa_Cinza", "Mat_Parede_Creme"),
    "Copa": ("Mat_Piso_Quadriculado", "Mat_Faixa_Amarela", "Mat_Parede_Creme"),
}


# ---------------------------------------------------------------------------
# Consultas à planta
# ---------------------------------------------------------------------------

def comodo_em(x, z):
    for c in planta_v2.COMODOS:
        nome, _, x0, x1, z0, z1, _ = c
        if x0 - 1e-6 <= x <= x1 + 1e-6 and z0 - 1e-6 <= z <= z1 + 1e-6:
            return c
    return None


def blender_para_planta(v):
    return v.x + 30.0, 22.5 - v.y


def material_da_face(centro, normal):
    """Cor da face olhando para o cômodo para onde ela está virada (faixa embaixo, parede em cima)."""
    if abs(normal.z) > 0.5:
        return "Mat_Parede_Creme"
    x, z = blender_para_planta(centro + normal * 0.15)
    c = comodo_em(x, z)
    if c is None:
        return "Mat_Parede_Externa"
    _, faixa, parede = VISUAL[c[0]]
    return faixa if centro.z < ALTURA_FAIXA - 1e-4 else parede


# ---------------------------------------------------------------------------
# Paredes: saem das bordas dos cômodos (sem duplicar as compartilhadas)
# ---------------------------------------------------------------------------

def linhas_de_parede():
    """Devolve {(eixo, fixo): [(a, b), ...]} com todas as bordas de cômodo, já unidas."""
    linhas = {}
    for _, _, x0, x1, z0, z1, _ in planta_v2.COMODOS:
        for fixo, a, b, eixo in ((z0, x0, x1, "z"), (z1, x0, x1, "z"), (x0, z0, z1, "x"), (x1, z0, z1, "x")):
            linhas.setdefault((eixo, float(fixo)), []).append((float(a), float(b)))
    # Corta cada linha nos pontos de todos os trechos, para depois remover duplicados.
    for chave, trechos in linhas.items():
        pontos = sorted({p for t in trechos for p in t})
        cobertos = []
        for a, b in zip(pontos[:-1], pontos[1:]):
            meio = (a + b) / 2
            if any(t0 - 1e-6 <= meio <= t1 + 1e-6 for t0, t1 in trechos):
                cobertos.append((a, b))
        linhas[chave] = cobertos
    return linhas


def vaos_na_linha(eixo, fixo):
    """
    Vãos de porta e janela que cortam esta linha de parede: [(a, b, z_baixo, z_cima)].
    A "catraca" (porta da frente, trancada) também tem vão: as portas de vidro com a corrente
    ficam DENTRO dele. Antes a parede era cheia e só o cadeado e a corrente apareciam,
    saindo da parede ("cadeado numa parede sem porta"). Quem bloqueia a passagem é a
    colisão da própria porta (Recepcao_Porta_Frente, em moveis_v2_publico.py).
    """
    vaos = []
    for e, f, centro, larg, tipo, _ in planta_v2.PORTAS:
        if e == eixo and abs(f - fixo) < 1e-6:
            vaos.append((centro - larg / 2, centro + larg / 2, 0.0, ALTURA_PORTA))
    for e, f, centro, larg, _ in planta_v2.JANELAS:
        if e == eixo and abs(f - fixo) < 1e-6:
            vaos.append((centro - larg / 2, centro + larg / 2, 1.0, 1.9))
    return vaos


def altura_da_parede(eixo, fixo, meio):
    """A parede vai até o teto mais alto dos dois cômodos que ela separa."""
    alturas = []
    for d in (-0.3, 0.3):
        c = comodo_em(meio, fixo + d) if eixo == "z" else comodo_em(fixo + d, meio)
        if c:
            alturas.append(c[6])
    return max(alturas) if alturas else 3.2


def nome_da_parede(eixo, fixo, meio):
    lados = []
    for d in (-0.3, 0.3):
        c = comodo_em(meio, fixo + d) if eixo == "z" else comodo_em(fixo + d, meio)
        lados.append(c[0] if c else "Externa")
    return "Parede_" + "__".join(sorted(set(lados)))


def caixa_blender(eixo, fixo, a, b, meia=ESPESSURA / 2):
    if eixo == "z":
        p0, p1 = comum.p2(a, fixo), comum.p2(b, fixo)
        return min(p0.x, p1.x), max(p0.x, p1.x), p0.y - meia, p0.y + meia
    p0, p1 = comum.p2(fixo, a), comum.p2(fixo, b)
    return p0.x - meia, p0.x + meia, min(p0.y, p1.y), max(p0.y, p1.y)


def gerar_paredes():
    col = comum.colecao("Paredes")
    malhas = {}          # nome -> MalhaMultiMaterial
    colisoes = []
    for (eixo, fixo), trechos in linhas_de_parede().items():
        vaos = vaos_na_linha(eixo, fixo)
        for a, b in trechos:
            meio = (a + b) / 2
            altura = altura_da_parede(eixo, fixo, meio)
            nome = nome_da_parede(eixo, fixo, meio)
            m = malhas.setdefault(nome, MalhaMultiMaterial())
            # Pedaços cheios entre os vãos. Só estica 0,1 m nas pontas que NÃO continuam em outro
            # trecho da mesma linha (assim fecha os cantos sem sobrepor faces, o que faria a imagem piscar).
            ext_a = 0.0 if any(abs(t1 - a) < 1e-6 for _, t1 in trechos) else ESPESSURA / 2
            ext_b = 0.0 if any(abs(t0 - b) < 1e-6 for t0, _ in trechos) else ESPESSURA / 2
            cortes = [a - ext_a] + [v for va, vb, _, _ in vaos if a < va < b or a < vb < b for v in (va, vb)] + [b + ext_b]
            cortes = sorted(set(cortes))
            for s0, s1 in zip(cortes[:-1], cortes[1:]):
                centro_seg = (s0 + s1) / 2
                vao = next((v for v in vaos if v[0] - 1e-6 <= centro_seg <= v[1] + 1e-6), None)
                xmin, xmax, ymin, ymax = caixa_blender(eixo, fixo, s0, s1)
                faixas_z = [(0.0, ALTURA_FAIXA), (ALTURA_FAIXA, altura)]
                if vao:
                    # Dentro do vão: só o que fica abaixo (janela) e acima (verga).
                    faixas_z = [(z0, min(z1, vao[2])) for z0, z1 in [(0.0, ALTURA_FAIXA), (ALTURA_FAIXA, vao[2])] if min(z1, vao[2]) > z0] if vao[2] > 0 else []
                    faixas_z.append((vao[3], altura))
                for z0, z1 in faixas_z:
                    if z1 - z0 > 1e-3:
                        m.caixa(xmin, xmax, ymin, ymax, z0, z1, material_da_face)
                        colisoes.append((xmin, xmax, ymin, ymax, z0, z1))
    for nome, m in malhas.items():
        m.criar_objeto(nome, col)

    mc = MalhaMultiMaterial()
    for c in colisoes:
        mc.caixa(*c, lambda *_: "Mat_Parede_Creme")
    obj = mc.criar_objeto("Colisao_Paredes-colonly", comum.colecao("Colisao"))
    obj.data.materials.clear()
    obj.display_type = "WIRE"
    obj.hide_render = True


# ---------------------------------------------------------------------------
# Pisos, tetos e palco
# ---------------------------------------------------------------------------

def gerar_pisos_e_tetos():
    for nome, _, x0, x1, z0, z1, altura in planta_v2.COMODOS:
        col = comum.colecao(nome)
        a, b = comum.p2(x0, z1), comum.p2(x1, z0)
        centro = comum.p2((x0 + x1) / 2, (z0 + z1) / 2)
        piso = MalhaMultiMaterial()
        piso.plano(a.x, b.x, a.y, b.y, 0.0, VISUAL[nome][0])
        piso.criar_objeto(f"Piso_{nome}", col, origem=centro)
        teto = MalhaMultiMaterial()
        teto.plano(a.x, b.x, a.y, b.y, altura, "Mat_Teto_Escuro", para_baixo=True)
        teto.criar_objeto(f"Teto_{nome}", col, origem=(centro.x, centro.y, altura))
    comum.colisao_caixa("Piso", (60.6, 45.6, 0.3), comum.p2(30, 22.5, -0.3), comum.colecao("Colisao"))
    bpy.data.objects["Piso_Colisao-colonly"].name = "Colisao_Piso-colonly"


def gerar_palco():
    col = comum.colecao("Salao")
    col_colisao = comum.colecao("Colisao")
    x0, x1, z0, z1 = planta_v2.PONTOS["palco"]
    base = comum.p2((x0 + x1) / 2, (z0 + z1) / 2)
    tam = (x1 - x0, z1 - z0, ALTURA_PALCO)
    comum.caixa("Palco_Piso", tam, base, "Mat_Palco_Madeira", col)
    comum.colisao_caixa("Palco_Piso", tam, base, col_colisao)
    ex0, ex1, ez0, ez1 = planta_v2.PONTOS["palco_escada"]
    m = MalhaMultiMaterial()
    degraus = 4
    passo = (ez1 - ez0) / degraus
    for k in range(1, degraus + 1):
        a, b = comum.p2(ex0, ez1 - (k - 1) * passo), comum.p2(ex1, ez0)
        m.caixa(a.x, b.x, a.y, b.y, 0.0, ALTURA_PALCO * k / degraus, lambda *_: "Mat_Palco_Madeira")
    m.criar_objeto("Palco_Escada", col, origem=comum.p2((ex0 + ex1) / 2, (ez0 + ez1) / 2))
    # Rampa invisível sobre a escada (para andar sem tropeçar e para a navegação).
    # Ela é 0,75 m mais larga de cada lado e um pouco mais comprida que a escada visível:
    # assim ninguém (vigia ou animatrônico) esbarra na lateral da rampa como num meio-fio.
    pa, pb = comum.p2(ex0 - 0.75, ez1 + 0.5), comum.p2(ex1 + 0.75, ez0)
    verts = [(pa.x, pa.y, 0), (pb.x, pa.y, 0), (pb.x, pb.y, 0), (pa.x, pb.y, 0),
             (pa.x, pb.y, ALTURA_PALCO), (pb.x, pb.y, ALTURA_PALCO)]
    faces = [(0, 3, 2, 1), (0, 1, 5, 4), (3, 4, 5, 2), (0, 4, 3), (1, 2, 5)]
    rampa = comum.malha_de_pontos("Palco_Rampa_Colisao-colonly", verts, faces, col=col_colisao)
    rampa.display_type = "WIRE"
    rampa.hide_render = True


# ---------------------------------------------------------------------------
# Batentes e portas especiais
# ---------------------------------------------------------------------------

ID_PORTA = {  # nome curto de cada porta especial (o Godot usa: Porta__<tipo>__<id>)
    "corrente": "deposito", "chave": "gerente", "teclado": "eletrica", "emperrada": "oficina",
    "aco": "seguranca", "pesada": "camara", "vaivem": "cozinha",
}
# Cômodo que cada porta trancada protege: trancas (corrente e cadeado) ficam do OUTRO lado,
# que é por onde o vigia chega.
COMODO_TRANCADO = {"corrente": "Deposito", "chave": "Sala_Gerente", "teclado": "Sala_Eletrica"}


def sinal_lado_de_fora(eixo, fixo, centro, tipo):
    """
    +1 se o lado de fora (o do vigia) é o +Y local da folha; -1 se é o -Y local (a "frente").
    A folha gira 0° (porta em parede z) ou 90° (parede x): o -Y local aponta para +z ou +x da planta.
    """
    trancado = COMODO_TRANCADO.get(tipo)
    if trancado is None:
        return -1
    x, z = (centro, fixo + 0.3) if eixo == "z" else (fixo + 0.3, centro)
    c = comodo_em(x, z)
    return 1 if c and c[0] == trancado else -1


def gerar_portas():
    col = comum.colecao("Portas")
    unicas = 0
    for eixo, fixo, centro, larg, tipo, lado in planta_v2.PORTAS:
        if tipo == "catraca":
            continue
        rot = 0.0 if eixo == "z" else 90.0
        base = comum.p2(centro, fixo) if eixo == "z" else comum.p2(fixo, centro)
        # Batente (moldura) em todo vão.
        prof = ESPESSURA + 0.06
        batente = comum.caixa(f"Batente_{eixo}{fixo:g}_{centro:g}", (larg + 0.16, prof, 0.08),
                              (base.x, base.y, ALTURA_PORTA), "Mat_Batente_Madeira", col, rot)
        bpy.context.view_layer.update()  # a posição da verga precisa estar valendo antes de prender os lados nela
        for lado_b in (-1, 1):
            off = (larg / 2 + 0.04) * lado_b
            pos = (base.x + off, base.y, 0) if eixo == "z" else (base.x, base.y + off, 0)
            comum.parentar(comum.caixa(f"{batente.name}_Lado{'E' if lado_b < 0 else 'D'}", (0.08, prof, ALTURA_PORTA),
                                       pos, "Mat_Batente_Madeira", col, rot), batente)
        if tipo == "livre":
            continue
        if tipo == "unica":
            unicas += 1
            nome = f"Porta__unica__{lado.lower()}_{unicas}"
        else:
            nome = f"Porta__{tipo}__{ID_PORTA[tipo]}"
        mat = {"aco": "Mat_Porta_Aco", "pesada": "Mat_Inox", "teclado": "Mat_Porta_Metal",
               "corrente": "Mat_Porta_Metal"}.get(tipo, "Mat_Madeira_Velha")
        # A folha da porta: origem na dobradiça (borda esquerda), fechada. O Godot gira pela origem.
        dobradica = (base.x - larg / 2, base.y, 0) if eixo == "z" else (base.x, base.y - larg / 2, 0)
        folha = comum.caixa(nome, (larg - 0.04, 0.05, ALTURA_PORTA - 0.02), (0, 0, 0), mat, col)
        for v in folha.data.vertices:
            v.co.x += (larg - 0.04) / 2  # a malha começa na dobradiça
        folha.location = dobradica
        folha.rotation_euler = (0, 0, math.radians(rot))
        # Maçaneta dos dois lados da folha (antes só havia na frente).
        macaneta = comum.cilindro(f"{nome}_Macaneta", 0.025, 0.1, (larg - 0.16, -0.025, 1.0), "Mat_Metal_Cinza", col,
                                  vertices=8, rot=(90, 0, 0))
        macaneta.parent = folha
        macaneta_tras = comum.cilindro(f"{nome}_Macaneta_Tras", 0.025, 0.1, (larg - 0.16, 0.025, 1.0), "Mat_Metal_Cinza",
                                       col, vertices=8, rot=(-90, 0, 0))
        macaneta_tras.parent = folha
        if tipo == "corrente":
            # Corrente e cadeado do lado de FORA (corredor), onde o vigia vê e usa o alicate.
            # Antes ficavam sempre no -Y local, que nesta porta era o lado de dentro do depósito.
            s = sinal_lado_de_fora(eixo, fixo, centro, tipo)
            corrente = comum.caixa(f"{nome}_Corrente", (0.5, 0.06, 0.04), (larg - 0.2, s * 0.06, 1.05), "Mat_Metal_Enferrujado", col)
            corrente.parent = folha
            cadeado = comum.caixa(f"{nome}_Cadeado", (0.09, 0.05, 0.11), (larg - 0.2, s * 0.1, 0.95), "Mat_Plastico_Amarelo", col)
            cadeado.parent = folha
        if tipo == "aco":
            # Botão e luz dentro da sala de segurança, ao lado da porta (o vigia fecha por aqui).
            painel = comum.caixa("Botao_Porta_Seguranca", (0.16, 0.06, 0.22), comum.p2(47.45, 27.13, 1.15),
                                 "Mat_Metal_Escuro", comum.colecao("Sala_Seguranca"), comum.ROT_OLHA_SUL)
            botao = comum.cilindro("Botao_Porta_Seguranca_Botao", 0.045, 0.03, (0, -0.06, 0.08), "Mat_Botao_Vermelho",
                                   comum.colecao("Sala_Seguranca"), vertices=10, rot=(90, 0, 0))
            botao.parent = painel
            luz = comum.esfera("Botao_Porta_Seguranca_Luz", 0.025, (0, -0.04, 0.17), "Mat_Luz_Porta_Verde",
                               comum.colecao("Sala_Seguranca"), segmentos=8, aneis=6)
            luz.parent = painel
    # Teclado numérico da sala elétrica (do lado da recepção).
    tx, tz, _ = planta_v2.PONTOS["teclado_eletrica"]
    teclado = comum.caixa("Teclado_Eletrica", (0.14, 0.05, 0.2), comum.p2(tx, tz, 1.3), "Mat_Metal_Escuro",
                          comum.colecao("Recepcao"), comum.ROT_OLHA_LESTE)
    tela = comum.caixa("Teclado_Eletrica_Tela", (0.1, 0.01, 0.04), (0, -0.03, 0.14), "Mat_Tela_Monitor", comum.colecao("Recepcao"))
    tela.parent = teclado


def gerar_janela():
    """Janela de vidro aramado da sala de segurança (parede para o corredor)."""
    col = comum.colecao("Sala_Seguranca")
    for eixo, fixo, centro, larg, _ in planta_v2.JANELAS:
        base = comum.p2(fixo, centro, 1.0) if eixo == "x" else comum.p2(centro, fixo, 1.0)
        rot = 90.0 if eixo == "x" else 0.0
        comum.caixa("Janela_Seguranca_Vidro", (larg, 0.02, 0.9), base, "Mat_Vidro_Aramado", col, rot)
        moldura = comum.caixa("Janela_Seguranca_Moldura", (larg + 0.1, ESPESSURA + 0.04, 0.05), base, "Mat_Metal_Escuro", col, rot)
        moldura.location.z = 0.975


def contar_triangulos():
    return sum(sum(len(p.vertices) - 2 for p in o.data.polygons)
               for o in bpy.context.scene.objects if o.type == "MESH" and not o.name.endswith("-colonly"))


def gerar():
    comum.limpar_cena()
    planta_v2.conferir()
    gerar_pisos_e_tetos()
    gerar_paredes()
    gerar_palco()
    gerar_portas()
    gerar_janela()
    print(f"[predio_v2] objetos: {len(bpy.context.scene.objects)}  triângulos: {contar_triangulos()}")
    comum.salvar_blend(comum.PASTA_BLENDER / "v2_predio.blend")
    comum.exportar_glb(comum.PASTA_CENARIO / "v2_predio.glb")


if __name__ == "__main__":
    gerar()
