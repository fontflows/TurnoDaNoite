extends Node
## Menu principal: capa do jogo ao fundo (fofa, que de vez em quando "vira" sombria com um
## glitch de fita VHS e a música fica macabra), estática por cima e os botões.
## Sem a arte da capa, mostra o palco escuro em 3D da V1.
## Jogar -> intro -> jogo. Controles e Opções abrem painéis por cima do menu.

@export_group("Sons")
## Volume da musiquinha de caixinha de música (em dB; mais negativo = mais baixo).
@export var volume_musica_db := -14.0
## Volume do ambiente grave de fundo (em dB).
@export var volume_ambiente_db := -16.0

@export_group("Câmera")
## Quanto a câmera balança devagar (graus), para a cena não parecer uma foto parada.
@export var balanco_camera_graus := 1.2

const CENA_INTRO := "res://ui/intro.tscn"

@onready var camera: Camera3D = $Cenario/Camera
@onready var botoes: VBoxContainer = %Botoes
@onready var botao_jogar: Button = %BotaoJogar
@onready var botao_controles: Button = %BotaoControles
@onready var botao_opcoes: Button = %BotaoOpcoes
@onready var botao_sair: Button = %BotaoSair
@onready var painel_controles: PanelContainer = $Interface/Controles
@onready var painel_opcoes: PanelContainer = $Interface/Opcoes
@onready var musica: AudioStreamPlayer = $Musica
@onready var ambiente: AudioStreamPlayer = $SomAmbiente

var _tempo := 0.0
var _rotacao_inicial := Vector3.ZERO
var _capa: CapaMenu
var _musica_sombria: AudioStreamPlayer
var _tween_musica: Tween


func _ready() -> void:
	get_tree().paused = false
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	_rotacao_inicial = camera.rotation

	botao_jogar.pressed.connect(_abrir_dificuldade)
	_criar_painel_dificuldade()
	_criar_fliperama()
	_criar_creditos()
	botao_controles.pressed.connect(_abrir_painel.bind(painel_controles))
	botao_opcoes.pressed.connect(_abrir_painel.bind(painel_opcoes))
	botao_sair.pressed.connect(get_tree().quit)
	painel_controles.get_node("%BotaoVoltar").pressed.connect(_fechar_paineis)
	painel_opcoes.fechado.connect(_fechar_paineis)

	_tocar_em_loop(musica, volume_musica_db)
	_tocar_em_loop(ambiente, volume_ambiente_db)
	if CapaMenu.disponivel():
		_montar_capa()
	botao_jogar.grab_focus()


## Troca o palco 3D pela capa e prepara a versão macabra da música.
func _montar_capa() -> void:
	_capa = CapaMenu.new()
	_capa.name = "Capa"
	var interface := $Interface
	interface.add_child(_capa)
	interface.move_child(_capa, 0)  # atrás da estática, do título e dos botões
	$Cenario.visible = false
	$Cenario.process_mode = Node.PROCESS_MODE_DISABLED
	_musica_sombria = AudioStreamPlayer.new()
	_musica_sombria.name = "MusicaSombria"
	_musica_sombria.add_to_group("som_musica")
	if ResourceLoader.exists("res://assets/sons/musica_menu_sombria.wav"):
		_musica_sombria.stream = load("res://assets/sons/musica_menu_sombria.wav")
	add_child(_musica_sombria)
	_tocar_em_loop(_musica_sombria, -80.0)
	_capa.virou.connect(_trocar_musica)


## A música acompanha a capa: caixinha alegre <-> caixinha em tom menor, lenta e desafinada.
func _trocar_musica(sombria: bool) -> void:
	if _tween_musica:
		_tween_musica.kill()
	var ligada := _musica_sombria if sombria else musica
	var desligada := musica if sombria else _musica_sombria
	ligada.volume_db = volume_musica_db + (2.0 if sombria else 0.0)
	_tween_musica = create_tween()
	_tween_musica.tween_property(desligada, "volume_db", -80.0, 0.35)


func _process(delta: float) -> void:
	_tempo += delta
	var b := deg_to_rad(balanco_camera_graus)
	camera.rotation = _rotacao_inicial + Vector3(sin(_tempo * 0.37) * b * 0.4, sin(_tempo * 0.23) * b, 0.0)


func _unhandled_input(evento: InputEvent) -> void:
	# ESC fecha o painel aberto (Controles ou Opções).
	if evento.is_action_pressed("ui_cancel") and not botoes.visible:
		if painel_opcoes.visible:
			painel_opcoes.voltar()
		else:
			_fechar_paineis()
		get_viewport().set_input_as_handled()


# ---------------------------------------------------------------------------
# Modo FLIPERAMA: jogar os minigames avulsos, sem o resto do jogo (ótimo para apresentar)
# ---------------------------------------------------------------------------
const MINIGAMES_AVULSOS := [
	["Máquina de garra", "res://cenas/minigames/garra.tscn", {}],
	["TITO KART", "res://cenas/minigames/kart.tscn", {"codigo": "4712"}],
	["SPACE PIZZA", "res://cenas/minigames/space_pizza.tscn", {"codigo": "4712"}],
	["Conserto do disjuntor: fios", "res://cenas/minigames/conserto.tscn", {"modo": "fios"}],
	["Conserto do disjuntor: fusível", "res://cenas/minigames/conserto.tscn", {"modo": "fusivel"}],
]
var _painel_fliperama: PanelContainer
var _camada_minigame: CanvasLayer
var _resultado_fliperama: Label
var _primeiro_fliperama: Button


func _criar_fliperama() -> void:
	var botao := Button.new()
	botao.name = "BotaoFliperama"
	botao.text = "Fliperama"
	botoes.add_child(botao)
	botoes.move_child(botao, 1)  # logo depois de "Jogar"
	botao.pressed.connect(_abrir_fliperama)
	_painel_fliperama = PanelContainer.new()
	_painel_fliperama.anchor_left = 0.5
	_painel_fliperama.anchor_right = 0.5
	_painel_fliperama.anchor_top = 0.5
	_painel_fliperama.anchor_bottom = 0.5
	_painel_fliperama.offset_left = -300
	_painel_fliperama.offset_right = 300
	_painel_fliperama.offset_top = -200
	_painel_fliperama.offset_bottom = 230
	_painel_fliperama.hide()
	var coluna := VBoxContainer.new()
	coluna.add_theme_constant_override("separation", 10)
	_painel_fliperama.add_child(coluna)
	var titulo := Label.new()
	titulo.text = "FLIPERAMA"
	titulo.theme_type_variation = &"RotuloArcade"
	titulo.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	coluna.add_child(titulo)
	var aviso := Label.new()
	aviso.text = "Os minigames do jogo, avulsos (dificuldade: a escolhida em Jogar)."
	aviso.theme_type_variation = &"RotuloHUD"
	aviso.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	aviso.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	coluna.add_child(aviso)
	for m in MINIGAMES_AVULSOS:
		var b := Button.new()
		b.text = m[0]
		b.pressed.connect(_jogar_avulso.bind(m[1], m[2]))
		coluna.add_child(b)
		if _primeiro_fliperama == null:
			_primeiro_fliperama = b
	_resultado_fliperama = Label.new()
	_resultado_fliperama.theme_type_variation = &"RotuloHUD"
	_resultado_fliperama.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	coluna.add_child(_resultado_fliperama)
	var voltar := Button.new()
	voltar.text = "Voltar"
	voltar.pressed.connect(_fechar_paineis)
	coluna.add_child(voltar)
	$Interface.add_child(_painel_fliperama)
	_camada_minigame = CanvasLayer.new()
	_camada_minigame.layer = 30
	add_child(_camada_minigame)


## Rodapé com os créditos obrigatórios (efeitos sonoros da ElevenLabs, plano gratuito).
func _criar_creditos() -> void:
	var rodape := Label.new()
	rodape.text = "Efeitos sonoros: elevenlabs.io  ·  Fontes: OFL  ·  Texturas: CC0 (ver docs/CREDITOS.md)"
	rodape.theme_type_variation = &"RotuloHUD"
	rodape.add_theme_font_size_override("font_size", 16)
	rodape.add_theme_color_override("font_color", Color(0.75, 0.75, 0.7, 0.7))
	rodape.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT)
	rodape.offset_left = -760
	rodape.offset_top = -30
	rodape.offset_right = -16
	rodape.offset_bottom = -8
	rodape.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	$Interface.add_child(rodape)


func _abrir_fliperama() -> void:
	_resultado_fliperama.text = ""
	_abrir_painel(_painel_fliperama)
	_primeiro_fliperama.grab_focus()


func _jogar_avulso(cena: String, dados: Dictionary) -> void:
	if not ResourceLoader.exists(cena):
		_resultado_fliperama.text = "Esse minigame não está no projeto."
		return
	Jogo.carregar_dificuldade()
	_painel_fliperama.hide()
	get_viewport().gui_release_focus()
	var m: Minigame = load(cena).instantiate()
	_camada_minigame.add_child(m)
	musica.volume_db = -80.0
	if _musica_sombria:
		_musica_sombria.volume_db = -80.0
	m.terminado.connect(func(venceu: bool, resultado: Dictionary) -> void:
		musica.volume_db = volume_musica_db
		_resultado_fliperama.text = "Você venceu!" if venceu else ("Saiu da máquina." if resultado.get("cancelado", false) else "Não foi dessa vez!")
		_painel_fliperama.show()
		_primeiro_fliperama.grab_focus())
	m.iniciar(Jogo.dificuldade, dados)


# ---------------------------------------------------------------------------
# Escolha de dificuldade (aparece ao clicar em Jogar)
# ---------------------------------------------------------------------------
const DESCRICOES := [
	"Noite mais longa, bateria e stamina de sobra, animatrônicos lentos. Bom para a apresentação.",
	"O jogo como foi pensado: escuro, pilhas escassas e animatrônicos atentos. Espere perder algumas vezes.",
	"Para quem já venceu: quase sem pilhas, inimigos rápidos que checam esconderijos e itens em lugares sorteados.",
]
var _painel_dificuldade: PanelContainer
var _descricao: Label
var _botoes_nivel: Array[Button] = []


func _criar_painel_dificuldade() -> void:
	_painel_dificuldade = PanelContainer.new()
	# Centralizado na tela (âncoras no meio e metade do tamanho para cada lado).
	_painel_dificuldade.anchor_left = 0.5
	_painel_dificuldade.anchor_right = 0.5
	_painel_dificuldade.anchor_top = 0.5
	_painel_dificuldade.anchor_bottom = 0.5
	_painel_dificuldade.offset_left = -320
	_painel_dificuldade.offset_right = 320
	_painel_dificuldade.offset_top = -120  # um pouco abaixo do meio, para não cobrir o título
	_painel_dificuldade.offset_bottom = 230
	_painel_dificuldade.hide()
	var coluna := VBoxContainer.new()
	coluna.add_theme_constant_override("separation", 16)
	var titulo := Label.new()
	titulo.text = "ESCOLHA A DIFICULDADE"
	titulo.theme_type_variation = &"RotuloLetreiro"
	titulo.add_theme_font_size_override("font_size", 28)
	titulo.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	coluna.add_child(titulo)
	var linha := HBoxContainer.new()
	linha.alignment = BoxContainer.ALIGNMENT_CENTER
	linha.add_theme_constant_override("separation", 14)
	for i in 3:
		var b := Button.new()
		b.text = ["Fácil", "Normal", "Pesadelo"][i]
		b.custom_minimum_size.x = 170
		b.pressed.connect(_escolher_nivel.bind(i))
		b.focus_entered.connect(_mostrar_descricao.bind(i))
		b.mouse_entered.connect(_mostrar_descricao.bind(i))
		linha.add_child(b)
		_botoes_nivel.append(b)
	coluna.add_child(linha)
	_descricao = Label.new()
	_descricao.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_descricao.custom_minimum_size = Vector2(560, 90)
	_descricao.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	coluna.add_child(_descricao)
	var voltar := Button.new()
	voltar.text = "Voltar"
	voltar.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	voltar.pressed.connect(_fechar_paineis)
	coluna.add_child(voltar)
	_painel_dificuldade.add_child(coluna)
	$Interface.add_child(_painel_dificuldade)


func _abrir_dificuldade() -> void:
	_abrir_painel(_painel_dificuldade)
	_botoes_nivel[Config.dificuldade].grab_focus()
	_mostrar_descricao(Config.dificuldade)


func _mostrar_descricao(nivel: int) -> void:
	_descricao.text = DESCRICOES[nivel]


func _escolher_nivel(nivel: int) -> void:
	Config.dificuldade = nivel
	Config.salvar()
	_jogar()


func _jogar() -> void:
	if ResourceLoader.exists(CENA_INTRO):
		get_tree().change_scene_to_file(CENA_INTRO)
	else:
		Jogo.reiniciar_partida()


func _abrir_painel(painel: Control) -> void:
	botoes.hide()
	painel.show()
	if painel == painel_controles:
		painel.get_node("%BotaoVoltar").grab_focus()


func _fechar_paineis() -> void:
	if _painel_dificuldade:
		_painel_dificuldade.hide()
	if _painel_fliperama:
		_painel_fliperama.hide()
	painel_controles.hide()
	painel_opcoes.hide()
	botoes.show()
	botao_jogar.grab_focus()


## Toca o som e, quando acabar, toca de novo (garante o loop mesmo se o .wav não tiver ponto de loop).
func _tocar_em_loop(player: AudioStreamPlayer, volume_db: float) -> void:
	player.volume_db = volume_db
	if not player.finished.is_connected(player.play):
		player.finished.connect(player.play)
	player.play()
