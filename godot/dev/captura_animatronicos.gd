extends Node
## FERRAMENTA DE DESENVOLVIMENTO: prints dos animatrônicos finais DENTRO do jogo (página de progresso).
## Modo observação ligado: eles patrulham de verdade e o vigia fica de frente para cada um, com a lanterna.
## No fim, um jumpscare de verdade (modo observação desligado).
## Rodar (com janela): godot --path godot res://dev/captura_animatronicos.tscn

var _mundo: Node3D
var _jogador: CharacterBody3D
var _carimbo := ""


func _ready() -> void:
	var t := Time.get_datetime_dict_from_system()
	_carimbo = "%04d-%02d-%02d_%02d%02d" % [t.year, t.month, t.day, t.hour, t.minute]
	Config.dificuldade = 1
	Jogo.trocar_cena_ao_terminar = false
	Jogo.modo_captura = true
	_mundo = load("res://cenas/mundo_v2.tscn").instantiate()
	add_child(_mundo)
	await _quadros(40)
	_jogador = _mundo.get_node("Jogador")
	Jogo.em_partida = true
	Jogo.ia_ativa = true
	Jogo.hora = 2
	Jogo.modo_observacao = true
	Jogo.invencivel = true
	_jogador.set_physics_process(false)
	_jogador.lanterna_ligada = true
	var tito: Animatronico = _mundo.get_node("Animatronicos/Tito")
	var pipoca: Animatronico = _mundo.get_node("Animatronicos/Pipoca")
	tito.global_position = PlantaV2.mundo(26, 10, 0.05)
	pipoca.global_position = PlantaV2.mundo(33, 12, 0.05)
	await _quadros(150)
	await _foto_de(pipoca, 2.8, "anim_jogo_pipoca", "No jogo (modo observação): Pipoca patrulhando o salão, vista com a lanterna")
	await _foto_de(tito, 2.6, "anim_jogo_tito", "No jogo (modo observação): Tito andando pelo salão, visto com a lanterna")
	Jogo._alternar_luz_debug()
	await _foto_de(pipoca, 3.2, "anim_jogo_pipoca_luz", "No jogo, com a luz de depuração (F8): Pipoca andando — orelhas e saia balançando")
	await _foto_de(tito, 3.0, "anim_jogo_tito_luz", "No jogo, com a luz de depuração (F8): Tito andando")
	Jogo._alternar_luz_debug()
	# Jumpscare de verdade
	Jogo.modo_observacao = false
	Jogo.invencivel = false
	tito.set_physics_process(false)
	tito.global_position = PlantaV2.mundo(5, 40, 0.05)
	pipoca.global_position = _jogador.global_position + (-_jogador.global_transform.basis.z) * 0.8
	pipoca.pegar()
	await get_tree().create_timer(0.45).timeout
	_salvar("anim_jogo_jumpscare", "No jogo: jumpscare da Pipoca (animação 'jumpscare' na frente da câmera)")
	await get_tree().create_timer(0.5).timeout
	Config.dificuldade = 1
	Jogo.trocar_cena_ao_terminar = true
	Jogo.modo_observacao = false
	get_tree().quit()


func _quadros(n: int) -> void:
	for i in n:
		await get_tree().process_frame


## Põe o vigia a 'dist' metros na frente do animatrônico, olhando para o peito dele, por alguns quadros.
func _foto_de(quem: Animatronico, dist: float, nome: String, legenda: String) -> void:
	for i in 40:
		var frente := quem.global_transform.basis.z
		frente.y = 0.0
		frente = frente.normalized()
		var de := quem.global_position + frente * dist
		_jogador.global_position = de
		var d := quem.global_position + Vector3(0, 1.15, 0) - (de + Vector3(0, 1.6, 0))
		_jogador.rotation.y = atan2(-d.x, -d.z)
		_jogador.get_node("Cabeca").rotation.x = clampf(atan2(d.y, Vector2(d.x, d.z).length()), -0.6, 0.4)
		_jogador._seguir_lanterna(1.0)
		await get_tree().process_frame
	_salvar(nome, legenda)


func _salvar(nome: String, legenda: String) -> void:
	var pasta := ProjectSettings.globalize_path("res://").path_join("../docs/progresso/imagens").simplify_path()
	var base := "%s_%s" % [_carimbo, nome]
	var imagem := get_viewport().get_texture().get_image()
	imagem.save_jpg(pasta.path_join(base + ".jpg"), 0.9)
	var t := Time.get_datetime_dict_from_system()
	var dados := {"arquivo": base + ".jpg", "legenda": legenda, "fase": "AF3",
		"horario": "%04d-%02d-%02d %02d:%02d:%02d" % [t.year, t.month, t.day, t.hour, t.minute, t.second]}
	var arq := FileAccess.open(pasta.path_join(base + ".json"), FileAccess.WRITE)
	arq.store_string(JSON.stringify(dados, "  "))
	arq.close()
	print("[captura] ", base)
