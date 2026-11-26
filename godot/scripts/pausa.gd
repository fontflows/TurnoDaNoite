extends CanvasLayer
## Menu de pausa (ESC). Fica escondido até o jogador apertar ESC durante a partida.
## Este nó continua funcionando com o jogo pausado (process_mode = Sempre).

@onready var centro: Control = $Centro
@onready var botao_continuar: Button = %BotaoContinuar
@onready var botao_opcoes: Button = %BotaoOpcoes
@onready var botao_menu: Button = %BotaoMenu
@onready var painel_opcoes: PanelContainer = $Opcoes


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	visible = false
	botao_continuar.pressed.connect(continuar)
	botao_opcoes.pressed.connect(_abrir_opcoes)
	botao_menu.pressed.connect(Jogo.ir_para_menu)
	painel_opcoes.fechado.connect(_fechar_opcoes)


func _unhandled_input(evento: InputEvent) -> void:
	if not evento.is_action_pressed("pausar"):
		return
	if visible:
		get_viewport().set_input_as_handled()
		if painel_opcoes.visible:
			painel_opcoes.voltar()  # ESC com as opções abertas: volta para a pausa
		else:
			continuar()
		return
	# Não pausa fora da partida (susto, vitória...) nem quando o vigia usa o ESC
	# para sair do monitor de câmeras.
	if not Jogo.em_partida:
		return
	var jogador := get_tree().get_first_node_in_group("jogador")
	if jogador and jogador.get("travado"):
		return
	get_viewport().set_input_as_handled()
	pausar()


func pausar() -> void:
	get_tree().paused = true
	visible = true
	centro.show()
	painel_opcoes.hide()
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	botao_continuar.grab_focus()


func continuar() -> void:
	visible = false
	get_tree().paused = false
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _abrir_opcoes() -> void:
	centro.hide()
	painel_opcoes.show()


func _fechar_opcoes() -> void:
	centro.show()
	botao_opcoes.grab_focus()
