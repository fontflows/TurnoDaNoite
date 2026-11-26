"""
moveis_v2_servico.py — móveis e set dressing da ÁREA DE SERVIÇO da V2:
sala de segurança (pequena e apertada), oficina/bastidores, depósito, sala elétrica com o
gerador, vestiário, sala do gerente, arquivo morto, copa, armário de limpeza e o corredor
dos funcionários. Também os disjuntores do Depósito, do Gerente e da Sala elétrica.

Reaproveita os ajudantes de moveis_v2_diversao.py (Lote, caixas, montar, colisao, estante...).
Saída: blender/v2_servico.blend e godot/assets/cenario/v2_servico.glb
Rodar:  blender --background --python blender/scripts/moveis_v2_servico.py
"""

import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import comum  # noqa: E402
import moveis_v2_diversao as d  # noqa: E402  (ajudantes compartilhados)
import planta_v2  # noqa: E402

V = Vector
P = planta_v2.PONTOS
SORTE = d.SORTE
COMODOS_GRUPO = ["Sala_Seguranca", "Oficina", "Deposito", "Sala_Eletrica", "Vestiario", "Sala_Gerente",
                 "Arquivo", "Copa", "Armario_Limpeza", "Corredor_Funcionarios"]
COLECAO_DISJUNTORES = "Disjuntores_Servico"

# Cores lisas novas deste grupo (as com textura vêm de materiais_v2.py)
CORES_SERVICO = {
    "Mat_Crt_Bege": ("#cfc6b0", 0.0),
    "Mat_Cortica": ("#a07a4a", 0.0),
    "Mat_Cadeira_Couro": ("#2e2420", 0.0),
    "Mat_Cafe": ("#2a1a10", 0.0),
    "Mat_Cinzeiro": ("#5a5a5a", 0.0),
    "Mat_Gerador_Amarelo": ("#c9a227", 0.0),
    "Mat_Perigo_Faixa": ("#1a1a1a", 0.0),
    "Mat_Fusivel_Bom": ("#d8d0b8", 0.0),
    "Mat_Fusivel_Queimado": ("#1c1612", 0.0),
    "Mat_Abajur_Verde": ("#2f6a3a", 0.0),
    "Mat_Postit_Amarelo": ("#f0dc6a", 0.0),
    "Mat_Postit_Rosa": ("#f08ab0", 0.0),
    "Mat_Tela_TV_Copa": ("#10161a", 0.3),
    "Mat_Grade_Duto": ("#4a4c4e", 0.0),
    "Mat_Pele_Animatronico": ("#8a6a4a", 0.0),
}


def M(nome):
    return comum.material(nome)


def teto(comodo):
    return next(c[6] for c in planta_v2.COMODOS if c[0] == comodo)


def grade_duto(nome, col, x, z, parede):
    """Grade de duto na parede, perto do chão (o jogador entra agachado)."""
    g = d.caixas(nome, [((0.8, 0.04, 0.6), (0, 0, 0))], "Mat_Grade_Duto", col)
    barras = d.Lote()
    for i in range(7):
        barras.caixa((0.02, 0.05, 0.56), (-0.33 + i * 0.11, -0.01, 0.02), "Mat_Metal_Escuro")
    b = barras.objeto(nome + "_Barras", col)
    return d.montar(g, [b], x, z, 0.15, parede)


# ---------------------------------------------------------------------------
# SALA DE SEGURANÇA (3 x 2,5 m, teto 2,4 m)
# ---------------------------------------------------------------------------

def crt(nome, col, largura, tela_nome):
    """Monitor CRT bege com a tela como objeto separado (UV 0-1, 4:3), frente em -Y."""
    corpo = d.Lote()
    corpo.caixa((largura, 0.42, largura * 0.82), (0, 0.06, 0), "Mat_Crt_Bege")
    corpo.caixa((largura * 0.7, 0.2, largura * 0.6), (0, 0.32, 0.06), "Mat_Crt_Bege")   # o "traseiro" do tubo
    obj = corpo.objeto(nome, col)
    lw, lh = largura * 0.78, largura * 0.78 * 0.75
    z0 = largura * 0.82 * 0.15
    tela = d.plano_uv(tela_nome, [(-lw / 2, -0.152, z0), (lw / 2, -0.152, z0), (lw / 2, -0.152, z0 + lh), (-lw / 2, -0.152, z0 + lh)],
                      "Mat_Tela_Monitor", col)
    tela.parent = obj
    return obj


def sala_seguranca(col):
    h = teto("Sala_Seguranca")
    # Mesa na parede leste, de frente para oeste (para o vigia sentado no ponto de início).
    mesa = d.caixas("Mesa_Seguranca", [((2.25, 0.7, 0.04), (0, 0, 0.71)), ((0.04, 0.66, 0.71), (-1.1, 0, 0)),
                                       ((0.04, 0.66, 0.71), (1.1, 0, 0)), ((2.2, 0.03, 0.5), (0, 0.33, 0.2))],
                     "Mat_Madeira_Escura", col)
    filhos = [d.colisao("Mesa_Seguranca", (2.25, 0.7, 0.75), (0, 0, 0), col)]
    for nome, x, tela in (("Monitor_Esquerdo", -0.62, "Monitor_Esquerdo_Tela"), ("Monitor_Principal", 0.0, "Monitor_Tela"),
                          ("Monitor_Direito", 0.62, "Monitor_Direito_Tela")):
        m = crt(nome, col, 0.5 if x == 0 else 0.44, tela)
        m.location = V((x, 0.08, 0.75))
        m.rotation_euler = (0, 0, math.radians(SORTE.uniform(-4, 4)))
        filhos.append(m)
    det = d.Lote()
    for i, (cx, cy) in enumerate([(-0.95, -0.2), (-0.35, -0.27), (0.4, -0.25)]):   # copos de café
        det.cilindro(0.04, 0.11, (cx, cy, 0.75), "Mat_Plastico_Branco", lados=8)
        det.cilindro(0.036, 0.004, (cx, cy, 0.85), "Mat_Cafe", lados=8)
    det.cilindro(0.07, 0.025, (0.25, -0.22, 0.75), "Mat_Cinzeiro", lados=10, raio_topo=0.06)   # cinzeiro vazio
    det.caixa((0.42, 0.14, 0.03), (0.0, -0.28, 0.75), "Mat_Plastico_Preto")                       # teclado
    det.caixa((0.22, 0.15, 0.06), (-0.98, 0.1, 0.75), "Mat_Plastico_Preto")                       # secretária eletrônica
    det.caixa((0.18, 0.1, 0.12), (0.98, 0.15, 0.75), "Mat_Plastico_Preto")                        # rádio
    det.caixa((0.06, 0.02, 0.18), (1.02, 0.2, 0.87), "Mat_Metal_Cinza", rot=(-20, 0, 0))           # antena
    filhos.append(det.objeto("Mesa_Seguranca_Objetos", col))
    secretaria = d.caixas("Secretaria_Eletronica", [((0.2, 0.13, 0.02), (0, 0, 0))], "Mat_Plastico_Branco", col)
    secretaria.location = V((-0.98, 0.1, 0.81))
    filhos.append(secretaria)
    # Ventilador de mesa oscilante: base, cabeça (gira de um lado para o outro) e hélice.
    vent = d.caixas("Ventilador_Mesa", [((0.16, 0.16, 0.03), (0, 0, 0))], "Mat_Metal_Escuro", col)
    cab = d.Lote()
    cab.cilindro(0.015, 0.22, (0, 0, -0.22), "Mat_Metal_Escuro", lados=6)
    cab.esfera(0.06, (0, 0.03, 0.0), "Mat_Metal_Escuro", seg=8, aneis=5)
    cab.cilindro(0.15, 0.02, (0, -0.04, 0.0), "Mat_Metal_Cinza", rot=(90, 0, 0), lados=12)
    cabeca = cab.objeto("Ventilador_Mesa_Cabeca", col)
    cabeca.location = V((0, 0, 0.25))
    cabeca.parent = vent
    hel = d.Lote()
    for a in (0, 120, 240):
        hel.caixa((0.04, 0.005, 0.12), (0, 0, 0), "Mat_Plastico_Azul", rot=(0, a, 0))
    helice = hel.objeto("Ventilador_Mesa_Helice", col)
    helice.location = V((0, -0.06, 0.0))
    helice.parent = cabeca
    vent.location = V((0.75, 0.05, 0.75))
    vent.rotation_euler = (0, 0, math.radians(-25))
    filhos.append(vent)
    # Pasta do manual do vigia deitada na mesa (ARTE-23).
    manual = comum.plano_arte("capa_manual_vigia.jpg", 0.23, 0.3, (0, 0, 0), col)
    manual.location = V((-0.6, -0.26, 0.757))  # 7 mm acima do tampo
    manual.rotation_euler = (math.radians(-90), 0, math.radians(8))
    filhos.append(manual)
    d.montar(mesa, filhos, 49.6, 28.25, 0.0, "oeste")
    d.marcador("Luz__abajur_03", col, 49.75, 27.45, 1.25)     # luminária de mesa (luz quente fraca)
    lum = d.Lote()
    lum.cilindro(0.06, 0.02, comum.p2(49.75, 27.45, 0.75), "Mat_Metal_Escuro", lados=8)
    lum.tubo([comum.p2(49.75, 27.45, 0.77), comum.p2(49.7, 27.5, 1.15), comum.p2(49.6, 27.6, 1.3)], 0.012, "Mat_Metal_Escuro")
    lum.cilindro(0.09, 0.12, comum.p2(49.6, 27.6, 1.2), "Mat_Abajur_Verde", lados=8, raio_topo=0.05)
    lum.objeto("Luminaria_Mesa_Seguranca", col)
    d.marcador("Som__ventilacao_01", col, 49.5, 28.9, 1.0)

    # Cadeira giratória velha SEM colisão (fica no ponto de início do vigia), virada para a mesa.
    cad = d.Lote()
    cad.caixa((0.5, 0.48, 0.08), (0, 0, 0.45), "Mat_Cadeira_Couro")
    cad.caixa((0.48, 0.07, 0.55), (0, 0.24, 0.55), "Mat_Cadeira_Couro", rot=(-8, 0, 0))
    cad.cilindro(0.03, 0.45, (0, 0, 0), "Mat_Metal_Escuro", lados=6)
    for a in range(5):
        cad.caixa((0.3, 0.04, 0.04), (0, 0, 0.02), "Mat_Metal_Escuro", rot=(0, 0, a * 72))
    cadeira = cad.objeto("Cadeira_Seguranca", col)
    sx, sz, _ = P["spawn_jogador"]
    d.montar(cadeira, [], sx + 0.25, sz, 0.0, "leste", 12)

    # Paredes cobertas: pôsteres, desenhos, regras, post-its, calendário.
    # (6 mm na frente da face da parede: antes ficavam 2 cm soltos dela)
    comum.plano_arte("poster_celebre.jpg", 0.6, 0.9, comum.p2(49.894, 28.25, 1.32), col, comum.ROT_OLHA_OESTE)
    comum.plano_arte("poster_sorria_camera.jpg", 0.5, 0.75, comum.p2(48.4, 27.106, 1.2), col, comum.ROT_OLHA_SUL)
    comum.plano_arte("poster_pizza_quentinha.jpg", 0.5, 0.75, comum.p2(48.95, 29.394, 1.2), col, comum.ROT_OLHA_NORTE)
    comum.plano_arte("regras_vigia", 0.45, 0.6, comum.p2(47.95, 29.394, 1.2), col, comum.ROT_OLHA_NORTE)
    comum.plano_arte("funcionario_do_mes", 0.3, 0.4, comum.p2(49.65, 29.394, 1.5), col, comum.ROT_OLHA_NORTE)
    cortica = d.caixas("Painel_Cortica_Seguranca", [((0.75, 0.03, 0.55), (0, 0, 0))], "Mat_Cortica", col)
    pins = d.Lote()
    for i, (px, pz, mat) in enumerate([(-0.3, 0.42, "Mat_Postit_Amarelo"), (-0.18, 0.12, "Mat_Postit_Rosa"),
                                       (0.28, 0.4, "Mat_Postit_Amarelo"), (0.3, 0.1, "Mat_Papel_Branco")]):
        pins.caixa((0.08, 0.004, 0.08), (px, -0.018, pz), mat, rot=(0, SORTE.uniform(-12, 12), 0))
    desenho = comum.plano_arte("desenho_crianca_amigos.jpg", 0.36, 0.27, (0.0, -0.022, 0.14), col)  # 7 mm da cortiça
    d.montar(cortica, [pins.objeto("Painel_Cortica_Seguranca_Papeis", col), desenho], 49.45, 27.12, 1.25, "sul")
    cal = d.caixas("Calendario_Velho", [((0.25, 0.01, 0.35), (0, 0, 0))], "Mat_Papel_Branco", col)
    d.montar(cal, [], 47.6, 27.12, 1.45, "sul", 4)
    d.teias("Teias_Seguranca", col, [(47.1, 27.1, 1, 1), (49.9, 29.4, -1, -1)], h)
    d.decal("refrigerante", col, 48.6, 28.6, 0.6, 0.6)     # mancha de café derramado
    d.decal("pegadas", col, 47.8, 28.1, 0.5, 0.9, giro=90)


# ---------------------------------------------------------------------------
# OFICINA / BASTIDORES (porta para o corredor EMPERRADA: entra-se pelo duto)
# ---------------------------------------------------------------------------

def cabeca_aberta(nome, col):
    """Cabeça antiga de animatrônico aberta na bancada: casca de plástico e mecanismo à mostra (nada perturbador)."""
    lote = d.Lote()
    lote.esfera(0.24, (0, 0, 0.22), "Mat_Plastico_Branco", escala=(1, 1, 0.9), seg=10, aneis=6)
    lote.esfera(0.08, (0.1, -0.2, 0.28), "Mat_Plastico_Preto", seg=6, aneis=4)
    lote.esfera(0.08, (-0.1, -0.2, 0.28), "Mat_Plastico_Preto", seg=6, aneis=4)
    lote.caixa((0.3, 0.02, 0.02), (0, 0, 0.42), "Mat_Metal_Cinza")
    lote.cilindro(0.05, 0.03, (0.0, 0.05, 0.24), "Mat_Metal_Enferrujado", rot=(90, 0, 0), lados=10)   # engrenagem
    lote.tubo([(0.05, 0.1, 0.05), (0.2, 0.25, 0.0), (0.35, 0.2, 0.0)], 0.01, "Mat_Fio_Vermelho")
    lote.esfera(0.12, (0.2, -0.05, 0.42), "Mat_Plastico_Branco", escala=(0.5, 1, 0.4), seg=6, aneis=4)   # orelha solta
    return lote.objeto(nome, col)


def oficina(col):
    h = teto("Oficina")
    # Bancada de conserto (o alicate fica em cima dela).
    ax, az, _ = P["alicate"]
    banc = d.caixas("Bancada_Oficina", [((2.4, 0.9, 0.06), (0, 0, 0.9)), ((0.06, 0.85, 0.9), (-1.15, 0, 0)),
                                        ((0.06, 0.85, 0.9), (1.15, 0, 0)), ((2.3, 0.8, 0.03), (0, 0, 0.3))],
                     "Mat_Madeira_Velha", col)
    ferr = d.Lote()
    ferr.caixa((0.35, 0.2, 0.15), (0.75, 0.15, 0.96), "Mat_Metal_Pintado_Verde")       # caixa de ferramentas
    ferr.caixa((0.25, 0.03, 0.02), (0.6, -0.25, 0.96), "Mat_Metal_Cinza", rot=(0, 0, 25))   # chave inglesa
    ferr.cilindro(0.05, 0.25, (-0.8, 0.25, 0.96), "Mat_Metal_Escuro", lados=8)          # lata de óleo
    for i in range(4):
        ferr.caixa((0.06, 0.04, 0.02), (-0.5 + i * 0.12, 0.3, 0.96), "Mat_Metal_Enferrujado")   # parafusos e peças
    alicate = d.Lote()   # alicate corta-corrente (o item)
    alicate.caixa((0.5, 0.04, 0.03), (0, 0, 0), "Mat_Plastico_Vermelho", rot=(0, 0, 8))
    alicate.caixa((0.5, 0.04, 0.03), (0, 0, 0.0), "Mat_Plastico_Vermelho", rot=(0, 0, -8))
    alicate.caixa((0.14, 0.05, 0.04), (0.3, 0, 0), "Mat_Metal_Escuro")
    alic = alicate.objeto("Alicate_Corta_Corrente", col)
    alic.location = V((ax - 4.0, 0.0, 0.96))   # ajustado depois do montar (fica no ponto do item)
    cab = cabeca_aberta("Cabeca_Animatronico_Aberta", col)
    cab.location = V((-0.55, 0.05, 0.93))
    filhos = [ferr.objeto("Bancada_Oficina_Ferramentas", col), cab, d.colisao("Bancada_Oficina", (2.4, 0.9, 0.95), (0, 0, 0), col)]
    d.montar(banc, filhos, ax, az + 0.25, 0.0, "sul")
    alic.location = comum.p2(ax, az, 0.96)
    alic.rotation_euler = (0, 0, math.radians(30))
    d.marcador("Item__alicate", col, ax, az, 1.0)
    d.marcador("Luz__abajur_04", col, ax - 0.7, az + 0.4, 1.4)
    d.marcador("Som__radio_01", col, ax + 0.8, az + 0.3, 1.1)

    # Arara de figurinos (parecem pessoas no escuro) = esconderijo.
    fx, fz = 1.2, 13.0
    arara = d.Lote()
    arara.tubo([(0, -1.2, 1.75), (0, 1.2, 1.75)], 0.02, "Mat_Metal_Cinza", lados=6)
    for sy in (-1.2, 1.2):
        arara.tubo([(0, sy, 0), (0, sy, 1.75)], 0.02, "Mat_Metal_Cinza", lados=6)
    mats = ["Mat_Tecido_Figurino_Vermelho", "Mat_Tecido_Figurino_Azul", "Mat_Tecido_Figurino_Amarelo", "Mat_Lencol_Branco"]
    for i in range(7):
        y = -1.0 + i * 0.33
        arara.caixa((0.45, 0.12, 1.15), (0, y, 0.55), mats[i % 4], rot=(0, 0, SORTE.uniform(-10, 10)))
        if i % 3 == 0:
            arara.esfera(0.17, (0, y, 1.5), mats[(i + 1) % 4], seg=8, aneis=5)   # "cabeça" da fantasia
    obj = arara.objeto("Arara_Figurinos", col)
    d.montar(obj, [d.colisao("Arara_Figurinos", (0.5, 2.5, 1.8), (0, 0, 0), col)], fx, fz, 0.0, "leste")
    d.marcador("Esconderijo__figurinos_01", col, *P["esconderijos"][12][1:], 0.0)

    # Estantes de peças na parede norte e entulho na porta emperrada (do lado de dentro).
    est, f = d.estante("Estante_Pecas_Oficina", col, 2.4, 0.5, 2.0, 4, "Mat_Metal_Pintado_Azul", "Mat_Metal_Enferrujado")
    d.montar(est, f, 9.5, 0.4, 0.0, "sul")
    entulho = d.Lote()
    entulho.caixa((1.8, 0.6, 0.9), (0, 0, 0), "Mat_Metal_Pintado_Verde", rot=(0, 78, 12))   # armário caído
    entulho.caixa((0.6, 0.5, 0.5), (0.9, -0.5, 0), "Mat_Papelao_Caixa", rot=(0, 0, 20))
    entulho.caixa((0.5, 0.4, 0.4), (-0.7, -0.6, 0), "Mat_Papelao_Caixa", rot=(0, 0, -15))
    ent = entulho.objeto("Entulho_Porta_Oficina", col)
    d.montar(ent, [d.colisao("Entulho_Porta_Oficina", (2.2, 1.0, 1.2), (0, -0.2, 0), col)], 7.0, 15.0, 0.0, "norte")
    grade_duto("Duto_Grade_Oficina", col, 11.0, 15.85, "norte")
    d.marcador("Esconderijo__duto_01", col, 11.0, 15.5, 0.0)
    # Pedaços de animatrônicos antigos numa mesa lateral, cabos e placa do forro caída.
    pecas = d.Lote()
    pecas.caixa((1.6, 0.7, 0.75), (0, 0, 0), "Mat_Madeira_Velha")
    pecas.esfera(0.2, (-0.4, 0, 0.95), "Mat_Pele_Animatronico", seg=8, aneis=5)
    pecas.cilindro(0.07, 0.6, (0.3, 0, 0.8), "Mat_Metal_Cinza", rot=(0, 90, 10), lados=6)   # braço metálico
    pecas.esfera(0.1, (0.55, -0.1, 0.82), "Mat_Plastico_Branco", seg=6, aneis=4)            # mão de plástico
    mesa_pecas = pecas.objeto("Mesa_Pecas_Animatronico", col)
    d.montar(mesa_pecas, [d.colisao("Mesa_Pecas", (1.6, 0.7, 0.8), (0, 0, 0), col)], 12.6, 9.0, 0.0, "oeste")
    cabos = d.Lote()
    cabos.tubo([comum.p2(9, 6, 0.02), comum.p2(10, 7.5, 0.02), comum.p2(12, 7.8, 0.02), comum.p2(12.4, 8.6, 0.6)], 0.02, "Mat_Plastico_Preto")
    cabos.objeto("Cabos_Oficina", col)
    d.forro_caido("Forro_Caido_Oficina", col, 6.0, 9.0, 25, h)
    d.teias("Teias_Oficina", col, [(0.1, 0.1, 1, 1), (13.9, 0.1, -1, 1), (0.1, 15.9, 1, -1)], h)
    d.decal("gordura", col, 4.0, 4.5, 1.2, 1.0)
    d.decal("pegadas", col, 9.0, 12.0, 0.6, 2.0, giro=30)
    d.decal("mancha_agua", col, 13.85, 6.0, 1.2, 1.4, parede="leste", h=2.2)


# ---------------------------------------------------------------------------
# DEPÓSITO (prateleiras altas, corredores estreitos, lençóis, cabeças velhas)
# ---------------------------------------------------------------------------

def coberto_lencol(nome, col, x, z, largura, prof, altura, giro):
    """Móvel coberto com lençol: ótimo para sustos falsos."""
    lote = d.Lote()
    lote.caixa((largura, prof, altura), (0, 0, 0), "Mat_Lencol_Branco", rot=(0, 0, 0))
    lote.esfera(min(largura, prof) * 0.45, (largura * 0.2, 0, altura + 0.1), "Mat_Lencol_Branco", escala=(1, 1, 0.8), seg=8, aneis=5)
    lote.caixa((largura + 0.1, prof + 0.1, 0.15), (0, 0, 0), "Mat_Lencol_Branco")   # barra do pano no chão
    obj = lote.objeto(nome, col)
    return d.montar(obj, [d.colisao(nome, (largura, prof, altura), (0, 0, 0), col)], x, z, 0.0, "sul", giro)


def deposito(col, col_disj):
    h = teto("Deposito")
    for i, (x, z0, z1) in enumerate([(2.6, 22.0, 28.0), (5.3, 21.0, 28.5), (10.6, 21.0, 28.5)], 1):
        comp = z1 - z0
        n = max(2, int(comp // 2.0))
        for k in range(n):
            zc = z0 + comp * (k + 0.5) / n
            est, f = d.estante(f"Prateleira_Alta_{i}_{k + 1}", col, comp / n - 0.05, 0.6, 2.9, 5, "Mat_Metal_Pintado_Amarelo",
                               "Mat_Papelao_Caixa", faltando=(2, 7) if k % 2 else (4,))
            d.montar(est, f, x, zc, 0.0, "leste" if i != 3 else "oeste")
    # Cabeças e peças antigas numa prateleira (sustos falsos).
    cab = d.Lote()
    for i, mat in enumerate(["Mat_Pele_Animatronico", "Mat_Plastico_Lilas", "Mat_Plastico_Branco"]):
        cab.esfera(0.22, (0, -0.6 + i * 0.6, 1.55), mat, seg=8, aneis=6)
        cab.esfera(0.05, (-0.2, -0.65 + i * 0.6, 1.6), "Mat_Plastico_Preto", seg=6, aneis=4)
    cab.objeto("Cabecas_Antigas", col, (0, 0, 0)).location = comum.p2(10.2, 24.0, 0.0)
    coberto_lencol("Movel_Coberto_1", col, 3.5, 31.5, 1.4, 0.8, 1.0, 10)
    coberto_lencol("Movel_Coberto_2", col, 9.8, 31.8, 1.8, 0.9, 1.6, -6)
    pilha = d.Lote()
    for i in range(6):
        pilha.caixa((0.6, 0.5, 0.45), (SORTE.uniform(-0.1, 0.1), 0, i % 3 * 0.45), "Mat_Papelao_Caixa", rot=(0, 0, SORTE.uniform(-12, 12)))
    pc = pilha.objeto("Pilha_Caixas_Deposito", col)
    d.montar(pc, [d.colisao("Pilha_Caixas_Deposito", (0.7, 0.6, 1.35), (0, 0, 0), col)], 12.8, 20.4, 0.0, "sul")
    relatorio = comum.plano_arte("capa_relatorio_manutencao.jpg", 0.26, 0.34, (0, 0, 0), col)
    # Em pé na BEIRADA da prateleira do meio (tábua em 1,23 m), virado para o corredor da estante.
    # Antes ficava no fundo dela (x = 10,9), virado para dentro: as caixas tampavam a capa.
    relatorio.location = comum.p2(10.315, 25.4, 1.235)
    relatorio.rotation_euler = (0, 0, math.radians(-90))
    disjuntor(col_disj, "Deposito", "DEPÓSITO", "disjuntor_deposito")
    d.marcador("Som__rangido_01", col, 7.0, 30.0, 2.5)
    d.teias("Teias_Deposito", col, [(0.1, 19.1, 1, 1), (13.9, 19.1, -1, 1), (0.1, 32.9, 1, -1), (13.9, 32.9, -1, -1)], h)
    d.decal("mancha_agua", col, 7.5, 24.0, 2.0, 2.0)
    d.decal("pegadas", col, 7.8, 28.0, 0.6, 3.0)
    d.forro_caido("Forro_Caido_Deposito", col, 8.0, 21.5, -20, h)


# ---------------------------------------------------------------------------
# SALA ELÉTRICA (gerador principal, painéis, alta tensão)
# ---------------------------------------------------------------------------

def sala_eletrica(col, col_disj):
    h = teto("Sala_Eletrica")
    gx, gz, frente = P["gerador"]
    ger = d.Lote()
    ger.caixa((2.4, 1.2, 1.3), (0, 0, 0), "Mat_Gerador_Amarelo")
    ger.caixa((2.5, 1.3, 0.12), (0, 0, 0), "Mat_Metal_Escuro")
    ger.cilindro(0.18, 0.9, (0.7, 0.3, 1.3), "Mat_Metal_Enferrujado", lados=8)    # escapamento
    ger.caixa((0.5, 0.05, 0.35), (-0.6, -0.62, 0.7), "Mat_Metal_Escuro")           # painel de controle
    ger.caixa((2.4, 0.02, 0.1), (0, -0.61, 1.1), "Mat_Perigo_Faixa")
    g = ger.objeto("Gerador_Principal", col)
    alav = d.caixas("Gerador_Principal_Alavanca", [((0.06, 0.06, 0.4), (0, 0, 0)), ((0.12, 0.12, 0.08), (0, 0, 0.4))],
                    "Mat_Plastico_Vermelho", col)
    alav.location = V((-0.6, -0.7, 0.75))
    alav.rotation_euler = (math.radians(-35), 0, 0)
    d.montar(g, [alav, d.colisao("Gerador_Principal", (2.5, 1.3, 1.6), (0, 0, 0), col)], gx, gz, 0.0, frente)
    d.marcador("Som__zumbido_01", col, gx, gz, 1.2)
    paineis = d.Lote()
    for i in range(4):
        paineis.caixa((0.7, 0.3, 1.8), (-1.2 + i * 0.8, 0, 0), "Mat_Metal_Pintado_Azul")
        paineis.caixa((0.08, 0.02, 0.08), (-1.2 + i * 0.8 + 0.2, -0.16, 1.4), "Mat_Led_Disjuntor")
    pn = paineis.objeto("Paineis_Eletricos", col)
    d.montar(pn, [d.colisao("Paineis_Eletricos", (3.2, 0.35, 1.8), (0, 0, 0), col)], 6.5, 33.35, 0.0, "sul")
    cabos = d.Lote()
    for i in range(3):
        cabos.tubo([comum.p2(5.4 + i * 0.6, 33.5, 1.8), comum.p2(5.6 + i * 0.6, 35.0, 2.9), comum.p2(gx - 0.5 + i * 0.4, gz - 0.6, 2.9),
                    comum.p2(gx - 0.5 + i * 0.4, gz - 0.6, 1.3)], 0.035, "Mat_Plastico_Preto")
    cabos.objeto("Cabos_Grossos", col)
    for i, (x, z, frente_p) in enumerate([(12.0, 33.12, "sul"), (0.12, 38.0, "leste")], 1):
        placa = d.caixas(f"Placa_Perigo_{i}", [((0.5, 0.02, 0.35), (0, 0, 0))], "Mat_Metal_Pintado_Amarelo", col)
        txt = d.texto(f"Placa_Perigo_{i}_Texto", "PERIGO\nALTA TENSÃO", 0.06, "Mat_Texto_Preto", col, (0, -0.012, 0.17), largura_max=0.44)
        d.montar(placa, [txt], x, z, 1.5, frente_p)
    d.marcador("Luz__tela_02", col, 6.5, 34.0, 2.0)
    disjuntor(col_disj, "Eletrica", "ELÉTRICA", "disjuntor_eletrica")
    d.teias("Teias_Eletrica", col, [(0.1, 33.1, 1, 1), (13.9, 44.9, -1, -1)], h)
    d.decal("gordura", col, gx + 1.8, gz, 1.0, 1.2)
    d.decal("rachadura", col, 3.0, 36.0, 1.5, 1.5)


# ---------------------------------------------------------------------------
# DISJUNTORES (mesmo modelo da cozinha; o do Gerente tem fusíveis)
# ---------------------------------------------------------------------------

def disjuntor(col, area, rotulo, chave):
    x, z, frente = P[chave]
    nome = f"Disjuntor_{area}"
    cx = d.caixas(nome, [((0.45, 0.15, 0.6), (0, -0.075, -0.3))], "Mat_Disjuntor_Caixa", col)
    alav = d.caixas(nome + "_Alavanca", [((0.12, 0.04, 0.04), (0, 0, -0.02)), ((0.03, 0.14, 0.03), (0, 0.07, -0.015)),
                                         ((0.09, 0.04, 0.04), (0, 0.15, -0.02))], "Mat_Disjuntor_Alavanca", col)
    alav.parent = cx
    alav.location = V((0, -0.15, 0))
    alav.rotation_euler = (math.radians(-40), 0, math.radians(180))
    led = d.caixas(nome + "_Led", [((0.03, 0.01, 0.03), (0.16, -0.155, 0.2))], "Mat_Led_Disjuntor", col)
    led.parent = cx
    placa = d.texto(nome + "_Placa", rotulo, 0.05, "Mat_Texto_Branco", col, (-0.03, -0.152, 0.22), largura_max=0.3)
    placa.parent = cx
    if area == "Gerente":
        # Troca de fusível: 3 fusíveis, o do meio queimado.
        for i in range(1, 4):
            fus = d.Lote()
            fus.cilindro(0.025, 0.1, (0, 0, 0), "Mat_Fusivel_Queimado" if i == 2 else "Mat_Fusivel_Bom", rot=(0, 90, 0), lados=8)
            f = fus.objeto(f"{nome}_Fusivel_{i}", col)
            f.parent = cx
            f.location = V((-0.15 + (i - 1) * 0.12, -0.16, -0.12))
    cx.location = comum.p2(x, z, 1.3)
    cx.rotation_euler = (0, 0, math.radians(d.FRENTES[frente][0]))
    return cx


# ---------------------------------------------------------------------------
# VESTIÁRIO, GERENTE, ARQUIVO, COPA, ARMÁRIO DE LIMPEZA, CORREDOR
# ---------------------------------------------------------------------------

def armario_metal(nome, col, x, z, frente, aberto=False):
    """Armário de metal com porta (filho '_Porta', origem na dobradiça)."""
    corpo = d.caixas(nome, [((0.7, 0.55, 1.9), (0, 0, 0))], "Mat_Metal_Pintado_Verde", col)
    porta = d.Lote()
    porta.caixa((0.66, 0.03, 1.8), (0.33, 0, 0), "Mat_Metal_Pintado_Verde")
    for i in range(5):
        porta.caixa((0.3, 0.035, 0.02), (0.33, -0.005, 1.45 + i * 0.05), "Mat_Metal_Escuro")   # frestas de ventilação
    p = porta.objeto(nome + "_Porta", col)
    p.parent = corpo
    p.location = V((-0.33, -0.285, 0.05))
    p.rotation_euler = (0, 0, math.radians(-100 if aberto else 0))
    return d.montar(corpo, [p, d.colisao(nome, (0.7, 0.55, 1.9), (0, 0, 0), col)], x, z, 0.0, frente)


def vestiario(col):
    h = teto("Vestiario")
    esc = [e for e in P["esconderijos"] if e[0] == "armario"]
    for i, (_, x, z) in enumerate(esc, 1):
        armario_metal(f"Armario_Vestiario_{i}", col, x + 0.1, z, "oeste")
        d.marcador(f"Esconderijo__armario_{i:02d}", col, x - 0.5, z, 0.0)
    armario_metal("Armario_Antigo_Vigia", col, 53.6, 26.4, "oeste", aberto=True)
    bilhete = d.texto("Bilhete_Demissao", "NÃO VOLTO MAIS.\nELES SE MEXEM.", 0.05, "Mat_Texto_Preto", col, (0, 0, 0),
                      largura_max=0.4, fonte_chave="Caveat")
    bilhete.location = comum.p2(53.25, 26.4, 1.3)
    bilhete.rotation_euler = (0, 0, math.radians(d.FRENTES["oeste"][0]))
    banco = d.caixas("Banco_Vestiario", [((0.4, 2.2, 0.06), (0, 0, 0.42)), ((0.06, 0.06, 0.42), (0, -0.9, 0)),
                                         ((0.06, 0.06, 0.42), (0, 0.9, 0))], "Mat_Madeira_Velha", col)
    d.montar(banco, [d.colisao("Banco_Vestiario", (0.4, 2.2, 0.48), (0, 0, 0), col)], 50.8, 23.2, 0.0, "leste")
    unif = d.Lote()
    for i in range(4):
        unif.caixa((0.45, 0.1, 0.9), (-0.9 + i * 0.6, 0, 0.9), ["Mat_Tecido_Figurino_Azul", "Mat_Lencol_Branco"][i % 2])
        unif.cilindro(0.015, 0.1, (-0.9 + i * 0.6, 0.05, 1.8), "Mat_Metal_Cinza", rot=(90, 0, 0), lados=4)
    u = unif.objeto("Uniformes_Pendurados", col)
    d.montar(u, [], 50.0, 19.15, 0.0, "sul")
    pia = d.caixas("Pia_Vestiario", [((0.6, 0.45, 0.2), (0, 0, 0.7))], "Mat_Louca_Branca", col)
    d.montar(pia, [d.colisao("Pia_Vestiario", (0.6, 0.45, 0.9), (0, 0, 0), col)], 48.2, 26.7, 0.0, "norte")
    d.marcador("Som__goteira_03", col, 48.2, 26.6, 0.9)
    d.marcador("Luz__fluorescente_03", col, 50.5, 23.0, h - 0.1)
    d.teias("Teias_Vestiario", col, [(47.1, 19.1, 1, 1), (53.9, 26.9, -1, -1)], h)
    d.decal("mancha_agua", col, 48.2, 25.8, 1.0, 1.0)


def sala_gerente(col, col_disj):
    h = teto("Sala_Gerente")
    px, pz, _ = P["pista_recado_gerente"]
    mesa = d.caixas("Escrivaninha_Gerente", [((1.6, 0.8, 0.05), (0, 0, 0.72)), ((0.5, 0.75, 0.72), (-0.53, 0, 0)),
                                             ((0.5, 0.75, 0.72), (0.53, 0, 0))], "Mat_Madeira_Envernizada", col)
    det = d.Lote()
    det.caixa((0.25, 0.18, 0.004), (0.0, 0.05, 0.77), "Mat_Papel_Branco", rot=(0, 0, 12))    # o recado
    det.caixa((0.3, 0.2, 0.05), (0.5, 0.15, 0.77), "Mat_Papel_Branco")                         # pilha de papéis
    det.cilindro(0.08, 0.02, (-0.55, 0.2, 0.77), "Mat_Metal_Escuro", lados=8)
    det.tubo([(-0.55, 0.2, 0.79), (-0.5, 0.15, 1.1)], 0.012, "Mat_Metal_Escuro")
    det.cilindro(0.12, 0.12, (-0.5, 0.12, 1.05), "Mat_Abajur_Verde", lados=8, raio_topo=0.07)   # abajur verde
    d.montar(mesa, [det.objeto("Escrivaninha_Gerente_Objetos", col), d.colisao("Escrivaninha", (1.6, 0.8, 0.77), (0, 0, 0), col)],
             px, pz + 0.3, 0.0, "norte")
    d.marcador("Pista__recado_gerente", col, px, pz, 0.8)
    d.marcador("Luz__abajur_05", col, px - 0.5, pz + 0.4, 1.1)
    poltrona = d.caixas("Cadeira_Gerente", [((0.6, 0.6, 0.45), (0, 0, 0)), ((0.6, 0.12, 0.6), (0, 0.27, 0.45))], "Mat_Cadeira_Couro", col)
    d.montar(poltrona, [d.colisao("Cadeira_Gerente", (0.6, 0.6, 0.9), (0, 0, 0), col)], px, pz + 1.3, 0.0, "norte", 8)
    cofre = d.caixas("Cofre_Gerente", [((0.6, 0.6, 0.8), (0, 0, 0))], "Mat_Metal_Escuro", col)
    roda = d.Lote()
    roda.cilindro(0.08, 0.03, (0, -0.31, 0.45), "Mat_Metal_Cinza", rot=(90, 0, 0), lados=10)
    d.montar(cofre, [roda.objeto("Cofre_Gerente_Roda", col), d.colisao("Cofre", (0.6, 0.6, 0.8), (0, 0, 0), col)], 54.6, 26.3, 0.0, "norte")
    arq = d.caixas("Arquivo_Aco_Gerente", [((0.5, 0.6, 1.3), (0, 0, 0))], "Mat_Metal_Pintado_Azul", col)
    d.montar(arq, [d.colisao("Arquivo_Aco", (0.5, 0.6, 1.3), (0, 0, 0), col)], 54.5, 20.0, 0.0, "leste")
    quadro = d.caixas("Quadro_Recortes", [((1.0, 0.03, 0.7), (0, 0, 0))], "Mat_Cortica", col)
    rec = d.Lote()
    for i in range(6):
        rec.caixa((0.18, 0.004, 0.14), (-0.35 + (i % 3) * 0.3, -0.018, 0.12 + (i // 3) * 0.3), "Mat_Papel_Branco", rot=(0, SORTE.uniform(-10, 10), 0))
    d.montar(quadro, [rec.objeto("Quadro_Recortes_Papeis", col)], 54.12, 23.5, 1.3, "leste")
    relogio = d.Lote()
    relogio.cilindro(0.18, 0.04, (0, 0, 0), "Mat_Plastico_Branco", rot=(90, 0, 0), lados=12)
    relogio.caixa((0.02, 0.01, 0.12), (0, -0.04, -0.02), "Mat_Plastico_Preto", rot=(0, 40, 0))
    rl = relogio.objeto("Relogio_Parede_Gerente", col)
    d.montar(rl, [], 57.0, 26.88, 2.2, "norte")
    disjuntor(col_disj, "Gerente", "GERENTE", "disjuntor_gerente")
    d.teias("Teias_Gerente", col, [(54.1, 26.9, 1, -1), (59.9, 19.1, -1, 1)], h)
    d.decal("refrigerante", col, 58.5, 24.0, 0.8, 0.8)


def arquivo(col):
    h = teto("Arquivo")
    for i, x in enumerate([51.5, 53.9, 58.4], 1):
        est, f = d.estante(f"Estante_Arquivo_{i}", col, 2.0, 0.45, 2.2, 5, "Mat_Metal_Pintado_Azul", "Mat_Papelao_Caixa",
                           faltando=(3, 8) if i == 2 else ())
        d.montar(est, f, x, 27.4, 0.0, "sul")
    papeis = d.Lote()
    for i in range(10):
        papeis.caixa((0.22, 0.3, 0.003), comum.p2(51 + SORTE.uniform(0, 8), SORTE.uniform(28.5, 30.0), 0.002), "Mat_Papel_Branco",
                     rot=(0, 0, SORTE.uniform(0, 180)))
    papeis.objeto("Papeis_Chao_Arquivo", col)
    caixas_chao = d.Lote()
    caixas_chao.caixa((0.5, 0.4, 0.35), comum.p2(59.4, 30.4, 0), "Mat_Papelao_Caixa", rot=(0, 0, 12))
    caixas_chao.caixa((0.5, 0.4, 0.35), comum.p2(59.4, 30.4, 0.35), "Mat_Papelao_Caixa", rot=(0, 0, -6))
    cc = caixas_chao.objeto("Caixas_Arquivo", col)
    d.teias("Teias_Arquivo", col, [(50.1, 30.9, 1, -1), (59.9, 30.9, -1, -1)], h)
    d.decal("mancha_agua", col, 56.0, 29.5, 1.5, 1.2)


def copa(col):
    h = teto("Copa")
    mesa = d.caixas("Mesa_Copa", [((1.4, 0.9, 0.04), (0, 0, 0.72)), ((0.06, 0.06, 0.72), (-0.6, -0.35, 0)),
                                  ((0.06, 0.06, 0.72), (0.6, -0.35, 0)), ((0.06, 0.06, 0.72), (-0.6, 0.35, 0)),
                                  ((0.06, 0.06, 0.72), (0.6, 0.35, 0))], "Mat_Plastico_Branco", col)
    det = d.Lote()
    det.cilindro(0.04, 0.1, (0.3, 0.1, 0.76), "Mat_Plastico_Vermelho", lados=8)
    det.caixa((0.3, 0.22, 0.004), (-0.3, 0.0, 0.76), "Mat_Papel_Branco", rot=(0, 0, 20))
    d.montar(mesa, [det.objeto("Mesa_Copa_Objetos", col), d.colisao("Mesa_Copa", (1.4, 0.9, 0.76), (0, 0, 0), col)], 51.0, 36.0, 0.0, "sul")
    for i, (x, z, fr, g) in enumerate([(51.0, 35.2, "sul", 10), (51.0, 36.85, "norte", -15), (50.0, 36.0, "leste", 25), (52.2, 36.2, "oeste", 60)], 1):
        cad = d.caixas(f"Cadeira_Copa_{i}", [((0.42, 0.42, 0.04), (0, 0, 0.44)), ((0.42, 0.04, 0.45), (0, 0.2, 0.46)),
                                             ((0.03, 0.03, 0.44), (-0.18, -0.18, 0)), ((0.03, 0.03, 0.44), (0.18, 0.18, 0))],
                       "Mat_Plastico_Laranja", col)
        d.montar(cad, [], x, z, 0.0, fr, g)
    banc = d.caixas("Bancada_Copa", [((2.2, 0.6, 0.9), (0, 0, 0))], "Mat_Madeira_Velha", col)
    eletro = d.Lote()
    eletro.caixa((0.5, 0.35, 0.3), (-0.5, 0.05, 0.9), "Mat_Plastico_Branco")      # micro-ondas
    eletro.caixa((0.2, 0.15, 0.3), (0.5, 0.1, 0.9), "Mat_Metal_Escuro")           # cafeteira
    d.montar(banc, [eletro.objeto("Bancada_Copa_Eletros", col), d.colisao("Bancada_Copa", (2.2, 0.6, 0.9), (0, 0, 0), col)],
             58.3, 31.45, 0.0, "sul")
    gel = d.caixas("Geladeira_Copa", [((0.75, 0.7, 1.8), (0, 0, 0))], "Mat_Plastico_Branco", col)
    d.montar(gel, [d.colisao("Geladeira_Copa", (0.75, 0.7, 1.8), (0, 0, 0), col)], 59.5, 33.8, 0.0, "oeste")
    d.marcador("Som__geladeira_02", col, 59.3, 33.8, 1.0)
    movel = d.caixas("Movel_TV_Copa", [((1.0, 0.45, 0.6), (0, 0, 0))], "Mat_Madeira_Velha", col)
    tv = d.caixas("TV_Copa", [((0.6, 0.45, 0.48), (0, 0.05, 0.6))], "Mat_Plastico_Preto", col)
    tela = d.plano_uv("TV_Copa_Tela", [(-0.24, -0.176, 0.66), (0.24, -0.176, 0.66), (0.24, -0.176, 1.02), (-0.24, -0.176, 1.02)],
                      "Mat_Tela_TV_Copa", col)
    tela.parent = tv
    d.montar(movel, [tv, d.colisao("Movel_TV_Copa", (1.0, 0.45, 1.1), (0, 0, 0), col)], 59.5, 42.0, 0.0, "oeste")
    # Quadro de avisos com escala de horários e um bilhete estranho (pista do código).
    qx, qz, _ = P["pista_quadro_avisos"]
    quadro = d.caixas("Quadro_Avisos_Copa", [((1.1, 0.03, 0.75), (0, 0, 0))], "Mat_Cortica", col)
    papeis = d.Lote()
    for i, mat in enumerate(["Mat_Papel_Branco", "Mat_Papel_Branco", "Mat_Postit_Amarelo", "Mat_Papel_Branco", "Mat_Postit_Rosa"]):
        papeis.caixa((0.22, 0.004, 0.28 if "Papel" in mat else 0.09), (-0.4 + i * 0.2, -0.018, 0.15 + (i % 2) * 0.3), mat,
                     rot=(0, SORTE.uniform(-8, 8), 0))
    escala = d.texto("Quadro_Avisos_Escala", "ESCALA\nNOITE: VIGIA", 0.035, "Mat_Texto_Preto", (col), (-0.4, -0.022, 0.5),
                     largura_max=0.2, fonte_chave="Courier")
    d.montar(quadro, [papeis.objeto("Quadro_Avisos_Papeis", col), escala], qx - 0.02, qz, 1.25, "oeste")
    d.marcador("Pista__quadro_avisos", col, qx - 0.3, qz, 1.5)
    grade_duto("Duto_Grade_Copa", col, 53.0, 44.85, "norte")
    d.marcador("Esconderijo__duto_02", col, 53.0, 44.4, 0.0)
    lixo = d.Lote()
    lixo.cilindro(0.2, 0.55, comum.p2(47.5, 44.4, 0), "Mat_Plastico_Preto", lados=10)
    for i in range(4):
        lixo.caixa((0.15, 0.15, 0.06), comum.p2(47.8 + SORTE.uniform(0, 0.6), 44.0 + SORTE.uniform(-0.3, 0.3), 0), "Mat_Papel_Branco",
                   rot=(SORTE.uniform(0, 40), 0, SORTE.uniform(0, 180)))
    lixo.objeto("Lixo_Copa", col)
    d.marcador("Luz__fluorescente_04", col, 52.0, 38.0, h - 0.1)
    d.teias("Teias_Copa", col, [(47.1, 31.1, 1, 1), (59.9, 44.9, -1, -1)], h)
    d.decal("refrigerante", col, 51.5, 37.4, 0.8, 0.8)
    d.decal("pegadas", col, 49.0, 38.0, 0.6, 2.2, giro=90)


def armario_limpeza(col):
    h = teto("Armario_Limpeza")
    lote = d.Lote()
    for i, mat in enumerate(["Mat_Plastico_Azul", "Mat_Plastico_Amarelo"]):
        lote.cilindro(0.15, 0.3, comum.p2(49.55, 29.85 + i * 0.35, 0), mat, lados=8, raio_topo=0.13)   # baldes
    for i in range(2):
        lote.tubo([comum.p2(49.85, 30.75 - i * 0.2, 0.02), comum.p2(49.8, 30.8 - i * 0.2, 1.4)], 0.015, "Mat_Madeira_Velha", lados=4)  # vassouras
    lote.caixa((0.25, 0.6, 0.03), comum.p2(49.8, 30.2, 1.6), "Mat_Madeira_Velha")   # prateleira
    for i in range(3):
        lote.cilindro(0.04, 0.2, comum.p2(49.8, 29.95 + i * 0.2, 1.63), ["Mat_Plastico_Verde", "Mat_Plastico_Rosa", "Mat_Plastico_Branco"][i], lados=6)
    lote.objeto("Material_Limpeza", col)
    d.marcador("Esconderijo__armario_limpeza_01", col, 48.5, 30.25, 0.0)


def corredor_funcionarios(col):
    h = teto("Corredor_Funcionarios")
    placa = d.caixas("Placa_Somente_Funcionarios", [((1.1, 0.03, 0.25), (0, 0, 0))], "Mat_Metal_Pintado_Amarelo", col)
    txt = d.texto("Placa_Somente_Funcionarios_Texto", "SOMENTE FUNCIONÁRIOS", 0.07, "Mat_Texto_Preto", col, (0, -0.02, 0.12),
                  largura_max=1.0)
    d.montar(placa, [txt], 45.5, 19.15, 2.4, "sul")
    carrinho = d.Lote()
    carrinho.caixa((0.8, 0.35, 0.05), (0, 0, 0.12), "Mat_Plastico_Amarelo")
    carrinho.cilindro(0.17, 0.35, (0.2, 0, 0.17), "Mat_Plastico_Azul", lados=8)
    carrinho.tubo([(-0.35, 0, 0.17), (-0.35, 0, 1.0)], 0.015, "Mat_Metal_Cinza")
    car = carrinho.objeto("Carrinho_Limpeza_Funcionarios", col)
    d.montar(car, [d.colisao("Carrinho_Limpeza", (0.8, 0.38, 0.6), (0, 0, 0), col)], 46.6, 42.5, 0.0, "oeste")
    ext = d.Lote()
    ext.cilindro(0.08, 0.55, (0, 0, 0.3), "Mat_Plastico_Vermelho", lados=8)
    ext.caixa((0.28, 0.02, 0.28), (0, 0.06, 0.9), "Mat_Plastico_Vermelho")
    e = ext.objeto("Extintor_Funcionarios", col)
    d.montar(e, [], 44.2, 35.0, 0.0, "leste")
    for i, z in enumerate([25.0, 33.0, 41.0], 1):
        av = d.caixas(f"Aviso_Interno_{i}", [((0.3, 0.004, 0.42), (0, 0, 0))], "Mat_Papel_Branco", col)
        d.montar(av, [], 44.12, z, 1.3, "leste", SORTE.uniform(-4, 4))
    d.marcador("Luz__emergencia_06", col, 45.5, 44.75, 2.6)
    d.marcador("Luz__fluorescente_05", col, 45.5, 30.0, h - 0.1)
    d.teias("Teias_Corredor_Funcionarios", col, [(44.1, 44.9, 1, -1), (46.9, 19.1, -1, 1)], h)
    d.decal("pegadas", col, 45.5, 36.0, 0.6, 4.0)
    d.decal("mancha_agua", col, 45.0, 27.0, 1.0, 1.0)


# ---------------------------------------------------------------------------

def gerar():
    comum.limpar_cena()
    for tabela in (d.CORES_DIVERSAO, CORES_SERVICO):
        for nome, (cor, em) in tabela.items():
            comum.material(nome, cor, em)
    cols = {nome: comum.colecao(nome) for nome in COMODOS_GRUPO}
    col_disj = comum.colecao(COLECAO_DISJUNTORES)

    sala_seguranca(cols["Sala_Seguranca"])
    oficina(cols["Oficina"])
    deposito(cols["Deposito"], col_disj)
    sala_eletrica(cols["Sala_Eletrica"], col_disj)
    vestiario(cols["Vestiario"])
    sala_gerente(cols["Sala_Gerente"], col_disj)
    arquivo(cols["Arquivo"])
    copa(cols["Copa"])
    armario_limpeza(cols["Armario_Limpeza"])
    corredor_funcionarios(cols["Corredor_Funcionarios"])

    bpy.context.view_layer.update()
    problemas = comum.conferir_areas_livres_v2(permitidos=("Gerador_Principal", "Entulho_Porta"))
    alturas = {c[0]: c[6] for c in planta_v2.COMODOS}
    for nome in COMODOS_GRUPO:
        for obj in bpy.data.collections[nome].all_objects:
            if obj.type == "MESH":
                topo = max((obj.matrix_world @ V(c)).z for c in obj.bound_box)
                if topo > alturas[nome] + 0.02:
                    problemas.append(f"{obj.name} passa do teto ({topo:.2f} > {alturas[nome]})")
    for p in problemas:
        print("PROBLEMA:", p)
    if problemas:
        raise RuntimeError(f"{len(problemas)} problema(s); veja acima.")
    tri = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in bpy.context.scene.objects
              if o.type == "MESH" and not o.name.endswith("-colonly"))
    objs = list(bpy.context.scene.objects)
    print(f"[servico] objetos: {len(objs)} ({sum(o.type == 'EMPTY' for o in objs)} Empties)  triângulos: {tri}")
    comum.salvar_blend(comum.PASTA_BLENDER / "v2_servico.blend")
    comum.exportar_glb(comum.PASTA_CENARIO / "v2_servico.glb")


if __name__ == "__main__":
    gerar()
