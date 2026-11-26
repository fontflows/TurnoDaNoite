class_name CapaMenu
extends ColorRect
## Capa do menu principal com duas versões: a FOFA (ARTE-10, menu_fundo) e a SOMBRIA
## (ARTE-25, menu_fundo_sombrio). De tempos em tempos a "fita VHS embola" (chiado, faixas
## tortas, cores separadas) e a capa troca de uma para a outra; o menu troca a música junto.
## Se a imagem sombria ainda não existir, o shader faz uma versão escura da fofa.

## Avisa o menu que a capa virou (true = sombria), para trocar a música.
signal virou(sombria: bool)

const PASTA := "res://assets/arte_externa/menu/"
const SHADER := preload("res://assets/shaders/capa_menu.gdshader")
const SOM_GLITCH := "res://assets/sons/vhs_glitch.wav"
## Moldura de papel das artes do Gemini (x0, y0, x1, y1): é cortada.
const RECORTE := Vector4(0.02, 0.032, 0.982, 0.968)

@export_group("Ritmo")
## Segundos (mínimo e máximo) mostrando a capa fofa antes de virar.
@export var tempo_fofa := Vector2(10.0, 17.0)
## Segundos (mínimo e máximo) mostrando a capa sombria antes de voltar.
@export var tempo_sombria := Vector2(4.5, 7.5)
## Duração (s) do glitch da troca.
@export var duracao_glitch := 0.8

var sombria := false
var _material: ShaderMaterial
var _som: AudioStreamPlayer
var _espera := 0.0
var _tempo_tremidinha := 0.0


## Existe a capa fofa? (sem ela, o menu continua com o palco 3D da V1)
static func disponivel() -> bool:
	return _caminho("menu_fundo") != ""


static func _caminho(nome: String) -> String:
	for ext in ["jpg", "jpeg", "png", "webp"]:
		if ResourceLoader.exists(PASTA + nome + "." + ext):
			return PASTA + nome + "." + ext
	return ""


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_material = ShaderMaterial.new()
	_material.shader = SHADER
	_material.set_shader_parameter("capa_fofa", load(_caminho("menu_fundo")))
	var c_sombria := _caminho("menu_fundo_sombrio")
	_material.set_shader_parameter("tem_sombria", c_sombria != "")
	if c_sombria != "":
		_material.set_shader_parameter("capa_sombria", load(c_sombria))
	_material.set_shader_parameter("recorte", RECORTE)
	material = _material
	_som = AudioStreamPlayer.new()
	_som.bus = "Efeitos"
	if ResourceLoader.exists(SOM_GLITCH):
		_som.stream = load(SOM_GLITCH)
	_som.volume_db = -6.0
	add_child(_som)
	resized.connect(_ao_redimensionar)
	_ao_redimensionar()
	_espera = randf_range(tempo_fofa.x, tempo_fofa.y)
	_tempo_tremidinha = randf_range(3.0, 6.0)


func _ao_redimensionar() -> void:
	var tela := get_viewport_rect().size if size.x < 1.0 or size.y < 1.0 else size
	if tela.x >= 1.0 and tela.y >= 1.0:
		_material.set_shader_parameter("tamanho_tela", tela)


func _process(delta: float) -> void:
	_ao_redimensionar()
	_espera -= delta
	if _espera <= 0.0:
		trocar()
		_espera = randf_range(tempo_sombria.x, tempo_sombria.y) if sombria else randf_range(tempo_fofa.x, tempo_fofa.y)
	# Na capa fofa, de vez em quando a fita dá uma "tremidinha" rápida (avisando que algo vem aí).
	if not sombria:
		_tempo_tremidinha -= delta
		if _tempo_tremidinha <= 0.0:
			_tempo_tremidinha = randf_range(3.0, 7.0)
			var t := create_tween()
			t.tween_method(_definir_glitch, 0.0, 0.25, 0.05)
			t.tween_method(_definir_glitch, 0.25, 0.0, 0.12)


## Faz o glitch e troca de capa no meio dele (o pico do chiado esconde a troca).
func trocar() -> void:
	sombria = not sombria
	if _som.stream:
		_som.pitch_scale = randf_range(0.9, 1.1)
		_som.play()
	var metade := duracao_glitch / 2.0
	var t := create_tween()
	t.tween_method(_definir_glitch, 0.0, 1.0, metade * 0.6)
	t.tween_callback(func() -> void:
		_material.set_shader_parameter("mistura", 1.0 if sombria else 0.0)
		virou.emit(sombria))
	t.tween_interval(metade * 0.4)
	t.tween_method(_definir_glitch, 1.0, 0.0, metade)


func _definir_glitch(valor: float) -> void:
	_material.set_shader_parameter("glitch", valor)
