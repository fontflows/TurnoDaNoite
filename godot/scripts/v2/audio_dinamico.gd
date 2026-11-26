class_name AudioDinamico
extends Node
## Áudio da V2 que muda com o que acontece na noite:
##   - Reverb por cômodo: o eco do barramento "Efeitos" muda com o tamanho e o piso do cômodo
##     onde o vigia está (salão grande ecoa muito; armário de limpeza quase nada; azulejo é "brilhante").
##   - Música em camadas: um grave pulsando sobe com a TENSÃO (Jogo.tensao) e a percussão de
##     perseguição entra quando a Pipoca está caçando (ou depois que o gerador liga).
##   - Sustos de ambiente: de vez em quando, um som 3D longe do vigia (metal caindo, brinquedo
##     chiando, caixinha com notas erradas). Só quando está calmo, para não virar barulheira.
##   - Gerador ligado: a música do palco volta, lenta e mais alta (os animatrônicos "acordam").

const SUSTOS := ["res://assets/sons/susto_batida_metal.wav", "res://assets/sons/susto_brinquedo.wav",
	"res://assets/sons/susto_caixinha.wav"]

## Volume máximo (dB) da camada de tensão.
@export var volume_tensao_db := -8.0
## Volume máximo (dB) da camada de perseguição.
@export var volume_perseguicao_db := -6.0
## Intervalo (s) entre sustos de ambiente: mínimo e máximo (o diretor encurta no Pesadelo).
@export var intervalo_sustos := Vector2(45.0, 100.0)

var _tensao: AudioStreamPlayer
var _perseguicao: AudioStreamPlayer
var _reverb: AudioEffectReverb
var _tempo_susto := 60.0
var _tique := 0.0
var _comodo := ""


func _ready() -> void:
	_tensao = _camada("res://assets/sons/tensao_drone.wav")
	_perseguicao = _camada("res://assets/sons/perseguicao.wav")
	_reverb = _pegar_reverb()
	_tempo_susto = randf_range(intervalo_sustos.x, intervalo_sustos.y)
	Jogo.gerador_ligado.connect(_ao_ligar_gerador)


func _exit_tree() -> void:
	if _reverb:
		_reverb.wet = 0.0  # fora do jogo (menu) sem eco


func _camada(caminho: String) -> AudioStreamPlayer:
	var p := AudioStreamPlayer.new()
	p.add_to_group("som_musica")  # o Config põe no barramento "Musica"
	if ResourceLoader.exists(caminho):
		p.stream = load(caminho)
	p.volume_db = -80.0
	add_child(p)
	p.finished.connect(p.play)
	if p.stream:
		p.play()
	return p


## Usa (ou cria uma vez) o efeito de reverb no barramento "Efeitos".
func _pegar_reverb() -> AudioEffectReverb:
	var i := AudioServer.get_bus_index(&"Efeitos")
	if i < 0:
		return null
	for k in AudioServer.get_bus_effect_count(i):
		var e := AudioServer.get_bus_effect(i, k)
		if e is AudioEffectReverb:
			return e
	var r := AudioEffectReverb.new()
	r.wet = 0.0
	r.dry = 1.0
	AudioServer.add_bus_effect(i, r)
	return r


func _process(delta: float) -> void:
	if not Jogo.em_partida:
		return
	# Camadas de música: suaves, sem pulos.
	var perseguindo := Jogo.gerador_esta_ligado
	for a in get_tree().get_nodes_in_group("animatronico"):
		if a.get("estado") == 3:  # Pipoca perseguindo
			perseguindo = true
	var alvo_tensao := lerpf(-50.0, volume_tensao_db, clampf(Jogo.tensao * 1.4, 0.0, 1.0))
	_tensao.volume_db = move_toward(_tensao.volume_db, alvo_tensao, delta * 20.0)
	var alvo_perseguicao := volume_perseguicao_db if perseguindo else -80.0
	_perseguicao.volume_db = move_toward(_perseguicao.volume_db, alvo_perseguicao, delta * (40.0 if perseguindo else 15.0))
	_tique -= delta
	if _tique <= 0.0:
		_tique = 0.5
		_atualizar_reverb()
	_tempo_susto -= delta
	if _tempo_susto <= 0.0:
		var i := Jogo.dificuldade.intensidade_diretor if Jogo.dificuldade else 0.5
		_tempo_susto = randf_range(intervalo_sustos.x, intervalo_sustos.y) * lerpf(1.3, 0.7, i)
		if Jogo.tensao < 0.5:
			_susto_de_ambiente()


func _atualizar_reverb() -> void:
	var jogador := get_tree().get_first_node_in_group("jogador") as Node3D
	if jogador == null or _reverb == null:
		return
	var comodo := PlantaV2.comodo_em(jogador.global_position)
	if comodo == _comodo:
		return
	_comodo = comodo
	var area := 40.0
	for c in PlantaV2.dados()["comodos"]:
		if c["nome"] == comodo:
			area = (c["x1"] - c["x0"]) * (c["z1"] - c["z0"])
	var tamanho := clampf(area / 400.0, 0.15, 0.9)
	_reverb.room_size = tamanho
	_reverb.wet = 0.06 + 0.16 * tamanho
	# Azulejo e metal refletem os agudos (eco "brilhante"); carpete e tecido abafam.
	var piso := PlantaV2.piso_em(jogador.global_position)
	_reverb.damping = 0.15 if piso in ["azulejo", "metal"] else (0.8 if piso == "carpete" else 0.5)
	_reverb.predelay_msec = lerpf(15.0, 70.0, tamanho)


## Um som 3D num ponto da navegação a 10–18 m do vigia (parece que algo se mexeu lá).
func _susto_de_ambiente() -> void:
	var jogador := get_tree().get_first_node_in_group("jogador") as Node3D
	var mundo := get_tree().get_first_node_in_group("mundo")
	if jogador == null or mundo == null:
		return
	var mapa: RID = mundo.get_node("Navegacao").get_navigation_map()
	var angulo := randf() * TAU
	var ponto := NavigationServer3D.map_get_closest_point(mapa, jogador.global_position + Vector3(cos(angulo), 0, sin(angulo)) * randf_range(10.0, 18.0))
	var caminho: String = SUSTOS.pick_random()
	caminho = SomExterno.caminho("res://assets/audio_externo/efeitos/" + caminho.get_file().get_basename(), caminho)
	if caminho == "":
		return
	var s := AudioStreamPlayer3D.new()
	s.stream = load(caminho)
	s.unit_size = 6.0
	s.max_distance = 40.0
	s.volume_db = -4.0
	mundo.add_child(s)
	s.global_position = ponto + Vector3(0, 1.0, 0)
	s.finished.connect(s.queue_free)
	s.play()


## Fim da noite: a música do palco volta sozinha, lenta e alta (todos acordaram).
func _ao_ligar_gerador() -> void:
	var mundo := get_tree().get_first_node_in_group("mundo")
	var palco := mundo.get_node_or_null("Sons/MusicaPalco") as AudioStreamPlayer3D if mundo else null
	if palco:
		palco.pitch_scale = 0.82
		palco.max_distance = 60.0
		palco.unit_size = 8.0
		create_tween().tween_property(palco, "volume_db", 2.0, 2.0)
		if not palco.playing:
			palco.play()
