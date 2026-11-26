extends Node
## FERRAMENTA DE DESENVOLVIMENTO: mede o volume (pico) de cada áudio externo (WAV, MP3 ou OGG) tocando
## o arquivo num barramento com captura, e grava o ganho que falta para chegar no volume-alvo em
## godot/assets/audio_externo/volumes.json. O jogo aplica esse ganho sozinho (SomExterno.carregar).
## É assim que os MP3 ficam no mesmo volume que o resto (o Python não lê MP3 sem programas extras).
## Rodar: godot --headless --path godot res://dev/medir_audio_externo.tscn   (o verificar_audio.py chama sozinho)

const PASTA := "res://assets/audio_externo/"
const SAIDA := "res://assets/audio_externo/volumes.json"
## Volume-alvo do pico (dB). Os loops ficam mais baixos (tocam por muito tempo).
const ALVO := -3.0
const ALVO_LOOP := -9.0
## Toca mais rápido para medir (o pico quase não muda com a velocidade).
const VELOCIDADE := 4.0

var _captura: AudioEffectCapture
var _barramento := -1


func _ready() -> void:
	AudioServer.add_bus()
	_barramento = AudioServer.bus_count - 1
	AudioServer.set_bus_name(_barramento, &"Medidor")
	_captura = AudioEffectCapture.new()
	_captura.buffer_length = 0.5
	AudioServer.add_bus_effect(_barramento, _captura)
	AudioServer.set_bus_mute(_barramento, false)
	var volumes := {}
	var arquivos := _listar(PASTA)
	print("[medir] %d arquivo(s) de áudio externo" % arquivos.size())
	for caminho in arquivos:
		var stream := load(caminho) as AudioStream
		if stream == null:
			continue
		var pico := await _medir(stream)
		if pico <= 0.00001:
			print("[medir] %s: sem som medido (driver de áudio parado?)" % caminho)
			continue
		var pico_db := linear_to_db(pico)
		var alvo := ALVO_LOOP if caminho.get_file().contains("_loop") else ALVO
		var ganho := clampf(alvo - pico_db, -24.0, 24.0)
		volumes[caminho.trim_prefix(PASTA)] = snappedf(ganho, 0.1)
		print("[medir] %s: pico %.1f dB -> ganho %+.1f dB" % [caminho.trim_prefix(PASTA), pico_db, ganho])
	var arq := FileAccess.open(SAIDA, FileAccess.WRITE)
	arq.store_string(JSON.stringify(volumes, "  "))
	arq.close()
	print("[medir] gravado %s (%d volumes)" % [SAIDA, volumes.size()])
	get_tree().quit()


func _listar(pasta: String) -> Array[String]:
	var lista: Array[String] = []
	var dir := DirAccess.open(pasta)
	if dir == null:
		return lista
	for sub in dir.get_directories():
		lista.append_array(_listar(pasta + sub + "/"))
	for f in dir.get_files():
		var ext := f.get_extension().to_lower()
		if ext in ["wav", "mp3", "ogg"]:
			lista.append(pasta + f)
	return lista


func _medir(stream: AudioStream) -> float:
	var p := AudioStreamPlayer.new()
	p.stream = stream
	p.bus = &"Medidor"
	p.pitch_scale = VELOCIDADE
	add_child(p)
	_captura.clear_buffer()
	p.play()
	var pico := 0.0
	var limite := Time.get_ticks_msec() + int(stream.get_length() / VELOCIDADE * 1000.0) + 1500
	while Time.get_ticks_msec() < limite:
		await get_tree().process_frame
		var n := _captura.get_frames_available()
		if n > 0:
			for quadro in _captura.get_buffer(n):
				pico = maxf(pico, maxf(absf(quadro.x), absf(quadro.y)))
		if not p.playing and _captura.get_frames_available() == 0:
			break
	p.queue_free()
	return pico
