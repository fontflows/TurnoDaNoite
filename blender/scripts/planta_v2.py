"""
planta_v2.py — FONTE ÚNICA da planta da V2 (60 x 45 m).

Por que existe: o desenho da planta (docs/PLANO_V2.md) e o cenário gerado no Blender
saem destes mesmos dados, então nunca ficam diferentes.

Coordenadas da planta: x de 0 a 60 (oeste -> leste), z de 0 a 45 (norte -> sul).
Blender: X = x - 30, Y = 22.5 - z.   Godot: X = x - 30, Z = z - 22.5.

Rodar sozinho imprime a planta em ASCII:
    python blender/scripts/planta_v2.py
"""

# (nome da Collection, nome bonito, x0, x1, z0, z1, pé-direito)
COMODOS = [
    ("Salao", "Salão + palco", 14, 40, 0, 16, 3.6),
    ("Oficina", "Oficina / bastidores", 0, 14, 0, 16, 3.2),
    ("Cozinha", "Cozinha", 40, 52, 0, 16, 3.2),
    ("Camara_Fria", "Câmara frigorífica", 52, 60, 0, 8, 2.8),
    ("Banheiros", "Banheiros", 52, 60, 8, 16, 3.0),
    ("Corredor_Principal", "Corredor principal", 0, 60, 16, 19, 3.2),
    ("Deposito", "Depósito", 0, 14, 19, 33, 3.6),
    ("Sala_Eletrica", "Sala elétrica / gerador", 0, 14, 33, 45, 3.2),
    ("Fliperama", "Fliperama + prêmios", 14, 32, 19, 33, 3.2),
    ("Recepcao", "Recepção / entrada", 14, 32, 33, 45, 3.4),
    ("Corredor_Festas", "Corredor das festas", 32, 35, 19, 45, 3.0),
    ("Festa_Estrelas", "Sala de festa Estrelas", 35, 44, 19, 27.5, 3.0),
    ("Festa_Piratas", "Sala de festa Piratas", 35, 44, 27.5, 36, 3.0),
    ("Festa_Princesas", "Sala de festa Princesas", 35, 44, 36, 45, 3.0),
    ("Corredor_Funcionarios", "Corredor dos funcionários", 44, 47, 19, 45, 3.0),
    ("Vestiario", "Vestiário", 47, 54, 19, 27, 3.0),
    ("Sala_Gerente", "Sala do gerente", 54, 60, 19, 27, 3.0),
    ("Sala_Seguranca", "Sala de segurança", 47, 50, 27, 29.5, 2.4),
    ("Armario_Limpeza", "Armário de limpeza", 47, 50, 29.5, 31, 2.4),
    ("Arquivo", "Arquivo morto", 50, 60, 27, 31, 2.8),
    ("Copa", "Copa dos funcionários", 47, 60, 31, 45, 3.0),
]

# Portas: (eixo, coordenada fixa, centro, largura, tipo)
#   eixo "z": porta numa parede horizontal (z fixo), centro em x
#   eixo "x": porta numa parede vertical (x fixo), centro em z
# tipos: livre, vaivem, corrente (alicate), chave (chave do gerente), teclado (código),
#        emperrada (não abre; use o duto), unica (só abre de um lado: 'lado' diz de onde),
#        aco (porta da sala de segurança), pesada (câmara fria), catraca (saída trancada)
PORTAS = [
    ("z", 16, 20, 1.6, "livre", None),          # corredor -> salão (oeste)
    ("z", 16, 34, 1.6, "livre", None),          # corredor -> salão (leste)
    ("z", 16, 7, 1.4, "emperrada", None),       # corredor -> oficina (emperrada)
    ("x", 14, 3, 1.4, "unica", "Oficina"),      # oficina -> palco (atalho só de dentro da oficina)
    ("x", 40, 8, 1.6, "vaivem", None),          # salão <-> cozinha
    ("z", 16, 46, 1.4, "livre", None),          # corredor -> cozinha
    ("x", 52, 4, 1.4, "pesada", None),          # cozinha -> câmara fria
    ("z", 16, 56, 1.4, "livre", None),          # corredor -> banheiros
    ("z", 19, 7, 1.4, "corrente", None),        # corredor -> depósito (corrente + cadeado)
    ("x", 14, 30, 1.4, "unica", "Deposito"),    # depósito -> fliperama (atalho)
    ("z", 19, 18, 1.6, "livre", None),          # corredor -> fliperama
    ("z", 19, 28, 1.6, "livre", None),          # corredor -> fliperama
    ("z", 33, 23, 2.8, "livre", None),          # fliperama <-> recepção
    ("x", 32, 26, 1.4, "livre", None),          # fliperama <-> corredor das festas
    ("x", 14, 39, 1.4, "teclado", None),        # recepção -> sala elétrica (código)
    ("x", 32, 40, 1.4, "livre", None),          # recepção <-> corredor das festas
    ("z", 45, 23, 3.0, "catraca", None),        # saída da frente (trancada, decorativa)
    ("x", 35, 23, 1.4, "livre", None),          # festas -> Estrelas
    ("x", 35, 32, 1.4, "livre", None),          # festas -> Piratas
    ("x", 35, 40, 1.4, "livre", None),          # festas -> Princesas
    ("x", 44, 23, 1.4, "livre", None),          # Estrelas <-> corredor funcionários
    ("x", 44, 40, 1.4, "livre", None),          # Princesas <-> corredor funcionários
    ("z", 19, 45.5, 1.4, "livre", None),        # corredor principal <-> corredor funcionários
    ("z", 19, 57, 1.4, "chave", None),          # corredor -> sala do gerente (chave)
    ("x", 47, 23, 1.4, "livre", None),          # corredor funcionários -> vestiário
    ("x", 47, 28.25, 1.2, "aco", None),         # corredor funcionários -> sala de segurança
    ("x", 47, 30.25, 0.9, "livre", None),       # corredor funcionários -> armário de limpeza
    ("x", 47, 38, 1.4, "livre", None),          # corredor funcionários -> copa
    ("z", 31, 55, 1.2, "livre", None),          # copa -> arquivo morto
]

# Janela de vidro aramado da sala de segurança (parede x=47, para o corredor).
JANELAS = [("x", 47, 29.05, 0.7, "vidro_aramado")]  # (eixo, fixo, centro, largura, tipo); de 1,0 a 1,9 m de altura

# Dutos de ventilação: pontos de entrada (grades) e o tronco que os liga (acima do forro).
DUTO_GRADES = [
    ("Oficina", 11, 15.85),       # grades na parede, perto do chão (o jogador entra agachado)
    ("Cozinha", 45, 12),
    ("Fliperama", 23, 24),
    ("Festa_Piratas", 42, 29),
    ("Copa", 53, 44.85),
]
DUTO_TRONCO_Z = 17.5  # o tronco corre por cima do corredor principal
ALTURA_PALCO = 0.6    # plataforma do palco (gerar_predio_v2.py)

# ---------------------------------------------------------------------------
# PONTOS DE JOGO (x, z da planta; "olha" = para onde a frente do objeto aponta)
# Quem monta móveis precisa deixar estes lugares livres (raio ~1 m) ou colocar a
# peça pedida exatamente ali. O Godot usa os mesmos pontos para marcadores.
# ---------------------------------------------------------------------------
PONTOS = {
    # Jogador e animatrônicos
    "spawn_jogador": (48.2, 28.25, "leste"),          # sentado diante dos monitores
    "palco_tito": (23.5, 2.5, "sul"),
    "palco_pipoca": (30.5, 2.5, "sul"),
    # Palco (plataforma 0,6 m) e escada central na frente
    "palco": (20, 34, 0, 5),                           # x0, x1, z0, z1
    "palco_escada": (25.5, 28.5, 5, 6.5),  # 3 m de largura: cabe o vigia e os animatrônicos
    # Disjuntores (caixa na parede, centro a 1,3 m) e gerador
    "disjuntor_cozinha": (46.0, 0.1, "sul"),           # conserto de fios
    "disjuntor_deposito": (0.1, 30.0, "leste"),
    "disjuntor_gerente": (59.9, 23.0, "oeste"),        # troca de fusível
    "disjuntor_eletrica": (5.0, 44.9, "norte"),
    "gerador": (8.0, 39.0, "oeste"),                   # caixa ~2,4 x 1,2 x 1,6 m
    # Fliperama
    "maquina_tito_kart": (17.0, 19.6, "sul"),
    "maquina_space_pizza": (20.0, 19.6, "sul"),
    "maquina_pipoca_pula_pula": (23.0, 19.6, "sul"),
    "maquina_serpente_neon": (26.0, 19.6, "sul"),      # a que tem defeito
    "maquina_fantasminha": (29.0, 19.6, "sul"),
    "maquina_garra": (16.2, 31.4, "leste"),
    "skee_ball": (30.0, 30.0, "oeste"),
    "balcao_premios": (23.0, 32.2, "norte"),
    # Itens e travas
    "alicate": (4.0, 3.0, "sul"),                       # na bancada da oficina
    "teclado_eletrica": (14.125, 37.9, "leste"),        # do lado da recepção, encostado na parede (face em x = 14,1)
    "pista_aniversario": (39.5, 19.2, "sul"),           # pôster com a data (sala Estrelas)
    "pista_quadro_avisos": (59.8, 37.0, "oeste"),       # quadro de avisos da copa
    "pista_recado_gerente": (57.0, 21.5, "sul"),        # em cima da escrivaninha
    # Candidatos a pilha (o jogo sorteia/escolhe conforme a dificuldade; os primeiros são os arriscados)
    "pilhas": [(27.0, 1.2), (57.0, 1.5), (2.0, 44.0), (2.0, 20.0), (43.0, 35.0), (59.0, 15.0)],
    # Candidatos a ficha
    "fichas": [(23.0, 31.0), (54.0, 41.0), (50.0, 20.5), (39.5, 21.5), (39.5, 30.0), (39.5, 43.0), (18.0, 36.0), (42.0, 13.5)],
    # Esconderijos (tipo, x, z)
    "esconderijos": [
        ("armario", 53.5, 20.5), ("armario", 53.5, 22.0), ("armario", 53.5, 23.5), ("armario", 53.5, 25.0),
        ("cabine", 58.5, 9.5), ("cabine", 58.5, 11.5), ("cabine", 58.5, 13.5),
        ("mesa_toalha", 39.5, 23.25), ("mesa_toalha", 39.5, 31.75), ("mesa_toalha", 39.5, 40.5),
        ("cortina_palco", 20.6, 1.0), ("cortina_palco", 33.4, 1.0),
        ("figurinos", 2.0, 13.0), ("armario_limpeza", 48.5, 30.25),
    ],
    # Patrulha da Pipoca
    "patrulha": [(18, 10), (36, 10), (46, 8), (5, 17.5), (30, 17.5), (55, 17.5), (23, 26),
                 (23, 40), (33.5, 30), (45.5, 34), (53, 38), (7, 26)],
    # Câmeras de segurança: (nome, x, z, altura, olha_para_x, olha_para_z, disjuntor que a liga ou None)
    "cameras": [
        ("CAM 1 - Palco", 27.0, 14.5, 3.0, 27.0, 2.0, None),
        ("CAM 2 - Fliperama", 15.0, 20.0, 2.8, 30.0, 32.0, "cozinha"),
        ("CAM 3 - Corredor", 1.0, 17.5, 2.8, 60.0, 17.5, None),
        ("CAM 4 - Recepção", 31.0, 44.0, 3.0, 16.0, 34.0, None),
        ("CAM 5 - Festas", 33.5, 44.5, 2.7, 33.5, 19.0, "deposito"),
        ("CAM 6 - Cozinha", 51.0, 15.0, 2.8, 41.0, 1.0, "cozinha"),
    ],
}

# Qual disjuntor devolve a energia de quais cômodos (luzes fluorescentes, neons e telas).
# Emergência, claraboias (luar) e o abajur da sala de segurança não dependem de disjuntor.
# O palco (holofotes) e as luzes do salão só voltam com o gerador principal.
ENERGIA = {
    "cozinha": ["Cozinha", "Fliperama", "Camara_Fria"],
    "deposito": ["Deposito", "Corredor_Festas", "Festa_Estrelas", "Festa_Piratas", "Festa_Princesas"],
    "gerente": ["Sala_Gerente", "Vestiario", "Copa", "Arquivo", "Corredor_Funcionarios", "Armario_Limpeza"],
    "eletrica": ["Sala_Eletrica", "Recepcao", "Oficina", "Banheiros", "Corredor_Principal"],
    "gerador": ["Salao"],
}


def altura_do_piso(x, z):
    """
    Altura do chão no ponto (x, z) da planta: 0,6 m em cima do palco, a altura do degrau na
    escada e 0 no resto. Quem põe coisas no chão (pilhas, fichas) usa isto; antes a pilha do
    palco ficava na altura 0, ENTERRADA dentro da plataforma (só a luzinha aparecia).
    """
    x0, x1, z0, z1 = PONTOS["palco"]
    if x0 <= x <= x1 and z0 <= z <= z1:
        return ALTURA_PALCO
    ex0, ex1, ez0, ez1 = PONTOS["palco_escada"]
    if ex0 <= x <= ex1 and ez0 <= z <= ez1:
        degraus = 4
        k = min(degraus, int((ez1 - z) / ((ez1 - ez0) / degraus)) + 1)
        return ALTURA_PALCO * k / degraus
    return 0.0


def exportar_json(caminho):
    """Grava a planta em JSON para o Godot (godot/assets/dados/planta_v2.json)."""
    import json
    from pathlib import Path
    dados = {
        "comodos": [{"nome": n, "titulo": t, "x0": x0, "x1": x1, "z0": z0, "z1": z1, "altura": h}
                    for n, t, x0, x1, z0, z1, h in COMODOS],
        "portas": [{"eixo": e, "fixo": f, "centro": c, "largura": l, "tipo": tp, "lado": ld} for e, f, c, l, tp, ld in PORTAS],
        "pontos": PONTOS,
        "duto_grades": [{"comodo": n, "x": x, "z": z} for n, x, z in DUTO_GRADES],
        "energia": ENERGIA,
    }
    Path(caminho).parent.mkdir(parents=True, exist_ok=True)
    Path(caminho).write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")


SIMBOLO_PORTA = {
    "livre": " ", "vaivem": " ", "corrente": "&", "chave": "K", "teclado": "#",
    "emperrada": "X", "unica": ">", "aco": "S", "pesada": "P", "catraca": "=",
}

MARCAS = [  # (x, z, símbolo) — pontos importantes no desenho
    (22, 3.5, "T"), (31, 3.5, "P"),  # Tito e Pipoca no palco (a escada fica no meio)
    (48.5, 28.25, "*"),              # início e vitória
]


def desenhar(escala_z=1.5):
    """Desenha a planta: 1 caractere = 1 m na horizontal, 1 linha = 1,5 m na vertical."""
    largura, altura = 61, int(45 / escala_z) + 1
    grade = [[" "] * largura for _ in range(altura)]

    def lin(z):
        return int(round(z / escala_z))

    for _, _, x0, x1, z0, z1, _ in COMODOS:
        for x in range(int(x0), int(round(x1)) + 1):
            for z in (z0, z1):
                grade[lin(z)][x] = "-"
        for z in range(lin(z0), lin(z1) + 1):
            for x in (x0, x1):
                grade[z][int(round(x))] = "|"
        for x, z in ((x0, z0), (x1, z0), (x0, z1), (x1, z1)):
            grade[lin(z)][int(round(x))] = "+"

    for eixo, fixo, centro, larg, tipo, _ in PORTAS:
        s = SIMBOLO_PORTA[tipo]
        if eixo == "z":
            for x in range(int(round(centro - larg / 2 + 0.3)), int(round(centro + larg / 2 - 0.3)) + 1):
                grade[lin(fixo)][x] = s
        else:
            grade[lin(centro)][int(round(fixo))] = s

    for nome, x, z in DUTO_GRADES:
        grade[lin(z)][x] = "v"
    for x, z, s in MARCAS:
        grade[lin(z)][int(round(x))] = s

    rotulos = {
        "Salao": "SALAO", "Oficina": "OFICINA", "Cozinha": "COZINHA", "Camara_Fria": "FRIA",
        "Banheiros": "WC", "Corredor_Principal": "CORREDOR PRINCIPAL", "Deposito": "DEPOSITO",
        "Sala_Eletrica": "ELETRICA", "Fliperama": "FLIPERAMA", "Recepcao": "RECEPCAO",
        "Festa_Estrelas": "ESTRELAS", "Festa_Piratas": "PIRATAS", "Festa_Princesas": "PRINCESAS",
        "Vestiario": "VESTIAR", "Sala_Gerente": "GER.", "Arquivo": "ARQUIVO", "Copa": "COPA",
    }
    for nome, _, x0, x1, z0, z1, _ in COMODOS:
        if nome not in rotulos:
            continue
        txt = rotulos[nome]
        zc = lin((z0 + z1) / 2)
        xc = int((x0 + x1) / 2 - len(txt) / 2 + 0.5)
        for i, ch in enumerate(txt):
            if 0 < xc + i < largura and grade[zc][xc + i] == " ":
                grade[zc][xc + i] = ch

    linhas = []
    for i, linha in enumerate(grade):
        z = i * escala_z
        rotulo = f"z={z:<4g}" if z == int(z) and int(z) in (0, 16, 19, 27, 33, 45) else "      "
        linhas.append(rotulo + " " + "".join(linha).rstrip())
    regua = "       " + "".join(str(x // 10) if x % 10 == 0 else " " for x in range(largura))
    return regua + "\n" + "\n".join(linhas)


def conferir():
    """Confere se os cômodos não se sobrepõem e cobrem o retângulo 60 x 45 inteiro."""
    area = sum((x1 - x0) * (z1 - z0) for _, _, x0, x1, z0, z1, _ in COMODOS)
    for i, a in enumerate(COMODOS):
        for b in COMODOS[i + 1:]:
            if a[2] < b[3] and b[2] < a[3] and a[4] < b[5] and b[4] < a[5]:
                raise ValueError(f"Cômodos sobrepostos: {a[0]} e {b[0]}")
    if abs(area - 60 * 45) > 1e-6:
        raise ValueError(f"Os cômodos cobrem {area} m², mas o prédio tem {60 * 45} m².")
    return area


if __name__ == "__main__":
    import sys
    from pathlib import Path
    print(f"Área conferida: {conferir()} m² sem sobreposição")
    if "--json" in sys.argv:
        destino = Path(__file__).resolve().parents[2] / "godot" / "assets" / "dados" / "planta_v2.json"
        exportar_json(destino)
        print("planta exportada:", destino)
    else:
        print(desenhar())
