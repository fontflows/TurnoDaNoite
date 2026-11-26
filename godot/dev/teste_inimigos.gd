extends Node
## FERRAMENTA DE DESENVOLVIMENTO — não entra no build.
## Testa os animatrônicos: Tito congela quando visto e anda quando não é visto;
## Pipoca ouve ruído, persegue quando vê, é atordoada pela lanterna e volta ao palco;
## o susto acontece, a tela de Game Over aparece e "Tentar de novo" reinicia.
## Uso: godot --headless --path . res://dev/teste_inimigos.tscn

var _mundo: Node3D
var _jogador: CharacterBody3D
var _tito: Node3D
var _pipoca: Node3D
var _falhas := 0
var _pego_por := ""


func _ready() -> void:
	Jogo.modo_captura = false
	Jogo.jogador_pego.connect(func(q): _pego_por = q)
	# O mundo vira a "cena atual"; este nó de teste fica fora dela e sobrevive à troca de cena.
	_mundo = load("res://cenas/mundo.tscn").instantiate()
	get_tree().root.add_child.call_deferred(_mundo)
	await get_tree().process_frame
	await get_tree().process_frame
	get_tree().current_scene = _mundo
	await _quadros(60)  # tempo para a navegação sincronizar
	_jogador = get_tree().get_first_node_in_group("jogador")
	_tito = _mundo.get_node("Animatronicos/Tito")
	_pipoca = _mundo.get_node("Animatronicos/Pipoca")
	_jogador.set_physics_process(false)  # o teste posiciona o vigia
	_jogador.lanterna_ligada = false

	# --- Antes da 1 AM ninguém se mexe ---
	var tito_ini := _tito.global_position
	_por_jogador(Vector3(0, 0, 8), Vector3(0, 1, 20))  # longe, de costas para o palco
	await _quadros(90)
	_conferir("antes da 1 AM o Tito fica no palco", _tito.global_position.distance_to(tito_ini) < 0.1)

	# --- Tito: congela quando visto ---
	_pipoca.set_physics_process(false)
	Jogo.hora = 1
	_por_jogador(Vector3(-3, 0, -5), _tito.global_position + Vector3(0, 1.2, 0))  # olhando para ele
	await _quadros(120)
	_conferir("Tito congela enquanto é visto (andou %.2f m)" % _tito.global_position.distance_to(tito_ini),
		_tito.global_position.distance_to(tito_ini) < 0.1 and _tito.visto)
	_por_jogador(Vector3(-3, 0, -5), Vector3(-3, 1.5, 10))  # vira de costas
	await _quadros(90)
	var andou := _tito.global_position.distance_to(tito_ini)
	_conferir("Tito anda quando não é visto (andou %.2f m)" % andou, andou > 0.8)
	_tito.set_physics_process(false)
	_tito.global_position = tito_ini

	# --- Pipoca: ruído -> investiga ---
	_pipoca.set_physics_process(true)
	_por_jogador(Vector3(-15, 0, 7), Vector3(-15, 1.5, 12))  # fliperama, longe dela
	await _quadros(10)
	Jogo.emitir_ruido(_pipoca.global_position + Vector3(0, 0, 4), 10.0)
	await _quadros(5)
	_conferir("Pipoca ouve o ruído e vai investigar", _pipoca.estado == _pipoca.Estado.INVESTIGANDO)

	# --- Pipoca: vê o vigia -> persegue ---
	Jogo.invencivel = true
	_pipoca.global_position = Vector3(3, 0.5, -13)
	_pipoca.rotation.y = 0.0
	_por_jogador(Vector3(3, 0, -4), Vector3(0, 0, -30))  # de frente para ela, lanterna desligada
	_jogador.lanterna_ligada = false
	_jogador.get_node("Cabeca/Camera3D/Lanterna").visible = false
	await _quadros(10)
	_conferir("Pipoca vê o vigia e persegue", _pipoca.estado == _pipoca.Estado.PERSEGUINDO)

	# --- Pipoca: lanterna por 2 s -> atordoada -> volta ao palco ---
	var lanterna: SpotLight3D = _jogador.get_node("Cabeca/Camera3D/Lanterna")
	for i in 170:
		_mirar(_pipoca.global_position + Vector3(0, 1.3, 0))
		_jogador.lanterna_ligada = true
		lanterna.visible = true
		await get_tree().physics_frame
		if _pipoca.estado == _pipoca.Estado.ATORDOADA:
			break
	_conferir("lanterna por ~2 s atordoa a Pipoca", _pipoca.estado == _pipoca.Estado.ATORDOADA)
	await _quadros(110)
	var no_palco: float = _pipoca.global_position.distance_to(Vector3(3, 0.5, -13))
	_conferir("Pipoca atordoada volta para o palco (%.2f m do ponto)" % no_palco, no_palco < 0.6)

	# --- Susto: Tito encosta no vigia de costas ---
	Jogo.invencivel = false
	_pipoca.set_physics_process(false)
	_tito.set_physics_process(true)
	_tito.global_position = Vector3(-3, 0.05, -2)
	_por_jogador(Vector3(-3, 0, 0.2), Vector3(-3, 1.5, 10))  # de costas para o Tito
	_jogador.lanterna_ligada = false
	var espera := 0
	while _pego_por == "" and espera < 400:
		await get_tree().physics_frame
		espera += 1
	_conferir("Tito pega o vigia por trás em %.1f s (pego por '%s')" % [espera / 60.0, _pego_por], _pego_por == "Tito")
	var modelo_na_camera := _jogador.get_node("Cabeca/Camera3D/PontoJumpscare").get_child_count() > 0
	_conferir("modelo do Tito aparece na frente da câmera", modelo_na_camera)
	await _quadros(100)  # 1,2 s de susto
	var cena := get_tree().current_scene
	_conferir("tela de Game Over aparece (%s)" % (cena.name if cena else "nada"), cena != null and cena.name == "GameOver")

	# --- Tentar de novo ---
	Jogo.reiniciar_partida()
	# Passa pela tela de carregamento (mínimo 3 s) até o jogo abrir.
	for i in 900:
		await _quadros(1)
		cena = get_tree().current_scene
		if cena and cena.name == "Mundo":
			break
	await _quadros(20)
	cena = get_tree().current_scene
	_conferir("'Tentar de novo' recomeça a partida (%s, hora %d)" % [cena.name if cena else "nada", Jogo.hora],
		cena != null and cena.name == "Mundo" and Jogo.em_partida and Jogo.hora == 0)

	print("[inimigos] %d falha(s)" % _falhas)
	get_tree().quit(1 if _falhas > 0 else 0)


func _por_jogador(pos: Vector3, olhar_para: Vector3) -> void:
	_jogador.global_position = pos + Vector3(0, 0.05, 0)
	_mirar(olhar_para)


func _mirar(alvo: Vector3) -> void:
	var olho := _jogador.global_position + Vector3(0, 1.6, 0)
	var dir := alvo - olho
	_jogador.rotation = Vector3(0, atan2(-dir.x, -dir.z), 0)
	_jogador.get_node("Cabeca").rotation.x = atan2(dir.y, Vector2(dir.x, dir.z).length())
	_jogador._seguir_lanterna(1.0)  # a lanterna acompanha na hora (o processamento do vigia está desligado no teste)


func _quadros(n: int) -> void:
	for i in n:
		await get_tree().physics_frame


func _conferir(descricao: String, ok: bool) -> void:
	print("[inimigos] ", "ok   " if ok else "FALHA", " ", descricao)
	if not ok:
		_falhas += 1
