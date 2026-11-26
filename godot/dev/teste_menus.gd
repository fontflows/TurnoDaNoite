extends Node
## FERRAMENTA DE DESENVOLVIMENTO — não entra no build.
## Testa o fluxo completo das telas: menu -> intro -> jogo -> pausa -> vitória -> menu
## -> jogo -> derrota -> "Tentar de novo". Também confere se os sons de loop repetem.
## Uso: godot --headless --path . res://dev/teste_menus.tscn

const SONS_EM_LOOP := ["ambiente_grave", "zumbido_lampada", "estatica", "pipoca_chiado", "musica_pizzaria"]

var _falhas := 0


func _ready() -> void:
	for nome in SONS_EM_LOOP:
		var som := load("res://assets/sons/%s.wav" % nome) as AudioStreamWAV
		_conferir("som '%s' repete (loop)" % nome, som != null and som.loop_mode != AudioStreamWAV.LOOP_DISABLED)

	# Nenhum texto visível pode usar a fonte padrão do Godot (regra da V2).
	for caminho in ["res://ui/aviso_fones.tscn", "res://ui/menu_principal.tscn", "res://ui/intro.tscn",
			"res://ui/opcoes.tscn", "res://ui/controles.tscn", "res://ui/pausa.tscn", "res://ui/hud.tscn",
			"res://ui/game_over.tscn", "res://ui/vitoria.tscn", "res://cenas/objetos/monitor_cameras.tscn"]:
		var tela: Node = load(caminho).instantiate()
		add_child(tela)
		await _quadros(2)
		var com_padrao := []
		for c in tela.find_children("*", "Control", true, false):
			if (c is Label or c is Button) and c.get_theme_font("font") == ThemeDB.fallback_font:
				com_padrao.append(String(c.name))
		_conferir("%s sem fonte padrão %s" % [caminho.get_file(), com_padrao if com_padrao else ""], com_padrao.is_empty())
		tela.queue_free()
		await _quadros(2)

	# F11 alterna a tela cheia (no modo sem janela só muda a opção, mas a lógica é a mesma).
	var modo_antes := Config.modo_janela
	await _acao("tela_cheia")
	_conferir("F11 alterna a tela cheia", Config.modo_janela != modo_antes)
	await _acao("tela_cheia")
	_conferir("F11 de novo volta para janela", Config.modo_janela == modo_antes)

	# O menu vira a cena atual; este nó fica fora dela e sobrevive às trocas de cena.
	var menu: Node = load("res://ui/menu_principal.tscn").instantiate()
	get_tree().root.add_child.call_deferred(menu)
	await get_tree().process_frame
	await get_tree().process_frame
	get_tree().current_scene = menu
	await _quadros(10)
	var nome_menu := String(menu.name)
	_conferir("menu abriu", _cena() == nome_menu)

	menu.get_node("%BotaoJogar").pressed.emit()
	await _quadros(5)
	_conferir("Jogar abre a escolha de dificuldade", menu._painel_dificuldade.visible)
	menu._botoes_nivel[1].pressed.emit()  # Normal
	await _quadros(10)
	_conferir("dificuldade Normal carregada (%s)" % Jogo.dificuldade.nome if Jogo.dificuldade else "nenhuma", Config.dificuldade == 1)
	_conferir("Jogar -> intro (%s)" % _cena(), _cena().to_lower().contains("intro"))
	await _tecla()  # completa o texto
	await _quadros(5)
	await _tecla()  # pula para o jogo
	await _quadros(10)
	_conferir("intro -> tela de carregamento (%s)" % _cena(), _cena() == "Carregamento")
	for i in 900:  # carregamento: no mínimo 3 s e até o mapa ficar pronto
		await _quadros(1)
		if _cena() == "Mundo":
			break
	await _quadros(30)
	_conferir("carregamento -> jogo (%s)" % _cena(), _cena() == "Mundo")
	_conferir("partida rodando", Jogo.em_partida)

	await _acao("pausar")
	await _quadros(5)
	_conferir("ESC pausa o jogo", get_tree().paused)
	await _acao("pausar")
	await _quadros(5)
	_conferir("ESC de novo continua", not get_tree().paused)

	# Monitor: E abre, ESC fecha sem abrir a pausa.
	var monitor := get_tree().current_scene.get_node("MonitorCameras")
	var jogador := get_tree().get_first_node_in_group("jogador")
	monitor.interagir(jogador)
	await _quadros(5)
	_conferir("monitor abre e o tempo continua", monitor.usando and Jogo.em_partida)
	var hora_antes := Jogo.tempo_na_hora
	await _quadros(30)
	_conferir("o relógio anda com o monitor aberto", Jogo.tempo_na_hora > hora_antes)
	await _acao("trocar_camera")
	await _acao("pausar")
	await _quadros(5)
	_conferir("ESC fecha o monitor sem pausar", not monitor.usando and not get_tree().paused and not jogador.travado)

	# Vitória
	Jogo.ia_ativa = false
	for d in get_tree().get_nodes_in_group("disjuntor"):
		d.ligar()
	if Jogo.usa_gerador:
		# Mapa da V2: depois dos disjuntores, o gerador e a porta de aço fechada.
		Jogo.ligar_gerador()
		var prog := get_tree().get_first_node_in_group("progressao_v2")
		prog._portas["seguranca"].alternar()
		Jogo.mudar_porta_seguranca(true)
		jogador.global_position = get_tree().get_first_node_in_group("mundo").get_node("Marcadores/SpawnJogador").global_position
	else:
		jogador.global_position = Vector3(5.5, 0.05, 6.5)
	await _segundos(2.0)
	_conferir("vitória -> tela de vitória (%s)" % _cena(), _cena() == "Vitoria")
	get_tree().current_scene.get_node("%BotaoMenu").pressed.emit()
	await _quadros(20)
	_conferir("vitória -> menu (%s)" % _cena(), _cena() == nome_menu)

	# Derrota e "Tentar de novo"
	var menu2 := get_tree().current_scene
	menu2.get_node("%BotaoJogar").pressed.emit()
	await _quadros(5)
	menu2._botoes_nivel[2].pressed.emit()  # Pesadelo
	await _quadros(10)
	await _tecla()
	await _quadros(5)
	await _tecla()
	await _esperar_mundo()
	Jogo.perder("tempo")
	await _segundos(1.5)
	_conferir("derrota -> Game Over (%s)" % _cena(), _cena() == "GameOver")
	get_tree().current_scene.get_node("%BotaoDeNovo").pressed.emit()
	await _esperar_mundo()
	_conferir("Tentar de novo -> jogo (%s)" % _cena(), _cena() == "Mundo" and Jogo.em_partida)

	# O teste não pode deixar a escolha dele salva nas opções reais do jogador.
	Config.dificuldade = Config.Nivel.NORMAL
	Config.salvar()
	print("[menus] %d falha(s)" % _falhas)
	get_tree().quit(1 if _falhas > 0 else 0)


func _cena() -> String:
	var c := get_tree().current_scene
	return String(c.name) if c else "(nenhuma)"


func _tecla() -> void:
	var ev := InputEventKey.new()
	ev.keycode = KEY_SPACE
	ev.physical_keycode = KEY_SPACE
	ev.pressed = true
	Input.parse_input_event(ev)
	await _quadros(2)
	ev = ev.duplicate()
	ev.pressed = false
	Input.parse_input_event(ev)
	await _quadros(2)


func _acao(nome: String) -> void:
	var ev := InputEventAction.new()
	ev.action = nome
	ev.pressed = true
	Input.parse_input_event(ev)
	await _quadros(2)
	ev = InputEventAction.new()
	ev.action = nome
	ev.pressed = false
	Input.parse_input_event(ev)
	await _quadros(2)


func _segundos(s: float) -> void:
	await get_tree().create_timer(s, true).timeout


func _quadros(n: int) -> void:
	for i in n:
		await get_tree().process_frame


func _conferir(descricao: String, ok: bool) -> void:
	print("[menus] ", "ok   " if ok else "FALHA", " ", descricao)
	if not ok:
		_falhas += 1


## Espera a tela de carregamento entregar o jogo (no máximo ~15 s).
func _esperar_mundo() -> void:
	for i in 900:
		await _quadros(1)
		if _cena() == "Mundo":
			break
	await _quadros(30)
