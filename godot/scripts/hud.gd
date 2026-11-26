extends CanvasLayer
## HUD: hora, bateria, disjuntores, mira e dica de interação.
## Ele só LÊ o estado do jogo (Jogo e jogador); não muda nada.

## Cor da barra de bateria normal.
@export var cor_bateria := Color(0.9, 0.68, 0.22)
## Cor da barra quando a bateria está baixa.
@export var cor_bateria_baixa := Color(0.85, 0.2, 0.15)

const SOM_BADALADA := preload("res://assets/sons/badalada.wav")

@onready var relogio: Label = $Relogio
@onready var disjuntores: Label = $Disjuntores
@onready var barra: ProgressBar = $Bateria/Barra
@onready var porcentagem: Label = $Bateria/Porcentagem
@onready var dica: Label = $Dica
@onready var mensagem: Label = $Mensagem
@onready var som_badalada: AudioStreamPlayer = $SomBadalada

var _estilo_barra: StyleBoxFlat
var _tween_mensagem: Tween

# --- V2: fôlego, ar, objetivo e inventário (criados por código, só no mapa novo) ---
var _barra_stamina: ProgressBar
var _barra_folego: ProgressBar
var _painel_objetivo: PanelContainer
var _titulo_objetivo: Label
var _passos_objetivo: VBoxContainer
var _ultimo_objetivo := ""
var _tempo_destaque := 0.0
var _tempo_refazer := 0.0
var _som_objetivo: AudioStreamPlayer
var _inventario: PanelContainer
var _texto_inventario: Label
var _fichas: Label


func _ready() -> void:
	_estilo_barra = barra.get_theme_stylebox("fill").duplicate()
	barra.add_theme_stylebox_override("fill", _estilo_barra)
	mensagem.modulate.a = 0.0
	# Mensagens longas quebram por palavra, com margem dos lados (nunca cortam nas bordas).
	mensagem.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	mensagem.offset_left = 80
	mensagem.offset_right = -80
	mensagem.offset_bottom = mensagem.offset_top + 140
	mensagem.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	mensagem.vertical_alignment = VERTICAL_ALIGNMENT_TOP
	Jogo.mensagem.connect(mostrar_mensagem)
	Jogo.hora_mudou.connect(_ao_mudar_hora)
	Jogo.jogador_pego.connect(func(_q): visible = false)  # some durante o susto
	som_badalada.stream = SOM_BADALADA
	if Jogo.usa_gerador:
		_criar_hud_v2()


func _criar_hud_v2() -> void:
	# Barras finas logo acima da bateria: fôlego (correr) e ar (prender a respiração).
	_barra_stamina = _barra_fina(Color(0.55, 0.85, 0.45), -112.0)
	_barra_folego = _barra_fina(Color(0.5, 0.75, 1.0), -100.0)
	# O painel de objetivo (canto superior esquerdo) substitui o contador de disjuntores.
	disjuntores.visible = false
	# As mensagens grandes ficam à direita do painel de objetivo (nunca por cima dele).
	mensagem.offset_left = 500
	mensagem.offset_right = -40
	_painel_objetivo = PanelContainer.new()
	var estilo := StyleBoxFlat.new()
	estilo.bg_color = Color(0.02, 0.02, 0.03, 0.62)
	estilo.border_color = Color(1.0, 0.82, 0.3, 0.55)
	estilo.border_width_left = 3
	estilo.set_content_margin_all(12)
	estilo.content_margin_left = 16
	_painel_objetivo.add_theme_stylebox_override("panel", estilo)
	_painel_objetivo.position = Vector2(18, 14)
	_painel_objetivo.custom_minimum_size = Vector2(460, 0)
	_painel_objetivo.size = Vector2(460, 0)
	var coluna := VBoxContainer.new()
	coluna.add_theme_constant_override("separation", 4)
	_painel_objetivo.add_child(coluna)
	_titulo_objetivo = _rotulo_hud(24, Color(1.0, 0.85, 0.35))
	coluna.add_child(_titulo_objetivo)
	_passos_objetivo = VBoxContainer.new()
	_passos_objetivo.add_theme_constant_override("separation", 2)
	coluna.add_child(_passos_objetivo)
	_fichas = _rotulo_hud(19, Color(0.8, 0.8, 0.75))
	coluna.add_child(_fichas)
	add_child(_painel_objetivo)
	_som_objetivo = AudioStreamPlayer.new()
	_som_objetivo.bus = &"Efeitos"
	if ResourceLoader.exists("res://assets/sons/objetivo.wav"):
		_som_objetivo.stream = load("res://assets/sons/objetivo.wav")
	add_child(_som_objetivo)
	# Inventário (Tab): itens-chave, fichas e a senha que o vigia já descobriu.
	_inventario = PanelContainer.new()
	_inventario.set_anchors_and_offsets_preset(Control.PRESET_CENTER_RIGHT)
	_inventario.offset_left = -380
	_inventario.offset_right = -24
	_inventario.offset_top = -130
	_inventario.offset_bottom = 130
	_inventario.visible = false
	_texto_inventario = _rotulo_hud(20, Color(0.9, 0.9, 0.85))
	_inventario.add_child(_texto_inventario)
	add_child(_inventario)
	Jogo.objetivo_mudou.connect(func(_t: String) -> void: _atualizar_objetivo(true))
	Jogo.item_obtido.connect(_ao_obter_item)
	Jogo.disjuntor_ligado.connect(func(_n: int) -> void: _atualizar_objetivo(true))
	Jogo.codigo_revelado.connect(func(_p: int, _d: int) -> void: mostrar_mensagem("Senha: " + Jogo.codigo_conhecido(), 3.0))
	_atualizar_objetivo.call_deferred(true)


func _rotulo_hud(tamanho: int, cor: Color) -> Label:
	var r := Label.new()
	r.theme_type_variation = &"RotuloHUD"
	r.add_theme_font_size_override("font_size", tamanho)
	r.add_theme_color_override("font_color", cor)
	r.add_theme_constant_override("outline_size", 4)
	r.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.9))
	r.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	r.custom_minimum_size.x = 420
	return r


## Remonta o painel de objetivo. "destacar": acende o painel (mudou algo) e toca o som se um passo foi concluído.
func _atualizar_objetivo(destacar := false) -> void:
	if _painel_objetivo == null:
		return
	var o := Jogo.objetivo_estruturado()
	var assinatura := str(o)
	if assinatura == _ultimo_objetivo and not destacar:
		return
	var feitos_antes := _ultimo_objetivo.count("\"feito\": true")
	_ultimo_objetivo = assinatura
	_titulo_objetivo.text = o["titulo"]
	for f in _passos_objetivo.get_children():
		f.queue_free()
	for p in o["passos"]:
		var cor := Color(0.55, 0.85, 0.5) if p["feito"] else (Color(1, 1, 1) if p["atual"] else Color(0.7, 0.7, 0.68))
		var linha := _rotulo_hud(20 if p["atual"] else 18, cor)
		linha.text = ("[x] " if p["feito"] else ("> " if p["atual"] else "[ ] ")) + String(p["texto"])
		_passos_objetivo.add_child(linha)
	if destacar:
		if assinatura.count("\"feito\": true") > feitos_antes and _som_objetivo.stream:
			_som_objetivo.play()
		_tempo_destaque = 8.0


func mostrar_objetivo(_texto := "") -> void:
	_atualizar_objetivo(true)


func _barra_fina(cor: Color, topo: float) -> ProgressBar:
	var b := ProgressBar.new()
	b.show_percentage = false
	b.max_value = 1.0
	b.anchor_top = 1.0
	b.anchor_bottom = 1.0
	b.offset_left = 24
	b.offset_right = 224
	b.offset_top = topo
	b.offset_bottom = topo + 7
	var fundo := StyleBoxFlat.new()
	fundo.bg_color = Color(0, 0, 0, 0.45)
	var cheio := StyleBoxFlat.new()
	cheio.bg_color = cor
	b.add_theme_stylebox_override("background", fundo)
	b.add_theme_stylebox_override("fill", cheio)
	add_child(b)
	return b


func _ao_obter_item(id_item: String) -> void:
	var nomes := {"alicate": "ALICATE CORTA-CORRENTE", "chave_gerente": "CHAVE DO GERENTE"}
	mostrar_mensagem("Você pegou: " + String(nomes.get(id_item, id_item.to_upper())), 3.0)


func _unhandled_input(evento: InputEvent) -> void:
	if _painel_objetivo == null:
		return
	if evento.is_action_pressed("mostrar_objetivo"):
		mostrar_objetivo(Jogo.objetivo_atual())
	elif evento.is_action_pressed("inventario"):
		_inventario.visible = true
	elif evento.is_action_released("inventario"):
		_inventario.visible = false


func _texto_do_inventario() -> String:
	var linhas: Array[String] = ["INVENTÁRIO", ""]
	if Jogo.tem_item("alicate"):
		linhas.append("• Alicate corta-corrente")
	if Jogo.tem_item("chave_gerente"):
		linhas.append("• Chave do gerente")
	if linhas.size() == 2:
		linhas.append("(nenhum item ainda)")
	linhas.append("")
	linhas.append("Fichas: %d" % Jogo.fichas)
	linhas.append("Senha da sala elétrica: " + Jogo.codigo_conhecido())
	linhas.append("Disjuntores: %d/%d" % [Jogo.disjuntores_ligados, Jogo.total_disjuntores])
	return "\n".join(linhas)


func _process(_delta: float) -> void:
	relogio.text = Jogo.texto_relogio()
	disjuntores.text = "Disjuntores: %d/%d" % [Jogo.disjuntores_ligados, Jogo.total_disjuntores]
	var jogador := get_tree().get_first_node_in_group("jogador")
	if jogador == null:
		return
	var pct: float = jogador.porcentagem_bateria()
	barra.value = pct
	porcentagem.text = "%d%%" % roundi(pct)
	_estilo_barra.bg_color = cor_bateria_baixa if pct < jogador.limite_piscar else cor_bateria
	dica.text = jogador.dica_atual
	if _barra_stamina:
		_barra_stamina.value = jogador.stamina
		_barra_stamina.modulate.a = 0.35 if jogador.stamina >= 0.999 else (0.6 if jogador.exausto else 1.0)
		_barra_folego.value = jogador.folego
		_barra_folego.visible = jogador.folego < 0.999 or jogador.respiracao_presa
		_fichas.text = "Fichas: %d   ·   M: mapa e diário" % Jogo.fichas
		if _inventario.visible:
			_texto_inventario.text = _texto_do_inventario()
		# Painel de objetivo: sempre visível (opção para esconder); fica mais discreto depois de uns segundos.
		_painel_objetivo.visible = Config.mostrar_objetivo
		_tempo_destaque = maxf(_tempo_destaque - _delta, 0.0)
		var alfa := 1.0 if _tempo_destaque > 0.0 else 0.62
		_painel_objetivo.modulate.a = move_toward(_painel_objetivo.modulate.a, alfa, _delta * 2.0)
		_tempo_refazer -= _delta
		if _tempo_refazer <= 0.0:
			_tempo_refazer = 1.0
			_atualizar_objetivo()  # fichas e textos que mudam sem sinal


## Mostra um texto grande no meio da tela por alguns segundos.
func mostrar_mensagem(texto: String, duracao: float) -> void:
	mensagem.text = texto
	# Textos longos ficam um pouco menores para caber em até 2 linhas.
	mensagem.remove_theme_font_size_override("font_size")
	if texto.length() > 48:
		mensagem.add_theme_font_size_override("font_size", 30)
	if _tween_mensagem:
		_tween_mensagem.kill()
	_tween_mensagem = create_tween()
	_tween_mensagem.tween_property(mensagem, "modulate:a", 1.0, 0.25)
	_tween_mensagem.tween_interval(duracao)
	_tween_mensagem.tween_property(mensagem, "modulate:a", 0.0, 0.8)


func _ao_mudar_hora(_hora: int) -> void:
	som_badalada.play()
