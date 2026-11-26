extends Node
## FERRAMENTA DE DESENVOLVIMENTO: "teste de fumaça" do mapa da V2 com os animatrônicos ligados.
## Roda 1 minuto de jogo acelerado com o vigia parado na sala de segurança (invencível) e confere
## que nada dá erro e que o Tito e a Pipoca andam pelo mapa.
## Rodar: godot --headless --path godot res://dev/teste_fumaca_v2.tscn

func _ready() -> void:
	var mundo: Node3D = load("res://cenas/mundo_v2.tscn").instantiate()
	mundo.segundos_por_hora = 25.0  # horas curtas: os animatrônicos acordam logo (e a noite não acaba no meio do teste)
	add_child(mundo)
	Jogo.invencivel = true
	Engine.time_scale = 4.0
	var inicio := {}
	for a in get_tree().get_nodes_in_group("animatronico"):
		inicio[a.name] = (a as Node3D).global_position
	var comodos := {}
	for i in 30:
		await get_tree().create_timer(3.0).timeout  # 3 s de jogo (o tempo do jogo está 4x mais rápido)
		for a in get_tree().get_nodes_in_group("animatronico"):
			comodos.get_or_add(a.name, {})[PlantaV2.comodo_em((a as Node3D).global_position)] = true
	var falhas := 0
	for a in get_tree().get_nodes_in_group("animatronico"):
		var andou: float = (a as Node3D).global_position.distance_to(inicio[a.name])
		var visitou: Array = comodos.get(a.name, {}).keys()
		print("[fumaca] %s: andou %.1f m da posição inicial; passou por %s" % [a.name, andou, visitou])
		if visitou.size() < 2:
			falhas += 1
			print("[fumaca] FALHA %s ficou parado num cômodo só" % a.name)
	print("[fumaca] hora final: %d, em partida: %s" % [Jogo.hora, Jogo.em_partida])
	print("[fumaca] %d falha(s)" % falhas)
	Engine.time_scale = 1.0
	get_tree().quit(1 if falhas else 0)
