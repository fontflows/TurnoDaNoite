class_name UIV2
extends CanvasLayer
## Telas por cima do jogo no mapa da V2: documento (pistas e bilhetes), teclado numérico
## da sala elétrica e o menu do duto. O MUNDO NÃO PAUSA enquanto elas estão abertas:
## o vigia fica parado lendo, e os animatrônicos continuam andando.
##
## Tudo é criado por código para ficar fácil de ler e mudar.

signal fechou()

const CAMADA := 15
const SOM_BIP := "res://assets/sons/teclado_bip.wav"
const SOM_ERRO := "res://assets/sons/teclado_erro.wav"
const SOM_CERTO := "res://assets/sons/teclado_certo.wav"

var aberta := false
var _painel: Control
var _ao_fechar: Callable
var _som: AudioStreamPlayer
# Teclado
var _digitado := ""
var _visor: Label
var _ao_acertar: Callable
# Menu (duto)
var _opcoes: Array = []
var _escolha := 0
var _rotulos_opcoes: Array[Label] = []
var _ao_escolher: Callable


func _ready() -> void:
	layer = CAMADA
	_som = AudioStreamPlayer.new()
	add_child(_som)


func _jogador() -> Node:
	return get_tree().get_first_node_in_group("jogador")


func _abrir(painel: Control) -> void:
	fechar()
	aberta = true
	_painel = painel
	add_child(painel)
	var j := _jogador()
	if j:
		j.travado = true


func fechar() -> void:
	if not aberta:
		return
	aberta = false
	if is_instance_valid(_painel):
		_painel.queue_free()
	var j := _jogador()
	if j:
		j.travado = false
	if _ao_fechar.is_valid():
		var f := _ao_fechar
		_ao_fechar = Callable()
		f.call()
	fechou.emit()


func _fundo(cor_papel: Color, largura: float, altura: float) -> PanelContainer:
	var escuro := ColorRect.new()
	escuro.color = Color(0, 0, 0, 0.55)
	escuro.set_anchors_preset(Control.PRESET_FULL_RECT)
	escuro.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var papel := PanelContainer.new()
	var estilo := StyleBoxFlat.new()
	estilo.bg_color = cor_papel
	estilo.set_content_margin_all(28)
	estilo.shadow_size = 12
	estilo.shadow_color = Color(0, 0, 0, 0.6)
	papel.add_theme_stylebox_override("panel", estilo)
	papel.set_anchors_preset(Control.PRESET_CENTER)
	papel.custom_minimum_size = Vector2(largura, altura)
	papel.position = Vector2(-largura / 2.0, -altura / 2.0)
	papel.rotation = deg_to_rad(randf_range(-1.5, 1.5))
	escuro.add_child(papel)
	return papel


func _rotulo(texto: String, variacao: StringName, tamanho: int, cor: Color) -> Label:
	var r := Label.new()
	r.text = texto
	r.theme_type_variation = variacao
	r.add_theme_font_size_override("font_size", tamanho)
	r.add_theme_color_override("font_color", cor)
	r.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	return r


# ---------------------------------------------------------------------------
# Documento (pistas, bilhetes, recados)
# ---------------------------------------------------------------------------

## estilo: "documento" (papel, máquina de escrever), "manuscrito" (letra de mão) ou "cartaz".
func mostrar_documento(titulo: String, texto: String, estilo := "documento", ao_fechar := Callable()) -> void:
	var cor_papel := {"documento": Color(0.9, 0.87, 0.78), "manuscrito": Color(0.96, 0.92, 0.7),
		"cartaz": Color(0.3, 0.45, 0.75)}.get(estilo, Color(0.9, 0.87, 0.78)) as Color
	var cor_tinta := Color(1, 0.95, 0.85) if estilo == "cartaz" else Color(0.12, 0.1, 0.08)
	var papel := _fundo(cor_papel, 620, 420)
	var coluna := VBoxContainer.new()
	coluna.add_theme_constant_override("separation", 14)
	papel.add_child(coluna)
	var variacao: StringName = &"RotuloDocumento" if estilo != "manuscrito" else &"RotuloManuscrito"
	coluna.add_child(_rotulo(titulo, &"RotuloTitulo" if estilo == "cartaz" else variacao, 30, cor_tinta))
	coluna.add_child(_rotulo(texto, variacao, 24 if estilo != "manuscrito" else 30, cor_tinta))
	var dica := _rotulo("E / ESC: fechar", &"RotuloHUD", 18, Color(cor_tinta, 0.6))
	dica.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	dica.size_flags_vertical = Control.SIZE_EXPAND | Control.SIZE_SHRINK_END
	coluna.add_child(dica)
	_abrir(papel.get_parent())
	_ao_fechar = ao_fechar
	_modo = "documento"


# ---------------------------------------------------------------------------
# Teclado numérico (senha de 4 dígitos)
# ---------------------------------------------------------------------------

## Digite com os números (teclado ou numpad). Backspace apaga, Enter confere.
func abrir_teclado(senha: String, ao_acertar: Callable) -> void:
	var caixa := _fundo(Color(0.16, 0.17, 0.18), 380, 330)
	var coluna := VBoxContainer.new()
	coluna.add_theme_constant_override("separation", 12)
	caixa.add_child(coluna)
	coluna.add_child(_rotulo("SALA ELÉTRICA — ACESSO RESTRITO", &"RotuloHUD", 22, Color(0.85, 0.85, 0.8)))
	_visor = _rotulo("_ _ _ _", &"RotuloArcade", 40, Color(0.35, 1.0, 0.45))
	_visor.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_visor.autowrap_mode = TextServer.AUTOWRAP_OFF  # o visor é uma linha só (nunca quebra a palavra)
	var fundo_visor := PanelContainer.new()
	var estilo := StyleBoxFlat.new()
	estilo.bg_color = Color(0.02, 0.06, 0.03)
	estilo.set_content_margin_all(12)
	fundo_visor.add_theme_stylebox_override("panel", estilo)
	fundo_visor.add_child(_visor)
	coluna.add_child(fundo_visor)
	coluna.add_child(_rotulo("Digite os 4 números · Enter confere · Backspace apaga\nVocê sabe: " + Jogo.codigo_conhecido(),
		&"RotuloHUD", 20, Color(0.8, 0.8, 0.75)))
	coluna.add_child(_rotulo("E / ESC: sair", &"RotuloHUD", 18, Color(0.6, 0.6, 0.55)))
	_abrir(caixa.get_parent())
	_digitado = ""
	_ao_acertar = ao_acertar
	_senha = senha
	_modo = "teclado"


var _senha := ""
var _modo := ""


func _atualizar_visor(cor := Color(0.35, 1.0, 0.45)) -> void:
	var s := ""
	for i in 4:
		s += (_digitado[i] if i < _digitado.length() else "_") + (" " if i < 3 else "")
	_visor.text = s
	_visor.add_theme_color_override("font_color", cor)


func _digitar(tecla: String) -> void:
	if _digitado.length() >= 4:
		return
	_digitado += tecla
	_tocar(SOM_BIP)
	_atualizar_visor()


func _conferir() -> void:
	if _digitado == _senha:
		_tocar(SOM_CERTO)
		_atualizar_visor(Color(0.4, 0.8, 1.0))
		_visor.add_theme_font_size_override("font_size", 28)  # cabe inteiro no visor
		_visor.text = "LIBERADO"
		var f := _ao_acertar
		_modo = ""
		await get_tree().create_timer(0.8).timeout
		fechar()
		f.call()
	else:
		_tocar(SOM_ERRO)
		_atualizar_visor(Color(1.0, 0.3, 0.25))
		var j := _jogador() as Node3D
		if j:
			Jogo.emitir_ruido(j.global_position, 6.0, 0.4)  # o bipe de erro é alto
		await get_tree().create_timer(0.6).timeout
		if _modo == "teclado":
			_digitado = ""
			_atualizar_visor()


# ---------------------------------------------------------------------------
# Menu de escolha (usado pelo duto: para onde rastejar)
# ---------------------------------------------------------------------------

## opcoes: lista de textos. W/S escolhem, Espaço ou E confirmam, ESC cancela.
func abrir_menu(titulo: String, opcoes: Array, ao_escolher: Callable) -> void:
	var caixa := _fundo(Color(0.1, 0.1, 0.1), 460, 120 + 46 * opcoes.size())
	var coluna := VBoxContainer.new()
	coluna.add_theme_constant_override("separation", 10)
	caixa.add_child(coluna)
	coluna.add_child(_rotulo(titulo, &"RotuloHUD", 26, Color(0.9, 0.88, 0.8)))
	_rotulos_opcoes.clear()
	for o in opcoes:
		var r := _rotulo(String(o), &"RotuloHUD", 24, Color(0.75, 0.75, 0.7))
		coluna.add_child(r)
		_rotulos_opcoes.append(r)
	coluna.add_child(_rotulo("W/S escolhe · ESPAÇO confirma · ESC volta", &"RotuloHUD", 18, Color(0.55, 0.55, 0.5)))
	_abrir(caixa.get_parent())
	_opcoes = opcoes
	_escolha = 0
	_ao_escolher = ao_escolher
	_modo = "menu"
	_marcar_opcao()


func _marcar_opcao() -> void:
	for i in _rotulos_opcoes.size():
		var r := _rotulos_opcoes[i]
		r.text = ("> " if i == _escolha else "  ") + String(_opcoes[i])
		r.add_theme_color_override("font_color", Color(1, 0.85, 0.3) if i == _escolha else Color(0.75, 0.75, 0.7))


# ---------------------------------------------------------------------------

func _input(evento: InputEvent) -> void:
	if not aberta:
		return
	if evento.is_action_pressed("pausar") or (evento.is_action_pressed("interagir") and _modo != "menu"):
		get_viewport().set_input_as_handled()
		fechar()
		return
	match _modo:
		"teclado":
			if evento is InputEventKey and evento.pressed and not evento.echo:
				var k: Key = evento.physical_keycode
				if k >= KEY_0 and k <= KEY_9:
					_digitar(str(k - KEY_0))
				elif k >= KEY_KP_0 and k <= KEY_KP_9:
					_digitar(str(k - KEY_KP_0))
				elif k == KEY_BACKSPACE and _digitado.length() > 0:
					_digitado = _digitado.left(-1)
					_atualizar_visor()
				elif k == KEY_ENTER or k == KEY_KP_ENTER or (k == KEY_SPACE and _digitado.length() == 4):
					_conferir()
				get_viewport().set_input_as_handled()
		"menu":
			if evento.is_action_pressed("mover_frente"):
				_escolha = wrapi(_escolha - 1, 0, _opcoes.size())
				_marcar_opcao()
			elif evento.is_action_pressed("mover_tras"):
				_escolha = wrapi(_escolha + 1, 0, _opcoes.size())
				_marcar_opcao()
			elif evento.is_action_pressed("minigame_acao") or evento.is_action_pressed("interagir"):
				var f := _ao_escolher
				var i := _escolha
				_ao_fechar = Callable()
				fechar()
				f.call(i)
			get_viewport().set_input_as_handled()


func _tocar(caminho: String) -> void:
	if ResourceLoader.exists(caminho):
		_som.stream = load(caminho)
		_som.play()


## Para os testes automáticos: digita uma senha inteira e confere.
func digitar_senha_teste(senha: String) -> void:
	_digitado = senha.left(4)
	_conferir()
