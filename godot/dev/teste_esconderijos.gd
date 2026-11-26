extends Node
## FERRAMENTA DE DESENVOLVIMENTO: testa TODOS os esconderijos do mapa da V2 como um jogador faria.
## Para cada um: mira, aperta E (evento de verdade, pelo caminho normal das teclas), confere que ficou
## escondido (e continua escondido: não "sai no mesmo aperto"), a vista e a altura da câmera, que a
## Pipoca ao lado sem ter visto não acha, e que o E de novo sai para um ponto livre.
## No fim: a Pipoca que VIU o vigia entrar acha ele.
## Rodar: godot --headless --path godot res://dev/teste_esconderijos.tscn

var _mundo: Node3D
var _jogador: CharacterBody3D
var _prog: ProgressaoV2
var _pipoca: Node3D
var _falhas := 0


func _conferir(ok: bool, texto: String) -> void:
	if not ok:
		_falhas += 1
	print("[esconderijos] %s %s" % ["ok   " if ok else "FALHA", texto])


func _quadros(n: int) -> void:
	for i in n:
		await get_tree().physics_frame


func _apertar(acao: String) -> void:
	var ev := InputEventAction.new()
	ev.action = acao
	ev.pressed = true
	get_viewport().push_input(ev)
	await _quadros(2)
	var solta := InputEventAction.new()
	solta.action = acao
	solta.pressed = false
	get_viewport().push_input(solta)
	await _quadros(2)


func _ready() -> void:
	Jogo.trocar_cena_ao_terminar = false
	Config.dificuldade = 0
	_mundo = load("res://cenas/mundo_v2.tscn").instantiate()
	add_child(_mundo)
	await _quadros(20)
	_jogador = _mundo.get_node("Jogador")
	_prog = _mundo.get_node("Montador/ProgressaoV2")
	_pipoca = _mundo.get_node("Animatronicos/Pipoca")
	_mundo.get_node("Animatronicos/Tito").set_physics_process(false)
	_pipoca.set_physics_process(false)
	Jogo.em_partida = true
	Jogo.ia_ativa = true
	Jogo.hora = 2
	var marcadores := get_tree().get_nodes_in_group("esconderijo").filter(
		func(e: Node) -> bool: return ProgressaoV2.ESCONDERIJOS.has(String(e.get_meta("tipo", ""))))
	_conferir(marcadores.size() >= 14, "esconderijos no mapa: %d" % marcadores.size())
	for m in marcadores:
		await _testar(m as Node3D)
	await _viu_entrar(marcadores[0] as Node3D)
	print("[esconderijos] %d falha(s)" % _falhas)
	Jogo.trocar_cena_ao_terminar = true
	Config.dificuldade = 1
	get_tree().quit(1 if _falhas else 0)


func _testar(marcador: Node3D) -> void:
	var tipo := String(marcador.get_meta("tipo"))
	var nome := "%s em %s (%s)" % [tipo, PlantaV2.comodo_em(marcador.global_position), marcador.name]
	var area := marcador.get_node("Interacao_Esconderijo") as Node3D
	# Em pé na frente, olhando para o meio da área de interação.
	var olhar := _prog._olhar_do_esconderijo(marcador.global_position, String(marcador.get_meta("tipo", "")))
	var mapa: RID = _mundo.get_node("Navegacao").get_navigation_map()
	var frente := NavigationServer3D.map_get_closest_point(mapa, marcador.global_position + olhar * 1.3)
	_jogador.global_position = frente + Vector3(0, 0.05, 0)
	_jogador.velocity = Vector3.ZERO
	var alvo := area.global_position
	var d := alvo - (_jogador.global_position + Vector3(0, 1.6, 0))
	_jogador.rotation.y = atan2(-d.x, -d.z)
	_jogador.get_node("Cabeca").rotation.x = atan2(d.y, Vector2(d.x, d.z).length())
	await _quadros(4)
	var dica: String = _jogador.dica_atual
	if not dica.contains("ESCONDER"):
		_conferir(false, "%s: a mira não pega o esconderijo (dica: '%s')" % [nome, dica])
		return
	await _apertar("interagir")
	await _quadros(15)
	var cfg: Dictionary = ProgressaoV2.ESCONDERIJOS[tipo]
	var cabeca_y: float = _jogador.get_node("Cabeca").position.y
	_conferir(_jogador.escondido and _jogador.collision_layer == 0 and is_instance_valid(_prog._vista)
		and absf(cabeca_y - float(cfg["altura"])) < 0.05, "%s: entrou com E (vista '%s', câmera a %.2f m)" % [nome, cfg["vista"], cabeca_y])
	await _quadros(10)
	_conferir(_jogador.escondido, "%s: continua escondido depois do aperto" % nome)
	# A Pipoca bem do lado, sem ter visto, não acha.
	_pipoca.global_position = _jogador.global_position + olhar * 0.7
	_pipoca.mudar_estado(1)
	var ve: bool = _pipoca.ve_jogador()
	_pipoca.checar_contato()
	await _quadros(2)
	_conferir(not ve and Jogo.em_partida, "%s: Pipoca do lado sem ter visto não acha" % nome)
	_pipoca.global_position = Vector3(0, -50, 0)
	# Sai com E: ponto livre, na navegação, perto do esconderijo.
	await _apertar("interagir")
	await _quadros(4)
	var saida := _jogador.global_position
	var na_nav := NavigationServer3D.map_get_closest_point(mapa, saida)
	_conferir(not _jogador.escondido and _prog._livre(saida - Vector3(0, 0.05, 0)) and Vector2(na_nav.x - saida.x, na_nav.z - saida.z).length() < 0.4
		and saida.distance_to(marcador.global_position) < 3.0, "%s: saiu com E para um ponto livre (%.1f m do esconderijo)" % [nome, saida.distance_to(marcador.global_position)])


func _viu_entrar(marcador: Node3D) -> void:
	var olhar := _prog._olhar_do_esconderijo(marcador.global_position, String(marcador.get_meta("tipo", "")))
	_pipoca.set_physics_process(true)
	_pipoca.global_position = marcador.global_position + olhar * 4.0
	_pipoca.mudar_estado(3)  # perseguindo
	_pipoca._ultima_vez_viu = _pipoca._agora()
	await _prog.esconder(marcador)
	var pego := false
	for i in 600:
		await get_tree().physics_frame
		if not Jogo.em_partida:
			pego = true
			break
	_conferir(pego, "Pipoca que viu o vigia entrar acha ele (respirando normalmente)")
