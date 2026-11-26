extends Node
## Autoload "Jogo": guarda o estado da partida (hora, disjuntores, vitória/derrota)
## e avisa as outras partes do jogo por sinais.
##
## Por que um autoload: ele existe o tempo todo, em qualquer cena. Assim o HUD,
## os animatrônicos e os disjuntores conversam por aqui sem precisar se conhecer.
##
## Os VALORES da partida (duração da noite etc.) ficam no nó "Mundo" da cena
## cenas/mundo.tscn, para serem mudados no Inspector. Este script só os copia.

# ---------------------------------------------------------------------------
# MODO DEBUG: começa DESLIGADO. Para ligar/desligar durante a partida: Ctrl+Shift+D
# (ou abra o jogo com:  TurnoDaNoite.exe -- debug). Com ele ligado, valem as teclas:
#   F1 avança 1 hora · F2 liga todos os disjuntores · F3 invencível
#   F4 liga/desliga a IA dos animatrônicos · F5 recarrega a bateria
#   V2: F6 +3 fichas · F7 vence o minigame aberto · F8 luz de depuração
#       F9 PAINEL com todos os atalhos e o estado de cada um · F10 próximo cômodo · F12 navegação e ruídos
#   Shift+F1 congelar animatrônicos · Shift+F2 fôlego infinito · Shift+F3 bateria infinita
#   Shift+F4 todos os itens e a senha · Shift+F5 modo observação (animatrônicos ignoram o vigia)
#   (F11 é tela cheia e funciona sempre, mesmo sem debug)
# ---------------------------------------------------------------------------
var DEBUG_ATIVO := false

signal hora_mudou(hora: int)
signal disjuntor_ligado(total: int)
signal energia_restaurada()
signal jogador_pego(quem: String)
signal vitoria()
signal derrota(motivo: String)
signal ruido_emitido(posicao: Vector3, raio: float, intensidade: float)
# --- V2 (docs/CONTRATOS.md, V2-4) ---
signal item_obtido(id_item: String)
signal fichas_mudaram(total: int)
signal codigo_revelado(posicao: int, digito: int)
signal objetivo_mudou(texto: String)
signal minigame_iniciado(nome: String)
signal minigame_terminado(nome: String, venceu: bool)
signal gerador_ligado()
signal porta_seguranca_mudou(fechada: bool)
signal tensao_mudou(valor: float)
signal mensagem(texto: String, duracao: float)
signal debug_mudou()

## A partir da V2.5 o jogo usa o mapa novo (o da V1 continua em cenas/mundo.tscn para os testes antigos).
const CENA_MUNDO := "res://cenas/mundo_v2.tscn"
const CENA_MENU := "res://ui/menu_principal.tscn"
const CENA_CARREGAMENTO := "res://ui/carregamento.tscn"
const CENA_GAME_OVER := "res://ui/game_over.tscn"
const CENA_VITORIA := "res://ui/vitoria.tscn"

## Quanto tempo (s) a imagem do susto fica na tela antes do Game Over.
const DURACAO_JUMPSCARE := 1.2

## Arquivos de dificuldade, na ordem do enum Config.Nivel (Fácil, Normal, Pesadelo).
const ARQUIVOS_DIFICULDADE := [
	"res://assets/dificuldade/facil.tres",
	"res://assets/dificuldade/normal.tres",
	"res://assets/dificuldade/pesadelo.tres",
]

## Dificuldade da partida atual (todos os números de balanceamento estão nela).
var dificuldade: Dificuldade

# --- Valores copiados quando a partida começa ---
var segundos_por_hora := 80.0
var total_disjuntores := 4

# --- Estado da partida ---
var em_partida := false        ## true enquanto o relógio está rodando
var hora := 0                  ## 0 = meia-noite ... 6 = fim do turno
var tempo_na_hora := 0.0       ## segundos já passados dentro da hora atual
var disjuntores_ligados := 0
var tempo_total := 0.0         ## tempo real jogado (aparece na tela de vitória)
var motivo_derrota := ""       ## "pego" ou "tempo"
var quem_pegou := ""           ## "Tito" ou "Pipoca"

# --- Estado da partida V2 (mapa novo) ---
var usa_gerador := false       ## true no mapa da V2: vencer exige gerador + porta de aço fechada
var itens := {}                ## id do item -> true ("alicate", "chave_gerente")
var fichas := 0
var codigo := ""               ## senha de 4 dígitos da sala elétrica (sorteada a cada partida)
var digitos_conhecidos: Array[bool] = [false, false, false, false]
var disjuntores_feitos := {}   ## "cozinha" -> true ...
var minigames_vencidos := {}   ## "garra" -> true, "kart" -> true
var gerador_esta_ligado := false
var porta_seguranca_fechada := false
var minigame_aberto := ""      ## nome do minigame em andamento ("" = nenhum)
var diario: Array = []        ## pistas achadas [{titulo, texto}] (ver anotar())
var comodos_visitados := {}    ## nome do cômodo -> true (o mapa mostra o que já foi visto)
var tensao := 0.0              ## 0 = calmo, 1 = sendo perseguido (o diretor de tensão calcula)
var tensao_alta_demais := false ## o diretor pede um respiro: a Pipoca desiste mais rápido
## Checkpoint (só no Fácil): o progresso salvo no último disjuntor. "Tentar de novo" continua daqui.
var checkpoint := {}
## Estatísticas da noite (aparecem na tela de vitória). Ver contar().
var estatisticas := {}
## Quantas vezes o vigia perdeu nesta noite (volta a zero ao voltar para o menu).
var derrotas_na_noite := 0

# --- Debug ---
var invencivel := false
var ia_ativa := true
var modo_captura := false      ## usado só pela ferramenta de captura de tela (pasta dev/)
var trocar_cena_ao_terminar := true  ## os testes (pasta dev/) desligam para não sair da cena de teste

var _rotulo_debug: Label
var _painel_debug: PanelContainer
var _texto_painel_debug: Label
## Debug V2.2: animatrônicos parados no lugar (com animação de "parado"), fôlego e bateria sem fim.
var congelar_animatronicos := false
## Debug: os animatrônicos andam e patrulham normalmente, mas ignoram o vigia (para ver de perto).
var modo_observacao := false
var stamina_infinita := false
var bateria_infinita := false
var _luz_debug: DirectionalLight3D
var _ambiente_normal: Environment
var _mostrar_ruido := false
var _comodo_teleporte := -1


func _ready() -> void:
	carregar_dificuldade()
	# O Jogo continua recebendo teclas mesmo com o jogo pausado (para o debug não travar).
	process_mode = Node.PROCESS_MODE_ALWAYS
	if OS.get_cmdline_user_args().has("debug"):
		DEBUG_ATIVO = true
	_criar_rotulo_debug()


## Chamado pelo nó Mundo quando a cena do jogo termina de carregar.
func iniciar_partida(mundo: Node) -> void:
	carregar_dificuldade()
	# O Mundo pode forçar uma duração (útil na apresentação); 0 = usar a da dificuldade.
	segundos_por_hora = mundo.segundos_por_hora if mundo.segundos_por_hora > 0.0 else dificuldade.segundos_por_hora
	total_disjuntores = mundo.total_disjuntores
	usa_gerador = mundo.has_node("Montador")  # só o mapa da V2 tem o montador
	hora = 0
	tempo_na_hora = 0.0
	disjuntores_ligados = 0
	tempo_total = 0.0
	motivo_derrota = ""
	quem_pegou = ""
	em_partida = not modo_captura
	_atualizar_rotulo_debug()


## Zera o estado da V2 e sorteia a senha. O montador do mapa novo chama isto ANTES de montar
## o mapa (o pôster da festa e o quadro de avisos mostram dígitos da senha).
func preparar_partida_v2(codigo_fixo := "") -> void:
	carregar_dificuldade()
	usa_gerador = true
	itens = {}
	fichas = 0
	disjuntores_feitos = {}
	minigames_vencidos = {}
	gerador_esta_ligado = false
	porta_seguranca_fechada = false
	minigame_aberto = ""
	digitos_conhecidos = [false, false, false, false]
	tensao = 0.0
	tensao_alta_demais = false
	diario = []
	comodos_visitados = {}
	if checkpoint.is_empty():
		estatisticas = {}
	if not checkpoint.is_empty():
		codigo = checkpoint["codigo"]  # continua com a mesma senha
	elif codigo_fixo != "":
		codigo = codigo_fixo
	else:
		# O 3º dígito é a idade do Lucas no pôster da festa: de 3 a 9 anos.
		codigo = "%d%d%d%d" % [randi_range(1, 9), randi_range(0, 9), randi_range(3, 9), randi_range(0, 9)]


## Soma 1 (ou n) numa estatística da noite: "escondido", "pilhas", "fichas", "latas",
## "tentativas_garra", "tentativas_kart", "barulhos_altos"...
func contar(chave: String, n := 1) -> void:
	estatisticas[chave] = int(estatisticas.get(chave, 0)) + n


func dar_item(id_item: String) -> void:
	itens[id_item] = true
	item_obtido.emit(id_item)
	objetivo_mudou.emit(objetivo_atual())


func tem_item(id_item: String) -> bool:
	return itens.get(id_item, false)


func mudar_fichas(quantidade: int) -> void:
	fichas = maxi(fichas + quantidade, 0)
	fichas_mudaram.emit(fichas)


func revelar_digitos(inicio: int, quantos: int) -> void:
	for i in range(inicio, mini(inicio + quantos, 4)):
		if not digitos_conhecidos[i]:
			digitos_conhecidos[i] = true
			codigo_revelado.emit(i, int(codigo[i]))
	objetivo_mudou.emit(objetivo_atual())


## A senha como o vigia conhece até agora, ex.: "47_2".
func codigo_conhecido() -> String:
	var s := ""
	for i in 4:
		s += codigo[i] if digitos_conhecidos[i] else "_"
	return s


func registrar_minigame(nome: String, venceu: bool) -> void:
	minigame_aberto = ""
	if nome in ["garra", "kart", "space_pizza"]:
		contar("tentativas_garra" if nome == "garra" else "tentativas_kart")
	if venceu:
		minigames_vencidos[nome] = true
	minigame_terminado.emit(nome, venceu)
	objetivo_mudou.emit(objetivo_atual())


func ligar_gerador() -> void:
	if gerador_esta_ligado:
		return
	gerador_esta_ligado = true
	gerador_ligado.emit()
	mensagem.emit("O GERADOR LIGOU! CORRA PARA A SALA DE SEGURANÇA E FECHE A PORTA DE AÇO!", 6.0)
	objetivo_mudou.emit(objetivo_atual())


func mudar_porta_seguranca(fechada: bool) -> void:
	porta_seguranca_fechada = fechada
	porta_seguranca_mudou.emit(fechada)


## Guarda o progresso da noite (Fácil: a cada disjuntor religado).
func salvar_checkpoint() -> void:
	var portas: Array[String] = []
	for p in get_tree().get_nodes_in_group("porta"):
		if p.tipo in ["corrente", "chave", "teclado", "unica"] and (not p.trancada and (p.tipo != "unica" or p.aberta)):
			portas.append(p.id_porta)
	checkpoint = {
		"codigo": codigo, "itens": itens.duplicate(), "fichas": fichas,
		"disjuntores": disjuntores_feitos.keys(), "minigames": minigames_vencidos.duplicate(),
		"digitos": digitos_conhecidos.duplicate(), "hora": hora, "tempo_na_hora": tempo_na_hora, "portas": portas,
	}


## true quando o vigia pode vencer estando dentro da sala de segurança.
func pode_vencer() -> bool:
	if usa_gerador:
		return gerador_esta_ligado and porta_seguranca_fechada
	return todos_disjuntores_ligados()


## O objetivo como LISTA, para o painel fixo do HUD e para o mapa (V2.2: o vigia nunca fica perdido).
## Devolve {"titulo": String, "passos": [{"texto", "feito", "atual"}], "alvo": id do próximo alvo}.
## "alvo" diz ONDE é o próximo passo (a progressão converte em posição para o mapa):
##   "disjuntor_cozinha", "maquina_garra", "disjuntor_gerente", "maquina_kart", "duto_piratas",
##   "alicate", "disjuntor_deposito", "teclado_eletrica", "disjuntor_eletrica", "gerador", "botao_porta".
func objetivo_estruturado() -> Dictionary:
	if not usa_gerador:
		return {"titulo": "Religue os %d disjuntores e volte para a sala de segurança." % total_disjuntores, "passos": [], "alvo": ""}
	if gerador_esta_ligado:
		return {"titulo": "CORRA! Feche a porta de aço da sala de segurança", "passos": [
			{"texto": "Aperte o botão vermelho ao lado da porta, DENTRO da sala", "feito": porta_seguranca_fechada, "atual": true}],
			"alvo": "botao_porta"}
	if todos_disjuntores_ligados():
		return {"titulo": "Ligue o GERADOR PRINCIPAL (sala elétrica)", "passos": [
			{"texto": "Gerador: alavanca vermelha na frente dele", "feito": false, "atual": true}], "alvo": "gerador"}
	var d := disjuntores_feitos
	var senha_kart := digitos_conhecidos[0] and digitos_conhecidos[1]
	var senha_bilhete := digitos_conhecidos[2] and digitos_conhecidos[3]
	# Cada ramo mostra só o passo em que está. A ordem da lista é a sugerida.
	var ramos: Array = []
	ramos.append({"texto": "Cozinha: conserte os fios do disjuntor", "feito": d.get("cozinha", false), "alvo": "disjuntor_cozinha"})
	if d.get("gerente", false):
		ramos.append({"texto": "Gerente: disjuntor religado", "feito": true, "alvo": ""})
	elif tem_item("chave_gerente"):
		ramos.append({"texto": "Gerente: abra a sala com a chave e troque o fusível", "feito": false, "alvo": "disjuntor_gerente"})
	else:
		ramos.append({"texto": "Gerente: ganhe a CHAVE na máquina de garra (fliperama, %d ficha%s)" % [fichas, "" if fichas == 1 else "s"],
			"feito": false, "alvo": "maquina_garra"})
	if d.get("eletrica", false):
		ramos.append({"texto": "Elétrica: disjuntor religado", "feito": true, "alvo": ""})
	elif senha_kart and senha_bilhete:
		ramos.append({"texto": "Elétrica: digite %s no teclado e religue o disjuntor" % codigo, "feito": false, "alvo": "teclado_eletrica"})
	elif not senha_kart:
		ramos.append({"texto": "Elétrica: senha %s — bata o recorde do TITO KART (fliperama)" % codigo_conhecido(), "feito": false, "alvo": "maquina_kart"})
	else:
		ramos.append({"texto": "Elétrica: senha %s — o resto está no bilhete na mesa do gerente" % codigo_conhecido(), "feito": false,
			"alvo": "maquina_garra" if not tem_item("chave_gerente") else "disjuntor_gerente"})
	if d.get("deposito", false):
		ramos.append({"texto": "Depósito: disjuntor religado", "feito": true, "alvo": ""})
	elif tem_item("alicate"):
		ramos.append({"texto": "Depósito: corte a corrente (BARULHO!) e religue o disjuntor", "feito": false, "alvo": "disjuntor_deposito"})
	else:
		var jogador := get_tree().get_first_node_in_group("jogador") as Node3D
		if jogador and PlantaV2.comodo_em(jogador.global_position) == "Oficina":
			ramos.append({"texto": "Depósito: pegue o ALICATE na bancada da oficina", "feito": false, "alvo": "alicate"})
		else:
			ramos.append({"texto": "Depósito: precisa do ALICATE da oficina — entre pelo DUTO da sala dos Piratas", "feito": false, "alvo": "duto_piratas"})
	var alvo := ""
	for r in ramos:
		if not r["feito"] and alvo == "":
			alvo = r["alvo"]
			r["atual"] = true
		else:
			r["atual"] = false
	return {"titulo": "RELIGUE OS DISJUNTORES (%d/%d)" % [disjuntores_ligados, total_disjuntores], "passos": ramos, "alvo": alvo}


## Uma linha só (mensagens e testes antigos).
func objetivo_atual() -> String:
	var o := objetivo_estruturado()
	for p in o["passos"]:
		if p["atual"]:
			return "%s — %s" % [o["titulo"], p["texto"]]
	return o["titulo"]


## Diário do vigia: pistas e informações achadas (aparecem no mapa, tecla M). Sem repetir títulos.
func anotar(titulo: String, texto: String) -> void:
	for e in diario:
		if e["titulo"] == titulo:
			e["texto"] = texto
			return
	diario.append({"titulo": titulo, "texto": texto})
	objetivo_mudou.emit(objetivo_atual())


## Carrega o arquivo da dificuldade escolhida no menu (Config.dificuldade).
func carregar_dificuldade() -> void:
	dificuldade = load(ARQUIVOS_DIFICULDADE[clampi(Config.dificuldade, 0, 2)]) as Dificuldade


func _process(delta: float) -> void:
	if not em_partida or get_tree().paused:
		return
	tempo_total += delta
	tempo_na_hora += delta
	if tempo_na_hora >= segundos_por_hora:
		avancar_hora()


## Passa para a próxima hora (o relógio chama sozinho; F1 também chama).
func avancar_hora() -> void:
	if not em_partida:
		return
	tempo_na_hora = 0.0
	hora += 1
	hora_mudou.emit(hora)
	if hora >= 6:
		perder("tempo")
	else:
		mensagem.emit("%d AM" % hora, 3.0)


## Texto do relógio do HUD, ex.: "02:35". Os minutos andam junto com o tempo real.
func texto_relogio() -> String:
	var minutos := int(tempo_na_hora / segundos_por_hora * 60.0)
	return "%02d:%02d" % [hora, clampi(minutos, 0, 59)]


## Quão "acordados" estão os animatrônicos: cresce com as horas e com os disjuntores.
func nivel_agressividade() -> Dictionary:
	return {"horas": hora, "disjuntores": disjuntores_ligados}


## Os disjuntores chamam isto quando o jogador religa um deles.
func registrar_disjuntor(id_area := "") -> void:
	disjuntores_ligados += 1
	if id_area != "":
		disjuntores_feitos[id_area] = true
	disjuntor_ligado.emit(disjuntores_ligados)
	objetivo_mudou.emit(objetivo_atual())
	if usa_gerador and dificuldade and dificuldade.checkpoint_por_disjuntor and id_area != "":
		salvar_checkpoint()
	if disjuntores_ligados >= total_disjuntores:
		energia_restaurada.emit()
		if usa_gerador:
			mensagem.emit("Os 4 disjuntores estão ligados. Agora o gerador principal, na sala elétrica.", 5.0)
		else:
			mensagem.emit("Energia restaurada! Volte para a sala de segurança!", 5.0)
	elif usa_gerador:
		# O que mudou (a luz da área voltou) e para onde ir agora.
		var nomes := {"cozinha": "COZINHA", "gerente": "SALA DO GERENTE", "deposito": "DEPÓSITO", "eletrica": "SALA ELÉTRICA"}
		var area: String = nomes.get(id_area, id_area.to_upper())
		var o := objetivo_estruturado()
		var proximo := ""
		for p in o["passos"]:
			if p["atual"]:
				proximo = String(p["texto"])
		mensagem.emit("%s: energia de volta! (%d/%d)
Próximo: %s" % [area, disjuntores_ligados, total_disjuntores, proximo], 5.0)
	else:
		mensagem.emit("Disjuntores: %d/%d" % [disjuntores_ligados, total_disjuntores], 2.5)


func todos_disjuntores_ligados() -> bool:
	return disjuntores_ligados >= total_disjuntores


## A zona da sala de segurança chama isto quando o jogador está lá dentro.
func tentar_vencer() -> void:
	if em_partida and pode_vencer():
		em_partida = false
		vitoria.emit()
		_trocar_cena_depois(CENA_VITORIA, 1.0)


## Um animatrônico encostou no jogador.
func pegar_jogador(quem: String) -> void:
	if not em_partida or invencivel:
		return
	em_partida = false
	quem_pegou = quem
	motivo_derrota = "pego"
	derrotas_na_noite += 1
	jogador_pego.emit(quem)          # o jogador mostra o susto
	derrota.emit("pego")
	_trocar_cena_depois(CENA_GAME_OVER, DURACAO_JUMPSCARE)


func perder(motivo: String) -> void:
	if not em_partida:
		return
	em_partida = false
	motivo_derrota = motivo
	derrotas_na_noite += 1
	derrota.emit(motivo)
	_trocar_cena_depois(CENA_GAME_OVER, 0.5)


## Usado pelos botões "Tentar de novo" e "Jogar".
func reiniciar_partida() -> void:
	get_tree().paused = false
	get_tree().change_scene_to_file(CENA_CARREGAMENTO if ResourceLoader.exists(CENA_CARREGAMENTO) else CENA_MUNDO)


func ir_para_menu() -> void:
	checkpoint = {}  # voltar ao menu começa uma noite nova
	derrotas_na_noite = 0
	em_partida = false
	get_tree().paused = false
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	if ResourceLoader.exists(CENA_MENU):
		get_tree().change_scene_to_file(CENA_MENU)
	else:
		get_tree().quit()


func _trocar_cena_depois(cena: String, segundos: float) -> void:
	await get_tree().create_timer(segundos, true).timeout
	if not trocar_cena_ao_terminar:
		return
	get_tree().paused = false
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	if ResourceLoader.exists(cena):
		get_tree().change_scene_to_file(cena)
	else:
		# Enquanto as telas não existirem, recomeça direto.
		reiniciar_partida()


## Avisa os animatrônicos que houve barulho (a Pipoca escuta).
## intensidade: 0 a 1 (passo agachado ~0,2; corrente cortada 1,0).
func emitir_ruido(posicao: Vector3, raio: float, intensidade := 0.5) -> void:
	ruido_emitido.emit(posicao, raio, intensidade)
	if intensidade >= 0.7:
		contar("barulhos_altos")
	if _mostrar_ruido:
		_desenhar_ruido(posicao, raio, intensidade)


# ---------------------------------------------------------------------------
# Debug (F1..F5)
# ---------------------------------------------------------------------------

func _input(evento: InputEvent) -> void:
	if not (evento is InputEventKey and evento.pressed and not evento.echo):
		return
	# Ctrl+Shift+D liga/desliga o modo debug (combinação difícil de apertar sem querer).
	if evento.keycode == KEY_D and evento.ctrl_pressed and evento.shift_pressed:
		DEBUG_ATIVO = not DEBUG_ATIVO
		mensagem.emit("Modo DEBUG %s" % ("LIGADO (F9 mostra os atalhos)" if DEBUG_ATIVO else "desligado"), 3.0)
		_atualizar_rotulo_debug()
		return
	if not DEBUG_ATIVO or not em_partida:
		return
	if evento.shift_pressed:
		match evento.keycode:
			KEY_F1:
				congelar_animatronicos = not congelar_animatronicos
			KEY_F2:
				stamina_infinita = not stamina_infinita
			KEY_F3:
				bateria_infinita = not bateria_infinita
			KEY_F4:
				dar_item("alicate")
				dar_item("chave_gerente")
				if codigo.length() == 4:
					revelar_digitos(0, 4)
				mudar_fichas(3)
				mensagem.emit("DEBUG: todos os itens e a senha " + codigo, 3.0)
			KEY_F5:
				modo_observacao = not modo_observacao
				mensagem.emit("DEBUG: modo observação %s" % ("LIGADO: eles ignoram você" if modo_observacao else "desligado"), 3.0)
			_:
				return
	else:
		match evento.keycode:
			KEY_F1:
				avancar_hora()
			KEY_F2:
				for d in get_tree().get_nodes_in_group("disjuntor"):
					if d.has_method("ligar") and not d.ligado:
						d.ligar()
			KEY_F3:
				invencivel = not invencivel
			KEY_F4:
				ia_ativa = not ia_ativa
			KEY_F5:
				var jogador := get_tree().get_first_node_in_group("jogador")
				if jogador and jogador.has_method("recarregar"):
					jogador.recarregar(1000.0)
			KEY_F6:
				mudar_fichas(3)
			KEY_F7:
				# Os minigames também escutam o F7 sozinhos; aqui cobre o caso de ninguém ter tratado.
				var progressao := get_tree().get_first_node_in_group("progressao_v2")
				if progressao:
					progressao.vencer_minigame_aberto()
			KEY_F8:
				_alternar_luz_debug()
			KEY_F9:
				_painel_debug.visible = not _painel_debug.visible
			KEY_F10:
				_teleportar_proximo_comodo()
			KEY_F12:
				_mostrar_ruido = not _mostrar_ruido
				NavigationServer3D.set_debug_enabled(_mostrar_ruido)
			_:
				return
	debug_mudou.emit()
	_atualizar_rotulo_debug()


func _criar_rotulo_debug() -> void:
	var camada := CanvasLayer.new()
	camada.layer = 90
	add_child(camada)
	_rotulo_debug = Label.new()
	_rotulo_debug.anchor_top = 1.0
	_rotulo_debug.anchor_bottom = 1.0
	_rotulo_debug.offset_top = -28
	_rotulo_debug.offset_left = 10
	_rotulo_debug.theme_type_variation = &"RotuloHUD"
	_rotulo_debug.add_theme_font_size_override("font_size", 18)
	_rotulo_debug.add_theme_color_override("font_color", Color(1, 0.85, 0.3, 0.85))
	_rotulo_debug.add_theme_constant_override("outline_size", 4)
	_rotulo_debug.add_theme_color_override("font_outline_color", Color.BLACK)
	camada.add_child(_rotulo_debug)
	# Painel com TODOS os atalhos e o estado de cada um (F9 mostra/esconde).
	_painel_debug = PanelContainer.new()
	var estilo := StyleBoxFlat.new()
	estilo.bg_color = Color(0, 0, 0, 0.78)
	estilo.border_color = Color(1, 0.85, 0.3, 0.7)
	estilo.set_border_width_all(2)
	estilo.set_content_margin_all(14)
	_painel_debug.add_theme_stylebox_override("panel", estilo)
	_painel_debug.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
	_painel_debug.offset_left = -470
	_painel_debug.offset_right = -16
	_painel_debug.offset_top = 90
	_painel_debug.visible = false
	_texto_painel_debug = Label.new()
	_texto_painel_debug.theme_type_variation = &"RotuloHUD"
	_texto_painel_debug.add_theme_font_size_override("font_size", 20)
	_texto_painel_debug.add_theme_color_override("font_color", Color(1, 0.92, 0.7))
	_painel_debug.add_child(_texto_painel_debug)
	camada.add_child(_painel_debug)
	_atualizar_rotulo_debug()


func _atualizar_rotulo_debug() -> void:
	if _rotulo_debug == null:
		return
	_rotulo_debug.visible = em_partida and DEBUG_ATIVO
	_rotulo_debug.text = "DEBUG ligado  ·  F9: painel com todos os atalhos  ·  Ctrl+Shift+D desliga"
	_painel_debug.visible = _painel_debug.visible and em_partida and DEBUG_ATIVO
	var ligado := func(v: bool) -> String: return "LIGADO" if v else "desligado"
	var linhas: Array[String] = [
		"PAINEL DE DEBUG (F9 fecha)", "",
		"F1   avançar 1 hora (agora %s)" % texto_relogio(),
		"F2   ligar todos os disjuntores (%d/%d)" % [disjuntores_ligados, total_disjuntores],
		"F3   invencível: %s" % ligado.call(invencivel),
		"F4   IA dos animatrônicos: %s" % ("ligada" if ia_ativa else "DESLIGADA"),
		"F5   bateria cheia agora",
		"F6   +3 fichas (tem %d)" % fichas,
		"F7   vencer o minigame aberto",
		"F8   luz de depuração",
		"F10  ir para o próximo cômodo",
		"F12  navegação e esferas de ruído: %s" % ligado.call(_mostrar_ruido),
		"",
		"Shift+F1  congelar animatrônicos: %s" % ligado.call(congelar_animatronicos),
		"Shift+F2  fôlego infinito: %s" % ligado.call(stamina_infinita),
		"Shift+F3  bateria infinita: %s" % ligado.call(bateria_infinita),
		"Shift+F4  todos os itens e a senha (%s)" % codigo,
		"Shift+F5  modo observação (ignoram o vigia): %s" % ligado.call(modo_observacao),
		"",
		"F11  tela cheia (sempre funciona)",
	]
	_texto_painel_debug.text = "\n".join(linhas)


## F8: luz forte sem névoa, para enxergar o mapa (apertar de novo volta ao normal).
func _alternar_luz_debug() -> void:
	var mundo := get_tree().get_first_node_in_group("mundo")
	if mundo == null:
		return
	var ambiente := mundo.find_children("*", "WorldEnvironment", true, false)
	if is_instance_valid(_luz_debug):
		_luz_debug.queue_free()
		_luz_debug = null
		if not ambiente.is_empty() and _ambiente_normal:
			ambiente[0].environment = _ambiente_normal
		return
	_luz_debug = DirectionalLight3D.new()
	_luz_debug.light_energy = 1.1
	_luz_debug.rotation_degrees = Vector3(-60, 30, 0)
	mundo.add_child(_luz_debug)
	if not ambiente.is_empty():
		_ambiente_normal = ambiente[0].environment
		var claro: Environment = _ambiente_normal.duplicate()
		claro.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
		claro.ambient_light_color = Color(0.8, 0.8, 0.85)
		claro.ambient_light_energy = 1.0
		claro.fog_enabled = false
		claro.volumetric_fog_enabled = false
		ambiente[0].environment = claro


## F10: leva o vigia para o meio do próximo cômodo da planta (na ordem da lista).
func _teleportar_proximo_comodo() -> void:
	var jogador := get_tree().get_first_node_in_group("jogador") as Node3D
	var mundo := get_tree().get_first_node_in_group("mundo")
	if jogador == null or mundo == null or not usa_gerador:
		return
	var comodos: Array = PlantaV2.dados()["comodos"]
	_comodo_teleporte = (_comodo_teleporte + 1) % comodos.size()
	var c: Dictionary = comodos[_comodo_teleporte]
	var alvo := PlantaV2.mundo((c["x0"] + c["x1"]) / 2.0, (c["z0"] + c["z1"]) / 2.0)
	var mapa: RID = mundo.get_node("Navegacao").get_navigation_map()
	jogador.global_position = NavigationServer3D.map_get_closest_point(mapa, alvo) + Vector3(0, 0.1, 0)
	mensagem.emit("DEBUG: " + String(c["nome"]), 1.5)


## F12: mostra cada barulho como uma esfera que some (tamanho = alcance; vermelho = forte).
func _desenhar_ruido(posicao: Vector3, raio: float, intensidade: float) -> void:
	var mundo := get_tree().get_first_node_in_group("mundo")
	if mundo == null:
		return
	var esfera := MeshInstance3D.new()
	var malha := SphereMesh.new()
	malha.radius = raio
	malha.height = raio * 2.0
	malha.radial_segments = 16
	malha.rings = 8
	esfera.mesh = malha
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.albedo_color = Color(1.0, 1.0 - intensidade, 0.2, 0.18)
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	m.no_depth_test = true
	esfera.material_override = m
	mundo.add_child(esfera)
	esfera.global_position = posicao
	var t := esfera.create_tween()
	t.tween_property(m, "albedo_color:a", 0.0, 0.8)
	t.tween_callback(esfera.queue_free)
