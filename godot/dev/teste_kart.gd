extends Node
## FERRAMENTA DE DESENVOLVIMENTO: testa a jogabilidade do TITO KART (e do SPACE PIZZA).
##
## Para cada dificuldade:
##   1) "piloto automático": o carrinho do jogador é dirigido pelo piloto do computador (com velocidade de
##      jogador e usando os turbos). Confere o tempo da corrida e se ele vence.
##   2) "jogador parado": ninguém aperta nada; confere que os dois rivais completam as 3 voltas.
##   3) SPACE PIZZA com a nave no automático: quantos pontos faz em 40 s.
## A simulação é feita chamando o laço do minigame com passos de 1/60 s, então uma corrida
## inteira roda em menos de um segundo de verdade.
##
## Rodar:  godot --headless --path godot res://dev/teste_kart.tscn
## Prints: godot --path godot res://dev/teste_kart.tscn -- print   (precisa de janela, sem --headless)

const CENA_KART := "res://cenas/minigames/kart.tscn"
const CENA_SPACE := "res://cenas/minigames/space_pizza.tscn"
const DT := 1.0 / 60.0
const PASTA_IMAGENS := "C:/Users/User/Documents/TurnoDaNoite/docs/progresso/imagens/"

var _falhas := 0
var _camada: CanvasLayer


func _ready() -> void:
	_camada = CanvasLayer.new()
	_camada.layer = 20
	add_child(_camada)
	if "print" in OS.get_cmdline_user_args():
		await _tirar_prints()
		get_tree().quit()
		return

	for nome_dif: String in ["facil", "normal", "pesadelo"]:
		var dif: Dificuldade = load("res://assets/dificuldade/%s.tres" % nome_dif)
		var auto := _correr(dif, true)
		var parado := _correr(dif, false)
		var tempo: float = auto["tempo_jogador"]
		var ger: float = auto["tempo_ger"]
		var rivais_auto: Array = auto["tempos_rivais"]
		var rivais: Array = parado["tempos_rivais"]
		print("[kart] %-8s piloto automático: %.2f s, %dº, venceu=%s | GER %.2f s (folga %.2f s) | grama %.1f s, turbos %d" % [
			nome_dif, tempo, auto["posicao"], auto["venceu"], ger, ger - tempo, auto["tempo_grama"], auto["turbos"]])
		print("[kart] %-8s rivais (jogador parado): PIP %.2f s, BOB %.2f s | na corrida do piloto: %s" % [
			nome_dif, rivais[0], rivais[1], str(rivais_auto)])
		if nome_dif != "pesadelo" and not auto["venceu"]:
			_falhar("%s: o piloto automático deveria vencer" % nome_dif)
		if nome_dif == "normal" and (tempo < 45.0 or tempo > 75.0):
			_falhar("normal: corrida fora de 45–75 s (%.2f)" % tempo)
		for t: float in rivais:
			if t <= 0.0:
				_falhar("%s: um rival não completou as 3 voltas" % nome_dif)

	for nome_dif: String in ["facil", "normal", "pesadelo"]:
		var dif: Dificuldade = load("res://assets/dificuldade/%s.tres" % nome_dif)
		var r := _jogar_space_pizza(dif)
		print("[space_pizza] %-8s nave automática: %d/%d pontos em %.1f s, venceu=%s" % [
			nome_dif, r["pontos"], r["meta"], r["tempo"], r["venceu"]])
		if nome_dif != "pesadelo" and not r["venceu"]:
			_falhar("space_pizza %s: a nave automática deveria vencer" % nome_dif)

	print("[kart] %d falha(s)" % _falhas)
	get_tree().quit(1 if _falhas > 0 else 0)


## Roda uma corrida inteira, simulada. Devolve o resultado_corrida do kart + medições.
func _correr(dif: Dificuldade, automatico: bool) -> Dictionary:
	var kart: Minigame = load(CENA_KART).instantiate()
	_camada.add_child(kart)
	var fim := {"terminou": false, "venceu": false, "resultado": {}}
	kart.terminado.connect(func(v: bool, r: Dictionary) -> void:
		fim["terminou"] = true
		fim["venceu"] = v
		fim["resultado"] = r)
	kart.iniciar(dif, {"codigo": "4712"})
	kart.set("piloto_automatico", automatico)
	kart.set("encerrar_quando_impossivel", automatico)
	if not automatico:
		kart.set("estado", 1)  # pula a tela de recordes (Estado.CONTAGEM)
	var tempo_grama := 0.0
	var turbos := 0
	var tinha_turbo := false
	var resultado := {}
	for i in int(240.0 / DT):
		if fim["terminou"]:
			break
		kart.call("_ao_processar", DT)
		var jogador: Object = kart.get("jogador")
		if int(kart.get("estado")) == 2:  # Estado.CORRIDA
			if jogador.get("na_grama"):
				tempo_grama += DT
			var tem: bool = jogador.get("tem_turbo")
			if tinha_turbo and not tem:
				turbos += 1
			tinha_turbo = tem
		var r: Dictionary = kart.get("resultado_corrida")
		if not r.is_empty():
			resultado = r
	if resultado.is_empty():
		_falhar("a corrida não terminou em 240 s")
		resultado = {"venceu": false, "tempo_jogador": -1.0, "posicao": 3, "tempo_ger": 0.0, "tempos_rivais": [-1.0, -1.0]}
	if not fim["terminou"]:
		_falhar("o kart não chamou finalizar()")
	elif fim["venceu"] != resultado["venceu"]:
		_falhar("finalizar() e resultado_corrida discordam")
	elif fim["venceu"] and fim["resultado"].get("digitos") != "47":
		_falhar("resultado da vitória sem os dígitos certos: " + str(fim["resultado"]))
	resultado = resultado.duplicate()
	resultado["tempo_grama"] = tempo_grama
	resultado["turbos"] = turbos
	if is_instance_valid(kart):
		kart.free()
	return resultado


func _jogar_space_pizza(dif: Dificuldade) -> Dictionary:
	var jogo: Minigame = load(CENA_SPACE).instantiate()
	_camada.add_child(jogo)
	var fim := {"terminou": false, "venceu": false, "resultado": {}}
	jogo.terminado.connect(func(v: bool, r: Dictionary) -> void:
		fim["terminou"] = true
		fim["venceu"] = v
		fim["resultado"] = r)
	jogo.iniciar(dif, {"codigo": "4712"})
	jogo.set("piloto_automatico", true)
	var tempo := 0.0
	var pontos := 0
	for i in int(60.0 / DT):
		if fim["terminou"]:
			break
		jogo.call("_ao_processar", DT)
		if int(jogo.get("estado")) == 1:
			tempo += DT
		pontos = jogo.get("pontos")
	var r := {"pontos": pontos, "meta": jogo.get("meta"), "tempo": tempo, "venceu": fim["venceu"]}
	if fim["venceu"] and fim["resultado"].get("digitos") != "47":
		_falhar("space_pizza: resultado sem os dígitos certos")
	if is_instance_valid(jogo):
		jogo.free()
	return r


## Abre o kart de verdade (em tempo real, numa janela) e salva prints.
func _tirar_prints() -> void:
	var fundo := ColorRect.new()  # imita o mundo escuro atrás da máquina
	fundo.color = Color(0.05, 0.04, 0.06)
	fundo.set_anchors_preset(Control.PRESET_FULL_RECT)
	_camada.add_child(fundo)
	var kart: Minigame = load(CENA_KART).instantiate()
	_camada.add_child(kart)
	kart.iniciar(load("res://assets/dificuldade/normal.tres"), {"codigo": "4712"})
	await get_tree().create_timer(1.5).timeout
	await _salvar(OS.get_user_data_dir() + "/kart_recordes.png")
	kart.set("piloto_automatico", true)
	await get_tree().create_timer(12.0).timeout
	var data := Time.get_datetime_dict_from_system()
	var carimbo := "%04d-%02d-%02d_%02d%02d" % [data.year, data.month, data.day, data.hour, data.minute]
	var nome := carimbo + "_v25_kart.png"
	await _salvar(PASTA_IMAGENS + nome)
	var legenda := {
		"arquivo": nome,
		"fase": "V2.5",
		"horario": "%04d-%02d-%02d %02d:%02d:%02d" % [data.year, data.month, data.day, data.hour, data.minute, data.second],
		"legenda": "V2.5: TITO KART rodando na tela de CRT (piloto automático de teste, dificuldade Normal)",
	}
	var arq := FileAccess.open(PASTA_IMAGENS + nome.replace(".png", ".json"), FileAccess.WRITE)
	arq.store_string(JSON.stringify(legenda, "  ", true))
	arq.close()
	kart.queue_free()
	# Fim da corrida (mensagem de vitória) e SPACE PIZZA, só para conferir.
	var kart2: Minigame = load(CENA_KART).instantiate()
	_camada.add_child(kart2)
	kart2.iniciar(load("res://assets/dificuldade/normal.tres"), {"codigo": "4712"})
	kart2.set("piloto_automatico", true)
	for i in int(70.0 / DT):
		if not is_instance_valid(kart2) or int(kart2.get("estado")) == 3:
			break
		kart2.call("_ao_processar", DT)
	await get_tree().create_timer(0.6).timeout
	await _salvar(OS.get_user_data_dir() + "/kart_fim.png")
	if is_instance_valid(kart2):
		kart2.queue_free()
	var sp: Minigame = load(CENA_SPACE).instantiate()
	_camada.add_child(sp)
	sp.iniciar(load("res://assets/dificuldade/normal.tres"), {"codigo": "4712"})
	await get_tree().create_timer(1.0).timeout
	await _salvar(OS.get_user_data_dir() + "/space_intro.png")
	sp.set("piloto_automatico", true)
	await get_tree().create_timer(8.0).timeout
	await _salvar(OS.get_user_data_dir() + "/space_jogo.png")


func _salvar(caminho: String) -> void:
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(caminho)
	print("[kart] print salvo: ", caminho)


func _falhar(texto: String) -> void:
	_falhas += 1
	print("[kart] FALHA ", texto)
