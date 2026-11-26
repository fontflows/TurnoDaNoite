class_name DiretorTensao
extends Node
## "Diretor de tensão": mede o quanto o vigia está em perigo e mexe no ritmo da noite.
##   - Calmo demais por muito tempo  -> manda a Pipoca investigar perto do vigia.
##   - Tenso demais por muito tempo  -> dá um respiro (a Pipoca desiste mais rápido por um tempo).
## Quão insistente ele é vem da dificuldade (intensidade_diretor: Fácil baixo, Pesadelo alto).
## Não "trapaceia": a Pipoca vai até um ponto PERTO do vigia, não até ele.

## Distância (m) do animatrônico mais perto em que a tensão já é máxima.
@export var distancia_tensao_maxima := 3.0
## Distância (m) a partir da qual a tensão é zero.
@export var distancia_tensao_zero := 22.0

var tempo_calmo := 0.0
var tempo_tenso := 0.0
var _tempo_respiro := 0.0
var _tique := 0.0


func _intensidade() -> float:
	return Jogo.dificuldade.intensidade_diretor if Jogo.dificuldade else 0.5


func _process(delta: float) -> void:
	if not Jogo.em_partida or not Jogo.ia_ativa:
		return
	_tique -= delta
	if _tique > 0.0:
		return
	_tique = 1.0
	var jogador := get_tree().get_first_node_in_group("jogador") as Node3D
	if jogador == null:
		return
	# 1. Tensão de agora: proximidade do animatrônico mais perto, perseguição = máximo.
	var alvo := 0.0
	for a in get_tree().get_nodes_in_group("animatronico"):
		var d := (a as Node3D).global_position.distance_to(jogador.global_position)
		alvo = maxf(alvo, clampf(inverse_lerp(distancia_tensao_zero, distancia_tensao_maxima, d), 0.0, 1.0))
		if a.get("estado") == 3:  # Pipoca.Estado.PERSEGUINDO
			alvo = 1.0
	Jogo.tensao = lerpf(Jogo.tensao, alvo, 0.35)
	Jogo.tensao_mudou.emit(Jogo.tensao)
	# 2. Ritmo: conta quanto tempo seguido está calmo ou tenso.
	if Jogo.tensao < 0.25:
		tempo_calmo += 1.0
	else:
		tempo_calmo = 0.0
	tempo_tenso = tempo_tenso + 1.0 if Jogo.tensao > 0.8 else 0.0
	var i := _intensidade()
	if i <= 0.0 or Jogo.hora < 1:
		return
	if tempo_calmo >= lerpf(150.0, 45.0, i):
		tempo_calmo = 0.0
		_mandar_investigar(jogador)
	if tempo_tenso >= lerpf(40.0, 90.0, i):
		tempo_tenso = 0.0
		Jogo.tensao_alta_demais = true
		_tempo_respiro = lerpf(25.0, 10.0, i)
	if Jogo.tensao_alta_demais:
		_tempo_respiro -= 1.0
		if _tempo_respiro <= 0.0:
			Jogo.tensao_alta_demais = false


## Manda a Pipoca para um ponto navegável a alguns metros do vigia (não em cima dele).
func _mandar_investigar(jogador: Node3D) -> void:
	var mundo := get_tree().get_first_node_in_group("mundo")
	if mundo == null:
		return
	var mapa: RID = mundo.get_node("Navegacao").get_navigation_map()
	var angulo := randf() * TAU
	var raio := lerpf(9.0, 4.5, _intensidade())
	var ponto := NavigationServer3D.map_get_closest_point(mapa, jogador.global_position + Vector3(cos(angulo), 0, sin(angulo)) * raio)
	for a in get_tree().get_nodes_in_group("animatronico"):
		if a.has_method("investigar"):
			a.investigar(ponto)
