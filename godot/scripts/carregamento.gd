extends Control
## Tela de carregamento: a fachada da pizzaria à noite (ARTE-11), uma dica que troca a cada
## poucos segundos e a barra de progresso de verdade (o mapa carrega numa thread separada).
## Quando termina, espera o jogador ler pelo menos um pouco e entra no jogo.

const ARTE := "res://assets/arte_externa/menu/tela_carregamento.jpg"
const SHADER := preload("res://assets/shaders/capa_menu.gdshader")

## Tempo mínimo (s) na tela, mesmo se carregar rápido (dá para ler a dica).
@export var tempo_minimo := 3.0
## De quanto em quanto tempo (s) a dica muda.
@export var troca_dica := 4.5

const DICAS := [
	"O Tito só se mexe quando você NÃO está vendo. No escuro, olhar não basta: ilumine.",
	"A Pipoca ouve tudo. Agachado (Ctrl) você quase não faz barulho.",
	"Lanterna acesa chama atenção. Às vezes, andar no escuro é mais seguro.",
	"Escondido no armário, segure Alt para prender a respiração quando ela chegar perto.",
	"Cada tentativa na garra ou no TITO KART gasta uma ficha. Procure no chão: elas brilham.",
	"A porta da oficina está emperrada... mas o duto da sala dos piratas chega lá.",
	"Cortar a corrente do depósito faz MUITO barulho. Corte e saia de perto.",
	"A senha da sala elétrica muda toda noite. O gerente sempre deixa um bilhete.",
	"Tab mostra o inventário e a senha que você já sabe. O repete o objetivo.",
	"Bateria fraca? R sacode a lanterna (mas faz um pouco de barulho).",
	"Cacos de vidro no chão estalam alto. Passe agachado.",
	"Jogue uma lata (G) para atrair a Pipoca para longe.",
	"Quando o gerador ligar, todos vão atrás de você. Corra para a sala de segurança e feche a porta de aço!",
]

var _dica: Label
var _barra: ProgressBar
var _tempo := 0.0
var _tempo_dica := 0.0
var _ordem: Array = []
var _cena_pronta: PackedScene


func _ready() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_HIDDEN
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var fundo := ColorRect.new()
	fundo.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	if ResourceLoader.exists(ARTE):
		var m := ShaderMaterial.new()
		m.shader = SHADER
		m.set_shader_parameter("capa_fofa", load(ARTE))
		m.set_shader_parameter("recorte", Vector4(0.025, 0.036, 0.975, 0.964))
		m.set_shader_parameter("tamanho_tela", get_viewport_rect().size)
		fundo.material = m
	else:
		fundo.color = Color(0.03, 0.04, 0.07)
	add_child(fundo)
	# Faixa escura embaixo, para o texto ficar legível sobre a arte.
	var faixa := ColorRect.new()
	faixa.color = Color(0, 0, 0, 0.72)
	faixa.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	faixa.offset_top = -170
	add_child(faixa)
	var coluna := VBoxContainer.new()
	coluna.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	coluna.offset_top = -150
	coluna.offset_bottom = -24
	coluna.offset_left = 80
	coluna.offset_right = -80
	coluna.add_theme_constant_override("separation", 12)
	add_child(coluna)
	var titulo := Label.new()
	titulo.text = "PIZZARIA DO TITO — 23:58"
	titulo.theme_type_variation = &"RotuloLetreiro"
	titulo.add_theme_font_size_override("font_size", 30)
	coluna.add_child(titulo)
	_dica = Label.new()
	_dica.theme_type_variation = &"RotuloHUD"
	_dica.add_theme_font_size_override("font_size", 24)
	_dica.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	coluna.add_child(_dica)
	_barra = ProgressBar.new()
	_barra.max_value = 1.0
	_barra.show_percentage = false
	_barra.custom_minimum_size.y = 8
	coluna.add_child(_barra)
	_ordem = DICAS.duplicate()
	_ordem.shuffle()
	_proxima_dica()
	ResourceLoader.load_threaded_request(Jogo.CENA_MUNDO)


func _proxima_dica() -> void:
	if _ordem.is_empty():
		_ordem = DICAS.duplicate()
		_ordem.shuffle()
	_dica.text = "DICA: " + String(_ordem.pop_back())
	_tempo_dica = troca_dica


func _process(delta: float) -> void:
	_tempo += delta
	_tempo_dica -= delta
	if _tempo_dica <= 0.0:
		_proxima_dica()
	if _cena_pronta == null:
		var progresso := []
		var estado := ResourceLoader.load_threaded_get_status(Jogo.CENA_MUNDO, progresso)
		if estado == ResourceLoader.THREAD_LOAD_LOADED:
			_cena_pronta = ResourceLoader.load_threaded_get(Jogo.CENA_MUNDO)
		elif estado == ResourceLoader.THREAD_LOAD_FAILED or estado == ResourceLoader.THREAD_LOAD_INVALID_RESOURCE:
			# Plano B: carrega do jeito simples.
			_cena_pronta = load(Jogo.CENA_MUNDO)
		elif not progresso.is_empty():
			_barra.value = move_toward(_barra.value, float(progresso[0]), delta * 2.0)
	else:
		_barra.value = move_toward(_barra.value, 1.0, delta * 2.0)
		if _tempo >= tempo_minimo and _barra.value >= 1.0:
			set_process(false)
			get_tree().change_scene_to_packed(_cena_pronta)
