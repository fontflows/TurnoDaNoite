extends Light3D
## Luz que falha de vez em quando (pisca). Serve para qualquer OmniLight3D ou SpotLight3D:
## é só arrastar este script para a luz.
##
## Luzes do grupo "luz_area" começam apagadas (ativa = false) e acendem quando
## o disjuntor da área é religado (o disjuntor chama acender()).

## Se a luz está ligada. Desligada = totalmente apagada.
@export var ativa := true
## Se a luz deve falhar/piscar de vez em quando.
@export var piscar := true
## Chance (por segundo) de começar uma falha. 0.3 = falha mais ou menos a cada 3 s.
@export var chance_falha_por_segundo := 0.3
## Quanto a luz enfraquece durante a falha (0 = apaga, 1 = não muda).
@export var forca_na_falha := 0.15

var _energia_normal := 1.0
var _tempo_falha := 0.0


func _ready() -> void:
	_energia_normal = light_energy
	visible = ativa


## Acende a luz com um "tremido" de lâmpada velha pegando.
func acender() -> void:
	ativa = true
	visible = true
	var t := create_tween()
	for i in 5:
		t.tween_property(self, "light_energy", _energia_normal * randf_range(0.0, 0.4), 0.06)
		t.tween_property(self, "light_energy", _energia_normal, 0.08)


func apagar() -> void:
	ativa = false
	visible = false


func _process(delta: float) -> void:
	if not ativa or not piscar:
		return
	if _tempo_falha > 0.0:
		_tempo_falha -= delta
		light_energy = _energia_normal * (forca_na_falha if randf() < 0.6 else 1.0)
		if _tempo_falha <= 0.0:
			light_energy = _energia_normal
	elif randf() < chance_falha_por_segundo * delta:
		_tempo_falha = randf_range(0.1, 0.7)
