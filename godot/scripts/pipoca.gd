extends Animatronico
## PIPOCA, a coelha: a "caçadora".
## Patrulha pela pizzaria, vai investigar barulhos, persegue quando vê o vigia
## e fica atordoada se a lanterna ficar nela por alguns segundos.
## V2: abre portas destrancadas, checa esconderijos (prender a respiração ajuda),
## enxerga menos o vigia agachado e mais quem anda com a lanterna acesa, e depois
## que o gerador liga ela CAÇA o vigia sabendo onde ele está.

enum Estado { PARADA, PATRULHANDO, INVESTIGANDO, PERSEGUINDO, ATORDOADA, CHECANDO }

@export_group("Velocidade da Pipoca")
## Velocidade (m/s) patrulhando ou investigando.
@export var velocidade_patrulha := 1.6
## Velocidade (m/s) perseguindo. Mais rápida que o vigia andando (3,0),
## mais lenta que correndo (5,5).
@export var velocidade_perseguicao := 3.6
## Quanto a perseguição fica mais rápida a cada hora.
@export var aumento_por_hora := 0.15
## Quanto a perseguição fica mais rápida a cada disjuntor religado.
@export var aumento_por_disjuntor := 0.15

@export_group("Visão")
## Abertura total do cone de visão (graus).
@export var angulo_visao := 70.0
## Até que distância (m) ela enxerga o vigia.
@export var distancia_visao := 14.0
## Perto assim (m) ela "sente" o vigia mesmo de costas.
@export var distancia_sentir := 2.0
## Segundos sem ver o vigia até desistir da perseguição.
@export var tempo_para_desistir := 5.0

@export_group("Lanterna")
## Segundos de lanterna nela para ficar atordoada.
@export var tempo_para_atordoar := 2.0
## Segundos que ela fica parada no palco depois de atordoada.
@export var tempo_atordoada := 20.0

@export_group("Sentidos (V2)")
## Agachado, o vigia é visto só até esta fração da distância de visão.
@export var fator_visao_agachado := 0.6
## Com a lanterna acesa, a distância de visão é multiplicada por isto (luz chama atenção).
@export var fator_visao_lanterna := 1.3
## Raio (m) em volta de um barulho em que ela procura esconderijos para checar.
@export var raio_procurar_esconderijo := 4.5
## Segundos olhando dentro do esconderijo.
@export var tempo_checando := 1.8
## Com o gerador ligado, a velocidade de perseguição é multiplicada por isto.
@export var mult_gerador := 1.15

@export_group("Patrulha")
## Segundos que ela espera em cada ponto de patrulha.
@export var espera_no_ponto := 1.5

@onready var som_chiado: AudioStreamPlayer3D = $SomChiado
@onready var som_pane: AudioStreamPlayer3D = $SomPane

var estado := Estado.PARADA
var _pontos: Array[Node] = []
var _ponto_atual: Node3D
var _espera := 0.0
var _alvo_ruido := Vector3.ZERO
var _tempo_sem_ver := 0.0
var _tempo_lanterna := 0.0
var _tempo_estado := 0.0
var _olhos: Array[Node3D] = []
## Esconderijo que ela vai checar (estado CHECANDO).
var _esconderijo_alvo: Node3D
## Último instante em que ela VIU o vigia (para saber se viu ele se escondendo).
var _ultima_vez_viu := -100.0


func _ready() -> void:
	super._ready()
	_pontos = get_tree().get_nodes_in_group("ponto_patrulha")
	for nome in ["Pipoca_Olho_Esq", "Pipoca_Olho_Dir"]:
		var olho := modelo.find_child(nome, true, false) as Node3D
		if olho:
			_olhos.append(olho)
	Jogo.ruido_emitido.connect(_ao_ouvir_ruido)
	# Sons externos (docs/PROMPTS_AUDIO.md), se existirem.
	var servo := SomExterno.efeito("pipoca_servo_loop")
	if servo:
		som_chiado.stream = servo
	var pane := SomExterno.efeito("pipoca_pane")
	if pane:
		som_pane.stream = pane


func velocidade_perseguindo() -> float:
	var horas_acordada := maxi(Jogo.hora - hora_de_acordar, 0)
	var v := velocidade_perseguicao + aumento_por_hora * horas_acordada + aumento_por_disjuntor * Jogo.disjuntores_ligados
	if Jogo.gerador_esta_ligado:
		v *= mult_gerador
	return v * mult_velocidade()


func _agora() -> float:
	return Time.get_ticks_msec() / 1000.0


func mudar_estado(novo: Estado) -> void:
	estado = novo
	_tempo_estado = 0.0
	_espera = 0.0


func _physics_process(delta: float) -> void:
	_tempo_estado += delta
	if estado == Estado.ATORDOADA:
		_processar_atordoada(delta)
		return
	if not ativo():
		anim_parado = "parado"
		olhar_vigia(0.0)
		parar(delta)
		som_chiado.stop()
		return
	# Modo observação (debug): ela ignora o vigia e volta a patrulhar.
	if Jogo.modo_observacao and estado in [Estado.PERSEGUINDO, Estado.CHECANDO, Estado.INVESTIGANDO]:
		mudar_estado(Estado.PATRULHANDO)
	if estado == Estado.PARADA:
		mudar_estado(Estado.PATRULHANDO)

	_conferir_lanterna(delta)
	if estado == Estado.ATORDOADA:
		return

	# Fim da noite: com o gerador ligado ela sabe onde o vigia está e não desiste.
	if Jogo.gerador_esta_ligado and jogador_exposto() and estado != Estado.CHECANDO:
		if estado != Estado.PERSEGUINDO:
			mudar_estado(Estado.PERSEGUINDO)
		_tempo_sem_ver = 0.0

	var vendo := ve_jogador()
	if vendo:
		if estado != Estado.PERSEGUINDO:
			mudar_estado(Estado.PERSEGUINDO)
		_tempo_sem_ver = 0.0
		_ultima_vez_viu = _agora()

	# Animação de cada estado: andando / parada.
	match estado:
		Estado.PERSEGUINDO:
			anim_movendo = "perseguir"
			anim_parado = "procurar"
		_:
			anim_movendo = "andar"
			anim_parado = "procurar"
	olhar_vigia(1.0 if vendo or estado == Estado.PERSEGUINDO else 0.0)

	match estado:
		Estado.PATRULHANDO:
			_patrulhar(delta)
		Estado.INVESTIGANDO:
			if mover_para(_alvo_ruido, velocidade_patrulha * 1.3 * mult_velocidade(), delta):
				_espera += delta
				if _espera > 2.0:
					# Chegou no barulho e não achou ninguém: às vezes checa um esconderijo por perto.
					var perto := _esconderijo_perto_de(_alvo_ruido)
					if perto and randf() < _chance_checar() * 0.6:
						_checar(perto)
					else:
						mudar_estado(Estado.PATRULHANDO)
		Estado.PERSEGUINDO:
			if not jogador_exposto():
				# Sumiu! Se ela VIU o vigia se esconder (agora há pouco), vai direto naquele esconderijo
				# (aí só prender a respiração salva, com a chance da dificuldade).
				var onde: Node3D = jogador.get_meta("esconderijo", null) if jogador.has_meta("esconderijo") else null
				if onde and _agora() - _ultima_vez_viu < 2.5:
					_checar(onde)
				else:
					_alvo_ruido = jogador.global_position
					mudar_estado(Estado.INVESTIGANDO)
			else:
				mover_para(jogador.global_position, velocidade_perseguindo(), delta)
				if not ve_jogador() and not Jogo.gerador_esta_ligado:
					_tempo_sem_ver += delta
					if _tempo_sem_ver >= _tempo_desistir():
						# Vai até o último lugar onde viu o vigia e depois volta a patrulhar.
						_alvo_ruido = jogador.global_position
						mudar_estado(Estado.INVESTIGANDO)
				checar_contato()
		Estado.CHECANDO:
			_processar_checando(delta)

	# O chiado mecânico toca enquanto ela anda.
	var andando := Vector2(velocity.x, velocity.z).length() > 0.2
	if andando and not som_chiado.playing:
		som_chiado.play()
	elif not andando and som_chiado.playing:
		som_chiado.stop()
	som_chiado.pitch_scale = 1.25 if estado == Estado.PERSEGUINDO else 1.0
	if estado != Estado.PERSEGUINDO:
		checar_contato()


func _patrulhar(delta: float) -> void:
	if _pontos.is_empty():
		parar(delta)
		return
	if _ponto_atual == null:
		_ponto_atual = _pontos.pick_random()
	if mover_para(_ponto_atual.global_position, velocidade_patrulha * mult_velocidade(), delta):
		_espera += delta
		if _espera >= espera_no_ponto:
			_espera = 0.0
			var anterior := _ponto_atual
			while _pontos.size() > 1 and _ponto_atual == anterior:
				_ponto_atual = _pontos.pick_random()


## Cone de visão + nada no caminho. Muito perto, ela sente mesmo de costas.
func ve_jogador() -> bool:
	if not jogador_exposto():
		return false
	var olho := posicao_cabeca()
	var alvo := jogador.global_position + Vector3(0, 1.0 if jogador.get("agachado") else 1.5, 0)
	var distancia := olho.distance_to(alvo)
	var alcance := distancia_visao * mult_sentidos()
	if jogador.get("agachado"):
		alcance *= fator_visao_agachado
	if jogador.get("lanterna_ligada"):
		alcance *= fator_visao_lanterna
	if distancia > alcance:
		return false
	if distancia > distancia_sentir:
		var frente := global_transform.basis.z  # a frente do modelo é +Z
		frente.y = 0.0
		var para_jogador := alvo - olho
		para_jogador.y = 0.0
		if frente.angle_to(para_jogador) > deg_to_rad(angulo_visao / 2.0):
			return false
	return not parede_entre(olho, alvo)


func _ao_ouvir_ruido(posicao: Vector3, raio: float, _intensidade := 1.0) -> void:
	if Jogo.modo_observacao:
		return
	if not ativo() or estado in [Estado.PERSEGUINDO, Estado.ATORDOADA, Estado.CHECANDO]:
		return
	if global_position.distance_to(posicao) <= raio * mult_sentidos():
		_alvo_ruido = posicao
		mudar_estado(Estado.INVESTIGANDO)


## O diretor de tensão usa isto para "mandar" a Pipoca dar uma olhada num lugar.
func investigar(posicao: Vector3) -> void:
	if Jogo.modo_observacao:
		return
	if not ativo() or estado in [Estado.PERSEGUINDO, Estado.ATORDOADA, Estado.CHECANDO]:
		return
	_alvo_ruido = posicao
	mudar_estado(Estado.INVESTIGANDO)


# ---------------------------------------------------------------------------
# Checar esconderijos (V2)
# ---------------------------------------------------------------------------

func _chance_checar() -> float:
	return Jogo.dificuldade.chance_checar_esconderijo if Jogo.dificuldade else 0.4


## Menos tempo sem ver o vigia até desistir quando a tensão está alta demais (diretor).
func _tempo_desistir() -> float:
	return tempo_para_desistir * (0.6 if Jogo.tensao_alta_demais else 1.0)


func _esconderijo_perto_de(ponto: Vector3) -> Node3D:
	var melhor: Node3D = null
	var menor := raio_procurar_esconderijo
	for e in get_tree().get_nodes_in_group("esconderijo"):
		var d := (e as Node3D).global_position.distance_to(ponto)
		if d < menor and e.has_node("Interacao_Esconderijo"):
			menor = d
			melhor = e
	return melhor


func _checar(esconderijo: Node3D) -> void:
	_esconderijo_alvo = esconderijo
	mudar_estado(Estado.CHECANDO)


## Vai até o esconderijo, para na frente e "olha dentro".
## Se o vigia estiver lá: segurando a respiração ainda há chance de ela não perceber;
## respirando normalmente (ou ofegante), ela acha na hora.
func _processar_checando(delta: float) -> void:
	if _esconderijo_alvo == null:
		mudar_estado(Estado.PATRULHANDO)
		return
	var chegou := mover_para(_esconderijo_alvo.global_position, velocidade_patrulha * 1.4 * mult_velocidade(), delta) \
		or global_position.distance_to(_esconderijo_alvo.global_position) < 1.3
	if not chegou:
		return
	parar(delta)
	_espera += delta
	if _espera < tempo_checando:
		virar_para(_esconderijo_alvo.global_position - global_position, delta)
		return
	var esta_aqui: bool = jogador.get("escondido") and jogador.get_meta("esconderijo", null) == _esconderijo_alvo
	if esta_aqui:
		var achou := true
		if jogador.get("respiracao_presa"):
			achou = randf() < _chance_checar()
		if achou:
			var prog := get_tree().get_first_node_in_group("progressao_v2")
			if prog:
				prog.sair_do_esconderijo()  # arrancado do esconderijo...
			pegar()
			return
	_esconderijo_alvo = null
	mudar_estado(Estado.PATRULHANDO)


func _conferir_lanterna(delta: float) -> void:
	if jogador.lanterna_ilumina(posicao_peito()) or jogador.lanterna_ilumina(posicao_cabeca()):
		_tempo_lanterna += delta
		# Enquanto está sendo iluminada, os olhos tremem (dá para ver que está funcionando).
		for olho in _olhos:
			olho.visible = randf() > 0.25
		if _tempo_lanterna >= tempo_para_atordoar:
			_atordoar()
	else:
		_tempo_lanterna = maxf(_tempo_lanterna - delta * 0.5, 0.0)
		for olho in _olhos:
			olho.visible = true


func _atordoar() -> void:
	mudar_estado(Estado.ATORDOADA)
	_tempo_lanterna = 0.0
	som_chiado.stop()
	som_pane.play()


## Atordoada: pisca os olhos por 1,5 s, "reinicia" no palco e fica parada um tempo.
func _processar_atordoada(delta: float) -> void:
	parar(delta, false)
	tocar("atordoado")
	olhar_vigia(0.0)
	if _tempo_estado < 1.5:
		modelo.rotation.z = sin(_tempo_estado * 40.0) * 0.05  # treme
		for olho in _olhos:
			olho.visible = fmod(_tempo_estado, 0.2) < 0.1
		return
	if _tempo_estado - delta < 1.5:
		# Acabou o tremor: volta para o palco.
		modelo.rotation.z = 0.0
		var palco := get_node_or_null(ponto_palco) as Node3D
		if palco:
			global_position = palco.global_position
			rotation.y = 0.0
		velocity = Vector3.ZERO
	for olho in _olhos:
		olho.visible = fmod(_tempo_estado, 1.6) < 1.3  # olhos "religando" de vez em quando
	if _tempo_estado >= 1.5 + tempo_atordoada:
		for olho in _olhos:
			olho.visible = true
		_ponto_atual = null
		mudar_estado(Estado.PATRULHANDO)


func _ao_dar_susto() -> void:
	som_chiado.stop()
	for olho in _olhos:
		olho.visible = true
