class_name MapaVigia
extends CanvasLayer
## Tela do MAPA do vigia (tecla M).
##
## Mostra uma planta azul (blueprint) da pizzaria, desenhada por código a partir de
## PlantaV2.dados(): cômodos, paredes com as aberturas das portas, a posição e a direção
## do vigia, os cômodos já visitados (os outros ficam hachurados, como uma "névoa"),
## disjuntores, gerador, portas trancadas e o objetivo atual, marcado conforme a
## dificuldade. Ao lado fica o DIÁRIO DO VIGIA: objetivo, senha anotada, fichas, itens
## e as pistas encontradas.
##
## Os dados do jogo vêm de ProgressaoV2.dados_mapa() (grupo "progressao_v2"), lidos ao
## abrir e a cada 0,2 s enquanto a tela está aberta. Sem a progressão (cena de teste),
## a tela usa _dados_exemplo().
##
## No Fácil (marcacao 0) o jogo pausa enquanto o mapa está aberto; nas outras
## dificuldades o mundo continua andando e o vigia só fica parado lendo.
## O mapa NUNCA mostra os animatrônicos: para isso existem as câmeras.
##
## Uso: crie o nó (MapaVigia.new()) e adicione na árvore. Ele mesmo escuta a tecla M
## (ação "mapa") e o ESC (ação "pausar"). Também dá para chamar abrir(), fechar() e alternar().

const CAMADA := 16
const INTERVALO_DADOS := 0.2  # segundos entre duas leituras de dados_mapa()

# Tamanho da planta em metros (x de 0 a 60, z de 0 a 45).
const LARGURA_PLANTA := 60.0
const ALTURA_PLANTA := 45.0

# Espaços da tela, em pixels (da tela "lógica" de 1280×720, que o Godot escala).
const MARGEM_TELA := 24.0      # entre a borda da tela e o conteúdo
const MARGEM_FOLHA := 30.0     # entre a borda do papel e a planta
const ESPACO_DIARIO := 22.0    # entre a folha e o diário
const INCLINACAO_FOLHA := -0.6  # graus: a folha fica levemente torta
const INCLINACAO_DIARIO := 0.8

const FONTE_MAO := preload("res://assets/fontes/GochiHand/GochiHand-Regular.ttf")
const FONTE_CANETA := preload("res://assets/fontes/Caveat/Caveat-Variable.ttf")
const FONTE_MAQUINA := preload("res://assets/fontes/CourierPrime/CourierPrime-Regular.ttf")
const FONTE_MAQUINA_NEGRITO := preload("res://assets/fontes/CourierPrime/CourierPrime-Bold.ttf")
const FONTE_HUD := preload("res://assets/fontes/VT323/VT323-Regular.ttf")
const FONTE_LETREIRO := preload("res://assets/fontes/Bungee/Bungee-Regular.ttf")
const SHADER_PAPEL := preload("res://assets/shaders/mapa_papel.gdshader")

# Cores da planta (tinta branca sobre papel azul) e das marcações.
const COR_LINHA := Color(0.9, 0.95, 1.0)
const COR_LINHA_FRACA := Color(0.85, 0.92, 1.0, 0.45)
const COR_GRADE := Color(0.85, 0.92, 1.0, 0.06)
const COR_GRADE_FORTE := Color(0.85, 0.92, 1.0, 0.14)
const COR_CONTORNO := Color(0.03, 0.08, 0.2, 0.9)
const COR_NEVOA := Color(0.01, 0.04, 0.12, 0.42)
const COR_HACHURA := Color(0.75, 0.85, 1.0, 0.17)
const COR_VISITADO := Color(1.0, 1.0, 1.0, 0.05)
const COR_CANETA := Color(1.0, 0.2, 0.15)
const COR_LIGADO := Color(0.25, 0.9, 0.4)
const COR_DESLIGADO := Color(0.98, 0.26, 0.2)
const COR_VIGIA := Color(1.0, 0.84, 0.25)
const COR_FITA := Color(0.93, 0.88, 0.7, 0.72)
const COR_POST_IT := Color(0.99, 0.9, 0.42)
# Cores do diário (papel envelhecido e tinta de máquina de escrever).
const COR_PAPEL_DIARIO := Color(0.87, 0.82, 0.69)
const COR_TINTA := Color(0.14, 0.11, 0.09)
const COR_TINTA_FRACA := Color(0.14, 0.11, 0.09, 0.62)
const COR_TINTA_VERMELHA := Color(0.6, 0.1, 0.07)

# Tipos de porta da planta que são "especiais" (só usados nos dados de exemplo).
const PORTAS_ESPECIAIS := ["emperrada", "unica", "pesada", "corrente", "teclado", "catraca", "chave", "aco"]

## true enquanto a tela está aberta.
var aberto := false
## Marcação usada pelos dados de exemplo (0 Fácil, 1 Normal, 2 Pesadelo). Só para testes.
var marcacao_exemplo := 0

var _dados: Dictionary = {}
var _tempo := 0.0            # relógio das animações (pulsar)
var _tempo_dados := 0.0      # contagem para reler os dados
var _pausou := false         # fomos nós que pausamos a árvore?
var _assinatura_diario := ""
var _rolar_fim_quadros := 0  # quadros até rolar o diário para o fim
var _tamanho_diario := Vector2.ZERO

# Layout calculado em _montar_layout().
var _escala := 12.0          # pixels por metro da planta
var _origem := Vector2.ZERO  # onde fica o ponto (0, 0) da planta dentro da folha
var _altura_rodape := 60.0
var _largura_titulo := 160.0
var _rotulos: Array[Dictionary] = []  # um por cômodo: como escrever o nome
var _legenda: Array[Dictionary] = []  # itens da legenda do rodapé, já posicionados
var _paredes: Array[Dictionary] = []  # trechos de parede (em metros), já com os vãos das portas

# Nós da interface.
var _raiz: Control
var _folha: Control
var _papel: ColorRect
var _desenho: Control
var _diario: PanelContainer
var _rot_objetivo: Label
var _rot_senha: Label
var _rot_fichas: Label
var _rot_itens: Label
var _rot_anotacoes: Label
var _rolagem: ScrollContainer
var _lista_diario: VBoxContainer
var _rot_dica: Label


func _ready() -> void:
	layer = CAMADA
	process_mode = Node.PROCESS_MODE_ALWAYS  # continua funcionando com o jogo pausado (Fácil)
	add_to_group("mapa_vigia")
	_criar_interface()
	_raiz.visible = false
	get_viewport().size_changed.connect(_ao_mudar_tamanho)


func _exit_tree() -> void:
	# Se o nó sair da árvore com o mapa aberto, devolve o controle e despausa.
	fechar()


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

func abrir() -> void:
	if aberto:
		return
	aberto = true
	_dados = _ler_dados()
	var jogador := _jogador()
	if jogador:
		jogador.set("travado", true)
	if int(_dados.get("marcacao", 1)) == 0 and not get_tree().paused:
		get_tree().paused = true
		_pausou = true
	_assinatura_diario = ""
	_montar_layout()
	_atualizar_diario()
	_tempo_dados = INTERVALO_DADOS
	_rolar_fim_quadros = 3
	_raiz.modulate.a = 0.0
	_raiz.visible = true
	_desenho.queue_redraw()


func fechar() -> void:
	if not aberto:
		return
	aberto = false
	_raiz.visible = false
	var jogador := _jogador()
	if jogador:
		jogador.set("travado", false)
	if _pausou and is_inside_tree():
		get_tree().paused = false
	_pausou = false


func alternar() -> void:
	if aberto:
		fechar()
	else:
		abrir()


# ---------------------------------------------------------------------------
# Entrada e atualização
# ---------------------------------------------------------------------------

func _unhandled_input(evento: InputEvent) -> void:
	if InputMap.has_action("mapa") and evento.is_action_pressed("mapa"):
		if aberto:
			fechar()
		elif _pode_abrir():
			abrir()
		else:
			return
		get_viewport().set_input_as_handled()
		return
	if not aberto:
		return
	if InputMap.has_action("pausar") and evento.is_action_pressed("pausar"):
		fechar()
		get_viewport().set_input_as_handled()
		return
	# Rolagem do diário: setas, Page Up/Down ou a roda do mouse (o mouse fica preso
	# no centro da tela durante o jogo, então rolamos daqui, sem depender do ponteiro).
	var passo := 0
	if evento is InputEventMouseButton and evento.pressed:
		var botao := (evento as InputEventMouseButton).button_index
		if botao == MOUSE_BUTTON_WHEEL_UP:
			passo = -50
		elif botao == MOUSE_BUTTON_WHEEL_DOWN:
			passo = 50
	elif evento.is_action_pressed("ui_up", true):
		passo = -40
	elif evento.is_action_pressed("ui_down", true):
		passo = 40
	elif evento.is_action_pressed("ui_page_up", true):
		passo = -int(_rolagem.size.y * 0.8)
	elif evento.is_action_pressed("ui_page_down", true):
		passo = int(_rolagem.size.y * 0.8)
	if passo != 0:
		_rolagem.scroll_vertical += passo
		get_viewport().set_input_as_handled()


## Não abre por cima do menu de pausa nem de outra tela que já travou o vigia
## (documento, teclado, câmeras, minigame...).
func _pode_abrir() -> bool:
	if get_tree().paused:
		return false
	var jogador := _jogador()
	return jogador == null or not bool(jogador.get("travado"))


func _process(delta: float) -> void:
	if not aberto:
		return
	_tempo += delta
	_raiz.modulate.a = move_toward(_raiz.modulate.a, 1.0, delta * 7.0)
	_tempo_dados -= delta
	if _tempo_dados <= 0.0:
		_tempo_dados = INTERVALO_DADOS
		_dados = _ler_dados()
		_calcular_rotulos(_escala)  # disjuntores e portas podem ter mudado de estado
		_atualizar_diario()
	# Labels com quebra de linha só sabem a altura certa depois que recebem a largura;
	# no primeiro quadro o painel pode ter crescido demais. Reaplicamos o tamanho.
	if _diario.size != _tamanho_diario:
		_diario.size = _tamanho_diario
	if _rolar_fim_quadros > 0:
		# Espera o layout assentar para saber o tamanho real da lista.
		_rolar_fim_quadros -= 1
		if _rolar_fim_quadros == 0:
			_rolagem.scroll_vertical = int(_rolagem.get_v_scroll_bar().max_value)
	_desenho.queue_redraw()  # redesenha todo quadro por causa das animações


func _ao_mudar_tamanho() -> void:
	if aberto:
		_montar_layout()


func _jogador() -> Node:
	return get_tree().get_first_node_in_group("jogador") if is_inside_tree() else null


# ---------------------------------------------------------------------------
# Dados
# ---------------------------------------------------------------------------

func _ler_dados() -> Dictionary:
	var progressao := get_tree().get_first_node_in_group("progressao_v2")
	if progressao and progressao.has_method("dados_mapa"):
		var d: Variant = progressao.call("dados_mapa")
		if d is Dictionary:
			return d
	return _dados_exemplo()


## Lê um número de um dicionário (aceita int ou float).
static func _num(d: Dictionary, chave: String, padrao := 0.0) -> float:
	return float(d.get(chave, padrao))


func _comodos() -> Array:
	return PlantaV2.dados()["comodos"]


func _comodo_por_nome(nome: String) -> Dictionary:
	for comodo: Dictionary in _comodos():
		if str(comodo["nome"]) == nome:
			return comodo
	return {}


## Dados de mentira, no formato de ProgressaoV2.dados_mapa(), para testar a tela sozinha.
func _dados_exemplo() -> Dictionary:
	var planta := PlantaV2.dados()
	var pontos: Dictionary = planta["pontos"]
	var disjuntores: Array = []
	var estados := {"cozinha": true, "deposito": false, "gerente": true, "eletrica": false}
	for area: String in estados:
		var p: Array = pontos["disjuntor_" + area]
		disjuntores.append({"x": p[0], "z": p[1], "area": area, "ligado": estados[area]})
	var g: Array = pontos["gerador"]
	var portas: Array = []
	for porta: Dictionary in planta["portas"]:
		var tipo := str(porta["tipo"])
		if tipo not in PORTAS_ESPECIAIS:
			continue
		var fixo := float(porta["fixo"])
		var centro := float(porta["centro"])
		var no_eixo_z := str(porta["eixo"]) == "z"
		var trancada := tipo in ["corrente", "teclado", "chave", "aco", "emperrada"]
		portas.append({"x": centro if no_eixo_z else fixo, "z": fixo if no_eixo_z else centro,
			"eixo": porta["eixo"], "largura": porta["largura"], "tipo": tipo,
			"trancada": trancada, "aberta": not trancada})
	var visitados := {}
	for nome in ["Sala_Seguranca", "Corredor_Funcionarios", "Arquivo", "Copa", "Corredor_Principal",
			"Salao", "Oficina", "Cozinha", "Recepcao", "Fliperama", "Vestiario"]:
		visitados[nome] = true
	return {
		"jogador": {"x": 39.0, "z": 17.6, "angulo": PI * 1.5 + 0.25},
		"visitados": visitados,
		"disjuntores": disjuntores,
		"gerador": {"x": g[0], "z": g[1], "ligado": false},
		"portas": portas,
		"objetivo": {"texto": "Corte a corrente da porta do depósito com o alicate", "x": 7.0, "z": 19.4,
			"comodo": "Deposito"},
		"marcacao": marcacao_exemplo,
		"diario": [
			{"titulo": "Recado do gerente", "texto": "Vigia: o alicate ficou na oficina, em cima da bancada. Não abra a câmara fria por nada."},
			{"titulo": "Quadro de avisos da copa", "texto": "\"Senha nova da sala elétrica: começa com o número da mesa do aniversário do Tito.\""},
			{"titulo": "Cartão de aniversário", "texto": "Parabéns pelos 47 anos de pizzaria! Assinado: toda a equipe."},
			{"titulo": "Recorde do Tito Kart", "texto": "O placar mostra o recorde: 1º lugar, 0'58\". Alguém riscou os dois últimos números da senha embaixo dele."},
			{"titulo": "Folha de ponto rasgada", "texto": "Último turno registrado: 23h47. A assinatura do vigia anterior está borrada."},
		],
		"itens": ["Lanterna", "Alicate", "Chave do armário"],
		"fichas": 3,
		"senha": "47__",
	}


# ---------------------------------------------------------------------------
# Interface (criada por código)
# ---------------------------------------------------------------------------

func _criar_interface() -> void:
	_raiz = Control.new()
	_raiz.name = "Mapa"
	_raiz.set_anchors_preset(Control.PRESET_FULL_RECT)
	_raiz.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_raiz)

	# Fundo escuro: o jogo continua visível por trás (nas dificuldades sem pausa).
	var escuro := ColorRect.new()
	escuro.color = Color(0.0, 0.0, 0.02, 0.74)
	escuro.set_anchors_preset(Control.PRESET_FULL_RECT)
	escuro.mouse_filter = Control.MOUSE_FILTER_STOP
	_raiz.add_child(escuro)

	# A folha da planta: um Control que desenha a própria sombra, com o papel (shader)
	# e o desenho da planta como filhos que ocupam a folha inteira.
	_folha = Control.new()
	_folha.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_folha.draw.connect(_desenhar_sombra_folha)
	_raiz.add_child(_folha)

	_papel = ColorRect.new()
	_papel.set_anchors_preset(Control.PRESET_FULL_RECT)
	_papel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var material_papel := ShaderMaterial.new()
	material_papel.shader = SHADER_PAPEL
	_papel.material = material_papel
	_folha.add_child(_papel)

	_desenho = Control.new()
	_desenho.set_anchors_preset(Control.PRESET_FULL_RECT)
	_desenho.mouse_filter = Control.MOUSE_FILTER_IGNORE
	# O sinal "draw" é emitido quando o Control precisa ser redesenhado; aí chamamos as
	# funções draw_* dele a partir deste script.
	_desenho.draw.connect(_desenhar_planta)
	_folha.add_child(_desenho)

	_criar_diario()


func _criar_diario() -> void:
	_diario = PanelContainer.new()
	var estilo := StyleBoxFlat.new()
	estilo.bg_color = COR_PAPEL_DIARIO
	estilo.set_content_margin_all(20)
	estilo.content_margin_top = 18
	estilo.content_margin_bottom = 14
	estilo.set_border_width_all(1)
	estilo.border_color = Color(0.5, 0.42, 0.3)
	estilo.shadow_size = 14
	estilo.shadow_offset = Vector2(6, 8)
	estilo.shadow_color = Color(0, 0, 0, 0.55)
	_diario.add_theme_stylebox_override("panel", estilo)
	_raiz.add_child(_diario)

	var coluna := VBoxContainer.new()
	coluna.add_theme_constant_override("separation", 6)
	_diario.add_child(coluna)

	coluna.add_child(_rotulo("DIÁRIO DO VIGIA", FONTE_MAQUINA_NEGRITO, 24, COR_TINTA))
	coluna.add_child(_rotulo("Turno da noite · Pizzaria do Tito", FONTE_MAQUINA, 14, COR_TINTA_FRACA))
	coluna.add_child(_linha())
	coluna.add_child(_rotulo("OBJETIVO ATUAL", FONTE_MAQUINA_NEGRITO, 15, COR_TINTA_VERMELHA))
	_rot_objetivo = _rotulo("", FONTE_MAQUINA, 16, COR_TINTA)
	coluna.add_child(_rot_objetivo)
	coluna.add_child(_linha())
	_rot_senha = _rotulo("", FONTE_MAQUINA, 15, COR_TINTA)
	_rot_fichas = _rotulo("", FONTE_MAQUINA, 15, COR_TINTA)
	_rot_itens = _rotulo("", FONTE_MAQUINA, 15, COR_TINTA)
	coluna.add_child(_rot_senha)
	coluna.add_child(_rot_fichas)
	coluna.add_child(_rot_itens)
	coluna.add_child(_linha())
	_rot_anotacoes = _rotulo("ANOTAÇÕES", FONTE_MAQUINA_NEGRITO, 15, COR_TINTA_VERMELHA)
	coluna.add_child(_rot_anotacoes)

	_rolagem = ScrollContainer.new()
	_rolagem.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_rolagem.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	_estilizar_barra(_rolagem.get_v_scroll_bar())
	coluna.add_child(_rolagem)
	_lista_diario = VBoxContainer.new()
	_lista_diario.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_lista_diario.add_theme_constant_override("separation", 10)
	_rolagem.add_child(_lista_diario)

	coluna.add_child(_linha())
	_rot_dica = _rotulo("", FONTE_HUD, 20, COR_TINTA_FRACA)
	coluna.add_child(_rot_dica)


func _rotulo(texto: String, fonte: Font, tamanho: int, cor: Color) -> Label:
	var r := Label.new()
	r.text = texto
	r.add_theme_font_override("font", fonte)
	r.add_theme_font_size_override("font_size", tamanho)
	r.add_theme_color_override("font_color", cor)
	r.add_theme_constant_override("outline_size", 0)
	# Quebra por palavra; o texto nunca passa da largura do diário.
	r.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	r.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	return r


func _linha() -> ColorRect:
	var linha := ColorRect.new()
	linha.color = Color(COR_TINTA, 0.3)
	linha.custom_minimum_size = Vector2(0, 2)
	linha.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return linha


func _estilizar_barra(barra: VScrollBar) -> void:
	var trilho := StyleBoxFlat.new()
	trilho.bg_color = Color(COR_TINTA, 0.1)
	trilho.content_margin_left = 3
	trilho.content_margin_right = 3
	var pegador := StyleBoxFlat.new()
	pegador.bg_color = Color(COR_TINTA, 0.45)
	pegador.set_corner_radius_all(3)
	barra.add_theme_stylebox_override("scroll", trilho)
	barra.add_theme_stylebox_override("grabber", pegador)
	barra.add_theme_stylebox_override("grabber_highlight", pegador)
	barra.add_theme_stylebox_override("grabber_pressed", pegador)


## Posiciona a folha e o diário de acordo com o tamanho da tela.
func _montar_layout() -> void:
	var tela := get_viewport().get_visible_rect().size
	var largura_diario := clampf(tela.x * 0.26, 300.0, 440.0)
	var area := Vector2(tela.x - largura_diario - ESPACO_DIARIO - 2.0 * MARGEM_TELA, tela.y - 2.0 * MARGEM_TELA)

	# A escala (pixels por metro) depende do rodapé, e o rodapé depende da largura da
	# folha (a legenda quebra em mais linhas se a folha for estreita). Algumas voltas
	# bastam para os dois concordarem.
	var escala := 12.0
	for i in 4:
		_calcular_rotulos(escala)
		_altura_rodape = _calcular_rodape(LARGURA_PLANTA * escala)
		escala = minf((area.x - 2.0 * MARGEM_FOLHA) / LARGURA_PLANTA,
			(area.y - 2.0 * MARGEM_FOLHA - _altura_rodape) / ALTURA_PLANTA)
	_escala = escala
	_calcular_rotulos(_escala)
	_altura_rodape = _calcular_rodape(LARGURA_PLANTA * _escala)
	_paredes = _calcular_paredes()

	var tamanho_folha := Vector2(LARGURA_PLANTA * _escala + 2.0 * MARGEM_FOLHA,
		ALTURA_PLANTA * _escala + 2.0 * MARGEM_FOLHA + _altura_rodape)
	_origem = Vector2(MARGEM_FOLHA, MARGEM_FOLHA)

	# Folha + diário centralizados juntos na tela.
	var largura_total := tamanho_folha.x + ESPACO_DIARIO + largura_diario
	var x0 := (tela.x - largura_total) * 0.5
	_folha.position = Vector2(x0, (tela.y - tamanho_folha.y) * 0.5)
	_folha.size = tamanho_folha
	_folha.pivot_offset = tamanho_folha * 0.5
	_folha.rotation = deg_to_rad(INCLINACAO_FOLHA)

	var altura_diario := minf(tamanho_folha.y, tela.y - 2.0 * MARGEM_TELA)
	_diario.position = Vector2(x0 + tamanho_folha.x + ESPACO_DIARIO, (tela.y - altura_diario) * 0.5)
	_tamanho_diario = Vector2(largura_diario, altura_diario)
	_diario.size = _tamanho_diario
	_diario.pivot_offset = _diario.size * 0.5
	_diario.rotation = deg_to_rad(INCLINACAO_DIARIO)
	_folha.queue_redraw()
	_desenho.queue_redraw()


## Preenche os textos do diário com os dados atuais.
func _atualizar_diario() -> void:
	var objetivo: Dictionary = _dados.get("objetivo", {})
	var texto_objetivo := str(objetivo.get("texto", ""))
	_rot_objetivo.text = texto_objetivo if texto_objetivo != "" else "Nenhum objetivo no momento."

	var senha := str(_dados.get("senha", ""))
	_rot_senha.text = "Senha anotada: " + (_formatar_senha(senha) if senha != "" else "nenhuma ainda")
	_rot_fichas.text = "Fichas: %d" % int(_dados.get("fichas", 0))
	var nomes := PackedStringArray()
	for item: Variant in _dados.get("itens", []):
		nomes.append(str(item).replace("_", " "))
	_rot_itens.text = "Itens: " + (", ".join(nomes) if not nomes.is_empty() else "nenhum")

	var dica := "M ou ESC: fechar\nSetas ou roda do mouse: rolar as anotações"
	if _pausou:
		dica += "\n(jogo pausado)"
	_rot_dica.text = dica

	# A lista de anotações só é refeita quando muda (para não piscar nem perder a rolagem).
	var diario: Array = _dados.get("diario", [])
	var assinatura := JSON.stringify(diario)
	if assinatura == _assinatura_diario:
		return
	var cresceu := diario.size() > _lista_diario.get_child_count()
	_assinatura_diario = assinatura
	for filho in _lista_diario.get_children():
		_lista_diario.remove_child(filho)
		filho.queue_free()
	_rot_anotacoes.text = "ANOTAÇÕES (%d)" % diario.size() if not diario.is_empty() else "ANOTAÇÕES"
	if diario.is_empty():
		_lista_diario.add_child(_rotulo("Nenhuma pista anotada ainda.", FONTE_MAQUINA, 14, COR_TINTA_FRACA))
	for i in diario.size():
		var entrada: Dictionary = diario[i]
		var bloco := VBoxContainer.new()
		bloco.add_theme_constant_override("separation", 2)
		bloco.add_child(_rotulo("%d. %s" % [i + 1, str(entrada.get("titulo", ""))], FONTE_MAQUINA_NEGRITO, 15, COR_TINTA))
		bloco.add_child(_rotulo(str(entrada.get("texto", "")), FONTE_MAQUINA, 14, COR_TINTA))
		_lista_diario.add_child(bloco)
	if cresceu:
		_rolar_fim_quadros = 3  # mostra a anotação mais nova


## "47__" vira "4 7 _ _" (mais fácil de ler).
static func _formatar_senha(senha: String) -> String:
	var partes := PackedStringArray()
	for letra in senha:
		partes.append(letra)
	return " ".join(partes)


# ---------------------------------------------------------------------------
# Cálculos da planta (feitos ao montar o layout, não a cada quadro)
# ---------------------------------------------------------------------------

## Ponto da planta (metros) para pixels dentro da folha.
func _p(x: float, z: float) -> Vector2:
	return _origem + Vector2(x, z) * _escala


func _rect_comodo(comodo: Dictionary) -> Rect2:
	var a := _p(_num(comodo, "x0"), _num(comodo, "z0"))
	var b := _p(_num(comodo, "x1"), _num(comodo, "z1"))
	return Rect2(a, b - a)


## Tamanho dos ícones (disjuntor, cadeado...) em pixels.
func _tamanho_icone() -> float:
	return clampf(_escala * 1.3, 14.0, 26.0)


## Posição de um ícone na planta, empurrada para dentro do prédio se estiver na parede de fora.
func _pos_icone(x: float, z: float) -> Vector2:
	var folga := _tamanho_icone() * 0.6
	var p := _p(x, z)
	var minimo := _origem + Vector2(folga, folga)
	var maximo := _origem + Vector2(LARGURA_PLANTA, ALTURA_PLANTA) * _escala - Vector2(folga, folga)
	return p.clamp(minimo, maximo)


## Retângulos (em pixels) ocupados por ícones fixos; os nomes dos cômodos fogem deles.
func _obstaculos() -> Array[Rect2]:
	var lista: Array[Rect2] = []
	var t := _tamanho_icone()
	for dj: Dictionary in _dados.get("disjuntores", []):
		lista.append(Rect2(_pos_icone(_num(dj, "x"), _num(dj, "z")) - Vector2(t, t) * 0.6, Vector2(t, t) * 1.2))
	var gerador: Dictionary = _dados.get("gerador", {})
	if not gerador.is_empty():
		lista.append(Rect2(_pos_icone(_num(gerador, "x"), _num(gerador, "z")) - Vector2(t, t) * 0.8, Vector2(t, t) * 1.6))
	for porta: Dictionary in _dados.get("portas", []):
		lista.append(Rect2(_p(_num(porta, "x"), _num(porta, "z")) - Vector2(t, t) * 0.6, Vector2(t, t) * 1.2))
	return lista


## Quebra o texto em linhas que cabem na largura, só entre palavras.
## Devolve vazio se alguma palavra sozinha já não couber (aí tentamos uma fonte menor).
static func _quebrar_linhas(texto: String, fonte: Font, tamanho: int, largura: float) -> PackedStringArray:
	var linhas := PackedStringArray()
	var atual := ""
	for palavra in texto.split(" ", false):
		if fonte.get_string_size(palavra, HORIZONTAL_ALIGNMENT_LEFT, -1, tamanho).x > largura:
			return PackedStringArray()
		var tentativa := palavra if atual == "" else atual + " " + palavra
		if fonte.get_string_size(tentativa, HORIZONTAL_ALIGNMENT_LEFT, -1, tamanho).x <= largura:
			atual = tentativa
		else:
			linhas.append(atual)
			atual = palavra
	if atual != "":
		linhas.append(atual)
	return linhas


static func _altura_linha(fonte: Font, tamanho: int) -> float:
	return fonte.get_height(tamanho) * 0.92


## Acha o maior tamanho de fonte (entre maximo e minimo) em que o texto cabe na caixa.
## Devolve {tamanho, linhas, largura, altura} ou {} se não couber nem no mínimo.
static func _caber_texto(texto: String, fonte: Font, caixa: Vector2, maximo: int, minimo: int) -> Dictionary:
	for tamanho in range(maximo, minimo - 1, -1):
		var linhas := _quebrar_linhas(texto, fonte, tamanho, caixa.x)
		if linhas.is_empty():
			continue
		var altura := linhas.size() * _altura_linha(fonte, tamanho)
		if altura > caixa.y:
			continue
		var largura := 0.0
		for linha in linhas:
			largura = maxf(largura, fonte.get_string_size(linha, HORIZONTAL_ALIGNMENT_LEFT, -1, tamanho).x)
		return {"tamanho": tamanho, "linhas": linhas, "largura": largura, "altura": altura}
	return {}


## Decide como escrever o nome de cada cômodo: na horizontal, na vertical (corredores
## compridos) ou, se não couber de jeito nenhum, um número com a legenda no rodapé.
func _calcular_rotulos(escala: float) -> void:
	_escala = escala  # _p() e _obstaculos() usam a escala
	_rotulos.clear()
	var obstaculos := _obstaculos()
	var maximo := clampi(int(escala * 1.75), 15, 28)
	var minimo := 13
	var numero := 0
	for comodo: Dictionary in _comodos():
		var r := _rect_comodo(comodo)
		var folga := maxf(4.0, escala * 0.35)
		var dentro := r.grow(-folga)
		var titulo := str(comodo["titulo"])
		var rotulo := {"nome": str(comodo["nome"]), "titulo": titulo, "centro": r.get_center(), "numero": 0}
		var em_pe := dentro.size.y > dentro.size.x * 2.0
		var deitado := _caber_texto(titulo, FONTE_MAO, dentro.size, maximo, minimo)
		var vertical := _caber_texto(titulo, FONTE_MAO, Vector2(dentro.size.y, dentro.size.x), maximo, minimo)
		if em_pe and not vertical.is_empty():
			rotulo.merge(vertical)
			rotulo["vertical"] = true
		elif not deitado.is_empty():
			# Procura o maior tamanho em que o nome cabe SEM cobrir um ícone; se não houver,
			# fica com o maior tamanho que cabe, no centro.
			rotulo.merge(deitado)
			rotulo["vertical"] = false
			rotulo["caixa"] = _posicao_rotulo(dentro, Vector2(deitado["largura"], deitado["altura"]), obstaculos)
			for tamanho in range(int(deitado["tamanho"]), minimo - 1, -1):
				var tentativa := _caber_texto(titulo, FONTE_MAO, dentro.size, tamanho, tamanho)
				if tentativa.is_empty():
					continue
				var caixa := _posicao_rotulo(dentro, Vector2(tentativa["largura"], tentativa["altura"]), obstaculos)
				if caixa.has_area():
					rotulo.merge(tentativa, true)
					rotulo["caixa"] = caixa
					break
			if not (rotulo["caixa"] as Rect2).has_area():
				rotulo["caixa"] = _caixa_central(dentro, Vector2(deitado["largura"], deitado["altura"]))
		elif not vertical.is_empty():
			rotulo.merge(vertical)
			rotulo["vertical"] = true
		else:
			# Não cabe: vira um número no círculo (explicado na legenda), longe dos ícones.
			numero += 1
			rotulo["numero"] = numero
			var dx := maxf(0.0, dentro.size.x * 0.5 - 9.0)
			for centro: Vector2 in [r.get_center(), r.get_center() + Vector2(dx, 0), r.get_center() - Vector2(dx, 0)]:
				var circulo := Rect2(centro - Vector2(9, 9), Vector2(18, 18))
				if not obstaculos.any(func(o: Rect2) -> bool: return o.intersects(circulo)):
					rotulo["centro"] = centro
					break
		_rotulos.append(rotulo)


## Tenta o nome no centro do cômodo; se bater num ícone, tenta em cima e embaixo.
## Devolve Rect2() (sem área) se todas as posições baterem em algum ícone.
static func _posicao_rotulo(dentro: Rect2, tamanho: Vector2, obstaculos: Array[Rect2]) -> Rect2:
	var x := dentro.position.x + (dentro.size.x - tamanho.x) * 0.5
	var candidatos := [
		dentro.position.y + (dentro.size.y - tamanho.y) * 0.5,
		dentro.position.y,
		dentro.end.y - tamanho.y,
	]
	for y: float in candidatos:
		var caixa := Rect2(x, y, tamanho.x, tamanho.y)
		var livre := true
		for o in obstaculos:
			if caixa.intersects(o):
				livre = false
				break
		if livre:
			return caixa
	return Rect2()


static func _caixa_central(dentro: Rect2, tamanho: Vector2) -> Rect2:
	return Rect2(dentro.get_center() - tamanho * 0.5, tamanho)


## Trechos de parede de todos os cômodos, já sem os vãos das portas (em metros).
func _calcular_paredes() -> Array[Dictionary]:
	var lista: Array[Dictionary] = []
	var portas: Array = PlantaV2.dados()["portas"]
	for comodo: Dictionary in _comodos():
		var x0 := _num(comodo, "x0")
		var x1 := _num(comodo, "x1")
		var z0 := _num(comodo, "z0")
		var z1 := _num(comodo, "z1")
		# Paredes horizontais (z fixo) cortadas pelas portas de eixo "z"; verticais pelas de eixo "x".
		for z in [z0, z1]:
			for trecho in _cortar(x0, x1, z, "z", portas):
				lista.append({"a": Vector2(trecho.x, z), "b": Vector2(trecho.y, z),
					"externa": is_equal_approx(z, 0.0) or is_equal_approx(z, ALTURA_PLANTA)})
		for x in [x0, x1]:
			for trecho in _cortar(z0, z1, x, "x", portas):
				lista.append({"a": Vector2(x, trecho.x), "b": Vector2(x, trecho.y),
					"externa": is_equal_approx(x, 0.0) or is_equal_approx(x, LARGURA_PLANTA)})
	return lista


## Divide o intervalo [inicio, fim] de uma parede tirando os vãos das portas dela.
## Devolve uma lista de Vector2(começo, fim).
static func _cortar(inicio: float, fim: float, fixo: float, eixo: String, portas: Array) -> Array[Vector2]:
	var vaos: Array[Vector2] = []
	for porta: Dictionary in portas:
		if str(porta["eixo"]) != eixo or absf(float(porta["fixo"]) - fixo) > 0.01:
			continue
		var c := float(porta["centro"])
		var meia := float(porta["largura"]) * 0.5
		if c + meia > inicio and c - meia < fim:
			vaos.append(Vector2(c - meia, c + meia))
	vaos.sort_custom(func(a: Vector2, b: Vector2) -> bool: return a.x < b.x)
	var trechos: Array[Vector2] = []
	var cursor := inicio
	for vao in vaos:
		if vao.x > cursor:
			trechos.append(Vector2(cursor, minf(vao.x, fim)))
		cursor = maxf(cursor, vao.y)
	if cursor < fim:
		trechos.append(Vector2(cursor, fim))
	return trechos


## Monta a legenda do rodapé (em fileiras que cabem na largura) e devolve a altura dele.
func _calcular_rodape(largura: float) -> float:
	_legenda.clear()
	var titulo_1 := FONTE_LETREIRO.get_string_size("PIZZARIA DO TITO", HORIZONTAL_ALIGNMENT_LEFT, -1, 15).x
	var titulo_2 := FONTE_MAQUINA.get_string_size("Planta baixa · térreo", HORIZONTAL_ALIGNMENT_LEFT, -1, 13).x
	_largura_titulo = maxf(titulo_1, titulo_2) + 18.0
	var itens: Array[Dictionary] = [
		{"tipo": "vigia", "texto": "Você"},
		{"tipo": "ligado", "texto": "Energia ligada"},
		{"tipo": "desligado", "texto": "Energia desligada"},
		{"tipo": "cadeado", "texto": "Porta trancada"},
		{"tipo": "nevoa", "texto": "Não visitado"},
	]
	match int(_dados.get("marcacao", 1)):
		0:
			itens.append({"tipo": "objetivo_ponto", "texto": "Objetivo"})
		1:
			itens.append({"tipo": "objetivo_comodo", "texto": "Cômodo do objetivo"})
	for rotulo in _rotulos:
		if int(rotulo["numero"]) > 0:
			itens.append({"tipo": "numero", "numero": rotulo["numero"], "texto": str(rotulo["titulo"])})

	var inicio := _largura_titulo + 14.0
	var fim := largura - 40.0  # espaço da rosa dos ventos
	var x := inicio
	var fileira := 0
	for item in itens:
		var w := 22.0 + FONTE_MAQUINA_NEGRITO.get_string_size(str(item["texto"]), HORIZONTAL_ALIGNMENT_LEFT, -1, 13).x
		if x > inicio and x + w > fim:
			fileira += 1
			x = inicio
		item["pos"] = Vector2(x, 10.0 + fileira * 22.0)
		_legenda.append(item)
		x += w + 18.0
	return maxf(52.0, 10.0 + (fileira + 1) * 22.0 + 6.0) + 6.0


# ---------------------------------------------------------------------------
# Desenho
# ---------------------------------------------------------------------------

func _desenhar_sombra_folha() -> void:
	# Sombra em camadas (mais larga e mais fraca por fora) para parecer macia.
	for i in 4:
		var cresce := float(4 - i) * 3.0
		_folha.draw_rect(Rect2(Vector2(9, 12) - Vector2(cresce, cresce), _folha.size + Vector2(cresce, cresce) * 2.0),
			Color(0, 0, 0, 0.12))


func _desenhar_planta() -> void:
	var c := _desenho
	# Moldura fina, como nas plantas de verdade.
	c.draw_rect(Rect2(Vector2(7, 7), _folha.size - Vector2(14, 14)), Color(COR_LINHA, 0.35), false, 1.5)
	_desenhar_grade(c)
	_desenhar_cotas(c)
	_desenhar_comodos(c)
	_desenhar_paredes(c)
	_desenhar_portas_especiais(c)
	_desenhar_rotulos(c)
	_desenhar_energia(c)
	_desenhar_objetivo(c)
	_desenhar_vigia(c)
	_desenhar_rodape(c)
	_desenhar_fitas(c)


## Quadriculado de 1 m (mais forte a cada 5 m).
func _desenhar_grade(c: CanvasItem) -> void:
	for i in range(0, int(LARGURA_PLANTA) + 1):
		c.draw_line(_p(i, 0), _p(i, ALTURA_PLANTA), COR_GRADE_FORTE if i % 5 == 0 else COR_GRADE, 1.0)
	for i in range(0, int(ALTURA_PLANTA) + 1):
		c.draw_line(_p(0, i), _p(LARGURA_PLANTA, i), COR_GRADE_FORTE if i % 5 == 0 else COR_GRADE, 1.0)


## Cotas (medidas) em cima e à esquerda da planta.
func _desenhar_cotas(c: CanvasItem) -> void:
	var cor := Color(COR_LINHA, 0.55)
	var y := _origem.y - 13.0
	var a := Vector2(_origem.x, y)
	var b := Vector2(_origem.x + LARGURA_PLANTA * _escala, y)
	var texto := "60 m"
	var w := FONTE_MAQUINA.get_string_size(texto, HORIZONTAL_ALIGNMENT_LEFT, -1, 12).x
	var meio := (a + b) * 0.5
	c.draw_line(a, Vector2(meio.x - w * 0.5 - 6, y), cor, 1.0)
	c.draw_line(Vector2(meio.x + w * 0.5 + 6, y), b, cor, 1.0)
	c.draw_line(a + Vector2(0, -4), a + Vector2(0, 4), cor, 1.0)
	c.draw_line(b + Vector2(0, -4), b + Vector2(0, 4), cor, 1.0)
	c.draw_string(FONTE_MAQUINA, Vector2(meio.x - w * 0.5, y + 4), texto, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, cor)
	# Lateral: escrita de lado.
	var x := _origem.x - 13.0
	var a2 := Vector2(x, _origem.y)
	var b2 := Vector2(x, _origem.y + ALTURA_PLANTA * _escala)
	var meio2 := (a2 + b2) * 0.5
	texto = "45 m"
	w = FONTE_MAQUINA.get_string_size(texto, HORIZONTAL_ALIGNMENT_LEFT, -1, 12).x
	c.draw_line(a2, Vector2(x, meio2.y - w * 0.5 - 6), cor, 1.0)
	c.draw_line(Vector2(x, meio2.y + w * 0.5 + 6), b2, cor, 1.0)
	c.draw_line(a2 + Vector2(-4, 0), a2 + Vector2(4, 0), cor, 1.0)
	c.draw_line(b2 + Vector2(-4, 0), b2 + Vector2(4, 0), cor, 1.0)
	c.draw_set_transform(meio2, -PI * 0.5)
	c.draw_string(FONTE_MAQUINA, Vector2(-w * 0.5, 4), texto, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, cor)
	c.draw_set_transform(Vector2.ZERO)


## Fundo dos cômodos: visitados levemente claros; os outros escuros e hachurados.
func _desenhar_comodos(c: CanvasItem) -> void:
	var visitados: Dictionary = _dados.get("visitados", {})
	for comodo: Dictionary in _comodos():
		var r := _rect_comodo(comodo)
		if visitados.has(str(comodo["nome"])):
			c.draw_rect(r, COR_VISITADO)
		else:
			c.draw_rect(r, COR_NEVOA)
			_hachurar(c, r, 7.0, COR_HACHURA)


## Linhas diagonais ("/") recortadas no retângulo. Cada linha é x + y = k.
static func _hachurar(c: CanvasItem, r: Rect2, espaco: float, cor: Color) -> void:
	var x0 := r.position.x
	var y0 := r.position.y
	var x1 := r.end.x
	var y1 := r.end.y
	var k := x0 + y0 + espaco
	while k < x1 + y1:
		var inicio := Vector2(maxf(x0, k - y1), 0.0)
		inicio.y = k - inicio.x
		var fim := Vector2(minf(x1, k - y0), 0.0)
		fim.y = k - fim.x
		if inicio.x < fim.x:
			c.draw_line(inicio, fim, cor, 1.0)
		k += espaco


func _desenhar_paredes(c: CanvasItem) -> void:
	for parede in _paredes:
		var a: Vector2 = parede["a"]
		var b: Vector2 = parede["b"]
		c.draw_line(_p(a.x, a.y), _p(b.x, b.y), COR_LINHA, 3.0 if parede["externa"] else 2.0, true)
	# Portas comuns: batentes nas pontas e o arco de abertura (como nas plantas).
	for porta: Dictionary in PlantaV2.dados()["portas"]:
		var fixo := float(porta["fixo"])
		var centro := float(porta["centro"])
		var meia := float(porta["largura"]) * 0.5
		var horizontal := str(porta["eixo"]) == "z"  # parede horizontal: z fixo
		var ao_longo := Vector2(1, 0) if horizontal else Vector2(0, 1)
		var normal := Vector2(0, 1) if horizontal else Vector2(1, 0)
		var meio := _p(centro, fixo) if horizontal else _p(fixo, centro)
		var a := meio - ao_longo * meia * _escala
		var b := meio + ao_longo * meia * _escala
		var batente := 0.35 * _escala
		c.draw_line(a - normal * batente, a + normal * batente, COR_LINHA, 2.0, true)
		c.draw_line(b - normal * batente, b + normal * batente, COR_LINHA, 2.0, true)
		if meia * 2.0 <= 2.0:
			var raio := meia * 2.0 * _escala
			c.draw_line(a, a + normal * raio, COR_LINHA_FRACA, 1.0, true)
			c.draw_arc(a, raio, normal.angle(), ao_longo.angle(), 10, COR_LINHA_FRACA, 1.0, true)


## Portas especiais vindas de dados_mapa(): trancadas com barra e cadeado vermelho;
## abertas com um cadeado aberto claro.
func _desenhar_portas_especiais(c: CanvasItem) -> void:
	var t := _tamanho_icone()
	for porta: Dictionary in _dados.get("portas", []):
		var x := _num(porta, "x")
		var z := _num(porta, "z")
		var meia := _num(porta, "largura", 1.4) * 0.5 * _escala
		var ao_longo := Vector2(1, 0) if _porta_horizontal(porta) else Vector2(0, 1)
		var centro := _p(x, z)
		if bool(porta.get("trancada", false)):
			c.draw_line(centro - ao_longo * meia, centro + ao_longo * meia, Color(1, 1, 1, 0.7), 7.0)
			c.draw_line(centro - ao_longo * meia, centro + ao_longo * meia, COR_DESLIGADO, 4.0)
			_icone_cadeado(c, centro, t, true)
		else:
			_icone_cadeado(c, centro, t * 0.8, false)


## A parede da porta é horizontal (z fixo)? Usa a porta da planta mais próxima para não
## depender de como o campo "eixo" foi preenchido; se não achar, usa o "eixo" recebido.
func _porta_horizontal(porta: Dictionary) -> bool:
	var x := _num(porta, "x")
	var z := _num(porta, "z")
	for p: Dictionary in PlantaV2.dados()["portas"]:
		var horizontal := str(p["eixo"]) == "z"
		var px := float(p["centro"]) if horizontal else float(p["fixo"])
		var pz := float(p["fixo"]) if horizontal else float(p["centro"])
		if absf(px - x) < 0.8 and absf(pz - z) < 0.8:
			return horizontal
	return str(porta.get("eixo", "z")) == "z"


func _desenhar_rotulos(c: CanvasItem) -> void:
	var visitados: Dictionary = _dados.get("visitados", {})
	for rotulo in _rotulos:
		var visitado := visitados.has(str(rotulo["nome"]))
		var cor := COR_LINHA if visitado else Color(COR_LINHA, 0.6)
		var contorno := COR_CONTORNO if visitado else Color(COR_CONTORNO, 0.5)
		if int(rotulo["numero"]) > 0:
			_icone_numero(c, rotulo["centro"], int(rotulo["numero"]), cor)
			continue
		var tamanho: int = rotulo["tamanho"]
		var linhas: PackedStringArray = rotulo["linhas"]
		var largura: float = rotulo["largura"]
		var altura: float = rotulo["altura"]
		var topo: Vector2
		if rotulo["vertical"]:
			# Corredores compridos: gira o "papel" -90° em volta do centro e escreve normal.
			c.draw_set_transform(rotulo["centro"], -PI * 0.5)
			topo = Vector2(-largura * 0.5, -altura * 0.5)
		else:
			var caixa: Rect2 = rotulo["caixa"]
			topo = caixa.position
		var lh := _altura_linha(FONTE_MAO, tamanho)
		for i in linhas.size():
			var base := topo + Vector2(0, FONTE_MAO.get_ascent(tamanho) + i * lh)
			c.draw_string_outline(FONTE_MAO, base, linhas[i], HORIZONTAL_ALIGNMENT_CENTER, largura, tamanho, 4, contorno)
			c.draw_string(FONTE_MAO, base, linhas[i], HORIZONTAL_ALIGNMENT_CENTER, largura, tamanho, cor)
		c.draw_set_transform(Vector2.ZERO)


func _desenhar_energia(c: CanvasItem) -> void:
	var t := _tamanho_icone()
	for dj: Dictionary in _dados.get("disjuntores", []):
		_icone_disjuntor(c, _pos_icone(_num(dj, "x"), _num(dj, "z")), t, bool(dj.get("ligado", false)))
	var gerador: Dictionary = _dados.get("gerador", {})
	if not gerador.is_empty():
		_icone_gerador(c, _pos_icone(_num(gerador, "x"), _num(gerador, "z")), t * 1.35, bool(gerador.get("ligado", false)))


## Objetivo conforme a dificuldade: 0 = ponto exato + bilhete; 1 = cômodo; 2 = nada.
func _desenhar_objetivo(c: CanvasItem) -> void:
	var objetivo: Dictionary = _dados.get("objetivo", {})
	var marcacao := int(_dados.get("marcacao", 1))
	if objetivo.is_empty() or marcacao == 2:
		return
	var pulso := 0.5 + 0.5 * sin(_tempo * 4.5)
	if marcacao == 0 and objetivo.has("x") and objetivo.has("z"):
		var ponto := _p(_num(objetivo, "x"), _num(objetivo, "z"))
		var raio := clampf(_escala * 1.3, 12.0, 24.0) * (1.0 + 0.12 * pulso)
		_marca_objetivo(c, ponto, raio, 1.0)
		_bilhete_objetivo(c, ponto, raio, str(objetivo.get("texto", "")))
	elif marcacao == 1:
		var comodo := _comodo_por_nome(str(objetivo.get("comodo", "")))
		if comodo.is_empty():
			return
		var r := _rect_comodo(comodo)
		c.draw_rect(r, Color(COR_CANETA, 0.08 + 0.06 * pulso))
		var cor := Color(COR_CANETA, 0.75 + 0.25 * pulso)
		_retangulo_caneta(c, r.grow(2.0), Color(1, 1, 1, 0.45), 6.0, 0.0)
		_retangulo_caneta(c, r.grow(2.0), cor, 3.0, 0.0)
		_retangulo_caneta(c, r.grow(-2.0), Color(cor, 0.6), 1.5, 2.1)


## Círculo de caneta com um X no meio (com contorno claro para aparecer no azul).
func _marca_objetivo(c: CanvasItem, ponto: Vector2, raio: float, alfa: float) -> void:
	_circulo_caneta(c, ponto, raio, Color(1, 1, 1, 0.5 * alfa), 6.0)
	_circulo_caneta(c, ponto, raio, Color(COR_CANETA, alfa), 3.0)
	var d := raio * 0.5
	for traco in [[Vector2(-d, -d), Vector2(d, d)], [Vector2(d, -d), Vector2(-d, d)]]:
		c.draw_line(ponto + traco[0], ponto + traco[1], Color(1, 1, 1, 0.5 * alfa), 6.0, true)
		c.draw_line(ponto + traco[0], ponto + traco[1], Color(COR_CANETA, alfa), 3.0, true)


## Círculo "feito à mão": raio ondulando um pouco e a ponta passando do começo.
static func _circulo_caneta(c: CanvasItem, centro: Vector2, raio: float, cor: Color, largura: float) -> void:
	var pontos := PackedVector2Array()
	for i in 49:
		var a := -0.7 + float(i) / 48.0 * (TAU + 0.6)
		var r := raio * (1.0 + 0.07 * sin(a * 3.0 + 1.3))
		pontos.append(centro + Vector2(cos(a), sin(a)) * r)
	c.draw_polyline(pontos, cor, largura, true)


## Retângulo de caneta: as bordas tremem um pouquinho (seno), como um traço feito à mão.
static func _retangulo_caneta(c: CanvasItem, r: Rect2, cor: Color, largura: float, semente: float) -> void:
	var cantos := [r.position, Vector2(r.end.x, r.position.y), r.end, Vector2(r.position.x, r.end.y), r.position]
	var pontos := PackedVector2Array()
	for i in 4:
		var a: Vector2 = cantos[i]
		var b: Vector2 = cantos[i + 1]
		var normal := (b - a).normalized().orthogonal()
		var passos := maxi(2, int(a.distance_to(b) / 14.0))
		for j in passos:
			var t := float(j) / passos
			var tremida := sin(t * 9.0 + i * 2.3 + semente) * 1.3
			pontos.append(a.lerp(b, t) + normal * tremida)
	pontos.append(pontos[0])
	c.draw_polyline(pontos, cor, largura, true)


## Bilhete amarelo (post-it) com o texto do objetivo, ao lado da marca.
func _bilhete_objetivo(c: CanvasItem, ponto: Vector2, raio: float, texto: String) -> void:
	if texto == "":
		return
	var largura := clampf(_escala * 13.0, 150.0, 220.0)
	var folga := 8.0
	var encaixe := _caber_texto(texto, FONTE_CANETA, Vector2(largura - 2 * folga, 120.0), 22, 15)
	if encaixe.is_empty():
		return
	var tamanho := Vector2(largura, float(encaixe["altura"]) + 2 * folga)
	# Tenta à direita, à esquerda, embaixo e em cima; fica no primeiro que cabe na planta.
	var planta := Rect2(_origem, Vector2(LARGURA_PLANTA, ALTURA_PLANTA) * _escala)
	var opcoes := [
		Vector2(ponto.x + raio + 10, ponto.y - tamanho.y * 0.5),
		Vector2(ponto.x - raio - 10 - tamanho.x, ponto.y - tamanho.y * 0.5),
		Vector2(ponto.x - tamanho.x * 0.5, ponto.y + raio + 10),
		Vector2(ponto.x - tamanho.x * 0.5, ponto.y - raio - 10 - tamanho.y),
	]
	var canto: Vector2 = opcoes[0]
	for opcao: Vector2 in opcoes:
		if planta.encloses(Rect2(opcao, tamanho)):
			canto = opcao
			break
	canto = canto.clamp(planta.position, planta.end - tamanho)
	# Desenha girado 2° em volta do centro do bilhete.
	c.draw_set_transform(canto + tamanho * 0.5, deg_to_rad(2.0))
	var r := Rect2(-tamanho * 0.5, tamanho)
	c.draw_rect(Rect2(r.position + Vector2(3, 4), r.size), Color(0, 0, 0, 0.35))
	c.draw_rect(r, COR_POST_IT)
	c.draw_rect(Rect2(r.position, Vector2(r.size.x, 6)), Color(0.92, 0.8, 0.3))  # faixa de cola
	var t: int = encaixe["tamanho"]
	var linhas: PackedStringArray = encaixe["linhas"]
	var lh := _altura_linha(FONTE_CANETA, t)
	for i in linhas.size():
		var base := r.position + Vector2(folga, folga + FONTE_CANETA.get_ascent(t) + i * lh)
		c.draw_string(FONTE_CANETA, base, linhas[i], HORIZONTAL_ALIGNMENT_LEFT, r.size.x - 2 * folga, t, Color(0.55, 0.05, 0.04))
	c.draw_set_transform(Vector2.ZERO)


## O vigia: seta amarela pulsando, com o cone da lanterna e um anel que se espalha.
func _desenhar_vigia(c: CanvasItem) -> void:
	var jogador: Dictionary = _dados.get("jogador", {})
	if jogador.is_empty():
		return
	var pos := _p(_num(jogador, "x"), _num(jogador, "z"))
	var angulo := _num(jogador, "angulo")
	# 0 = norte (para cima no mapa), crescendo no sentido horário.
	var frente := Vector2(sin(angulo), -cos(angulo))
	var lado := frente.orthogonal()

	var cone := PackedVector2Array([pos])
	var alcance := 5.0 * _escala
	for i in 9:
		var a := angulo - 0.42 + 0.84 * float(i) / 8.0
		cone.append(pos + Vector2(sin(a), -cos(a)) * alcance)
	c.draw_colored_polygon(cone, Color(COR_VIGIA, 0.16))

	var fase := fmod(_tempo * 0.9, 1.0)
	c.draw_arc(pos, lerpf(6.0, 3.0 * _escala, fase), 0.0, TAU, 40, Color(COR_VIGIA, 0.6 * (1.0 - fase)), 2.0, true)

	var l := clampf(_escala * 1.1, 11.0, 20.0) * (1.0 + 0.1 * sin(_tempo * 6.0))
	var seta := PackedVector2Array([
		pos + frente * l,
		pos - frente * l * 0.6 + lado * l * 0.7,
		pos - frente * l * 0.25,
		pos - frente * l * 0.6 - lado * l * 0.7,
	])
	c.draw_colored_polygon(seta, COR_VIGIA)
	var contorno := seta.duplicate()
	contorno.append(seta[0])
	c.draw_polyline(contorno, COR_CONTORNO, 2.0, true)


## Rodapé da folha: carimbo com o título, legenda dos símbolos e a rosa dos ventos.
func _desenhar_rodape(c: CanvasItem) -> void:
	var largura := LARGURA_PLANTA * _escala
	var y0 := _origem.y + ALTURA_PLANTA * _escala + 10.0
	var x0 := _origem.x
	c.draw_line(Vector2(x0, y0), Vector2(x0 + largura, y0), COR_LINHA_FRACA, 1.5)
	c.draw_line(Vector2(x0 + _largura_titulo, y0 + 6), Vector2(x0 + _largura_titulo, y0 + _altura_rodape - 12), COR_LINHA_FRACA, 1.0)
	c.draw_string(FONTE_LETREIRO, Vector2(x0, y0 + 26), "PIZZARIA DO TITO", HORIZONTAL_ALIGNMENT_LEFT, -1, 15, COR_LINHA)
	c.draw_string(FONTE_MAQUINA, Vector2(x0, y0 + 44), "Planta baixa · térreo", HORIZONTAL_ALIGNMENT_LEFT, -1, 13, Color(COR_LINHA, 0.85))

	for item in _legenda:
		var p: Vector2 = Vector2(x0, y0) + item["pos"]
		var icone := p + Vector2(8, 9)
		match str(item["tipo"]):
			"vigia":
				var seta := PackedVector2Array([icone + Vector2(0, -8), icone + Vector2(6, 6), icone + Vector2(0, 3), icone + Vector2(-6, 6)])
				c.draw_colored_polygon(seta, COR_VIGIA)
			"ligado":
				_icone_disjuntor(c, icone, 15.0, true)
			"desligado":
				_icone_disjuntor(c, icone, 15.0, false)
			"cadeado":
				_icone_cadeado(c, icone, 15.0, true)
			"nevoa":
				var r := Rect2(icone - Vector2(7, 7), Vector2(14, 14))
				c.draw_rect(r, COR_NEVOA)
				_hachurar(c, r, 4.0, Color(COR_HACHURA, 0.5))
				c.draw_rect(r, COR_LINHA_FRACA, false, 1.0)
			"objetivo_ponto":
				_marca_objetivo(c, icone, 7.0, 1.0)
			"objetivo_comodo":
				var r2 := Rect2(icone - Vector2(7, 6), Vector2(14, 12))
				c.draw_rect(r2, Color(COR_CANETA, 0.15))
				c.draw_rect(r2, COR_CANETA, false, 2.0)
			"numero":
				_icone_numero(c, icone, int(item["numero"]), COR_LINHA)
		c.draw_string(FONTE_MAQUINA_NEGRITO, p + Vector2(22, 14), str(item["texto"]), HORIZONTAL_ALIGNMENT_LEFT, -1, 13, COR_LINHA)

	# Rosa dos ventos simples: seta para o norte.
	var n := Vector2(x0 + largura - 16, y0 + _altura_rodape * 0.5)
	c.draw_colored_polygon(PackedVector2Array([n + Vector2(0, -14), n + Vector2(7, 8), n + Vector2(0, 3), n + Vector2(-7, 8)]), COR_LINHA)
	c.draw_string(FONTE_MAQUINA_NEGRITO, n + Vector2(-5, -17), "N", HORIZONTAL_ALIGNMENT_LEFT, -1, 13, COR_LINHA)


## Duas tiras de fita crepe segurando a folha.
func _desenhar_fitas(c: CanvasItem) -> void:
	var tamanho := Vector2(78, 22)
	var cantos := [[Vector2(30, 4), -0.55], [Vector2(_folha.size.x - 30, 4), 0.55]]
	for canto in cantos:
		c.draw_set_transform(canto[0], canto[1])
		c.draw_rect(Rect2(-tamanho * 0.5, tamanho), COR_FITA)
		c.draw_set_transform(Vector2.ZERO)


# ---------------------------------------------------------------------------
# Ícones (desenhados com primitivas: retângulos, arcos e polígonos)
# ---------------------------------------------------------------------------

## Raio (relâmpago) dentro de um quadrado de lado t centrado em p.
static func _raio(c: CanvasItem, p: Vector2, t: float, cor: Color) -> void:
	var forma := [Vector2(0.15, -0.5), Vector2(-0.28, 0.06), Vector2(-0.02, 0.06), Vector2(-0.15, 0.5),
		Vector2(0.28, -0.1), Vector2(0.02, -0.1)]
	var pontos := PackedVector2Array()
	for v: Vector2 in forma:
		pontos.append(p + v * t)
	c.draw_colored_polygon(pontos, cor)


## Disjuntor: caixinha verde (ligado) ou vermelha (desligado) com um raio.
static func _icone_disjuntor(c: CanvasItem, p: Vector2, t: float, ligado: bool) -> void:
	var r := Rect2(p - Vector2(t * 0.42, t * 0.5), Vector2(t * 0.84, t))
	c.draw_rect(r.grow(1.5), COR_CONTORNO)
	c.draw_rect(r, COR_LIGADO if ligado else COR_DESLIGADO)
	_raio(c, p, t * 0.8, COR_CONTORNO)


## Gerador: círculo com raio, com anel claro.
static func _icone_gerador(c: CanvasItem, p: Vector2, t: float, ligado: bool) -> void:
	c.draw_circle(p, t * 0.5 + 2.5, COR_LINHA)
	c.draw_circle(p, t * 0.5 + 1.0, COR_CONTORNO)
	c.draw_circle(p, t * 0.5 - 0.5, COR_LIGADO if ligado else COR_DESLIGADO)
	_raio(c, p, t * 0.7, COR_CONTORNO)


## Cadeado: fechado e vermelho (porta trancada) ou aberto e claro (porta liberada).
static func _icone_cadeado(c: CanvasItem, p: Vector2, t: float, trancado: bool) -> void:
	var cor := COR_DESLIGADO if trancado else Color(0.85, 0.92, 1.0)
	var corpo := Rect2(p + Vector2(-t * 0.42, -t * 0.08), Vector2(t * 0.84, t * 0.6))
	# Alça: um arco em cima do corpo; no cadeado aberto, a alça sobe e fica de lado.
	var centro_alca := p + Vector2(0, -t * 0.08) + (Vector2.ZERO if trancado else Vector2(t * 0.2, -t * 0.2))
	var raio_alca := t * 0.26
	c.draw_arc(centro_alca, raio_alca, PI, TAU, 12, COR_CONTORNO, t * 0.14 + 3.0, true)
	c.draw_arc(centro_alca, raio_alca, PI, TAU, 12, cor, t * 0.14, true)
	c.draw_rect(corpo.grow(1.5), COR_CONTORNO)
	c.draw_rect(corpo, cor)
	c.draw_circle(corpo.get_center() + Vector2(0, -t * 0.04), t * 0.08, COR_CONTORNO)


## Número num círculo (cômodos pequenos demais para o nome).
static func _icone_numero(c: CanvasItem, p: Vector2, numero: int, cor: Color) -> void:
	c.draw_circle(p, 8.5, COR_CONTORNO)
	c.draw_arc(p, 8.0, 0.0, TAU, 24, cor, 1.5, true)
	var texto := str(numero)
	var w := FONTE_MAQUINA_NEGRITO.get_string_size(texto, HORIZONTAL_ALIGNMENT_LEFT, -1, 12).x
	c.draw_string(FONTE_MAQUINA_NEGRITO, p + Vector2(-w * 0.5, 4.5), texto, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, cor)
