class_name Animatronico
extends CharacterBody3D
## Base comum do Tito e da Pipoca: andar pela navegação, virar o corpo,
## animar o modelo por código e pegar o vigia (susto).
##
## O MODELO é só o nó filho "Modelo" (uma instância do .glb do personagem).
## Para trocar o personagem, basta trocar esse .glb: o resto continua funcionando.
## Animações do .glb (feitas no Blender, blender/scripts/animatronicos_animacoes.py):
##   parado, andar, perseguir, procurar, jumpscare (e atordoado na Pipoca).
## Andando, a animação roda na proporção velocidade_real / velocidade_de_referência
## (assets/personagens/animacoes_velocidades.json), assim os pés não escorregam no chão.
## Se o .glb não tiver animações, o código faz um balanço simples no lugar.
## A cabeça e os olhos seguem o vigia por código (OlharAlvo, por cima da animação).

@export_group("Identidade")
## Nome que aparece na tela de Game Over ("Tito te pegou!").
@export var nome_exibicao := "Animatrônico"

@export_group("Início")
## Hora em que o animatrônico começa a se mexer (1 = 1 AM).
@export var hora_de_acordar := 1
## Marcador do palco onde ele começa (e para onde volta).
@export var ponto_palco: NodePath

@export_group("Contato")
## Distância (m) em que ele "encosta" no vigia e dá o susto.
@export var distancia_pegar := 1.1

@export_group("Animação por código")
## Quanto o corpo balança de um lado para o outro ao andar (graus).
@export var balanco_andando := 6.0
## Velocidade com que o corpo vira para a direção do movimento.
@export var velocidade_giro := 6.0
## De quanto em quanto tempo (s) o caminho até o alvo é recalculado.
@export var intervalo_recalculo := 0.3

const GRAVIDADE := 9.8

@onready var agente: NavigationAgent3D = $Agente
@onready var modelo: Node3D = $Modelo

const ARQUIVO_VELOCIDADES := "res://assets/personagens/animacoes_velocidades.json"
const ANIMACOES_EM_LOOP := ["parado", "andar", "perseguir", "procurar", "atordoado"]

var jogador: Node3D
## Animação usada quando ele está andando e quando está parado (os filhos trocam conforme o estado).
var anim_movendo := "andar"
var anim_parado := "parado"
## Cabeça e olhos seguindo o vigia (null se o modelo não tiver esqueleto).
var olhar: OlharAlvo
var _vel_ref := {}
var _cabeca: Node3D
var _animacoes: AnimationPlayer
var _tempo_animacao := 0.0
var _tempo_recalculo := 0.0
var _ultimo_alvo := Vector3.INF
## Segundos parado esperando uma porta abrir (V2).
var _esperando_porta := 0.0


func _ready() -> void:
	add_to_group("animatronico")
	jogador = get_tree().get_first_node_in_group("jogador")
	_cabeca = modelo.find_child("*_Cabeca", true, false) as Node3D
	_animacoes = _achar_animacoes(modelo)
	_configurar_animacoes()
	var palco := get_node_or_null(ponto_palco) as Node3D
	if palco:
		global_position = palco.global_position
	rotation.y = 0.0  # de frente para o salão (a frente do modelo é +Z)
	# V2: portas fechadas (mas destrancadas) têm uma "ligação" de navegação pelo vão.
	# Quando o animatrônico chega nela, ele abre a porta e espera um pouco.
	agente.link_reached.connect(_ao_chegar_na_ligacao)


## Animações em loop, velocidades de referência e o modificador do olhar.
func _configurar_animacoes() -> void:
	if _animacoes:
		for nome in ANIMACOES_EM_LOOP:
			if _animacoes.has_animation(nome):
				_animacoes.get_animation(nome).loop_mode = Animation.LOOP_LINEAR
		if _animacoes.has_animation("jumpscare"):
			_animacoes.get_animation("jumpscare").loop_mode = Animation.LOOP_NONE
		if FileAccess.file_exists(ARQUIVO_VELOCIDADES):
			var dados: Variant = JSON.parse_string(FileAccess.get_file_as_string(ARQUIVO_VELOCIDADES))
			if dados is Dictionary:
				_vel_ref = (dados as Dictionary).get(nome_exibicao.to_lower(), {})
		tocar(anim_parado)
	var esqueletos := modelo.find_children("*", "Skeleton3D", true, false)
	if not esqueletos.is_empty():
		olhar = OlharAlvo.new()
		olhar.name = "OlharAlvo"
		(esqueletos[0] as Skeleton3D).add_child(olhar)


## Toca uma animação do .glb (se existir). velocidade: m/s reais (para andar/perseguir).
func tocar(nome: String, velocidade := 0.0) -> bool:
	if _animacoes == null or not _animacoes.has_animation(nome):
		return false
	if _animacoes.current_animation != nome:
		_animacoes.play(nome, 0.25)
	var ref: float = float(_vel_ref.get(nome, 0.0))
	_animacoes.speed_scale = clampf(velocidade / ref, 0.5, 2.6) if ref > 0.0 and velocidade > 0.0 else 1.0
	return true


## Cabeça e olhos: peso 0 = só a animação; 1 = olhando o vigia. congelar = segura onde está.
func olhar_vigia(peso: float, congelar := false) -> void:
	if olhar == null:
		return
	olhar.congelado = congelar
	if congelar:
		return
	olhar.peso = peso
	if jogador:
		var altura := 1.0 if jogador.get("agachado") else 1.6
		olhar.alvo = jogador.global_position + Vector3(0, altura, 0)


func _achar_animacoes(no: Node) -> AnimationPlayer:
	for filho in no.find_children("*", "AnimationPlayer", true, false):
		return filho
	return null


## Multiplicadores da dificuldade (docs/PLANO_V2.md §6).
func mult_velocidade() -> float:
	return Jogo.dificuldade.multiplicador_velocidade if Jogo.dificuldade else 1.0


func mult_sentidos() -> float:
	return Jogo.dificuldade.multiplicador_sentidos if Jogo.dificuldade else 1.0


## O vigia está "à vista" para a IA? (escondido ou dentro do duto, não.)
## No modo observação (debug), eles ignoram o vigia: patrulham normalmente.
func jogador_exposto() -> bool:
	return jogador != null and not jogador.get("escondido") and not jogador.get("no_duto") and not Jogo.modo_observacao


func _ao_chegar_na_ligacao(detalhes: Dictionary) -> void:
	var ligacao: Object = detalhes.get("owner")
	if ligacao == null or not (ligacao is Node) or not (ligacao as Node).has_meta("porta"):
		return
	var porta: Node = (ligacao as Node).get_meta("porta")
	if is_instance_valid(porta) and not porta.aberta and not porta.trancada:
		porta.alternar(self)
		_esperando_porta = 0.7


## true quando ele pode se mexer (partida rolando, IA ligada e já passou da hora de acordar).
func ativo() -> bool:
	if jogador == null:
		jogador = get_tree().get_first_node_in_group("jogador")
	return Jogo.em_partida and Jogo.ia_ativa and not Jogo.congelar_animatronicos and Jogo.hora >= hora_de_acordar \
		and jogador != null


func posicao_peito() -> Vector3:
	return global_position + Vector3(0, 1.2, 0)


func posicao_cabeca() -> Vector3:
	return global_position + Vector3(0, 1.75, 0)


## Anda um passo em direção ao alvo usando a navegação. Devolve true se já chegou.
func mover_para(alvo: Vector3, velocidade: float, delta: float) -> bool:
	if _esperando_porta > 0.0:
		_esperando_porta -= delta
		parar(delta)
		return false
	_tempo_recalculo -= delta
	if _tempo_recalculo <= 0.0 or alvo.distance_to(_ultimo_alvo) > 2.0:
		agente.target_position = alvo
		_ultimo_alvo = alvo
		_tempo_recalculo = intervalo_recalculo
	if agente.is_navigation_finished():
		parar(delta)
		return true
	var proximo := agente.get_next_path_position()
	var direcao := proximo - global_position
	direcao.y = 0.0
	if direcao.length() > 0.01:
		direcao = direcao.normalized()
		velocity.x = direcao.x * velocidade
		velocity.z = direcao.z * velocidade
		virar_para(direcao, delta)
	_aplicar_gravidade(delta)
	move_and_slide()
	animar(delta, true, velocidade)
	return false


## Fica parado (mas continua caindo se estiver no ar).
func parar(delta: float, animar_parado := true) -> void:
	velocity.x = 0.0
	velocity.z = 0.0
	_aplicar_gravidade(delta)
	move_and_slide()
	if animar_parado:
		animar(delta, false, 0.0)
	elif _animacoes:
		_animacoes.speed_scale = 0.0  # congela na pose em que está (o Tito quando é visto)


func _aplicar_gravidade(delta: float) -> void:
	if is_on_floor():
		velocity.y = 0.0
	else:
		velocity.y -= GRAVIDADE * delta


## Vira o corpo para a direção. A frente do modelo é +Z, por isso atan2(x, z).
func virar_para(direcao: Vector3, delta: float) -> void:
	var angulo := atan2(direcao.x, direcao.z)
	rotation.y = lerp_angle(rotation.y, angulo, clampf(delta * velocidade_giro, 0.0, 1.0))


## Animação simples por código (ou as animações do .glb, se existirem).
func animar(delta: float, andando: bool, velocidade: float) -> void:
	if tocar(anim_movendo if andando else anim_parado, velocidade if andando else 0.0):
		return
	if andando:
		_tempo_animacao += delta * (2.0 + velocidade * 1.6)
		modelo.rotation.z = deg_to_rad(balanco_andando) * sin(_tempo_animacao)
		modelo.position.y = absf(sin(_tempo_animacao)) * 0.05
		if _cabeca:
			_cabeca.rotation.y = lerpf(_cabeca.rotation.y, 0.0, delta * 3.0)
	else:
		_tempo_animacao += delta
		modelo.rotation.z = lerpf(modelo.rotation.z, 0.0, delta * 5.0)
		modelo.position.y = lerpf(modelo.position.y, 0.0, delta * 5.0)
		if _cabeca:
			# Parado, a cabeça vira devagar de um lado para o outro (dá aflição).
			_cabeca.rotation.y = sin(_tempo_animacao * 0.6) * 0.45


func distancia_ate_jogador() -> float:
	return global_position.distance_to(jogador.global_position) if jogador else INF


## Confere se encostou no vigia. Chamado pelos filhos a cada quadro.
func checar_contato() -> void:
	if not jogador_exposto():
		return  # escondido ou no duto: só é pego se o esconderijo for checado (Pipoca)
	if distancia_ate_jogador() <= distancia_pegar:
		pegar()


func pegar() -> void:
	if not Jogo.em_partida or Jogo.invencivel:
		return
	Jogo.pegar_jogador(nome_exibicao)
	if Jogo.quem_pegou == nome_exibicao and not Jogo.em_partida:
		set_physics_process(false)
		if olhar:
			olhar.active = false
		modelo.rotation = Vector3.ZERO
		modelo.position = Vector3.ZERO
		if _cabeca:
			_cabeca.rotation = Vector3.ZERO
		if _animacoes and _animacoes.has_animation("jumpscare"):
			_animacoes.speed_scale = 1.0
			_animacoes.play("jumpscare", 0.05)
		jogador.mostrar_jumpscare(modelo)
		_ao_dar_susto()


## Os filhos podem sobrescrever (ex.: parar sons).
func _ao_dar_susto() -> void:
	pass


## true se há uma parede (camada Mundo) entre os dois pontos.
func parede_entre(de: Vector3, ate: Vector3) -> bool:
	var consulta := PhysicsRayQueryParameters3D.create(de, ate, 1)
	return not get_world_3d().direct_space_state.intersect_ray(consulta).is_empty()
