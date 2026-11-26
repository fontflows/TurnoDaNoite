@tool
extends Camera3D
## Câmera de segurança do mapa. Ela NÃO é a câmera do jogador: o monitor da sala
## de segurança copia a posição dela para mostrar a imagem.
##
## O nome do nó aparece na tela do monitor (ex.: "CAM 1 - Palco").
## Para mudar o que a câmera mostra: mova o nó e ajuste "olhar_para".
## (@tool faz a câmera virar na hora, dentro do editor.)

## Ponto (coordenadas do mundo) para onde a câmera aponta.
@export var olhar_para := Vector3.ZERO:
	set(valor):
		olhar_para = valor
		_apontar()


func _ready() -> void:
	add_to_group("camera_seguranca")
	_apontar()


func _apontar() -> void:
	if not is_inside_tree():
		return
	if global_position.distance_to(olhar_para) > 0.01:
		look_at(olhar_para, Vector3.UP)
