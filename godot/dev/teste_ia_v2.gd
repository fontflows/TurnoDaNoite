extends Node
## FERRAMENTA DE DESENVOLVIMENTO: testa a IA da V2.6 no mapa novo, uma situação por vez.
##   visão (em pé, agachado, escondido) · audição · porta destrancada aberta pela Pipoca ·
##   checar esconderijo (respirando e prendendo a respiração) · Tito no escuro x com luz ·
##   gerador (caçada) · diretor de tensão · checkpoint do Fácil.
## Rodar: godot --headless --path godot res://dev/teste_ia_v2.tscn

var _mundo: Node3D
var _jogador: CharacterBody3D
var _tito: Animatronico
var _pipoca: Animatronico
var _prog: ProgressaoV2
var _falhas := 0


func _conferir(ok: bool, texto: String) -> void:
	if not ok:
		_falhas += 1
	print("[ia] %s %s" % ["ok   " if ok else "FALHA", texto])


func _abrir_mundo(dificuldade: int) -> void:
	if _mundo:
		_mundo.queue_free()
		await get_tree().process_frame
	Config.dificuldade = dificuldade
	_mundo = load("res://cenas/mundo_v2.tscn").instantiate()
	add_child(_mundo)
	for i in 20:
		await get_tree().physics_frame
	_jogador = _mundo.get_node("Jogador")
	_tito = _mundo.get_node("Animatronicos/Tito")
	_pipoca = _mundo.get_node("Animatronicos/Pipoca")
	_prog = _mundo.get_node("Montador/ProgressaoV2")
	if Jogo.checkpoint.is_empty():
		Jogo.hora = 2  # todos acordados
	Jogo.invencivel = false


## Coloca alguém num ponto da planta olhando para outro ponto da planta.
func _por(quem: Node3D, x: float, z: float, olhar_x: float, olhar_z: float) -> void:
	quem.global_position = PlantaV2.mundo(x, z, 0.05)
	var d := PlantaV2.mundo(olhar_x, olhar_z) - quem.global_position
	if quem is Animatronico:
		quem.rotation.y = atan2(d.x, d.z)  # frente do animatrônico = +Z
	else:
		quem.rotation.y = atan2(-d.x, -d.z)  # frente do vigia = -Z
	quem.velocity = Vector3.ZERO


func _planta(v: Vector3) -> String:
	return "(%.1f, %.1f)" % [v.x + 30.0, v.z + 22.5]


func _quadros(n: int) -> void:
	for i in n:
		await get_tree().physics_frame


func _ready() -> void:
	Jogo.trocar_cena_ao_terminar = false
	await _abrir_mundo(1)
	_tito.set_physics_process(false)
	_por(_tito, 59, 44, 59, 40)  # Tito fora do caminho (copa)

	# --- Visão da Pipoca (Normal: 14 m em pé, 8,4 m agachado) -----------------
	_jogador.lanterna_ligada = false
	_por(_pipoca, 20, 6, 20, 14)
	_por(_jogador, 20, 13, 20, 6)
	_conferir(_pipoca.ve_jogador(), "Pipoca vê o vigia em pé a 7 m")
	_por(_jogador, 20, 15.5, 20, 6)
	_jogador.agachado = false
	var em_pe: bool = _pipoca.ve_jogador()
	_jogador.agachado = true
	var agachado: bool = _pipoca.ve_jogador()
	_jogador.agachado = false
	_conferir(em_pe and not agachado, "a 9,5 m: em pé ela vê (%s), agachado não (%s)" % [em_pe, agachado])

	# --- Audição -------------------------------------------------------------
	_pipoca.mudar_estado(1)  # patrulhando
	Jogo.emitir_ruido(PlantaV2.mundo(24, 8), 10.0, 0.8)
	_conferir(_pipoca.estado == 2, "barulho a 4 m: Pipoca vai investigar (estado %d)" % _pipoca.estado)
	_pipoca.mudar_estado(1)
	Jogo.emitir_ruido(PlantaV2.mundo(55, 40), 6.0, 0.8)
	_conferir(_pipoca.estado == 1, "barulho longe: Pipoca nem liga")

	# --- Porta: a Pipoca abre a porta de vaivém da cozinha ---------------------
	_por(_jogador, 5, 10, 5, 5)  # vigia longe, na oficina (fora de vista)
	var vaivem: PortaV2 = _prog._portas["cozinha"]
	_conferir(not vaivem.aberta, "porta da cozinha começa fechada")
	_por(_pipoca, 37, 8, 44, 8)
	_pipoca.investigar(PlantaV2.mundo(44, 8))
	var chegou := false
	for i in 600:
		await get_tree().physics_frame
		if PlantaV2.comodo_em(_pipoca.global_position) == "Cozinha":
			chegou = true
			break
	_conferir(vaivem.aberta and chegou, "Pipoca abriu a porta de vaivém e entrou na cozinha (aberta %s, chegou %s, está em %s)" % [
		vaivem.aberta, chegou, PlantaV2.comodo_em(_pipoca.global_position)])

	# --- Esconderijo: ela viu o vigia entrar no armário -------------------------
	var armarios := get_tree().get_nodes_in_group("esconderijo").filter(func(e: Node) -> bool: return e.get_meta("tipo") == "armario")
	var armario: Node3D = armarios[0]
	var ax := armario.global_position.x + 30.0
	var az := armario.global_position.z + 22.5
	_por(_jogador, ax, az, ax - 3, az)
	_por(_pipoca, ax - 5, az, ax, az)
	await _quadros(2)
	_conferir(_pipoca.ve_jogador(), "Pipoca vê o vigia no vestiário")
	_pipoca.mudar_estado(3)
	_pipoca._ultima_vez_viu = _pipoca._agora()
	_prog.esconder(armario)
	var pego := false
	Jogo.em_partida = true
	for i in 400:
		await get_tree().physics_frame
		if not Jogo.em_partida:
			pego = true
			break
	_conferir(pego and Jogo.quem_pegou == _pipoca.nome_exibicao, "respirando no armário que ela viu: foi pego (quem: '%s')" % Jogo.quem_pegou)

	# Prendendo a respiração no Fácil (chance 15%): na maioria das vezes ela não acha.
	var escapou := 0
	for tentativa in 6:
		await _abrir_mundo(0)
		_tito.set_physics_process(false)
		_por(_tito, 59, 44, 59, 40)
		armario = get_tree().get_nodes_in_group("esconderijo").filter(func(e: Node) -> bool: return e.get_meta("tipo") == "armario")[0]
		_por(_jogador, ax, az, ax - 3, az)
		_prog.esconder(armario)
		Input.action_press("prender_respiracao")
		_pipoca._checar(armario)
		_por(_pipoca, ax - 4, az, ax, az)
		Jogo.em_partida = true
		var pego2 := false
		for i in 300:
			await get_tree().physics_frame
			if not Jogo.em_partida:
				pego2 = true
				break
			if _pipoca.estado != 5:
				break
		Input.action_release("prender_respiracao")
		if not pego2:
			escapou += 1
	_conferir(escapou >= 3, "prendendo a respiração no Fácil: escapou %d de 6" % escapou)

	# --- Tito: no escuro ele anda mesmo olhado; com a lanterna nele, congela ----
	await _abrir_mundo(1)
	_pipoca.set_physics_process(false)
	_por(_pipoca, 59, 44, 59, 40)
	Jogo.em_partida = true
	_por(_jogador, 22, 26, 22, 34)    # fliperama, olhando para o sul
	_por(_tito, 22, 33, 22, 26)       # 7 m na frente, no escuro
	_jogador.lanterna_ligada = false
	_jogador._atualizar_lanterna(0.0)
	var antes := _tito.global_position
	await _quadros(40)
	var andou_escuro := _tito.global_position.distance_to(antes)
	_jogador.lanterna_ligada = true
	_jogador.bateria = 100.0
	_jogador._atualizar_lanterna(0.0)
	_jogador._seguir_lanterna(1.0)
	await _quadros(3)
	antes = _tito.global_position
	await _quadros(40)
	var andou_luz := _tito.global_position.distance_to(antes)
	_conferir(andou_escuro > 0.5 and andou_luz < 0.05, "Tito anda no escuro mesmo sendo olhado (%.2f m) e congela na lanterna (%.2f m)" % [andou_escuro, andou_luz])

	# --- Gerador: a Pipoca caça o vigia sem precisar ver ----------------------
	_tito.set_physics_process(false)
	_pipoca.set_physics_process(true)
	_por(_pipoca, 20, 6, 20, 0)       # de costas, longe
	_por(_jogador, 50, 38, 50, 40)
	_pipoca.mudar_estado(1)
	Jogo.ligar_gerador()
	await _quadros(5)
	_conferir(_pipoca.estado == 3, "gerador ligado: Pipoca persegue sem ver (estado %d)" % _pipoca.estado)

	# --- Diretor de tensão ------------------------------------------------------
	await _abrir_mundo(2)
	Jogo.em_partida = true
	_tito.set_physics_process(false)
	_por(_pipoca, 5, 40, 5, 44)
	_pipoca.mudar_estado(1)
	_por(_jogador, 55, 40, 55, 44)
	var diretor: DiretorTensao = _prog.get_node("DiretorTensao")
	diretor.tempo_calmo = 1000.0
	await get_tree().create_timer(1.5).timeout
	var alvo: Vector3 = _pipoca._alvo_ruido
	_conferir(_pipoca.estado == 2 and alvo.distance_to(_jogador.global_position) < 10.0,
		"diretor (calmo demais no Pesadelo): Pipoca foi investigar a %.1f m do vigia" % alvo.distance_to(_jogador.global_position))

	# --- Checkpoint do Fácil -----------------------------------------------------
	await _abrir_mundo(0)
	Jogo.em_partida = true
	var codigo := Jogo.codigo
	Jogo.hora = 3
	Jogo.dar_item("chave_gerente")
	var dc := _mundo.get_node("Disjuntores/Disjuntor_Cozinha")
	dc.consertado = true
	dc.ligar()
	_conferir(not Jogo.checkpoint.is_empty(), "Fácil: checkpoint salvo ao religar o disjuntor")
	await _abrir_mundo(0)   # como o "Tentar de novo"
	await _quadros(5)
	dc = _mundo.get_node("Disjuntores/Disjuntor_Cozinha")
	_conferir(dc.ligado and Jogo.tem_item("chave_gerente") and Jogo.codigo == codigo and Jogo.hora == 3,
		"Fácil: recomeçou do checkpoint (disjuntor %s, chave %s, mesma senha %s, hora %d)" % [dc.ligado, Jogo.tem_item("chave_gerente"), Jogo.codigo == codigo, Jogo.hora])
	Jogo.checkpoint = {}

	print("[ia] %d falha(s)" % _falhas)
	Jogo.trocar_cena_ao_terminar = true
	Config.dificuldade = 1
	get_tree().quit(1 if _falhas else 0)
