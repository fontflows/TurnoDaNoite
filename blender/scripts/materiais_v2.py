"""
materiais_v2.py — quais materiais usam textura, e com que escala e "tinta".

Arquivo sem bpy de propósito: é lido pelo Blender (comum.py) E pelo gerador dos
materiais do Godot (ferramentas/gerar_materiais_godot.py), para os dois ficarem iguais.

Cada linha:  "Nome_do_Material": (pasta_da_textura, metros_por_repeticao, tinta)
  - pasta_da_textura: pasta em godot/assets/texturas/
  - metros_por_repeticao: tamanho real de 1 repetição da textura (sem esticar)
  - tinta: cor "#RRGGBB" que MULTIPLICA a textura ("#ffffff" = cor original).
    Para deixar a cortina azul, por exemplo, basta trocar a tinta (ou a Albedo Color no Godot).
Materiais que não estão aqui continuam com cor lisa (telas, letreiros, olhos...).
"""

TEXTURIZADOS = {
    # --- Pisos ---
    "Mat_Piso_Quadriculado": ("quadriculado_gasto", 2.0, "#ffffff"),
    "Mat_Carpete_Fliperama": ("carpete_fliperama", 3.0, "#ffffff"),
    "Mat_Piso_Azulejo_Azul": ("azulejo_branco", 1.0, "#9fc2d6"),
    "Mat_Piso_Concreto": ("concreto", 2.5, "#b8b2a8"),
    "Mat_Chapa_Antiderrapante": ("chapa_antiderrapante", 1.0, "#ffffff"),
    # --- Tetos ---
    "Mat_Teto_Escuro": ("forro_manchado", 1.2, "#8f8a80"),
    # --- Paredes ---
    "Mat_Parede_Creme": ("reboco_pintado", 2.0, "#e6dcc0"),
    "Mat_Papel_Parede_Festa": ("papel_parede_festa", 1.0, "#ffffff"),
    "Mat_Parede_Concreto": ("concreto", 2.5, "#c9c2b5"),
    "Mat_Parede_Externa": ("tijolo", 1.5, "#ffffff"),
    # Faixa de baixo das paredes = lambri de madeira pintado com a cor do cômodo
    "Mat_Faixa_Vermelha": ("madeira_lambri", 1.2, "#c04a40"),
    "Mat_Faixa_Azul_Petroleo": ("madeira_lambri", 1.2, "#4f8c99"),
    "Mat_Faixa_Azulejo_Branco": ("azulejo_branco", 0.6, "#ffffff"),
    "Mat_Faixa_Roxa": ("madeira_lambri", 1.2, "#8f5fb0"),
    "Mat_Faixa_Azul_Claro": ("azulejo_branco", 0.6, "#b9dcec"),
    "Mat_Faixa_Verde_Oliva": ("madeira_lambri", 1.2, "#8c9a5a"),
    "Mat_Faixa_Amarela": ("madeira_lambri", 1.2, "#e0b54e"),
    "Mat_Faixa_Cinza": ("concreto", 2.0, "#9c9890"),
    # --- Palco e portas ---
    "Mat_Palco_Madeira": ("madeira_palco", 2.0, "#ffffff"),
    "Mat_Batente_Madeira": ("madeira_lambri", 1.0, "#8a6a52"),
    "Mat_Porta_Metal": ("metal_pintado", 1.0, "#9aa3a8"),
    "Mat_Cortina_Vermelha": ("veludo", 0.8, "#b0242a"),
    # --- Móveis e props ---
    "Mat_Madeira_Clara": ("madeira_lambri", 1.0, "#ffffff"),
    "Mat_Madeira_Escura": ("madeira_lambri", 1.0, "#7a5a44"),
    "Mat_Metal_Cinza": ("metal_escovado", 0.8, "#ffffff"),
    "Mat_Metal_Escuro": ("metal_pintado", 0.8, "#6a6e72"),
    "Mat_Plastico_Preto": ("plastico", 0.5, "#3a3a3a"),
    "Mat_Plastico_Branco": ("plastico", 0.5, "#f2efe6"),
    "Mat_Plastico_Vermelho": ("plastico", 0.5, "#d0383c"),
    "Mat_Plastico_Amarelo": ("plastico", 0.5, "#f0c33a"),
    "Mat_Plastico_Azul": ("plastico", 0.5, "#3f78c8"),
    "Mat_Plastico_Verde": ("plastico", 0.5, "#4fa85a"),
    "Mat_Toalha_Xadrez_Vermelha": ("veludo", 0.5, "#d65a5a"),
    "Mat_Toalha_Branca": ("veludo", 0.5, "#efe9dc"),
    "Mat_Papelao": ("reboco_pintado", 0.6, "#b08a5a"),
    "Mat_Disjuntor_Caixa": ("metal_pintado", 0.4, "#a0a6a8"),
    # --- Genéricos da V2 (use estes nomes nos geradores de móveis) ---
    "Mat_Madeira_Velha": ("madeira_lambri", 1.0, "#8f7258"),
    "Mat_Madeira_Envernizada": ("madeira_palco", 1.5, "#ffffff"),
    "Mat_Inox": ("metal_escovado", 0.8, "#d8dadc"),
    "Mat_Metal_Enferrujado": ("ferrugem", 0.8, "#ffffff"),
    "Mat_Metal_Pintado_Verde": ("metal_pintado", 0.8, "#6f8f6a"),
    "Mat_Metal_Pintado_Azul": ("metal_pintado", 0.8, "#5a76a0"),
    "Mat_Metal_Pintado_Amarelo": ("metal_pintado", 0.8, "#d8b04a"),
    "Mat_Papelao_Caixa": ("reboco_pintado", 0.6, "#b4895a"),
    "Mat_Lencol_Branco": ("veludo", 0.8, "#e8e4da"),
    "Mat_Tecido_Figurino_Vermelho": ("veludo", 0.5, "#b03a3a"),
    "Mat_Tecido_Figurino_Azul": ("veludo", 0.5, "#3a5fb0"),
    "Mat_Tecido_Figurino_Amarelo": ("veludo", 0.5, "#d8b84a"),
    "Mat_Azulejo_Cozinha": ("azulejo_branco", 0.6, "#f2efe6"),
    "Mat_Concreto_Sujo": ("concreto", 2.0, "#8a857c"),
    "Mat_Tijolo_Aparente": ("tijolo", 1.5, "#ffffff"),
    "Mat_Plastico_Rosa": ("plastico", 0.5, "#e07aa8"),
    "Mat_Plastico_Lilas": ("plastico", 0.5, "#b08ae0"),
    "Mat_Plastico_Laranja": ("plastico", 0.5, "#e8873a"),
    "Mat_Carpete_Fliperama_Gasto": ("carpete_fliperama", 3.0, "#b8b0a8"),
    "Mat_Faixa_Rosa": ("madeira_lambri", 1.2, "#d88aa8"),
    "Mat_Faixa_Marrom": ("madeira_lambri", 1.2, "#8a5a3a"),
    # --- Objetos pequenos e props (AJUSTES V2.2 §3.5): todos ganham textura ---
    # A tinta é a mesma cor que o material tinha antes (a textura só dá o "material" por baixo).
    # Papel e papelão
    "Mat_Papel_Branco": ("papel", 0.4, "#e8e4d6"),          # pratos, copos, convites (e o fundo dos Arte__)
    "Mat_Papel_Amarelado": ("papel", 0.4, "#d6c693"),
    "Mat_Papel_Amarelo": ("papel", 0.3, "#e3cf6a"),
    "Mat_Papel_Toalha": ("papel", 0.3, "#ddd8c8"),
    "Mat_Postit_Amarelo": ("papel", 0.2, "#f0dc6a"),
    "Mat_Postit_Rosa": ("papel", 0.2, "#f08ab0"),
    "Mat_Ticket": ("papel", 0.2, "#e8873a"),
    "Mat_Faixa_Papel": ("papel", 0.6, "#f0e2a8"),
    "Mat_Estrela_Recortada": ("papelao", 0.5, "#d9b84a"),
    "Mat_Caixa_Pizza": ("papelao", 0.5, "#c9a46a"),
    "Mat_Papelao_Pintado_Cinza": ("papelao", 0.8, "#8e98a8"),
    "Mat_Cortica": ("cortica", 0.4, "#a07a4a"),
    # Tecidos, cordas e franjas
    "Mat_Toalha_Azul_Noite": ("tecido", 0.3, "#1f2c5a"),
    "Mat_Toalha_Pirata": ("tecido", 0.3, "#5a1f1f"),
    "Mat_Toalha_Rosa": ("tecido", 0.3, "#e0a0c0"),
    "Mat_Tule_Rosa": ("tecido", 0.2, "#f0c8dc"),
    "Mat_Tecido_Preto": ("tecido", 0.3, "#2a2a2a"),
    "Mat_Tela_Alto_Falante": ("tecido", 0.15, "#2a2622"),
    "Mat_Corda": ("tecido", 0.1, "#b89a6a"),
    "Mat_Franja_Dourada": ("tecido", 0.2, "#c9a03a"),
    "Mat_Letreiro_Arco": ("veludo", 0.8, "#7a1c22"),
    "Mat_Pele_Animatronico": ("veludo", 0.3, "#8a6a4a"),
    "Mat_Cadeira_Couro": ("veludo", 0.4, "#3a2e28"),
    # Plásticos, louça e brinquedos
    "Mat_Louca_Branca": ("plastico", 0.5, "#e6e4dc"),
    "Mat_Crt_Bege": ("plastico", 0.5, "#cfc6b0"),
    "Mat_Disjuntor_Alavanca": ("plastico", 0.3, "#c22d22"),
    "Mat_Fusivel_Bom": ("plastico", 0.2, "#d8d0b8"),
    "Mat_Fusivel_Queimado": ("plastico", 0.2, "#2a2420"),
    "Mat_Capsula_Chave": ("plastico", 0.3, "#f2c84a"),
    "Mat_Engradado": ("plastico", 0.5, "#2f5f8f"),
    "Mat_Mesa_Hoquei": ("plastico", 0.8, "#e8e8f0"),
    "Mat_Pinball_Mesa": ("plastico", 0.6, "#3a2a8a"),
    "Mat_Vela_Azul": ("plastico", 0.2, "#7fb0e0"),
    "Mat_Cafe": ("plastico", 0.3, "#3a2a20"),
    "Mat_Cinzeiro": ("plastico", 0.3, "#5a5a5a"),
    "Mat_Fio": ("plastico", 0.3, "#2a2a2a"),
    "Mat_Fio_Vermelho": ("plastico", 0.3, "#c22a22"),
    "Mat_Fio_Amarelo": ("plastico", 0.3, "#e0c02a"),
    "Mat_Fio_Azul": ("plastico", 0.3, "#2a52c2"),
    "Mat_Bolo_Rosa": ("reboco_pintado", 0.3, "#e8a0b8"),     # cobertura de bolo: textura "de reboco" parece glacê
    "Mat_Bolo_Creme": ("reboco_pintado", 0.3, "#f0e0c0"),
    "Mat_Farinha": ("reboco_pintado", 0.4, "#ece6d6"),
    "Mat_Vaso_Terracota": ("reboco_pintado", 0.4, "#9c5a3a"),
    "Mat_Gelo": ("concreto", 0.5, "#e4f4fa"),                # gelo/escarcha da câmara fria
    "Mat_Cinza_Forno": ("concreto", 0.5, "#4a4542"),
    "Mat_Tijolo_Forno": ("tijolo", 1.0, "#c06a50"),
    # Madeiras pequenas
    "Mat_Lenha": ("madeira_lambri", 0.4, "#6b4a2e"),
    "Mat_Bola_Madeira": ("madeira_lambri", 0.2, "#b8874a"),
    "Mat_Planta_Seca": ("madeira_lambri", 0.3, "#6b5236"),
    # Metais e peças pintadas (máquinas, gerador, grades)
    "Mat_Ouro": ("metal_escovado", 0.3, "#d4a832"),
    "Mat_Cobre": ("metal_escovado", 0.3, "#c07a40"),
    "Mat_Gordura": ("ferrugem", 0.5, "#8a7a5a"),
    "Mat_Porta_Aco": ("metal_pintado", 1.0, "#7d8286"),
    "Mat_Grade_Duto": ("metal_pintado", 0.5, "#4a4c4e"),
    "Mat_Abajur_Verde": ("metal_pintado", 0.4, "#2f6a3a"),
    "Mat_Gerador_Amarelo": ("metal_pintado", 1.0, "#c9a227"),
    "Mat_Perigo_Faixa": ("metal_pintado", 0.6, "#2a2a2a"),
    "Mat_Garra_Corpo": ("metal_pintado", 0.8, "#d8402e"),
    "Mat_Garra_Detalhe": ("metal_pintado", 0.5, "#f0c33a"),
    "Mat_Arcade_Tito_Kart": ("metal_pintado", 0.8, "#c8302a"),
    "Mat_Arcade_Tito_Kart_Detalhe": ("metal_pintado", 0.5, "#f0c33a"),
    "Mat_Arcade_Space_Pizza": ("metal_pintado", 0.8, "#1d3a8a"),
    "Mat_Arcade_Space_Pizza_Detalhe": ("metal_pintado", 0.5, "#ff8a2a"),
    "Mat_Arcade_Pipoca_Pula_Pula": ("metal_pintado", 0.8, "#e07aa8"),
    "Mat_Arcade_Pipoca_Pula_Pula_Detalhe": ("metal_pintado", 0.5, "#b08ae0"),
    "Mat_Arcade_Serpente_Neon": ("metal_pintado", 0.8, "#1c2620"),
    "Mat_Arcade_Fantasminha": ("metal_pintado", 0.8, "#4b2a7a"),
    "Mat_Arcade_Fantasminha_Detalhe": ("metal_pintado", 0.5, "#f2efe6"),
    # --- Personagens provisórios: pelúcia gasta ---
    "Mat_Tito_Marrom": ("veludo", 0.3, "#a86c45"),
    "Mat_Tito_Bege": ("veludo", 0.3, "#f0d4ae"),
    "Mat_Pipoca_Lilas": ("veludo", 0.3, "#c2a6ec"),
    "Mat_Pipoca_Branco": ("veludo", 0.3, "#ffffff"),
}

# Materiais que ficam com COR LISA de propósito (não entram em TEXTURIZADOS), com o motivo.
# O ferramentas/gerar_materiais_godot.py confere: todo material dos .glb tem que estar
# numa das duas listas; o que não estiver é listado como "sem textura" no relatório.
LISOS = {
    # Brilham sozinhos (telas, luzes, LEDs, neon, letreiros acesos): textura não aparece na luz própria.
    "Mat_Tela_Monitor": "tela (o Godot troca pela imagem das câmeras)",
    "Mat_Tela_Arcade_Desligada": "tela (o Godot acende com o modo demonstração)",
    "Mat_Tela_Arcade_Azul": "tela", "Mat_Tela_Arcade_Rosa": "tela", "Mat_Tela_Arcade_Verde": "tela",
    "Mat_Tela_TV_Copa": "tela",
    "Mat_Luz_Emergencia": "luz", "Mat_Luz_Ficha": "luz", "Mat_Luz_Fria": "luz", "Mat_Luz_Geladeira": "luz",
    "Mat_Luz_Porta_Verde": "luz", "Mat_Led_Disjuntor": "LED", "Mat_Placar_Led": "placar de LED",
    "Mat_Lampada_Acesa": "lâmpada", "Mat_Lampada_Apagada": "lâmpada (vidro leitoso)",
    "Mat_Lampada_Fluorescente": "lâmpada",
    "Mat_Neon_Rosa": "neon", "Mat_Neon_Ciano": "neon", "Mat_Neon_Amarelo": "neon",
    "Mat_Gel_Ambar": "gelatina colorida de holofote", "Mat_Gel_Azul": "gelatina de holofote",
    "Mat_Gel_Vermelho": "gelatina de holofote", "Mat_Botao_Vermelho": "botão aceso",
    "Mat_Estrela_Fosforescente": "adesivo que brilha no escuro",
    "Mat_Placa_Saida": "placa de saída acesa", "Mat_Letra_Saida": "letras acesas",
    "Mat_Arcade_Serpente_Neon_Detalhe": "detalhe em neon da máquina",
    "Mat_Olho_Tito": "olho aceso", "Mat_Olho_Pipoca": "olho aceso",
    # Vidro, espelho e plástico transparente: são lisos de verdade.
    "Mat_Vidro_Vitrine": "vidro", "Mat_Vidro_Escuro": "vidro", "Mat_Vidro_Sujo": "vidro", "Mat_Vidro_Porta": "vidro",
    "Mat_Vidro_Bilheteria": "vidro", "Mat_Vidro_Aramado": "vidro", "Mat_Pinball_Vidro": "vidro do pinball",
    "Mat_Espelho": "espelho", "Mat_PVC_Tiras": "cortina de PVC transparente",
    # Letras e traços: precisam de contraste chapado para serem lidos.
    "Mat_Texto_Preto": "letras", "Mat_Texto_Branco": "letras", "Mat_Texto_Vermelho": "letras",
    "Mat_Letreiro_Dourado": "letras do letreiro", "Mat_Letra_Apagada": "letras",
    "Mat_Giz_Rosa": "rabisco de giz", "Mat_Giz_Azul": "rabisco de giz", "Mat_Rachadura": "traços da rachadura",
    "Mat_Teia": "fios de teia (linhas finas)",
}

# Materiais da V1 que foram substituídos (o gerador do prédio usa os novos nomes).
SUBSTITUIDOS = {
    "Mat_Piso_Preto": "Mat_Piso_Quadriculado",
    "Mat_Piso_Branco": "Mat_Piso_Quadriculado",
    "Mat_Piso_Carpete_Roxo": "Mat_Carpete_Fliperama",
}


def metros_por_repeticao(nome_material, padrao=1.0):
    """Escala da UV para o material (usada pelo Blender ao gerar as coordenadas UV)."""
    dados = TEXTURIZADOS.get(nome_material)
    return dados[1] if dados else padrao
