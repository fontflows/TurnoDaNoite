extends PanelContainer
## Painel de opções (menu principal e pausa), com abas Vídeo / Áudio / Controles.
## Cada mudança vale na hora (Config.aplicar) e é salva em disco ao clicar em "Voltar".
##
## As opções são montadas por código a partir das listas abaixo: para criar uma opção
## nova, basta acrescentar uma linha (e a variável correspondente em scripts/config.gd).

## Avisa quem abriu o painel que ele foi fechado.
signal fechado()

# Cada item: [tipo, variável do Config, rótulo, ...detalhes]
#   "deslizar": mínimo, máximo, passo, formato do texto ("%" = porcentagem, "x" = multiplicador, "°", "")
#   "marcar": (sem detalhes)
#   "escolher": lista de opções (a posição na lista é o valor salvo)
const VIDEO := [
	["escolher", "modo_janela", "Modo da janela (F11)", ["Janela", "Tela cheia", "Tela cheia sem borda"]],
	["escolher", "qualidade", "Qualidade gráfica", ["Baixa", "Média", "Alta"]],
	["deslizar", "escala_render", "Resolução 3D", 0.5, 1.0, 0.05, "%"],
	["marcar", "vsync", "Sincronia vertical (VSync)"],
	["escolher", "limite_fps", "Limite de FPS", ["Sem limite", "30", "60", "120", "144"]],
	["deslizar", "fov", "Campo de visão (FOV)", 60.0, 100.0, 1.0, "°"],
	["deslizar", "brilho", "Brilho", 0.7, 1.25, 0.01, ""],
	["marcar", "vhs_ativo", "Filtro VHS"],
	["deslizar", "vhs_intensidade", "Intensidade do VHS", 0.0, 1.0, 0.05, "%"],
]
const AUDIO := [
	["deslizar", "volume_geral", "Volume geral", 0.0, 1.0, 0.05, "%"],
	["deslizar", "volume_musica", "Música", 0.0, 1.0, 0.05, "%"],
	["deslizar", "volume_efeitos", "Efeitos", 0.0, 1.0, 0.05, "%"],
	["deslizar", "volume_vozes", "Vozes", 0.0, 1.0, 0.05, "%"],
]
const CONTROLES := [
	["deslizar", "sensibilidade", "Sensibilidade do mouse", 0.2, 3.0, 0.1, "x"],
	["marcar", "inverter_y", "Inverter o eixo Y do mouse"],
	["marcar", "mostrar_objetivo", "Mostrar o objetivo na tela"],
]

@onready var abas: TabContainer = %Abas
@onready var botao_voltar: Button = %BotaoVoltar

## variável -> [controle, rótulo do valor ou null, formato]
var _controles := {}
var _primeiro_controle: Control


func _ready() -> void:
	_montar(abas.get_node("Vídeo"), VIDEO)
	_montar_calibragem(abas.get_node("Vídeo"))
	_montar(abas.get_node("Áudio"), AUDIO)
	_montar(abas.get_node("Controles"), CONTROLES)
	botao_voltar.pressed.connect(voltar)
	visibility_changed.connect(_ao_mudar_visibilidade)
	_ler_config()


## Fecha o painel salvando as opções.
func voltar() -> void:
	Config.salvar()
	hide()
	fechado.emit()


func _ao_mudar_visibilidade() -> void:
	if visible:
		_ler_config()  # outra tela pode ter mudado as opções (ex.: F11)
		if _primeiro_controle:
			_primeiro_controle.grab_focus()


func _montar(aba: Control, itens: Array) -> void:
	var grade := GridContainer.new()
	grade.columns = 3
	grade.add_theme_constant_override("h_separation", 18)
	grade.add_theme_constant_override("v_separation", 10)
	aba.add_child(grade)
	for item in itens:
		var tipo: String = item[0]
		var variavel: String = item[1]
		var rotulo := Label.new()
		rotulo.text = item[2]
		rotulo.custom_minimum_size.x = 260
		grade.add_child(rotulo)
		var valor: Label = null
		var controle: Control
		match tipo:
			"deslizar":
				var s := HSlider.new()
				s.min_value = item[3]
				s.max_value = item[4]
				s.step = item[5]
				s.custom_minimum_size.x = 260
				s.size_flags_vertical = Control.SIZE_SHRINK_CENTER
				s.value_changed.connect(_ao_mudar.bind(variavel))
				controle = s
				valor = Label.new()
				valor.theme_type_variation = &"RotuloHUD"
				valor.add_theme_font_size_override("font_size", 26)
				valor.custom_minimum_size.x = 70
			"marcar":
				var c := CheckButton.new()
				c.toggled.connect(_ao_mudar.bind(variavel))
				controle = c
			"escolher":
				var o := OptionButton.new()
				for texto in item[3]:
					o.add_item(texto)
				o.item_selected.connect(_ao_escolher.bind(variavel))
				controle = o
		grade.add_child(controle)
		grade.add_child(valor if valor else Control.new())
		_controles[variavel] = [controle, valor, item[6] if tipo == "deslizar" else ""]
		if _primeiro_controle == null:
			_primeiro_controle = controle


## Quadro de calibragem clássico: ajuste o brilho até o símbolo ficar QUASE invisível.
func _montar_calibragem(aba: Control) -> void:
	var caixa := HBoxContainer.new()
	caixa.add_theme_constant_override("separation", 16)
	var fundo := PanelContainer.new()
	var estilo := StyleBoxFlat.new()
	estilo.bg_color = Color.BLACK
	estilo.set_content_margin_all(14)
	fundo.add_theme_stylebox_override("panel", estilo)
	var simbolo := Label.new()
	simbolo.text = "T"  # a inicial do Tito, quase da cor do fundo
	simbolo.theme_type_variation = &"RotuloTitulo"
	simbolo.add_theme_font_size_override("font_size", 56)
	simbolo.add_theme_color_override("font_color", Color(0.045, 0.045, 0.05))
	simbolo.add_theme_constant_override("outline_size", 0)
	simbolo.custom_minimum_size = Vector2(80, 70)
	simbolo.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	fundo.add_child(simbolo)
	var texto := Label.new()
	texto.text = "Ajuste o brilho até a letra no quadro preto\nficar QUASE invisível. O jogo foi feito para ser escuro."
	texto.add_theme_font_size_override("font_size", 16)
	caixa.add_child(fundo)
	caixa.add_child(texto)
	aba.add_child(caixa)


func _ler_config() -> void:
	for variavel in _controles:
		var controle: Control = _controles[variavel][0]
		var v = Config.get(variavel)
		if controle is HSlider:
			controle.set_value_no_signal(v)
		elif controle is CheckButton:
			controle.set_pressed_no_signal(v)
		elif controle is OptionButton:
			controle.select(Config.LIMITES_FPS.find(v) if variavel == "limite_fps" else int(v))
	_atualizar_textos()


func _ao_mudar(valor, variavel: String) -> void:
	Config.set(variavel, valor)
	Config.aplicar()
	_atualizar_textos()


func _ao_escolher(indice: int, variavel: String) -> void:
	Config.set(variavel, Config.LIMITES_FPS[indice] if variavel == "limite_fps" else indice)
	Config.aplicar()
	_atualizar_textos()


func _atualizar_textos() -> void:
	for variavel in _controles:
		var c: Array = _controles[variavel]
		if c[1] == null:
			continue
		var v: float = c[0].value
		match c[2]:
			"%": c[1].text = "%d%%" % roundi(v * 100.0)
			"x": c[1].text = "x%.1f" % v
			"°": c[1].text = "%d°" % roundi(v)
			_: c[1].text = "%.2f" % v
	if _controles.has("vhs_intensidade"):
		_controles["vhs_intensidade"][0].editable = Config.vhs_ativo
