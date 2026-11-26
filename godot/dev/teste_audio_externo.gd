extends Node
## FERRAMENTA DE DESENVOLVIMENTO: confere se os áudios externos (docs/PROMPTS_AUDIO.md) entraram no jogo:
## sequência da voz do gerente com legendas, passos por piso, respirações, animatrônicos, volume medido e loops.
## Rodar: godot --headless --path godot res://dev/teste_audio_externo.tscn

var _falhas := 0


func _conferir(ok: bool, texto: String) -> void:
	if not ok:
		_falhas += 1
	print("[audio] %s %s" % ["ok   " if ok else "FALHA", texto])


func _ready() -> void:
	Jogo.trocar_cena_ao_terminar = false
	var mundo: Node3D = load("res://cenas/mundo_v2.tscn").instantiate()
	add_child(mundo)
	for i in 20:
		await get_tree().physics_frame
	var prog: ProgressaoV2 = mundo.get_node("Montador/ProgressaoV2")
	var jogador = mundo.get_node("Jogador")
	_conferir(prog._fila_vozes.size() >= 11, "voz do gerente: %d falas externas na fila" % prog._fila_vozes.size())
	_conferir(prog._recado.bus == &"Secretaria", "voz passa pelo filtro de secretária (barramento %s)" % prog._recado.bus)
	prog.tocar_recado()
	for i in 30:
		await get_tree().process_frame
	var legenda: String = prog._rotulo_legenda.text if prog._rotulo_legenda else ""
	_conferir(legenda.begins_with("GERENTE: Alô?"), "legenda acompanha a 1ª fala: '%s'" % legenda)
	prog.parar_recado()
	_conferir(jogador._passos_externos.size() == 5, "passos externos para %d pisos" % jogador._passos_externos.size())
	_conferir(not jogador._resp_ofegante.is_empty() and not jogador._resp_segurando.is_empty() and not jogador._resp_soltando.is_empty()
		and not jogador._resp_recuperando.is_empty(), "respirações externas carregadas")
	_conferir(SomExterno.variacoes("res://assets/audio_externo/efeitos/tito_passo").size() == 3, "Tito com 3 passos diferentes")
	var servo: AudioStream = mundo.get_node("Animatronicos/Pipoca").som_chiado.stream
	_conferir(servo is AudioStreamSynchronized or servo is AudioStreamMP3, "servo da Pipoca é o externo (%s)" % servo.get_class())
	var resp := SomExterno.efeito("resp_escondido_loop")
	_conferir(resp is AudioStreamSynchronized, "volume medido aplicado (respiração escondido ganhou ganho)")
	var mp3 := (resp as AudioStreamSynchronized).get_sync_stream(0) as AudioStreamMP3 if resp is AudioStreamSynchronized else null
	_conferir(mp3 != null and mp3.loop, "arquivo _loop repete sozinho")
	print("[audio] %d falha(s)" % _falhas)
	Jogo.trocar_cena_ao_terminar = true
	get_tree().quit(1 if _falhas else 0)
