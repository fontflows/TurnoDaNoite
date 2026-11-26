class_name SomExterno
extends RefCounted
## Troca de sons pelos arquivos externos (docs/PROMPTS_AUDIO.md), do mesmo jeito das artes:
## se existir godot/assets/audio_externo/<pasta>/<nome>.wav (ou .mp3/.ogg), ele é usado;
## senão, fica o som atual feito por código. Nunca quebra.

const EXTENSOES := ["wav", "mp3", "ogg"]


## base: caminho SEM extensão (ex.: "res://assets/audio_externo/efeitos/jumpscare").
## Devolve o arquivo externo se existir; senão o reserva (se existir); senão "".
static func caminho(base: String, reserva := "") -> String:
	for ext in EXTENSOES:
		if ResourceLoader.exists(base + "." + ext):
			return base + "." + ext
	if reserva != "" and ResourceLoader.exists(reserva):
		return reserva
	return ""


## Carrega o som externo (ou o reserva). null se nenhum existir.
## Arquivos externos ganham o ajuste de volume medido por dev/medir_audio_externo.tscn
## (volumes.json) e, se o nome terminar em "_loop", passam a repetir sozinhos.
static func carregar(base: String, reserva := "") -> AudioStream:
	var c := caminho(base, reserva)
	if c == "":
		return null
	var s := load(c) as AudioStream
	if s == null or not c.begins_with(PASTA):
		return s
	if c.get_file().get_basename().ends_with("_loop"):
		_ligar_loop(s)
	var ganho := float(_volumes().get(c.trim_prefix(PASTA), 0.0))
	if absf(ganho) < 0.5:
		return s
	# Um "sincronizado" com um stream só é o jeito de dar um volume fixo para um AudioStream.
	var com_volume := AudioStreamSynchronized.new()
	com_volume.stream_count = 1
	com_volume.set_sync_stream(0, s)
	com_volume.set_sync_stream_volume(0, ganho)
	return com_volume


const PASTA := "res://assets/audio_externo/"
static var _cache_volumes := {}
static var _volumes_lidos := false


static func _volumes() -> Dictionary:
	if not _volumes_lidos:
		_volumes_lidos = true
		if FileAccess.file_exists(PASTA + "volumes.json"):
			var d: Variant = JSON.parse_string(FileAccess.get_file_as_string(PASTA + "volumes.json"))
			if d is Dictionary:
				_cache_volumes = d
	return _cache_volumes


static func _ligar_loop(s: AudioStream) -> void:
	if s is AudioStreamWAV:
		var w := s as AudioStreamWAV
		if w.loop_mode == AudioStreamWAV.LOOP_DISABLED:
			w.loop_mode = AudioStreamWAV.LOOP_FORWARD
			w.loop_begin = 0
			w.loop_end = int(w.get_length() * w.mix_rate)
	elif s is AudioStreamMP3:
		(s as AudioStreamMP3).loop = true
	elif s is AudioStreamOggVorbis:
		(s as AudioStreamOggVorbis).loop = true


## Atalho para os efeitos: SomExterno.efeito("jumpscare", "res://assets/sons/jumpscare.wav").
static func efeito(nome: String, reserva := "") -> AudioStream:
	return carregar("res://assets/audio_externo/efeitos/" + nome, reserva)


## Todas as variações existentes (nome_01, nome_02...). Vazio se nenhuma.
## Também aceita o arquivo sem número (ex.: passo_azulejo.mp3) como uma variação.
static func variacoes(base: String, maximo := 5) -> Array[AudioStream]:
	var lista: Array[AudioStream] = []
	var sem_numero := carregar(base)
	if sem_numero:
		lista.append(sem_numero)
	for i in range(1, maximo + 1):
		var s := carregar("%s_%02d" % [base, i])
		if s:
			lista.append(s)
	return lista
