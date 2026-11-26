extends Area3D
## Pilha da lanterna. Brilha fraco para ser achada no escuro.
## Aperte E perto dela para recarregar a bateria.

## Quanto de bateria a pilha devolve (35 = +35%).
@export var recarga := 35.0
## Velocidade (graus/s) em que a pilha gira, para chamar atenção.
@export var velocidade_giro := 60.0

const SOM_PEGAR := preload("res://assets/sons/pegar_pilha.wav")

@onready var modelo: Node3D = $Modelo
var _tempo := 0.0


func _ready() -> void:
	add_to_group("pilha")
	add_to_group("interagivel")
	_tempo = randf() * TAU  # cada pilha balança num ritmo diferente


func _process(delta: float) -> void:
	_tempo += delta
	modelo.rotate_y(deg_to_rad(velocidade_giro) * delta)
	modelo.position.y = 0.12 + sin(_tempo * 2.0) * 0.03


func texto_dica() -> String:
	return "Aperte E para pegar a pilha (+%d%% de bateria)" % int(recarga)


func interagir(jogador: Node) -> void:
	Jogo.contar("pilhas")
	jogador.recarregar(recarga)
	jogador.tocar_som(SomExterno.efeito("pegar_item", "res://assets/sons/pegar_pilha.wav"), -4.0)
	queue_free()
