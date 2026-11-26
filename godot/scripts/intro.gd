extends Control
## Intro: conta a história em poucas linhas, com efeito de máquina de escrever.
## Qualquer tecla ou clique: 1ª vez completa o texto, 2ª vez começa o jogo.

@export_group("Texto")
## As linhas da história. Pode editar à vontade no Inspector.
@export_multiline var linhas: PackedStringArray = [
	"Pizzaria do Tito. 23h58.",
	"Você é o novo vigia noturno. À meia-noite, a energia vai cair.",
	"Religue os 4 disjuntores espalhados pela pizzaria e volte para a sala de segurança antes das 6h.",
	"E não confie nos animatrônicos do palco. Eles não deveriam se mexer...",
]
## Quantas letras aparecem por segundo.
@export var letras_por_segundo := 32.0
## Pausa (s) extra no fim de cada linha, para dar tempo de ler.
@export var pausa_entre_linhas := 0.6
## Depois do texto completo, começa o jogo sozinho após estes segundos.
@export var segundos_para_avancar_sozinho := 6.0

@export_group("Som")
## Toca um clique a cada quantas letras (0 = sem som).
@export var clique_a_cada_letras := 3

@onready var texto: Label = %Texto
@onready var aviso: Label = %Aviso
@onready var som_clique: AudioStreamPlayer = $SomClique

var _letras := 0.0
var _espera := 0.0
var _completo := false
var _tempo_completo := 0.0
var _ultimo_clique := 0
var _fins_de_linha: Array[int] = []


func _ready() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	texto.text = "\n\n".join(linhas)
	texto.visible_characters = 0
	# Guarda onde cada linha termina, para pausar um pouquinho ali.
	var total := 0
	for linha in linhas:
		total += linha.length()
		_fins_de_linha.append(total)
		total += 2  # as duas quebras de linha entre as linhas
	var piscar := create_tween().set_loops()
	piscar.tween_property(aviso, "modulate:a", 0.3, 0.8)
	piscar.tween_property(aviso, "modulate:a", 1.0, 0.8)


func _process(delta: float) -> void:
	if _completo:
		_tempo_completo += delta
		if _tempo_completo >= segundos_para_avancar_sozinho:
			_comecar_jogo()
		return
	if _espera > 0.0:
		_espera -= delta
		return
	var antes := int(_letras)
	_letras += letras_por_segundo * delta
	var agora := int(_letras)
	for fim in _fins_de_linha:
		if antes < fim and agora >= fim:
			agora = fim
			_letras = fim
			_espera = pausa_entre_linhas
	texto.visible_characters = agora
	_tocar_clique(agora)
	if agora >= texto.get_total_character_count():
		_completar()


func _unhandled_input(evento: InputEvent) -> void:
	var apertou: bool = (evento is InputEventKey and evento.pressed and not evento.echo) \
		or (evento is InputEventMouseButton and evento.pressed)
	if not apertou:
		return
	get_viewport().set_input_as_handled()
	if _completo:
		_comecar_jogo()
	else:
		_completar()


func _tocar_clique(letras_visiveis: int) -> void:
	if clique_a_cada_letras <= 0 or letras_visiveis - _ultimo_clique < clique_a_cada_letras:
		return
	_ultimo_clique = letras_visiveis
	som_clique.pitch_scale = randf_range(0.85, 1.15)
	som_clique.play()


func _completar() -> void:
	_completo = true
	texto.visible_characters = -1
	aviso.text = "Pressione qualquer tecla para começar"


func _comecar_jogo() -> void:
	set_process(false)
	set_process_unhandled_input(false)
	get_tree().change_scene_to_file(Jogo.CENA_CARREGAMENTO)  # tela de carregamento -> jogo
