class_name Interacao
extends Area3D
## Área de interação genérica (tecla E) criada por código pelo montador da V2.
## Quem cria passa duas funções: uma que devolve o texto da dica e outra que faz a ação.
##
## Exemplo:
##   var i := Interacao.criar(Vector3(0.5, 0.5, 0.3), func(): return "Aperte E", func(j): print("oi"))
##   modelo.add_child(i)

## Camada 4 = "Interativos" (o raio de interação do jogador enxerga as camadas 1 e 4).
const CAMADA_INTERATIVOS := 8

var funcao_dica: Callable
var funcao_acao: Callable


static func criar(tamanho: Vector3, dica: Callable, acao: Callable, nome := "Interacao") -> Interacao:
	var area := Interacao.new()
	area.name = nome
	area.funcao_dica = dica
	area.funcao_acao = acao
	area.collision_layer = CAMADA_INTERATIVOS
	area.collision_mask = 0
	area.monitoring = false
	var forma := CollisionShape3D.new()
	var caixa := BoxShape3D.new()
	caixa.size = tamanho
	forma.shape = caixa
	area.add_child(forma)
	return area


func _ready() -> void:
	add_to_group("interagivel")


func texto_dica() -> String:
	return funcao_dica.call() if funcao_dica.is_valid() else ""


func interagir(jogador: Node) -> void:
	if funcao_acao.is_valid():
		funcao_acao.call(jogador)


## Desliga a interação (ex.: item já pego).
func desativar() -> void:
	remove_from_group("interagivel")
	collision_layer = 0
