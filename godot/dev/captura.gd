extends Node
## FERRAMENTA DE DESENVOLVIMENTO — não faz parte do jogo (a pasta dev/ fica fora dos builds).
##
## Abre o mundo numa janela, posiciona a câmera em pontos interessantes, salva prints
## em docs/progresso/imagens/ (com um .json de legenda ao lado) e fecha sozinho.
##
## Uso (na pasta godot/):
##   godot --path . res://dev/captura.tscn -- plano=fase2
##
## Modos de cada foto:
##   "debug"    -> luz clara de depuração, sem névoa (para entender o mapa)
##   "lanterna" -> escuro de verdade, vista do vigia com a lanterna ligada
##   "escuro"   -> escuro de verdade, lanterna desligada
##   "ui"       -> abre uma cena de interface (menu, telas) e fotografa

const QUADROS_DE_ESPERA := 12
## Planos que usam o mapa novo da V2 (os outros usam o da V1).
const CENA_V2 := "res://cenas/mundo_v2.tscn"

# Posições em coordenadas do Godot (X = x - 20, Z = z - 15 da planta).
const PLANOS := {
	"fase2": [
		{"nome": "godot_planta_topo", "legenda": "Godot: mapa importado visto de cima (luz de depuração, sem teto)",
			"modo": "debug", "orto": 34.0, "pos": Vector3(0, 40, 0), "alvo": Vector3(0, 0, 0), "sem_teto": true},
		{"nome": "godot_perspectiva", "legenda": "Godot: visão geral com colisões e móveis importados (luz de depuração, sem teto)",
			"modo": "debug", "pos": Vector3(24, 26, 26), "alvo": Vector3(0, 0, 0), "sem_teto": true},
		{"nome": "godot_salao_debug", "legenda": "Godot: salão e palco (luz de depuração)",
			"modo": "debug", "pos": Vector3(5, 1.65, -2.4), "alvo": Vector3(-1, 1.0, -13)},
		{"nome": "godot_salao_lanterna", "legenda": "Godot: salão e palco no escuro, com a lanterna",
			"modo": "lanterna", "pos": Vector3(5, 0, -2.4), "alvo": Vector3(-1, 1.0, -13)},
		{"nome": "godot_sala_seguranca_lanterna", "legenda": "Godot: sala de segurança no início do jogo, com a lanterna",
			"modo": "lanterna", "pos": Vector3(5.5, 0, 6.5), "alvo": Vector3(2.4, 1.1, 6.5)},
		{"nome": "godot_corredor_escuro", "legenda": "Godot: corredor principal no escuro, só luzes de emergência",
			"modo": "escuro", "pos": Vector3(-18.5, 0, -0.5), "alvo": Vector3(20, 1.5, -0.5)},
		{"nome": "godot_corredor_lanterna", "legenda": "Godot: corredor principal com a lanterna",
			"modo": "lanterna", "pos": Vector3(-18.5, 0, -0.5), "alvo": Vector3(20, 1.4, -0.5)},
		{"nome": "godot_cozinha_debug", "legenda": "Godot: cozinha (luz de depuração)",
			"modo": "debug", "pos": Vector3(-15, 1.65, -2.6), "alvo": Vector3(-17, 1.0, -12)},
	],
	"fase3": [
		{"nome": "godot_disjuntor_debug", "legenda": "Godot: disjuntor da cozinha, alavanca para baixo (luz de depuração)",
			"modo": "debug", "pos": Vector3(-18.3, 1.55, -4.7), "alvo": Vector3(-19.8, 1.3, -5.5)},
		{"nome": "godot_disjuntor_desligado", "legenda": "Godot: chegando no disjuntor da cozinha com a lanterna (desligado)",
			"modo": "lanterna", "pos": Vector3(-18.2, 0, -5.0), "alvo": Vector3(-19.8, 1.3, -5.5)},
		{"nome": "godot_disjuntor_ligado", "legenda": "Godot: disjuntor religado — alavanca para cima, LED verde, aviso no HUD",
			"modo": "lanterna", "ligar": "Disjuntor_Cozinha", "pos": Vector3(-18.2, 0, -5.0), "alvo": Vector3(-19.8, 1.3, -5.5)},
		{"nome": "godot_cozinha_luz_voltou", "legenda": "Godot: cozinha com a luz fraca de volta depois do disjuntor (lanterna desligada)",
			"modo": "escuro", "pos": Vector3(-15, 0, -2.6), "alvo": Vector3(-16, 1.0, -12)},
		{"nome": "godot_pilha_no_escuro", "legenda": "Godot: pilha brilhando no escuro, perto da porta da cozinha",
			"modo": "escuro", "pos": Vector3(-13.6, 0, -5.4), "alvo": Vector3(-11.2, 0.15, -3.2)},
		{"nome": "godot_fliperama_lanterna", "legenda": "Godot: fliperama com as telas das máquinas acesas, com a lanterna",
			"modo": "lanterna", "pos": Vector3(-13, 0, 1.8), "alvo": Vector3(-8, 1.0, 6)},
		{"nome": "godot_banheiros_lanterna", "legenda": "Godot: banheiros com a lanterna",
			"modo": "lanterna", "pos": Vector3(-2, 0, 1.6), "alvo": Vector3(-3, 0.9, 10)},
	],
	"fase4": [
		{"nome": "godot_palco_debug", "legenda": "Godot: Tito e Pipoca no palco, esperando a 1 AM (luz de depuração)",
			"modo": "debug", "pos": Vector3(0, 1.65, -5.5), "alvo": Vector3(0, 1.3, -13)},
		{"nome": "godot_palco_lanterna", "legenda": "Godot: o palco no escuro, com a lanterna — os olhos brilham",
			"modo": "lanterna", "pos": Vector3(0, 0, -5.5), "alvo": Vector3(-1.5, 1.6, -13)},
		{"nome": "godot_tito_corredor", "legenda": "Godot: Tito parado no corredor (ele congela quando é visto)",
			"modo": "lanterna", "mover": {"Tito": [Vector3(-9, 0, -0.5), 90.0]},
			"pos": Vector3(-4, 0, -0.5), "alvo": Vector3(-9, 1.4, -0.5)},
		{"nome": "godot_pipoca_fliperama_escuro", "legenda": "Godot: Pipoca no fliperama, só os olhos acesos no escuro",
			"modo": "escuro", "mover": {"Pipoca": [Vector3(-10, 0, 7), 200.0]},
			"pos": Vector3(-13, 0, 1.8), "alvo": Vector3(-10, 1.5, 7)},
		{"nome": "godot_pipoca_lanterna", "legenda": "Godot: Pipoca pega pela lanterna (2 s de luz e ela fica atordoada)",
			"modo": "lanterna", "mover": {"Pipoca": [Vector3(-10, 0, 7), 200.0]},
			"pos": Vector3(-12.5, 0, 2.5), "alvo": Vector3(-10, 1.3, 7)},
		{"nome": "godot_jumpscare_tito", "legenda": "Godot: susto do Tito (câmera trava, modelo salta na tela, som alto + estática)",
			"jumpscare": "Tito", "pos": Vector3(0, 0, 3)},
		{"nome": "godot_jumpscare_pipoca", "legenda": "Godot: susto da Pipoca",
			"jumpscare": "Pipoca", "pos": Vector3(0, 0, 3)},
	],
	"fase6": [
		{"nome": "godot_teste_cortina_azul", "legenda": "Teste do guia: cor da cortina trocada no Blender (Base Color) e reexportada — o Godot mostra a cortina azul",
			"modo": "debug", "pos": Vector3(5, 1.65, -2.4), "alvo": Vector3(-1, 1.3, -13)},
	],
	"V2.3-antes": [
		{"nome": "v23_antes_salao", "legenda": "ANTES (luz da V1) — Salão com a lanterna desligada", "modo": "escuro", "hud": false, "pos": Vector3(5, 0, -2.4), "alvo": Vector3(-1, 1, -13)},
		{"nome": "v23_antes_cozinha", "legenda": "ANTES (luz da V1) — Cozinha com a lanterna desligada", "modo": "escuro", "hud": false, "pos": Vector3(-15, 0, -2.6), "alvo": Vector3(-16, 1, -12)},
		{"nome": "v23_antes_deposito", "legenda": "ANTES (luz da V1) — Depósito com a lanterna desligada", "modo": "escuro", "hud": false, "pos": Vector3(15, 0, -2.6), "alvo": Vector3(16, 1, -12)},
		{"nome": "v23_antes_corredor", "legenda": "ANTES (luz da V1) — Corredor principal com a lanterna desligada", "modo": "escuro", "hud": false, "pos": Vector3(-18.5, 0, -0.5), "alvo": Vector3(20, 1.5, -0.5)},
		{"nome": "v23_antes_fliperama", "legenda": "ANTES (luz da V1) — Fliperama com a lanterna desligada", "modo": "escuro", "hud": false, "pos": Vector3(-13, 0, 1.8), "alvo": Vector3(-8, 1, 6)},
		{"nome": "v23_antes_banheiros", "legenda": "ANTES (luz da V1) — Banheiros com a lanterna desligada", "modo": "escuro", "hud": false, "pos": Vector3(-2, 0, 1.6), "alvo": Vector3(-3, 0.9, 10)},
		{"nome": "v23_antes_sala_seguranca", "legenda": "ANTES (luz da V1) — Sala de segurança com a lanterna desligada", "modo": "escuro", "hud": false, "pos": Vector3(5.5, 0, 6.5), "alvo": Vector3(2.4, 1.1, 6.5)},
		{"nome": "v23_antes_recepcao", "legenda": "ANTES (luz da V1) — Recepção com a lanterna desligada", "modo": "escuro", "hud": false, "pos": Vector3(15, 0, 1.8), "alvo": Vector3(15, 1, 12)},
		{"nome": "v23_antes_fundos", "legenda": "ANTES (luz da V1) — Corredor dos fundos com a lanterna desligada", "modo": "escuro", "hud": false, "pos": Vector3(-10, 0, 13.5), "alvo": Vector3(10, 1.5, 13.5)},
	],
	"V2.3": [
		{"nome": "v23_depois_salao", "legenda": "DEPOIS (escuro legível) — Salão com a lanterna desligada", "modo": "escuro", "hud": false, "pos": Vector3(5, 0, -2.4), "alvo": Vector3(-1, 1, -13)},
		{"nome": "v23_depois_cozinha", "legenda": "DEPOIS (escuro legível) — Cozinha com a lanterna desligada", "modo": "escuro", "hud": false, "pos": Vector3(-15, 0, -2.6), "alvo": Vector3(-16, 1, -12)},
		{"nome": "v23_depois_deposito", "legenda": "DEPOIS (escuro legível) — Depósito com a lanterna desligada", "modo": "escuro", "hud": false, "pos": Vector3(15, 0, -2.6), "alvo": Vector3(16, 1, -12)},
		{"nome": "v23_depois_corredor", "legenda": "DEPOIS (escuro legível) — Corredor principal com a lanterna desligada", "modo": "escuro", "hud": false, "pos": Vector3(-18.5, 0, -0.5), "alvo": Vector3(20, 1.5, -0.5)},
		{"nome": "v23_depois_fliperama", "legenda": "DEPOIS (escuro legível) — Fliperama com a lanterna desligada", "modo": "escuro", "hud": false, "pos": Vector3(-13, 0, 1.8), "alvo": Vector3(-8, 1, 6)},
		{"nome": "v23_depois_banheiros", "legenda": "DEPOIS (escuro legível) — Banheiros com a lanterna desligada", "modo": "escuro", "hud": false, "pos": Vector3(-2, 0, 1.6), "alvo": Vector3(-3, 0.9, 10)},
		{"nome": "v23_depois_sala_seguranca", "legenda": "DEPOIS (escuro legível) — Sala de segurança com a lanterna desligada", "modo": "escuro", "hud": false, "pos": Vector3(5.5, 0, 6.5), "alvo": Vector3(2.4, 1.1, 6.5)},
		{"nome": "v23_depois_recepcao", "legenda": "DEPOIS (escuro legível) — Recepção com a lanterna desligada", "modo": "escuro", "hud": false, "pos": Vector3(15, 0, 1.8), "alvo": Vector3(15, 1, 12)},
		{"nome": "v23_depois_fundos", "legenda": "DEPOIS (escuro legível) — Corredor dos fundos com a lanterna desligada", "modo": "escuro", "hud": false, "pos": Vector3(-10, 0, 13.5), "alvo": Vector3(10, 1.5, 13.5)},
	],
	"V2.4": [
		{"nome": "v24_planta_topo", "legenda": "V2.4: mapa novo visto de cima (luz de depuração, sem teto)", "modo": "debug", "orto": 50.0, "pos": Vector3(0, 60, 0), "alvo": Vector3(0, 0, 0), "sem_teto": true},
		{"nome": "v24_perspectiva", "legenda": "V2.4: visão geral do mapa novo (luz de depuração, sem teto)", "modo": "debug", "pos": Vector3(32, 38, 40), "alvo": Vector3(0, 0, 0), "sem_teto": true},
		{"nome": "v24_escuro_salao", "legenda": "V2.4: Salão e palco do Show do Tito & Amigos no escuro, sem lanterna", "modo": "escuro", "hud": false, "pos": Vector3(-3, 0, -8.5), "alvo": Vector3(-3, 1.1, -20.5)},
		{"nome": "v24_debug_salao", "legenda": "V2.4: Salão e palco do Show do Tito & Amigos (luz de depuração)", "modo": "debug", "pos": Vector3(-3, 1.65, -8.5), "alvo": Vector3(-3, 1.1, -20.5)},
		{"nome": "v24_escuro_palco", "legenda": "V2.4: Palco de perto no escuro, sem lanterna", "modo": "escuro", "hud": false, "pos": Vector3(-3, 0, -14.5), "alvo": Vector3(-3, 1.1, -21.5)},
		{"nome": "v24_debug_palco", "legenda": "V2.4: Palco de perto (luz de depuração)", "modo": "debug", "pos": Vector3(-3, 1.65, -14.5), "alvo": Vector3(-3, 1.1, -21.5)},
		{"nome": "v24_escuro_cozinha", "legenda": "V2.4: Cozinha no escuro, sem lanterna", "modo": "escuro", "hud": false, "pos": Vector3(16, 0, -7.5), "alvo": Vector3(16, 1.1, -20.5)},
		{"nome": "v24_debug_cozinha", "legenda": "V2.4: Cozinha (luz de depuração)", "modo": "debug", "pos": Vector3(16, 1.65, -7.5), "alvo": Vector3(16, 1.1, -20.5)},
		{"nome": "v24_escuro_camara_fria", "legenda": "V2.4: Câmara frigorífica no escuro, sem lanterna", "modo": "escuro", "hud": false, "pos": Vector3(23.5, 0, -18.5), "alvo": Vector3(29, 1.1, -18.5)},
		{"nome": "v24_debug_camara_fria", "legenda": "V2.4: Câmara frigorífica (luz de depuração)", "modo": "debug", "pos": Vector3(23.5, 1.65, -18.5), "alvo": Vector3(29, 1.1, -18.5)},
		{"nome": "v24_escuro_banheiros", "legenda": "V2.4: Banheiros no escuro, sem lanterna", "modo": "escuro", "hud": false, "pos": Vector3(25, 0, -7.5), "alvo": Vector3(28, 1.1, -13.5)},
		{"nome": "v24_debug_banheiros", "legenda": "V2.4: Banheiros (luz de depuração)", "modo": "debug", "pos": Vector3(25, 1.65, -7.5), "alvo": Vector3(28, 1.1, -13.5)},
		{"nome": "v24_escuro_oficina", "legenda": "V2.4: Oficina / bastidores no escuro, sem lanterna", "modo": "escuro", "hud": false, "pos": Vector3(-23, 0, -8.5), "alvo": Vector3(-23, 1.1, -20.5)},
		{"nome": "v24_debug_oficina", "legenda": "V2.4: Oficina / bastidores (luz de depuração)", "modo": "debug", "pos": Vector3(-23, 1.65, -8.5), "alvo": Vector3(-23, 1.1, -20.5)},
		{"nome": "v24_escuro_deposito", "legenda": "V2.4: Depósito no escuro, sem lanterna", "modo": "escuro", "hud": false, "pos": Vector3(-23, 0, -2.5), "alvo": Vector3(-23, 1.1, 9.5)},
		{"nome": "v24_debug_deposito", "legenda": "V2.4: Depósito (luz de depuração)", "modo": "debug", "pos": Vector3(-23, 1.65, -2.5), "alvo": Vector3(-23, 1.1, 9.5)},
		{"nome": "v24_escuro_sala_eletrica", "legenda": "V2.4: Sala elétrica / gerador no escuro, sem lanterna", "modo": "escuro", "hud": false, "pos": Vector3(-17, 0, 16.5), "alvo": Vector3(-27, 1.1, 17.5)},
		{"nome": "v24_debug_sala_eletrica", "legenda": "V2.4: Sala elétrica / gerador (luz de depuração)", "modo": "debug", "pos": Vector3(-17, 1.65, 16.5), "alvo": Vector3(-27, 1.1, 17.5)},
		{"nome": "v24_escuro_fliperama", "legenda": "V2.4: Fliperama no escuro, sem lanterna", "modo": "escuro", "hud": false, "pos": Vector3(-7, 0, 9.5), "alvo": Vector3(-7, 1.1, -2.5)},
		{"nome": "v24_debug_fliperama", "legenda": "V2.4: Fliperama (luz de depuração)", "modo": "debug", "pos": Vector3(-7, 1.65, 9.5), "alvo": Vector3(-7, 1.1, -2.5)},
		{"nome": "v24_escuro_recepcao", "legenda": "V2.4: Recepção no escuro, sem lanterna", "modo": "escuro", "hud": false, "pos": Vector3(-7, 0, 11.5), "alvo": Vector3(-7, 1.1, 21.5)},
		{"nome": "v24_debug_recepcao", "legenda": "V2.4: Recepção (luz de depuração)", "modo": "debug", "pos": Vector3(-7, 1.65, 11.5), "alvo": Vector3(-7, 1.1, 21.5)},
		{"nome": "v24_escuro_festa_estrelas", "legenda": "V2.4: Sala de festa Estrelas no escuro, sem lanterna", "modo": "escuro", "hud": false, "pos": Vector3(6, 0, 0.5), "alvo": Vector3(13, 1.1, 0.5)},
		{"nome": "v24_debug_festa_estrelas", "legenda": "V2.4: Sala de festa Estrelas (luz de depuração)", "modo": "debug", "pos": Vector3(6, 1.65, 0.5), "alvo": Vector3(13, 1.1, 0.5)},
		{"nome": "v24_escuro_festa_piratas", "legenda": "V2.4: Sala de festa Piratas no escuro, sem lanterna", "modo": "escuro", "hud": false, "pos": Vector3(6, 0, 9.5), "alvo": Vector3(13, 1.1, 9.5)},
		{"nome": "v24_debug_festa_piratas", "legenda": "V2.4: Sala de festa Piratas (luz de depuração)", "modo": "debug", "pos": Vector3(6, 1.65, 9.5), "alvo": Vector3(13, 1.1, 9.5)},
		{"nome": "v24_escuro_festa_princesas", "legenda": "V2.4: Sala de festa Princesas no escuro, sem lanterna", "modo": "escuro", "hud": false, "pos": Vector3(6, 0, 17.5), "alvo": Vector3(13, 1.1, 17.5)},
		{"nome": "v24_debug_festa_princesas", "legenda": "V2.4: Sala de festa Princesas (luz de depuração)", "modo": "debug", "pos": Vector3(6, 1.65, 17.5), "alvo": Vector3(13, 1.1, 17.5)},
		{"nome": "v24_escuro_vestiario", "legenda": "V2.4: Vestiário no escuro, sem lanterna", "modo": "escuro", "hud": false, "pos": Vector3(18, 0, 0.5), "alvo": Vector3(24, 1.1, 0.5)},
		{"nome": "v24_debug_vestiario", "legenda": "V2.4: Vestiário (luz de depuração)", "modo": "debug", "pos": Vector3(18, 1.65, 0.5), "alvo": Vector3(24, 1.1, 0.5)},
		{"nome": "v24_escuro_sala_gerente", "legenda": "V2.4: Sala do gerente no escuro, sem lanterna", "modo": "escuro", "hud": false, "pos": Vector3(25, 0, -2.5), "alvo": Vector3(29, 1.1, 2.5)},
		{"nome": "v24_debug_sala_gerente", "legenda": "V2.4: Sala do gerente (luz de depuração)", "modo": "debug", "pos": Vector3(25, 1.65, -2.5), "alvo": Vector3(29, 1.1, 2.5)},
		{"nome": "v24_escuro_copa", "legenda": "V2.4: Copa dos funcionários no escuro, sem lanterna", "modo": "escuro", "hud": false, "pos": Vector3(18, 0, 15.5), "alvo": Vector3(29, 1.1, 15.5)},
		{"nome": "v24_debug_copa", "legenda": "V2.4: Copa dos funcionários (luz de depuração)", "modo": "debug", "pos": Vector3(18, 1.65, 15.5), "alvo": Vector3(29, 1.1, 15.5)},
		{"nome": "v24_escuro_corredor", "legenda": "V2.4: Corredor principal no escuro, sem lanterna", "modo": "escuro", "hud": false, "pos": Vector3(-28, 0, -5), "alvo": Vector3(30, 1.1, -5)},
		{"nome": "v24_debug_corredor", "legenda": "V2.4: Corredor principal (luz de depuração)", "modo": "debug", "pos": Vector3(-28, 1.65, -5), "alvo": Vector3(30, 1.1, -5)},
		{"nome": "v24_escuro_sala_seguranca", "legenda": "V2.4: Sala de segurança (início) no escuro, sem lanterna", "modo": "escuro", "hud": false, "pos": Vector3(18.2, 0, 5.75), "alvo": Vector3(20, 1.1, 5.75)},
		{"nome": "v24_debug_sala_seguranca", "legenda": "V2.4: Sala de segurança (início) (luz de depuração)", "modo": "debug", "pos": Vector3(18.2, 1.65, 5.75), "alvo": Vector3(20, 1.1, 5.75)},
	],
	"V2.2": [
		{"nome": "v22_hud_forward_plus", "legenda": "V2.2: jogo no renderer Forward+ com as fontes novas no HUD (VT323)",
			"modo": "lanterna", "pos": Vector3(5, 0, -2.4), "alvo": Vector3(-1, 1.0, -13)},
		{"nome": "v22_aviso_fones", "legenda": "V2.2: tela de abertura 'Use fones de ouvido'", "ui": "res://ui/aviso_fones.tscn", "espera": 60},
		{"nome": "v22_menu", "legenda": "V2.2: menu principal com fontes OFL (título em Creepster, botões em Bungee)",
			"ui": "res://ui/menu_principal.tscn"},
		{"nome": "v22_dificuldade", "legenda": "V2.2: escolha de dificuldade antes de jogar (Fácil / Normal / Pesadelo)",
			"ui": "res://ui/menu_principal.tscn", "chamar": "_abrir_dificuldade"},
		{"nome": "v22_opcoes_video", "legenda": "V2.2: opções de vídeo (tela cheia, qualidade, resolução 3D, VSync, FPS, FOV, brilho com calibragem, VHS)",
			"ui": "res://ui/opcoes.tscn", "aba": 0},
		{"nome": "v22_opcoes_audio", "legenda": "V2.2: opções de áudio (geral, música, efeitos, vozes)", "ui": "res://ui/opcoes.tscn", "aba": 1},
		{"nome": "v22_opcoes_controles", "legenda": "V2.2: opções de controles (sensibilidade, inverter Y)", "ui": "res://ui/opcoes.tscn", "aba": 2},
	],
	"fase5": [
		{"nome": "godot_monitor_mesa", "legenda": "Godot: monitor da sala de segurança mostrando a câmera do palco",
			"modo": "escuro", "pos": Vector3(4.6, 0, 6.5), "alvo": Vector3(2.8, 1.0, 6.5)},
		{"nome": "godot_monitor_cam1", "legenda": "Godot: monitor de câmeras — CAM 1 - Palco (Q troca de câmera)",
			"monitor": 0},
		{"nome": "godot_monitor_cam3", "legenda": "Godot: monitor de câmeras — CAM 3 - Corredor",
			"monitor": 2},
		{"nome": "godot_monitor_cam5", "legenda": "Godot: monitor de câmeras — CAM 5 - Fliperama",
			"monitor": 4},
		{"nome": "godot_pausa", "legenda": "Godot: menu de pausa (ESC)", "ui": "pausa"},
		{"nome": "godot_menu_principal", "legenda": "Godot: menu principal com o palco ao fundo e estática VHS",
			"ui": "res://ui/menu_principal.tscn"},
		{"nome": "godot_intro", "legenda": "Godot: intro com efeito de máquina de escrever",
			"ui": "res://ui/intro.tscn", "espera": 300},
		{"nome": "godot_opcoes", "legenda": "Godot: opções (volume, mouse, brilho, filtro VHS)",
			"ui": "res://ui/opcoes.tscn"},
		{"nome": "godot_controles", "legenda": "Godot: tela de controles", "ui": "res://ui/controles.tscn"},
		{"nome": "godot_game_over", "legenda": "Godot: Game Over depois do susto", "ui": "res://ui/game_over.tscn",
			"fim": ["pego", "Pipoca"]},
		{"nome": "godot_demitido", "legenda": "Godot: derrota por tempo — 'O gerente chegou... e você foi demitido!'",
			"ui": "res://ui/game_over.tscn", "fim": ["tempo", ""]},
		{"nome": "godot_vitoria", "legenda": "Godot: tela de vitória", "ui": "res://ui/vitoria.tscn",
			"fim": ["vitoria", ""]},
	],
	# V2.7: acabamento (capa dupla do menu etc.).
	"V2.9-controles": [
		{"nome": "v29_controles", "legenda": "V2.9: tela de controles com todas as teclas da V2 (agachar, respiração, mapa, inventário...)", "ui": "res://ui/controles.tscn", "espera": 30},
	],
	"V2.7": [
		{"nome": "v27_recado_legenda", "legenda": "V2.7: a secretária eletrônica toca o recado do gerente no começo da noite (voz em português + legendas)",
			"modo": "lanterna", "pos": Vector3(18.2, 0, 5.75), "alvo": Vector3(19.6, 1.0, 5.4), "acao": "recado"},
		{"nome": "v27_carregamento", "legenda": "V2.7: tela de carregamento com a fachada (ARTE-11), dicas e progresso de verdade", "ui": "res://ui/carregamento.tscn", "espera": 50},
		{"nome": "v27_vitoria", "legenda": "V2.7: vitória com o relatório do turno e a avaliação do gerente", "ui": "res://ui/vitoria.tscn",
			"fim": ["vitoria", ""], "estatisticas": true},
		{"nome": "v27_menu_capa_fofa", "legenda": "V2.7: menu com a capa fofa (ARTE-10)", "ui": "res://ui/menu_principal.tscn", "capa": "fofa", "espera": 40},
		{"nome": "v27_menu_capa_glitch", "legenda": "V2.7: a fita VHS 'embola' e a capa começa a virar (chiado e faixas tortas)", "ui": "res://ui/menu_principal.tscn", "capa": "glitch", "espera": 40},
		{"nome": "v27_menu_capa_sombria", "legenda": "V2.7: capa sombria (ARTE-25) — a música vira a caixinha em tom menor", "ui": "res://ui/menu_principal.tscn", "capa": "sombria", "espera": 40},
	],
	# V2.5: mecânicas novas no mapa da V2 ("acao" prepara a cena antes da foto).
	"V2.5": [
		{"nome": "v25_hud_objetivo", "legenda": "V2.5: começo do turno — objetivo no topo, fichas, barras de fôlego e de ar sobre a bateria",
			"modo": "lanterna", "pos": Vector3(18.2, 0, 5.75), "alvo": Vector3(19.6, 1.0, 5.75), "acao": "objetivo"},
		{"nome": "v25_inventario", "legenda": "V2.5: inventário (Tab) com itens, fichas e a senha descoberta até agora",
			"modo": "lanterna", "pos": Vector3(18.2, 0, 5.75), "alvo": Vector3(19.6, 1.0, 5.75), "acao": "inventario"},
		{"nome": "v25_porta_corrente", "legenda": "V2.5: porta do depósito com corrente e cadeado (precisa do alicate; cortar faz muito barulho)",
			"modo": "lanterna", "pos": Vector3(-23, 0, -5.6), "alvo": Vector3(-23, 1.0, -3.5)},
		{"nome": "v25_teclado", "legenda": "V2.5: teclado da sala elétrica — senha sorteada a cada partida (kart + pistas)",
			"modo": "lanterna", "pos": Vector3(-15.2, 0, 16.5), "alvo": Vector3(-15.75, 1.3, 15.4), "acao": "teclado"},
		{"nome": "v25_pista_festa", "legenda": "V2.5: pista do código — o pôster da festa do Lucas mostra a idade (3º dígito)",
			"modo": "lanterna", "pos": Vector3(9.5, 0, -2.2), "alvo": Vector3(9.5, 1.6, -3.3), "acao": "documento:aniversario"},
		{"nome": "v25_recado_gerente", "legenda": "V2.5: recado do gerente explicando de onde vem cada parte da senha",
			"modo": "lanterna", "pos": Vector3(25.8, 0, 0.6), "alvo": Vector3(27, 0.8, -1.0), "acao": "documento:recado_gerente"},
		{"nome": "v25_esconderijo_mesa", "legenda": "V2.5: escondido embaixo da mesa com toalha na sala de festa (E sai, Alt prende a respiração)",
			"modo": "lanterna", "pos": Vector3(9.5, 0, 0.75), "alvo": Vector3(5, 0.4, 0.75), "acao": "esconder:mesa_toalha"},
		{"nome": "v25_esconderijo_armario", "legenda": "V2.5: escondido no armário do vestiário — a vista pelas frestas",
			"modo": "lanterna", "pos": Vector3(23.5, 0, -2.0), "alvo": Vector3(18, 1.3, -2.0), "acao": "esconder:armario"},
		{"nome": "v25_duto_oficina", "legenda": "V2.5: grade do duto na oficina (a porta do corredor está emperrada: entra-se rastejando)",
			"modo": "lanterna", "pos": Vector3(-19, 0, -9.5), "alvo": Vector3(-19, 0.3, -6.65)},
		{"nome": "v25_menu_duto", "legenda": "V2.5: escolhendo para onde rastejar pelo duto",
			"modo": "escuro", "pos": Vector3(12, 0, 5.8), "alvo": Vector3(12, 0.3, 5.0), "acao": "duto"},
		{"nome": "v25_gerador", "legenda": "V2.5: gerador principal na sala elétrica (só liga com os 4 disjuntores)",
			"modo": "lanterna", "pos": Vector3(-25.5, 0, 16.5), "alvo": Vector3(-22, 0.8, 16.5)},
		{"nome": "v25_porta_aco", "legenda": "V2.5: porta de aço da sala de segurança e o botão vermelho (o fim do turno)",
			"modo": "lanterna", "pos": Vector3(19.4, 0, 5.2), "alvo": Vector3(17.2, 1.2, 5.0)},
		{"nome": "v25_ruido_debug", "legenda": "V2.5: depuração (F12) — barulhos aparecem como esferas: corrente cortada, cacos e lata",
			"modo": "debug", "pos": Vector3(-14, 9, -1), "alvo": Vector3(-23, 0, -4), "acao": "ruidos"},
	],
}

var _fase: Variant = 0
var _mundo: Node3D
var _camera_livre: Camera3D
var _luz_debug: DirectionalLight3D
var _ambiente_original: Environment
var _carimbo := ""


func _ready() -> void:
	get_window().size = Vector2i(1280, 720)
	var nome_plano := "fase2"
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("plano="):
			nome_plano = arg.get_slice("=", 1)
	# "fase3" -> 3; "V2.2" -> "V2.2" (fases da V2 têm nome).
	_fase = int(nome_plano.trim_prefix("fase")) if nome_plano.begins_with("fase") else nome_plano
	var t := Time.get_datetime_dict_from_system()
	_carimbo = "%04d-%02d-%02d_%02d%02d" % [t.year, t.month, t.day, t.hour, t.minute]

	if not PLANOS.has(nome_plano):
		push_error("Plano de captura desconhecido: " + nome_plano)
		get_tree().quit(1)
		return

	Jogo.modo_captura = true
	var cena := CENA_V2 if nome_plano in ["V2.4", "V2.5", "V2.7"] else "res://cenas/mundo.tscn"
	_mundo = load(cena).instantiate()
	add_child(_mundo)
	await _esperar(QUADROS_DE_ESPERA)

	var jogador := get_tree().get_first_node_in_group("jogador")
	if jogador:
		jogador.process_mode = Node.PROCESS_MODE_DISABLED
	var ambiente := _mundo.get_node("Ambiente") as WorldEnvironment
	_ambiente_original = ambiente.environment

	_camera_livre = Camera3D.new()
	_camera_livre.fov = 70
	_camera_livre.far = 200
	add_child(_camera_livre)

	for foto in PLANOS[nome_plano]:
		await _tirar_foto(foto, jogador, ambiente)

	print("[captura] concluída: ", PLANOS[nome_plano].size(), " imagens")
	get_tree().quit()


func _tirar_foto(foto: Dictionary, jogador, ambiente) -> void:
	var modo: String = foto.get("modo", "debug")
	if foto.has("monitor"):
		# Abre o monitor de câmeras na câmera pedida.
		var monitor := _mundo.get_node("MonitorCameras")
		ambiente.environment = _ambiente_original
		jogador.get_node("Cabeca/Camera3D").current = true
		if not monitor.usando:
			monitor.interagir(jogador)
		monitor._trocar_para(foto["monitor"])
		await _esperar(30)
		_salvar(foto["nome"], foto["legenda"])
		monitor.sair()
		return
	if foto.has("ui"):
		await _foto_de_interface(foto)
		return
	# "mover": {"Tito": [posição, rotação Y em graus]} — coloca um animatrônico num lugar.
	for nome in foto.get("mover", {}):
		var a := _mundo.get_node_or_null("Animatronicos/" + nome) as Node3D
		if a:
			a.global_position = foto["mover"][nome][0]
			a.rotation.y = deg_to_rad(foto["mover"][nome][1])
	# "jumpscare": "Tito" — mostra o susto daquele animatrônico (só a imagem, sem trocar de cena).
	if foto.has("jumpscare"):
		var a := _mundo.get_node("Animatronicos/" + foto["jumpscare"])
		var ponto: Node = jogador.get_node("Cabeca/Camera3D/PontoJumpscare")
		for velho in ponto.get_children():
			velho.queue_free()
		jogador.global_position = foto["pos"]
		jogador.get_node("Cabeca/Camera3D").current = true
		ambiente.environment = _ambiente_original
		_mostrar_tetos(true)
		var hud_susto := _mundo.get_node_or_null("HUD") as CanvasLayer
		if hud_susto:
			hud_susto.visible = false
		# As animações (tweens) do susto pertencem ao vigia: ele precisa estar processando.
		jogador.travado = true
		jogador.process_mode = Node.PROCESS_MODE_INHERIT
		var copia: Node3D = a.get_node("Modelo").duplicate()
		a.add_child(copia)
		# Igual ao jogo (Animatronico.pegar): pose neutra, cabeça reta.
		copia.rotation = Vector3.ZERO
		for cabeca in copia.find_children("*_Cabeca", "", true, false):
			cabeca.rotation = Vector3.ZERO
		jogador.mostrar_jumpscare(copia)
		await _esperar(14)
		_salvar(foto["nome"], foto["legenda"])
		return
	if foto.has("ligar"):
		# Liga um disjuntor antes da foto (mostra alavanca, LED, luz da área e aviso no HUD).
		# Procura só no nó "Disjuntores" (a lógica); o modelo do .glb tem o mesmo nome.
		var d := _mundo.get_node("Disjuntores").find_child(foto["ligar"], true, false)
		if d and d.has_method("ligar"):
			Jogo.em_partida = true  # para o aviso aparecer no HUD
			d.ligar()
			Jogo.em_partida = false
			await _esperar(40)
	_mostrar_tetos(not foto.get("sem_teto", false))
	var hud := _mundo.get_node_or_null("HUD") as CanvasLayer
	if hud:
		hud.visible = foto.get("hud", modo != "debug")

	if modo == "debug":
		ambiente.environment = _ambiente_debug()
		_garantir_luz_debug().visible = true
		_camera_livre.projection = Camera3D.PROJECTION_ORTHOGONAL if foto.has("orto") else Camera3D.PROJECTION_PERSPECTIVE
		if foto.has("orto"):
			_camera_livre.size = foto["orto"]
		_posicionar(_camera_livre, foto["pos"], foto["alvo"])
		_camera_livre.current = true
	else:
		ambiente.environment = _ambiente_original
		if _luz_debug:
			_luz_debug.visible = false
		# Usa o próprio vigia: pés em "pos", olhando para "alvo".
		jogador.global_position = foto["pos"]
		var cabeca: Node3D = jogador.get_node("Cabeca")
		var olho: Vector3 = foto["pos"] + Vector3(0, cabeca.position.y, 0)
		var dir: Vector3 = foto["alvo"] - olho
		jogador.rotation = Vector3(0, atan2(-dir.x, -dir.z), 0)
		cabeca.rotation.x = atan2(dir.y, Vector2(dir.x, dir.z).length())
		jogador.lanterna_ligada = modo == "lanterna"
		var lanterna: SpotLight3D = jogador.get_node("Cabeca/Camera3D/Lanterna")
		lanterna.visible = jogador.lanterna_ligada
		lanterna.light_energy = jogador.energia_lanterna
		jogador.get_node("Cabeca/Camera3D").current = true
		jogador._seguir_lanterna(1.0)  # a lanterna segue a câmera na hora (o vigia está parado)

	await _acao_v25(String(foto.get("acao", "")), jogador)
	await _esperar(QUADROS_DE_ESPERA)
	_salvar(foto["nome"], foto["legenda"])
	_desfazer_v25(String(foto.get("acao", "")), jogador)


## V2.5: deixa a cena no estado da foto (tela aberta, vigia escondido...).
func _acao_v25(acao: String, jogador: Node) -> void:
	if acao == "":
		return
	var prog := get_tree().get_first_node_in_group("progressao_v2") as ProgressaoV2
	var hud := _mundo.get_node_or_null("HUD")
	match acao.get_slice(":", 0):
		"objetivo":
			Jogo.mudar_fichas(2)
			hud.mostrar_objetivo(Jogo.objetivo_atual())
		"inventario":
			Jogo.dar_item("alicate")
			Jogo.revelar_digitos(0, 2)
			hud._inventario.visible = true
		"teclado":
			Jogo.revelar_digitos(0, 3)
			prog.ui.abrir_teclado(Jogo.codigo, func() -> void: pass)
			prog.ui._digitado = Jogo.codigo.left(2)
			prog.ui._atualizar_visor()
		"documento":
			var id := acao.get_slice(":", 1)
			prog.ui.mostrar_documento(prog.PISTAS[id]["titulo"], prog.texto_pista(id), prog.PISTAS[id]["estilo"])
		"esconder":
			var tipo := acao.get_slice(":", 1)
			for e in get_tree().get_nodes_in_group("esconderijo"):
				if e.get_meta("tipo") == tipo:
					jogador.lanterna_ligada = true
					prog.esconder(e)
					await _esperar(30)
					jogador.get_node("Cabeca/Camera3D").current = true
					break
		"duto":
			prog._escolher_saida_duto("Oficina")
		"recado":
			Jogo.em_partida = true
			prog._recado.play(20.5)
			await _esperar(20)
		"ruidos":
			Jogo._mostrar_ruido = true
			Jogo.emitir_ruido(PlantaV2.mundo(7, 18.6, 1.0), 22.0, 1.0)
			Jogo.emitir_ruido(PlantaV2.mundo(9, 17.8, 0.5), 9.0, 0.7)
			Jogo.emitir_ruido(PlantaV2.mundo(16, 14, 0.5), 12.0, 0.75)
			await _esperar(4)
	await _esperar(10)


func _desfazer_v25(acao: String, jogador: Node) -> void:
	if acao == "":
		return
	var prog := get_tree().get_first_node_in_group("progressao_v2") as ProgressaoV2
	prog.ui.fechar()
	if jogador.escondido:
		prog.sair_do_esconderijo()
	var hud := _mundo.get_node_or_null("HUD")
	if hud and hud._inventario:
		hud._inventario.visible = false
	Jogo._mostrar_ruido = false


## Fotos de telas de interface (menu, opções, fim de jogo...).
var _ui_atual: Node


func _foto_de_interface(foto: Dictionary) -> void:
	if foto["ui"] == "pausa":
		# A pausa é fotografada por cima do jogo.
		var pausa := _mundo.get_node("Pausa")
		Jogo.em_partida = true
		pausa.pausar()
		await _esperar(20)
		_salvar(foto["nome"], foto["legenda"])
		get_tree().paused = false
		Jogo.em_partida = false
		_mundo.queue_free()  # daqui em diante só telas de interface
		_mundo = null
		await _esperar(4)
		return
	if _mundo and is_instance_valid(_mundo):
		# Fotos de interface sem o jogo (e o HUD dele) por trás.
		_mundo.queue_free()
		_mundo = null
		await _esperar(4)
	if foto.has("fim"):
		var fim: Array = foto["fim"]
		Jogo.motivo_derrota = fim[0]
		Jogo.quem_pegou = fim[1]
		Jogo.hora = 3
		Jogo.disjuntores_ligados = 4 if fim[0] == "vitoria" else 2
		Jogo.tempo_total = 412.0
		if foto.get("estatisticas", false):
			Jogo.usa_gerador = true
			Jogo.derrotas_na_noite = 1
			Jogo.estatisticas = {"fichas": 5, "tentativas_garra": 2, "tentativas_kart": 3, "escondido": 7, "pilhas": 2, "latas": 1, "barulhos_altos": 4}
	if _ui_atual:
		_ui_atual.queue_free()
		await _esperar(2)
	_ui_atual = load(foto["ui"]).instantiate()
	add_child(_ui_atual)
	await _esperar(4)
	if foto.has("chamar"):
		_ui_atual.call(foto["chamar"])
	if foto.has("aba"):
		var abas := _ui_atual.find_child("Abas", true, false) as TabContainer
		if abas:
			abas.current_tab = foto["aba"]
	if foto.has("capa"):
		# V2.7: estado da capa do menu ("fofa", "glitch" ou "sombria"), parado para a foto.
		var capa := _ui_atual.find_child("Capa", true, false) as CapaMenu
		if capa:
			capa.set_process(false)
			capa._ao_redimensionar()
			var m := capa.material as ShaderMaterial
			m.set_shader_parameter("mistura", 1.0 if foto["capa"] == "sombria" else (0.5 if foto["capa"] == "glitch" else 0.0))
			m.set_shader_parameter("glitch", 0.75 if foto["capa"] == "glitch" else 0.0)
	await _esperar(foto.get("espera", 30))
	_salvar(foto["nome"], foto["legenda"])


func _posicionar(cam: Camera3D, pos: Vector3, alvo: Vector3) -> void:
	cam.global_position = pos
	var cima := Vector3.UP
	if absf((alvo - pos).normalized().dot(Vector3.UP)) > 0.99:
		cima = Vector3(0, 0, -1)  # olhando reto para baixo: norte para cima na imagem
	cam.look_at(alvo, cima)


func _ambiente_debug() -> Environment:
	var amb := _ambiente_original.duplicate() as Environment
	amb.fog_enabled = false
	amb.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	amb.ambient_light_color = Color(1, 1, 1)
	amb.ambient_light_energy = 0.9
	amb.background_color = Color(0.08, 0.08, 0.1)
	return amb


func _garantir_luz_debug() -> DirectionalLight3D:
	if _luz_debug == null:
		_luz_debug = DirectionalLight3D.new()
		_luz_debug.light_energy = 0.9
		_luz_debug.rotation_degrees = Vector3(-60, 35, 0)
		add_child(_luz_debug)
	return _luz_debug


func _mostrar_tetos(mostrar: bool) -> void:
	for no in _mundo.find_children("Teto_*", "", true, false):
		no.visible = mostrar


func _esperar(quadros: int) -> void:
	for i in quadros:
		await RenderingServer.frame_post_draw


func _salvar(nome: String, legenda: String) -> void:
	var pasta := ProjectSettings.globalize_path("res://").path_join("../docs/progresso/imagens").simplify_path()
	DirAccess.make_dir_recursive_absolute(pasta)
	var base := "%s_%s" % [_carimbo, nome]
	var imagem := get_viewport().get_texture().get_image()
	imagem.save_png(pasta.path_join(base + ".png"))
	var brilho := brilho_medio(imagem)
	var t := Time.get_datetime_dict_from_system()
	var dados := {
		"arquivo": base + ".png",
		"legenda": legenda,
		"fase": _fase,
		"horario": "%04d-%02d-%02d %02d:%02d:%02d" % [t.year, t.month, t.day, t.hour, t.minute, t.second],
		"brilho": snappedf(brilho, 0.1),
	}
	var arq := FileAccess.open(pasta.path_join(base + ".json"), FileAccess.WRITE)
	arq.store_string(JSON.stringify(dados, "  "))
	arq.close()
	print("[captura] ", base, ".png  brilho médio: %.1f%%" % brilho)


## Brilho médio da imagem, de 0 (preto) a 100 (branco), como o olho percebe
## (luminância: o verde pesa mais que o vermelho e o azul). Amostra 1 a cada 4 pixels.
static func brilho_medio(imagem: Image) -> float:
	var soma := 0.0
	var n := 0
	for y in range(0, imagem.get_height(), 4):
		for x in range(0, imagem.get_width(), 4):
			var c := imagem.get_pixel(x, y)
			soma += 0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b
			n += 1
	return 100.0 * soma / maxf(n, 1)