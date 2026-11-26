class_name Minigame
extends Control
## Base de todos os minigames (garra, TITO KART, conserto do disjuntor).
##
## Como funciona:
##   - Quem abre o minigame (a máquina no mundo) instancia a cena, adiciona numa CanvasLayer
##     e chama iniciar(dificuldade, dados).
##   - O MUNDO NÃO PAUSA: os animatrônicos continuam andando enquanto o vigia joga.
##   - Quando acaba, o minigame emite "terminado(venceu, resultado)" UMA vez e se apaga sozinho.
##   - ESC ou E saem a qualquer momento (perde a tentativa).
##   - F7 (com Jogo.DEBUG_ATIVO) vence na hora.
##
## Cada minigame filho implementa _ao_iniciar(), _ao_processar(delta) e, se quiser, _ao_vencer_agora().

signal terminado(venceu: bool, resultado: Dictionary)

## Nome usado nos sinais do Jogo ("garra", "kart", "space_pizza", "conserto_fios", "conserto_fusivel").
@export var nome_minigame := ""
## Quanto barulho a máquina faz enquanto o minigame roda (0 a 1). A máquina no mundo
## lê este valor e emite ruído para os animatrônicos.
@export_range(0.0, 1.0) var intensidade_ruido := 0.5

var dificuldade: Dificuldade
var dados := {}
var rodando := false
var _acabou := false


func _ready() -> void:
	# Rodando sozinho no editor (F6): inicia com a dificuldade Normal.
	if get_tree().current_scene == self:
		await get_tree().create_timer(0.2).timeout
		if not rodando and not _acabou:
			iniciar(null, {"codigo": "4712", "modo": "fios"})


## dados: informações extras. Ex.: {"codigo": "4712"} para o kart, {"modo": "fusivel"} para o conserto.
func iniciar(dif: Dificuldade = null, dados_extra := {}) -> void:
	dificuldade = dif if dif else load("res://assets/dificuldade/normal.tres")
	dados = dados_extra
	rodando = true
	_acabou = false
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	_ao_iniciar()
	# Todo som do minigame vai para o barramento "Minigames" (mais baixo que o resto do jogo).
	_preparar_barramento()
	for no in find_children("*", "AudioStreamPlayer", true, false):
		(no as AudioStreamPlayer).bus = BARRAMENTO
	if not get_tree().node_added.is_connected(_ao_adicionar_no):
		get_tree().node_added.connect(_ao_adicionar_no)


## Barramento dos sons dos minigames: manda para "Efeitos" (o volume de efeitos das opções vale)
## com um corte fixo, porque os sons das máquinas são bem mais "cheios" que os do resto do jogo.
const BARRAMENTO := &"Minigames"
const VOLUME_MINIGAMES_DB := -14.0


static func _preparar_barramento() -> void:
	if AudioServer.get_bus_index(BARRAMENTO) >= 0:
		return
	AudioServer.add_bus()
	var i := AudioServer.bus_count - 1
	AudioServer.set_bus_name(i, BARRAMENTO)
	AudioServer.set_bus_send(i, &"Efeitos")
	AudioServer.set_bus_volume_db(i, VOLUME_MINIGAMES_DB)


## Sons criados depois (durante o minigame) também vão para o barramento dos minigames.
func _ao_adicionar_no(no: Node) -> void:
	if no is AudioStreamPlayer and is_ancestor_of(no):
		(no as AudioStreamPlayer).bus = BARRAMENTO


func _exit_tree() -> void:
	if get_tree() and get_tree().node_added.is_connected(_ao_adicionar_no):
		get_tree().node_added.disconnect(_ao_adicionar_no)


## Termina o minigame (chamado pelo filho quando vence ou perde).
func finalizar(venceu: bool, resultado := {}) -> void:
	if _acabou:
		return
	_acabou = true
	rodando = false
	terminado.emit(venceu, resultado)
	queue_free()


## Desiste (ESC ou E): perde a tentativa.
## Mas se a vitória JÁ foi decidida (a tela de "ganhou!" está aparecendo), sair só fecha mais
## rápido e a vitória vale: apertar E para "confirmar" não pode jogar o prêmio fora.
func cancelar() -> void:
	var decidido: Variant = _resultado_decidido()
	if decidido is Array and (decidido as Array)[0]:
		finalizar(true, (decidido as Array)[1])
		return
	finalizar(false, {"cancelado": true})


## Os filhos devolvem [true, resultado] quando já venceram e só estão mostrando a mensagem final.
func _resultado_decidido() -> Variant:
	return null


## F7 no debug, e também usado pelos testes automáticos.
func vencer_agora() -> void:
	if not _acabou:
		_ao_vencer_agora()


func _process(delta: float) -> void:
	if rodando:
		_ao_processar(delta)


func _unhandled_input(evento: InputEvent) -> void:
	if not rodando:
		return
	if evento.is_action_pressed("pausar") or evento.is_action_pressed("interagir"):
		get_viewport().set_input_as_handled()
		cancelar()
	elif Jogo.DEBUG_ATIVO and evento is InputEventKey and evento.pressed and not evento.echo \
			and evento.physical_keycode == KEY_F7:
		get_viewport().set_input_as_handled()
		vencer_agora()


# --- Para os filhos sobrescreverem ------------------------------------------

func _ao_iniciar() -> void:
	pass


func _ao_processar(_delta: float) -> void:
	pass


## Padrão: vence com resultado vazio. Os filhos devolvem o resultado certo (ex.: os dígitos).
func _ao_vencer_agora() -> void:
	finalizar(true, {})


## Lê uma tecla de movimento (WASD) como vetor: x = direita, y = baixo.
func direcao_movimento() -> Vector2:
	return Input.get_vector("mover_esquerda", "mover_direita", "mover_frente", "mover_tras")
