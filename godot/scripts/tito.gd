extends Animatronico
## TITO, o urso: o "estátua".
## Só anda quando o vigia NÃO está olhando para ele (fora da tela ou atrás de parede).
## Se o vigia olha, ele congela na hora. Vai sempre na direção do vigia.
## V2: olhar no escuro não basta. Ele só congela se o vigia o ENXERGA de verdade:
## com a lanterna nele, perto de uma luz acesa ou bem perto (a silhueta). Quando a
## lanterna pisca ou falha, ele aproveita para andar.

@export_group("Velocidade do Tito")
## Velocidade (m/s) quando ele acorda, à 1 AM.
@export var velocidade_base := 1.4
## Quanto ele fica mais rápido a cada hora que passa.
@export var aumento_por_hora := 0.25
## Quanto ele fica mais rápido a cada disjuntor religado (a energia "acorda" ele).
@export var aumento_por_disjuntor := 0.2

@export_group("Enxergar no escuro (V2)")
## Até esta distância (m) o vigia enxerga a silhueta do Tito mesmo sem luz.
@export var distancia_silhueta := 3.5
## Com o gerador ligado (fim da noite), a velocidade é multiplicada por isto.
@export var mult_gerador := 1.4

@export_group("Passos do Tito")
## Até que distância (m) o vigia ouve os passos metálicos dele.
@export var distancia_ouvir_passos := 12.0
## Tempo (s) entre um passo e outro.
@export var intervalo_passos := 0.6

@onready var som_passos: AudioStreamPlayer3D = $SomPassos

var visto := false  ## true enquanto o vigia está olhando para ele (útil para depurar)
var _tempo_passo := 0.0
var _alvo_vagar: Node3D
var _passos_externos: Array[AudioStream] = []
var _tempo_vagando := 0.0


func velocidade_atual() -> float:
	var horas_acordado := maxi(Jogo.hora - hora_de_acordar, 0)
	var v := velocidade_base + aumento_por_hora * horas_acordado + aumento_por_disjuntor * Jogo.disjuntores_ligados
	if Jogo.gerador_esta_ligado:
		v *= mult_gerador
	return v * mult_velocidade()


## O vigia consegue enxergar este ponto do Tito? (na tela, sem parede E com alguma luz)
func _enxergado(ponto: Vector3) -> bool:
	if not jogador.consegue_ver(ponto):
		return false
	if not Jogo.usa_gerador:
		return true  # mapa da V1: regra antiga (olhou, congelou)
	if jogador.lanterna_ilumina(ponto) or distancia_ate_jogador() <= distancia_silhueta:
		return true
	return _perto_de_luz_acesa(ponto)


## Está dentro do alcance de uma luz acesa (ilha de luz, neon, tela, holofote...)?
func _perto_de_luz_acesa(ponto: Vector3) -> bool:
	for luz in get_tree().get_nodes_in_group("fonte_luz_ilha"):
		var l := luz as Light3D
		if l == null or not l.is_visible_in_tree() or l.light_energy < 0.2:
			continue
		var alcance: float = l.omni_range if l is OmniLight3D else (l as SpotLight3D).spot_range
		if l.global_position.distance_to(ponto) <= alcance * 0.7:
			return true
	return false


func _physics_process(delta: float) -> void:
	if not ativo():
		anim_parado = "parado"
		olhar_vigia(0.0)
		parar(delta)
		return

	# Olhando para o peito OU para a cabeça já conta como "visto".
	visto = jogador_exposto() and (_enxergado(posicao_peito()) or _enxergado(posicao_cabeca()))
	if visto:
		# Congela na pose em que está: nem a animação nem a cabeça se mexem.
		parar(delta, false)
		olhar_vigia(0.0, true)
		return

	if jogador_exposto():
		# Indo atrás do vigia: passos de perseguição e a cabeça virada para ele
		# (quando o vigia olha de novo, a cabeça está apontada para ele).
		anim_movendo = "perseguir"
		anim_parado = "procurar"
		olhar_vigia(1.0)
		mover_para(jogador.global_position, velocidade_atual(), delta)
	else:
		# Vigia escondido ou no duto: o Tito perde o rastro e vaga pelos pontos de patrulha.
		anim_movendo = "andar"
		anim_parado = "procurar"
		olhar_vigia(0.0)
		_tempo_vagando -= delta
		if _alvo_vagar == null or _tempo_vagando <= 0.0:
			var pontos := get_tree().get_nodes_in_group("ponto_patrulha")
			_alvo_vagar = pontos.pick_random() if not pontos.is_empty() else null
			_tempo_vagando = 20.0
		if _alvo_vagar:
			mover_para(_alvo_vagar.global_position, velocidade_atual() * 0.6, delta)
	_tocar_passos(delta)
	checar_contato()


func _tocar_passos(delta: float) -> void:
	_tempo_passo -= delta
	if _tempo_passo > 0.0:
		return
	_tempo_passo = intervalo_passos / clampf(velocidade_atual() / velocidade_base, 1.0, 2.0)
	if distancia_ate_jogador() <= distancia_ouvir_passos:
		if _passos_externos.is_empty():
			_passos_externos = SomExterno.variacoes("res://assets/audio_externo/efeitos/tito_passo")
			if _passos_externos.is_empty():
				_passos_externos.append(som_passos.stream)
		som_passos.stream = _passos_externos.pick_random()
		som_passos.pitch_scale = randf_range(0.85, 1.0)
		som_passos.play()


func _ao_dar_susto() -> void:
	som_passos.stop()
