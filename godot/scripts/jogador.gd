extends CharacterBody3D
## O vigia noturno: anda (WASD), corre (Shift), olha com o mouse, usa a lanterna (F)
## e interage com as coisas (E).
## V2: fôlego para correr (stamina), agachar (Ctrl), prender a respiração (Alt),
## passos que mudam com o piso, batimento do coração com animatrônico perto e
## sacudir a lanterna fraca (R).

@export_group("Movimento")
## Velocidade andando (metros por segundo).
@export var velocidade_andando := 3.0
## Velocidade correndo com Shift. Correr faz mais barulho!
@export var velocidade_correndo := 5.5
## Quão rápido o vigia acelera e freia. Maior = mais "seco".
@export var aceleracao := 12.0
## Gravidade (m/s²). 9,8 é a da Terra; maior = cai mais rápido.
@export var gravidade := 9.8

@export_group("Câmera")
## Balanço da câmera ao andar (head bob), em metros.
@export var balanco_andando := 0.035
## Balanço da câmera ao correr, em metros.
@export var balanco_correndo := 0.07
## Quantos "passos" por segundo o balanço faz andando.
@export var frequencia_passos := 1.9
## Sensibilidade base do mouse (graus por pixel). A opção do menu multiplica este valor.
@export var graus_por_pixel := 0.12

@export_group("Lanterna")
## Carga máxima da bateria.
@export var bateria_maxima := 100.0
## Quanto a bateria gasta por segundo com a lanterna ligada (padrão 1,2 = ~83 s de luz).
@export var descarga_por_segundo := 1.2
## Abaixo desta porcentagem a lanterna começa a piscar.
@export var limite_piscar := 20.0
## Força da luz da lanterna.
@export var energia_lanterna := 3.0
## Cor da luz da lanterna (R, G, B de 0 a 1). Ex.: Color(1, 0, 0) = vermelha.
@export var cor_lanterna := Color(1, 0.93, 0.78)
## Abaixo desta porcentagem a lanterna vai perdendo alcance e força aos poucos.
@export var limite_fraca := 30.0
## Quanto a lanterna "atrasa" ao seguir a câmera (maior = segue mais rápido). Dá sensação de mão.
@export var rapidez_lanterna := 14.0
## Distância (m) em que um animatrônico faz a lanterna tremer na mão do vigia.
@export var distancia_tremer := 6.0

@export_group("Corpo (V2)")
## Velocidade agachado (m/s). Agachado quase não faz barulho e passa embaixo de mesas.
@export var velocidade_agachado := 1.6
## Altura da câmera agachado (em pé é a posição do nó Cabeca).
@export var altura_cabeca_agachado := 0.95
## Raio (m) em que se escuta o vigia andando agachado.
@export var raio_ruido_agachado := 1.2
## Quantos segundos o vigia consegue prender a respiração.
@export var duracao_folego_s := 8.0
## Distância (m) em que o coração começa a bater forte por causa de um animatrônico.
@export var distancia_batimento := 9.0
## Segundos em que a lanterna fica firme depois de sacudir (R).
@export var duracao_sacudida := 3.0

const COOKIE_LANTERNA := "res://assets/texturas/lanterna/lanterna_cookie.png"

@export_group("Ruído")
## Raio (m) em que a Pipoca escuta o vigia andando.
@export var raio_ruido_andando := 3.0
## Raio (m) em que a Pipoca escuta o vigia correndo.
@export var raio_ruido_correndo := 10.0
## De quanto em quanto tempo (s) o barulho dos passos é "anunciado".
@export var intervalo_ruido := 0.4

const SONS_PASSO := [
	preload("res://assets/sons/passo_1.wav"),
	preload("res://assets/sons/passo_2.wav"),
	preload("res://assets/sons/passo_3.wav"),
]

var bateria := 100.0
## Fôlego para correr: 1 = cheio, 0 = acabou (aí o vigia fica ofegante até recuperar 35%).
var stamina := 1.0
var exausto := false
var agachado := false
var respiracao_presa := false
## Ar para prender a respiração (1 = cheio).
var folego := 1.0
## Escondido num armário, cabine, embaixo da mesa... (o esconderijo controla isto).
var escondido := false
## Rastejando dentro do duto (a tela do duto controla isto).
var no_duto := false
## Escondido: para onde ele olha (centro) e quanto pode virar a cabeça (radianos).
var _olhar_base := 0.0
var _limite_giro := PI
var _limite_inclinacao := deg_to_rad(85)
## Piso embaixo do vigia ("carpete", "azulejo"...): muda o som e o barulho dos passos.
var piso_atual := "azulejo"
var lanterna_ligada := true
var correndo := false
## Quando true o vigia não anda nem olha (monitor de câmeras, susto, captura de tela).
var travado := false
## Texto da dica de interação que o HUD mostra (vazio = nada para interagir).
var dica_atual := ""

var _tempo_balanco := 0.0
var _altura_cabeca := 0.0
var _tempo_ruido := 0.0
var _ultimo_passo := 0
var _tempo_pisca := 0.0
var _alvo_interacao: Node = null
var _alcance_lanterna := 18.0
var _duracao_stamina := 5.5
var _altura_capsula := 1.75
var _tempo_ofegante := 0.0
var _sem_ar := false
var _tempo_sacudida := 0.0
var _som_batimento: AudioStreamPlayer
var _som_respiracao: AudioStreamPlayer
var _capsula: CapsuleShape3D
## Sons externos (docs/PROMPTS_AUDIO.md), quando existirem: passos por piso e respirações.
var _passos_externos := {}
var _resp_ofegante: Array[AudioStream] = []
var _resp_recuperando: Array[AudioStream] = []
var _resp_segurando: Array[AudioStream] = []
var _resp_soltando: Array[AudioStream] = []
var _estava_segurando := false

@onready var cabeca: Node3D = $Cabeca
@onready var camera: Camera3D = $Cabeca/Camera3D
@onready var lanterna: SpotLight3D = $Cabeca/Camera3D/Lanterna
@onready var raio_interacao: RayCast3D = $Cabeca/Camera3D/RaioInteracao
@onready var ponto_jumpscare: Node3D = $Cabeca/Camera3D/PontoJumpscare
@onready var som_passos: AudioStreamPlayer = $SomPassos
@onready var som_efeitos: AudioStreamPlayer = $SomEfeitos


func _ready() -> void:
	add_to_group("jogador")
	# A duração da bateria vem da dificuldade (Normal: ~90 s de luz contínua).
	if Jogo.dificuldade:
		descarga_por_segundo = bateria_maxima / Jogo.dificuldade.duracao_bateria_s
		limite_piscar = Jogo.dificuldade.bateria_falhando
		limite_fraca = Jogo.dificuldade.bateria_fraca
		_duracao_stamina = Jogo.dificuldade.duracao_stamina_s
	# A cápsula vira um recurso só deste vigia (para encolher ao agachar sem mexer no arquivo).
	_capsula = ($Colisao.shape as CapsuleShape3D).duplicate()
	$Colisao.shape = _capsula
	_altura_capsula = _capsula.height
	_som_batimento = _novo_som("res://assets/sons/batimento.wav", -40.0)
	_som_respiracao = _novo_som("res://assets/sons/ofegante.wav", -12.0)
	_carregar_sons_externos()
	bateria = bateria_maxima
	_alcance_lanterna = lanterna.spot_range
	# Textura de projeção: o feixe ganha anel e imperfeições de lanterna velha.
	if ResourceLoader.exists(COOKIE_LANTERNA):
		lanterna.light_projector = load(COOKIE_LANTERNA)
	# A lanterna passa a ser "solta" da câmera para poder seguir com atraso (ver _seguir_lanterna).
	lanterna.top_level = true
	camera.fov = Config.fov
	Config.mudou.connect(_ao_mudar_opcoes)
	_altura_cabeca = cabeca.position.y
	lanterna.light_energy = energia_lanterna
	lanterna.light_color = cor_lanterna
	Jogo.jogador_pego.connect(_ao_ser_pego)
	if not Jogo.modo_captura:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


## As opções mudaram (ex.: FOV no menu de pausa): aplica na hora.
func _ao_mudar_opcoes() -> void:
	camera.fov = Config.fov


func _unhandled_input(evento: InputEvent) -> void:
	if travado:
		return
	if evento is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		var graus := graus_por_pixel * Config.sensibilidade
		rotate_y(deg_to_rad(-evento.relative.x * graus))
		if escondido:
			# Dentro do esconderijo só dá para virar um pouco (espiar pelas frestas).
			var desvio := clampf(angle_difference(_olhar_base, rotation.y), -_limite_giro, _limite_giro)
			rotation.y = _olhar_base + desvio
		var sinal_y := 1.0 if Config.inverter_y else -1.0
		cabeca.rotate_x(deg_to_rad(sinal_y * evento.relative.y * graus))
		cabeca.rotation.x = clampf(cabeca.rotation.x, -_limite_inclinacao, _limite_inclinacao)
	elif escondido and evento.is_action_pressed("interagir"):
		# Escondido, o E serve só para sair (e a tecla para aqui: não "re-entra" no mesmo aperto).
		get_viewport().set_input_as_handled()
		var progressao := get_tree().get_first_node_in_group("progressao_v2")
		if progressao:
			progressao.sair_do_esconderijo()
	elif evento.is_action_pressed("lanterna"):
		if escondido:
			return  # lanterna desligada enquanto escondido
		alternar_lanterna()
	elif evento.is_action_pressed("sacudir_lanterna"):
		sacudir_lanterna()
	elif evento.is_action_pressed("interagir"):
		if _alvo_interacao and is_instance_valid(_alvo_interacao):
			# A tecla é "consumida" aqui: ninguém mais reage ao mesmo E (era o bug do esconderijo).
			get_viewport().set_input_as_handled()
			_alvo_interacao.interagir(self)
	elif evento is InputEventMouseButton and evento.pressed:
		# Clicar na janela recaptura o mouse (por exemplo, depois de dar Alt+Tab).
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _physics_process(delta: float) -> void:
	if escondido or no_duto:
		# Parado no esconderijo/duto: só olha em volta (sem física, para não ser empurrado
		# para fora do móvel onde está escondido).
		velocity = Vector3.ZERO
		correndo = false
		_atualizar_stamina(delta)
		_atualizar_respiracao(delta, Input.is_action_pressed("prender_respiracao"))
		_atualizar_lanterna(delta)
		_seguir_lanterna(delta)
		_atualizar_batimento(delta)
		dica_atual = ""
		_alvo_interacao = null
		return
	if not is_on_floor():
		velocity.y -= gravidade * delta

	var direcao := Vector3.ZERO
	var pode_andar := not travado and not escondido and not no_duto
	if pode_andar:
		var entrada := Input.get_vector("mover_esquerda", "mover_direita", "mover_frente", "mover_tras")
		direcao = (transform.basis * Vector3(entrada.x, 0, entrada.y)).normalized()
		_atualizar_agachar(Input.is_action_pressed("agachar"))
		correndo = Input.is_action_pressed("correr") and entrada.length() > 0.1 and not agachado and not exausto
	else:
		correndo = false
	_atualizar_stamina(delta)
	_atualizar_respiracao(delta, pode_andar and Input.is_action_pressed("prender_respiracao"))

	var velocidade := velocidade_correndo if correndo else velocidade_andando
	if agachado:
		velocidade = velocidade_agachado
	var alvo := direcao * velocidade
	velocity.x = move_toward(velocity.x, alvo.x, aceleracao * velocidade * delta)
	velocity.z = move_toward(velocity.z, alvo.z, aceleracao * velocidade * delta)
	move_and_slide()

	_atualizar_balanco(delta)
	_atualizar_ruido(delta)
	_atualizar_lanterna(delta)
	_seguir_lanterna(delta)
	_atualizar_interacao()
	_atualizar_batimento(delta)


# ---------------------------------------------------------------------------
# Corpo (V2): agachar, fôlego, respiração, batimento
# ---------------------------------------------------------------------------

## Troca pelos arquivos externos que existirem (cada um é opcional).
func _carregar_sons_externos() -> void:
	var externo := SomExterno.efeito("batimento_loop")
	if externo:
		_som_batimento.stream = externo
	for piso in PlantaV2.SOM_PISO:
		var v := SomExterno.variacoes("res://assets/audio_externo/efeitos/passo_" + piso)
		if not v.is_empty():
			_passos_externos[piso] = v
	_resp_ofegante = SomExterno.variacoes("res://assets/audio_externo/efeitos/resp_ofegante")
	_resp_recuperando = SomExterno.variacoes("res://assets/audio_externo/efeitos/resp_recuperando")
	_resp_segurando = SomExterno.variacoes("res://assets/audio_externo/efeitos/resp_segurando")
	_resp_soltando = SomExterno.variacoes("res://assets/audio_externo/efeitos/resp_soltando")
	var susto := SomExterno.efeito("jumpscare")
	if susto:
		$SomJumpscare.stream = susto


## Toca uma respiração (sorteia entre as variações externas; senão usa a feita por código).
func _respirar(variacoes: Array[AudioStream], volume := -12.0) -> void:
	if not variacoes.is_empty():
		_som_respiracao.stream = variacoes.pick_random()
	elif _som_respiracao.stream == null:
		return
	_som_respiracao.volume_db = volume
	_som_respiracao.play()


func _novo_som(caminho: String, volume: float) -> AudioStreamPlayer:
	var s := AudioStreamPlayer.new()
	if ResourceLoader.exists(caminho):
		s.stream = load(caminho)
	s.volume_db = volume
	add_child(s)
	return s


func _atualizar_agachar(quer_agachar: bool) -> void:
	if not quer_agachar and agachado and _tem_teto_em_cima():
		return  # embaixo de uma mesa: não dá para levantar ainda
	agachado = quer_agachar
	var alvo := _altura_capsula * (0.62 if agachado else 1.0)
	_capsula.height = move_toward(_capsula.height, alvo, get_physics_process_delta_time() * 4.0)
	$Colisao.position.y = _capsula.height / 2.0


func _tem_teto_em_cima() -> bool:
	var de := global_position + Vector3(0, _capsula.height, 0)
	var consulta := PhysicsRayQueryParameters3D.create(de, global_position + Vector3(0, _altura_capsula + 0.05, 0), 1)
	consulta.exclude = [get_rid()]
	return not get_world_3d().direct_space_state.intersect_ray(consulta).is_empty()


func _atualizar_stamina(delta: float) -> void:
	if Jogo.stamina_infinita:
		stamina = 1.0
		exausto = false
		return
	if correndo and Vector2(velocity.x, velocity.z).length() > 0.5:
		stamina = maxf(stamina - delta / _duracao_stamina, 0.0)
		if stamina <= 0.0:
			exausto = true
	else:
		# Parado recupera mais rápido que andando.
		var parado := Vector2(velocity.x, velocity.z).length() < 0.3
		stamina = minf(stamina + delta / (_duracao_stamina * (1.2 if parado else 2.0)), 1.0)
		if exausto and stamina >= 0.35:
			exausto = false
			if not _resp_recuperando.is_empty():
				_respirar(_resp_recuperando, -14.0)
	# Ofegante: a respiração faz barulho (fraco) enquanto o fôlego não volta.
	if exausto and not respiracao_presa:
		_tempo_ofegante -= delta
		if _tempo_ofegante <= 0.0:
			_tempo_ofegante = 1.0
			Jogo.emitir_ruido(global_position, 3.0, 0.3)
			if not _som_respiracao.playing:
				_respirar(_resp_ofegante)


func _atualizar_respiracao(delta: float, segurando: bool) -> void:
	respiracao_presa = segurando and not _sem_ar and not exausto
	if respiracao_presa and not _estava_segurando and not _resp_segurando.is_empty():
		_respirar(_resp_segurando, -20.0)
	_estava_segurando = respiracao_presa
	if respiracao_presa:
		folego = maxf(folego - delta / duracao_folego_s, 0.0)
		if folego <= 0.0:
			# Acabou o ar: solta tudo de uma vez (barulho!).
			_sem_ar = true
			respiracao_presa = false
			Jogo.emitir_ruido(global_position, 5.0, 0.6)
			_respirar(_resp_soltando if not _resp_soltando.is_empty() else _resp_ofegante, -8.0)
	else:
		if _estava_segurando and not _sem_ar and not _resp_soltando.is_empty():
			_respirar(_resp_soltando, -16.0)  # soltou o ar devagar
		folego = minf(folego + delta / 4.0, 1.0)
		if _sem_ar and folego >= 0.3:
			_sem_ar = false


## Coração acelera quando um animatrônico está perto (mais alto e mais rápido quanto mais perto).
func _atualizar_batimento(delta: float) -> void:
	if _som_batimento.stream == null:
		return
	var mais_perto := INF
	for a in get_tree().get_nodes_in_group("animatronico"):
		mais_perto = minf(mais_perto, global_position.distance_to(a.global_position))
	var forca := clampf(1.0 - mais_perto / distancia_batimento, 0.0, 1.0)
	if respiracao_presa:
		forca = minf(forca * 1.2, 1.0)  # segurando o ar o coração parece ainda mais alto
	var alvo_db := lerpf(-40.0, -2.0, forca)
	_som_batimento.volume_db = move_toward(_som_batimento.volume_db, alvo_db, delta * 30.0)
	_som_batimento.pitch_scale = lerpf(0.9, 1.5, forca)
	if forca > 0.02 and not _som_batimento.playing:
		_som_batimento.play()
	elif forca <= 0.0 and _som_batimento.volume_db <= -39.0:
		_som_batimento.stop()


## R: sacode a lanterna fraca. Ela fica firme por uns segundos (mas sacudir faz barulho).
func sacudir_lanterna() -> void:
	if not lanterna_ligada:
		return
	_tempo_sacudida = duracao_sacudida
	Jogo.emitir_ruido(global_position, 2.5, 0.2)
	var giro := create_tween()
	giro.tween_property(cabeca, "rotation:z", 0.06, 0.06)
	giro.tween_property(cabeca, "rotation:z", -0.06, 0.08)
	giro.tween_property(cabeca, "rotation:z", 0.0, 0.06)


# ---------------------------------------------------------------------------
# Balanço da câmera e passos
# ---------------------------------------------------------------------------

func _atualizar_balanco(delta: float) -> void:
	var altura := altura_cabeca_agachado if agachado else _altura_cabeca
	var velocidade_chao := Vector2(velocity.x, velocity.z).length()
	if velocidade_chao > 0.5 and is_on_floor():
		var fator := 1.45 if correndo else 1.0
		_tempo_balanco += delta * frequencia_passos * fator * TAU / 2.0
		var amplitude := balanco_correndo if correndo else balanco_andando
		if agachado:
			amplitude *= 0.5
		cabeca.position.y = lerpf(cabeca.position.y, altura + sin(_tempo_balanco * 2.0) * amplitude, clampf(delta * 12.0, 0.0, 1.0))
		cabeca.position.x = cos(_tempo_balanco) * amplitude * 0.5
		# Um som de passo a cada "descida" do balanço.
		var passo := int(_tempo_balanco / PI)
		if passo != _ultimo_passo:
			_ultimo_passo = passo
			if Jogo.usa_gerador:
				piso_atual = PlantaV2.piso_em(global_position)
			var som_piso: Array = PlantaV2.SOM_PISO.get(piso_atual, [1.0, 1.0, 0.0])
			var externos: Array = _passos_externos.get(piso_atual, [])
			som_passos.stream = externos.pick_random() if not externos.is_empty() else SONS_PASSO[randi() % SONS_PASSO.size()]
			som_passos.pitch_scale = randf_range(0.9, 1.1) * float(som_piso[1])
			som_passos.volume_db = (-4.0 if correndo else (-18.0 if agachado else -10.0)) + float(som_piso[2])
			som_passos.play()
	else:
		cabeca.position.y = lerpf(cabeca.position.y, altura, delta * 8.0)
		cabeca.position.x = lerpf(cabeca.position.x, 0.0, delta * 8.0)


func _atualizar_ruido(delta: float) -> void:
	_tempo_ruido -= delta
	var velocidade_chao := Vector2(velocity.x, velocity.z).length()
	if velocidade_chao > 0.5 and _tempo_ruido <= 0.0:
		_tempo_ruido = intervalo_ruido
		var mult := float(PlantaV2.SOM_PISO.get(piso_atual, [1.0])[0])
		if agachado:
			Jogo.emitir_ruido(global_position, raio_ruido_agachado * mult, 0.15)
		elif correndo:
			Jogo.emitir_ruido(global_position, raio_ruido_correndo * mult, 0.8)
		else:
			Jogo.emitir_ruido(global_position, raio_ruido_andando * mult, 0.4)


# ---------------------------------------------------------------------------
# Lanterna e bateria
# ---------------------------------------------------------------------------

func alternar_lanterna() -> void:
	if not lanterna_ligada and bateria <= 0.0:
		return  # sem bateria não liga
	lanterna_ligada = not lanterna_ligada
	som_efeitos.stream = SomExterno.efeito("lanterna_clique", "res://assets/sons/lanterna_clique.wav")
	som_efeitos.play()


func _atualizar_lanterna(delta: float) -> void:
	if Jogo.bateria_infinita:
		bateria = bateria_maxima
	if lanterna_ligada:
		bateria = maxf(bateria - descarga_por_segundo * delta, 0.0)
		if bateria <= 0.0:
			lanterna_ligada = false
	var energia := energia_lanterna if lanterna_ligada else 0.0
	# Bateria fraca: alcance e força caem aos poucos (de 100% do alcance em limite_fraca até 45% em 0%).
	var fator := clampf(porcentagem_bateria() / limite_fraca, 0.0, 1.0)
	lanterna.spot_range = _alcance_lanterna * lerpf(0.45, 1.0, fator)
	energia *= lerpf(0.35, 1.0, fator)
	# Com pouca bateria a luz falha de vez em quando.
	_tempo_sacudida = maxf(_tempo_sacudida - delta, 0.0)
	if lanterna_ligada and porcentagem_bateria() < limite_piscar and _tempo_sacudida <= 0.0:
		_tempo_pisca -= delta
		if _tempo_pisca <= 0.0:
			_tempo_pisca = randf_range(0.05, 0.6)
		if _tempo_pisca < 0.12:
			energia *= randf_range(0.0, 0.3)
	lanterna.visible = energia > 0.01
	lanterna.light_energy = energia


## A lanterna fica um pouco atrás do movimento da câmera e treme com bateria
## baixa ou com um animatrônico por perto (a mão do vigia está nervosa).
func _seguir_lanterna(delta: float) -> void:
	var alvo := camera.global_transform * Transform3D(Basis(), Vector3(0.15, -0.12, 0.0))
	var peso := clampf(delta * rapidez_lanterna, 0.0, 1.0)
	var base := lanterna.global_basis.orthonormalized().slerp(alvo.basis.orthonormalized(), peso)
	var tremor := 0.0
	if porcentagem_bateria() < limite_fraca:
		tremor += 0.004
	for a in get_tree().get_nodes_in_group("animatronico"):
		var d := global_position.distance_to(a.global_position)
		if d < distancia_tremer:
			tremor += 0.012 * (1.0 - d / distancia_tremer)
	if tremor > 0.0:
		base = base.rotated(Vector3.UP, randf_range(-tremor, tremor)).rotated(base.x, randf_range(-tremor, tremor))
	lanterna.global_transform = Transform3D(base, alvo.origin)


func porcentagem_bateria() -> float:
	return 100.0 * bateria / bateria_maxima


## Esconderijo: trava o olhar em volta da direção atual (giro e inclinação em radianos).
func travar_olhar(giro: float, inclinacao: float) -> void:
	_olhar_base = rotation.y
	_limite_giro = giro
	_limite_inclinacao = inclinacao


func liberar_olhar() -> void:
	_limite_giro = PI
	_limite_inclinacao = deg_to_rad(85)


## As pilhas chamam isto. 'quantidade' em pontos de bateria (35 = +35%).
func recarregar(quantidade: float) -> void:
	bateria = minf(bateria + quantidade, bateria_maxima)


## true se a lanterna está ligada e iluminando o ponto (cone + sem parede no meio).
func lanterna_ilumina(ponto: Vector3) -> bool:
	if not lanterna.visible:
		return false
	var origem := lanterna.global_position
	var ate := ponto - origem
	if ate.length() > lanterna.spot_range:
		return false
	var frente := -lanterna.global_transform.basis.z
	if frente.angle_to(ate) > deg_to_rad(lanterna.spot_angle):
		return false
	return not _parede_entre(origem, ponto)


## true se o ponto está dentro da tela e sem parede no caminho (usado pelo Tito).
func consegue_ver(ponto: Vector3) -> bool:
	if not camera.is_position_in_frustum(ponto):
		return false
	return not _parede_entre(camera.global_position, ponto)


func _parede_entre(de: Vector3, ate: Vector3) -> bool:
	var consulta := PhysicsRayQueryParameters3D.create(de, ate, 1)  # só a camada "Mundo"
	return not get_world_3d().direct_space_state.intersect_ray(consulta).is_empty()


# ---------------------------------------------------------------------------
# Interação (E)
# ---------------------------------------------------------------------------

func _atualizar_interacao() -> void:
	_alvo_interacao = null
	dica_atual = ""
	if travado or not raio_interacao.is_colliding():
		return
	var alvo := raio_interacao.get_collider()
	if alvo and alvo.is_in_group("interagivel") and alvo.has_method("interagir"):
		_alvo_interacao = alvo
		dica_atual = alvo.texto_dica() if alvo.has_method("texto_dica") else "Aperte E"


## Toca um som curto não posicional (pegar pilha etc.).
func tocar_som(som: AudioStream, volume_db := 0.0) -> void:
	som_efeitos.stream = som
	som_efeitos.volume_db = volume_db
	som_efeitos.play()


# ---------------------------------------------------------------------------
# Susto (jumpscare)
# ---------------------------------------------------------------------------

func _ao_ser_pego(_quem: String) -> void:
	travado = true
	velocity = Vector3.ZERO


## O animatrônico entrega o próprio modelo para aparecer na frente da câmera.
## Como a frente do modelo é +Z e a câmera olha para -Z, ele já fica de cara para o vigia.
func mostrar_jumpscare(modelo: Node3D) -> void:
	modelo.reparent(ponto_jumpscare, false)
	modelo.transform = Transform3D.IDENTITY
	cabeca.rotation.x = 0.0
	lanterna.visible = false
	$Cabeca/Camera3D/LuzJumpscare.visible = true
	$SomJumpscare.play()
	# O modelo "salta" para perto da câmera.
	modelo.scale = Vector3.ONE * 0.6
	modelo.position = Vector3(0, 0.3, -0.6)
	var salto := create_tween().set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	# Os animatrônicos finais têm ~2 m: desce um pouco para o rosto ficar no meio da tela.
	salto.tween_property(modelo, "position", Vector3(0, -0.3, 0), 0.12)
	salto.parallel().tween_property(modelo, "scale", Vector3.ONE, 0.12)
	# Câmera treme e a estática pisca por cima da imagem.
	var tremor := create_tween().set_loops(16)
	tremor.tween_property(camera, "h_offset", 0.05, 0.035)
	tremor.tween_property(camera, "h_offset", -0.05, 0.035)
	var tela: CanvasLayer = $TelaSusto
	var pisca := create_tween().set_loops(8)
	pisca.tween_callback(func(): tela.visible = true)
	pisca.tween_interval(0.07)
	pisca.tween_callback(func(): tela.visible = false)
	pisca.tween_interval(0.08)
