extends Control
## Tela de abertura curta: "Use fones de ouvido". Some sozinha (ou com qualquer tecla)
## e vai para o menu principal.

## Quanto tempo (s) o aviso fica na tela.
@export var duracao := 3.0

const CENA_MENU := "res://ui/menu_principal.tscn"
var _saindo := false


func _ready() -> void:
	modulate.a = 0.0
	var t := create_tween()
	t.tween_property(self, "modulate:a", 1.0, 0.6)
	t.tween_interval(duracao)
	t.tween_callback(_ir_para_menu)


func _input(evento: InputEvent) -> void:
	if (evento is InputEventKey or evento is InputEventMouseButton) and evento.pressed:
		_ir_para_menu()


func _ir_para_menu() -> void:
	if _saindo:
		return
	_saindo = true
	var t := create_tween()
	t.tween_property(self, "modulate:a", 0.0, 0.4)
	t.tween_callback(func(): get_tree().change_scene_to_file(CENA_MENU))
