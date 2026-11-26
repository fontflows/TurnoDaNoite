extends Node
## FERRAMENTA DE DESENVOLVIMENTO: o "DETONADO" da partida em prints, para a página de progresso.
## Para cada passo do caminho crítico (Fácil): põe o jogo no estado daquele passo, fotografa o vigia
## olhando para o alvo (com o painel de objetivo) e depois o mapa (M) com a marcação.
## No fim, fotografa a vista de dentro de cada tipo de esconderijo.
## Rodar (com janela): godot --path godot res://dev/captura_detonado.tscn

var _mundo: Node3D
var _jogador: CharacterBody3D
var _prog: ProgressaoV2
var _carimbo := ""


func _ready() -> void:
	var t := Time.get_datetime_dict_from_system()
	_carimbo = "%04d-%02d-%02d_%02d%02d" % [t.year, t.month, t.day, t.hour, t.minute]
	Config.dificuldade = 0
	Jogo.trocar_cena_ao_terminar = false
	Jogo.modo_captura = true
	_mundo = load("res://cenas/mundo_v2.tscn").instantiate()
	_mundo.get_node("Montador").codigo_fixo = "4752"
	add_child(_mundo)
	await _quadros(40)
	_jogador = _mundo.get_node("Jogador")
	_prog = _mundo.get_node("Montador/ProgressaoV2")
	Jogo.em_partida = true
	Jogo.ia_ativa = false
	_jogador.set_physics_process(false)
	_jogador.lanterna_ligada = true
	for c in ["Sala_Seguranca", "Corredor_Funcionarios", "Corredor_Principal", "Cozinha", "Salao", "Fliperama"]:
		Jogo.comodos_visitados[c] = true
	var passos := [
		["01", "Começo: o painel de objetivo já diz o primeiro passo (disjuntor da cozinha)", func() -> void: pass],
		["02", "Cozinha religada: o objetivo aponta a máquina de garra (a música dela guia até o fliperama)", func() -> void: _ligar("Cozinha")],
		["03", "Com a chave: abrir a sala do gerente e trocar o fusível", func() -> void: Jogo.dar_item("chave_gerente")],
		["04", "Gerente religado e bilhete lido: falta o recorde do TITO KART", func() -> void:
			_ligar("Gerente")
			Jogo.revelar_digitos(2, 2)
			Jogo.anotar("Bilhete do gerente (senha)", "Os 2 últimos números = 52.")],
		["05", "Senha completa: falta o alicate — entrar pelo duto da sala dos Piratas", func() -> void:
			Jogo.revelar_digitos(0, 2)
			Jogo.anotar("Recorde do TITO KART", "A senha começa com 47.")],
		["06", "Dentro da oficina: o alicate brilha na bancada", func() -> void:
			_jogador.global_position = PlantaV2.mundo(8, 6)
			_prog._marcar_visitado()],
		["07", "Com o alicate: cortar a corrente do depósito", func() -> void: Jogo.dar_item("alicate")],
		["08", "Depósito religado: digitar a senha no teclado da sala elétrica", func() -> void: _ligar("Deposito")],
		["09", "Sala elétrica religada: ligar o gerador", func() -> void:
			_prog._portas["eletrica"].destrancar()
			_ligar("Eletrica")],
		["10", "Gerador ligado: correr e fechar a porta de aço", func() -> void: Jogo.ligar_gerador()],
	]
	if OS.get_cmdline_user_args().has("so_esconderijos"):
		passos = []
	for p in passos:
		p[2].call()
		await _quadros(5)
		await _fotografar_passo(p[0], p[1])
	await _fotografar_esconderijos()
	Config.dificuldade = 1
	Jogo.trocar_cena_ao_terminar = true
	get_tree().quit()


func _quadros(n: int) -> void:
	for i in n:
		await get_tree().process_frame


func _ligar(area: String) -> void:
	var d := _mundo.get_node("Disjuntores/Disjuntor_" + area)
	d.consertado = true
	d.ligar()


## O vigia a ~2,5 m do alvo, olhando para ele; print com o HUD; depois o mapa aberto.
func _fotografar_passo(numero: String, legenda: String) -> void:
	var o := Jogo.objetivo_estruturado()
	var alvo: Variant = _prog.posicao_alvo(o["alvo"])
	if alvo != null:
		var a: Vector3 = alvo
		var mapa: RID = _mundo.get_node("Navegacao").get_navigation_map()
		var perto := NavigationServer3D.map_get_closest_point(mapa, a)
		var de := NavigationServer3D.map_get_closest_point(mapa, perto + (PlantaV2.mundo(30, 22.5) - perto).normalized() * 2.5)
		_jogador.global_position = de + Vector3(0, 0.05, 0)
		var d := a + Vector3(0, 0.6, 0) - (de + Vector3(0, 1.6, 0))
		_jogador.rotation.y = atan2(-d.x, -d.z)
		_jogador.get_node("Cabeca").rotation.x = clampf(atan2(d.y, Vector2(d.x, d.z).length()), -0.6, 0.4)
		_jogador._seguir_lanterna(1.0)
		_prog._marcar_visitado()
	var hud := _mundo.get_node("HUD")
	hud._atualizar_objetivo(true)
	await _quadros(40)
	_salvar("v29_detonado_%s_jogo" % numero, "Detonado %s — %s" % [numero, legenda])
	var mapa_tela := _prog.get_node_or_null("MapaVigia")
	if mapa_tela:
		_jogador.travado = false
		mapa_tela.abrir()
		await _quadros(30)
		_salvar("v29_detonado_%s_mapa" % numero, "Detonado %s — mapa (M) no Fácil: o X vermelho marca o próximo passo" % numero)
		mapa_tela.fechar()
		get_tree().paused = false
		await _quadros(5)


func _fotografar_esconderijos() -> void:
	var feitos := {}
	for m in get_tree().get_nodes_in_group("esconderijo"):
		var tipo := String(m.get_meta("tipo", ""))
		if not ProgressaoV2.ESCONDERIJOS.has(tipo) or feitos.has(tipo):
			continue
		feitos[tipo] = true
		await _prog.esconder(m)
		await _quadros(45)
		_salvar("v29_esconderijo_%s" % tipo, "V2.2: escondido (%s) — vista de dentro, máscara do tipo, 'ESCONDIDO' na tela" % tipo.replace("_", " "))
		_prog.sair_do_esconderijo()
		await _quadros(10)


func _salvar(nome: String, legenda: String) -> void:
	var pasta := ProjectSettings.globalize_path("res://").path_join("../docs/progresso/imagens").simplify_path()
	var base := "%s_%s" % [_carimbo, nome]
	var imagem := get_viewport().get_texture().get_image()
	imagem.save_png(pasta.path_join(base + ".png"))
	var t := Time.get_datetime_dict_from_system()
	var dados := {"arquivo": base + ".png", "legenda": legenda, "fase": "V2.9",
		"horario": "%04d-%02d-%02d %02d:%02d:%02d" % [t.year, t.month, t.day, t.hour, t.minute, t.second]}
	var arq := FileAccess.open(pasta.path_join(base + ".json"), FileAccess.WRITE)
	arq.store_string(JSON.stringify(dados, "  "))
	arq.close()
	print("[detonado] ", base)
