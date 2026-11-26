extends Area3D
## Monitor de câmeras da sala de segurança.
## Aperte E no monitor para ver as câmeras; Q troca; E ou ESC sai.
## O tempo e os animatrônicos CONTINUAM enquanto você olha o monitor.
##
## Como funciona: cada câmera de segurança (grupo "camera_seguranca") ganha uma
## SubViewport pequena. Só a câmera escolhida é desenhada, para não pesar no PC.

@export_group("Monitor")
## Resolução da imagem das câmeras. Baixa de propósito: é leve e parece câmera velha.
@export var resolucao := Vector2i(320, 180)
## Nó onde está o moveis.glb (lá dentro fica a tela "Monitor_Tela").
@export var no_moveis: NodePath
## Até que distância (m) a telinha do monitor continua mostrando imagem.
@export var distancia_tela_ligada := 9.0
## Cor da "visão noturna" das câmeras (as câmeras enxergam melhor que o vigia no escuro).
@export var cor_visao_noturna := Color(0.55, 0.85, 0.6)
## Força da visão noturna. 0 = tão escuro quanto o jogo; 1 = bem claro.
@export_range(0.0, 2.0) var forca_visao_noturna := 0.9

const SHADER_ESTATICA := preload("res://assets/shaders/estatica.gdshader")

var usando := false
var _cameras: Array[Camera3D] = []
var _visores: Array[SubViewport] = []
var _ativa := 0
var _material_tela: StandardMaterial3D
var _jogador: Node3D

@onready var tela: CanvasLayer = $Tela
@onready var imagem: TextureRect = $Tela/Imagem
@onready var estatica: ColorRect = $Tela/Estatica
@onready var nome_camera: Label = $Tela/NomeCamera
@onready var som_estatica: AudioStreamPlayer = $SomEstatica


func _ready() -> void:
	add_to_group("interagivel")
	tela.visible = false
	Jogo.jogador_pego.connect(func(_q): sair())
	# Espera um quadro para todas as câmeras do mapa estarem prontas.
	await get_tree().process_frame
	_jogador = get_tree().get_first_node_in_group("jogador")
	var lista := get_tree().get_nodes_in_group("camera_seguranca")
	lista.sort_custom(func(a, b): return a.name.naturalnocasecmp_to(b.name) < 0)
	for cam in lista:
		_criar_visor(cam)
	_preparar_tela_3d()
	_trocar_para(0)


func _criar_visor(original: Camera3D) -> void:
	var visor := SubViewport.new()
	visor.size = resolucao
	visor.render_target_update_mode = SubViewport.UPDATE_DISABLED
	visor.audio_listener_enable_3d = false
	add_child(visor)
	var cam := Camera3D.new()
	cam.fov = original.fov
	cam.near = 0.05
	cam.far = 40.0
	cam.environment = _ambiente_visao_noturna()
	visor.add_child(cam)
	cam.global_transform = original.global_transform
	cam.current = true
	_cameras.append(original)
	_visores.append(visor)


var _ambiente_noturno: Environment


## Ambiente só das câmeras: luz ambiente esverdeada, para o monitor ser útil no escuro.
func _ambiente_visao_noturna() -> Environment:
	if _ambiente_noturno == null:
		_ambiente_noturno = Environment.new()
		_ambiente_noturno.background_mode = Environment.BG_COLOR
		_ambiente_noturno.background_color = Color.BLACK
		_ambiente_noturno.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
		_ambiente_noturno.ambient_light_color = cor_visao_noturna
		_ambiente_noturno.ambient_light_energy = forca_visao_noturna
		_ambiente_noturno.fog_enabled = true
		_ambiente_noturno.fog_light_color = Color(0.02, 0.05, 0.03)
		_ambiente_noturno.fog_density = 0.04
	return _ambiente_noturno


## A telinha do monitor (objeto Monitor_Tela, vindo do Blender) passa a mostrar a câmera ativa.
func _preparar_tela_3d() -> void:
	var moveis := get_node_or_null(no_moveis)
	var malha := moveis.find_child("Monitor_Tela", true, false) as MeshInstance3D if moveis else null
	if malha == null:
		push_warning("Monitor: objeto 'Monitor_Tela' não encontrado no moveis.glb.")
		return
	_material_tela = StandardMaterial3D.new()
	_material_tela.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED  # brilha sozinha no escuro
	_material_tela.albedo_color = Color(0.85, 1.0, 0.9)
	malha.material_override = _material_tela


func _process(_delta: float) -> void:
	if _visores.is_empty():
		return
	# Só desenha a câmera ativa, e só quando alguém pode ver (economia para PC fraco).
	var perto := _jogador != null and _jogador.global_position.distance_to(global_position) < distancia_tela_ligada
	var desenhar := usando or perto
	for i in _visores.size():
		_visores[i].render_target_update_mode = SubViewport.UPDATE_ALWAYS if (desenhar and i == _ativa) else SubViewport.UPDATE_DISABLED


func texto_dica() -> String:
	return "Aperte E para ver as câmeras"


func interagir(jogador: Node) -> void:
	if usando or _visores.is_empty():
		return
	usando = true
	jogador.travado = true
	tela.visible = true
	som_estatica.play()
	_trocar_para(_ativa)


func sair() -> void:
	if not usando:
		return
	usando = false
	tela.visible = false
	som_estatica.stop()
	if _jogador and Jogo.em_partida:
		_jogador.travado = false


func _input(evento: InputEvent) -> void:
	if not usando:
		return
	if evento.is_action_pressed("trocar_camera"):
		_trocar_para((_ativa + 1) % _visores.size())
		get_viewport().set_input_as_handled()
	elif evento.is_action_pressed("interagir") or evento.is_action_pressed("pausar"):
		# Tratamos aqui (antes da pausa) para o ESC só fechar o monitor.
		get_viewport().set_input_as_handled()
		sair()


func _trocar_para(indice: int) -> void:
	if _visores.is_empty():
		return
	_ativa = indice
	var textura := _visores[_ativa].get_texture()
	imagem.texture = textura
	if _material_tela:
		_material_tela.albedo_texture = textura
	nome_camera.text = String(_cameras[_ativa].name)
	# Rajada de estática ao trocar, como num monitor antigo.
	var mat := estatica.material as ShaderMaterial
	mat.set_shader_parameter("intensidade", 1.0)
	var t := create_tween()
	t.tween_method(func(v): mat.set_shader_parameter("intensidade", v), 1.0, 0.22, 0.3)
