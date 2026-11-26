extends Node3D
## Cena principal do jogo. Monta a navegação, coloca o vigia no ponto de início
## e confere a vitória (vigia na sala de segurança com os 4 disjuntores ligados).
##
## Os valores mais importantes da partida ficam aqui, no Inspector do nó "Mundo".

@export_group("Relógio")
## Deixe 0 para usar a duração da dificuldade escolhida (Fácil 150 s, Normal 120 s, Pesadelo 100 s).
## Coloque um número (ex.: 40) para forçar uma noite mais curta, ótimo na apresentação.
@export var segundos_por_hora := 0.0

@export_group("Disjuntores")
## Quantos disjuntores precisam ser religados para vencer.
@export var total_disjuntores := 4

@export_group("Navegação")
## Recalcula o "mapa de caminhos" dos animatrônicos quando o jogo abre.
## Deixe ligado: assim, se você mover móveis no Blender, os caminhos se ajustam sozinhos.
@export var assar_navegacao_ao_iniciar := true

@onready var navegacao: NavigationRegion3D = $Navegacao
@onready var jogador: CharacterBody3D = $Jogador
@onready var spawn: Marker3D = $Marcadores/SpawnJogador
@onready var zona_sala: Area3D = $ZonaSalaSeguranca


func _ready() -> void:
	add_to_group("mundo")
	if assar_navegacao_ao_iniciar:
		# false = calcula agora, antes do primeiro quadro (leva uma fração de segundo).
		navegacao.bake_navigation_mesh(false)
	jogador.global_transform = spawn.global_transform
	Jogo.iniciar_partida(self)
	_aplicar_luz_da_dificuldade()
	_ajustar_pilhas()


## Deixa no mapa só a quantidade de pilhas da dificuldade (as primeiras da lista `Pilhas`).
## Por isso, no editor, as pilhas mais arriscadas devem ficar no topo da lista.
## (No Normal e no Pesadelo a lista é embaralhada antes: as pilhas mudam de lugar.)
func _ajustar_pilhas() -> void:
	var pilhas := get_node("Pilhas").get_children()
	# Normal e Pesadelo: quais pilhas ficam no mapa é sorteado a cada partida.
	if Jogo.dificuldade.nivel_sorteio >= 1:
		pilhas.shuffle()
	for i in pilhas.size():
		if i >= Jogo.dificuldade.pilhas_no_mapa:
			pilhas[i].queue_free()
		else:
			pilhas[i].recarga = Jogo.dificuldade.recarga_pilha


func _physics_process(_delta: float) -> void:
	if Jogo.em_partida and Jogo.pode_vencer() and zona_sala.overlaps_body(jogador):
		Jogo.tentar_vencer()


# ---------------------------------------------------------------------------
# V2: as portas mudam a navegação (porta fechada = parede para os animatrônicos)
# ---------------------------------------------------------------------------

var _reassar_pendente := false
var _assando := false


## As portas chamam isto quando terminam de abrir ou fechar. Espera um pouco (várias portas
## seguidas viram um cálculo só) e recalcula o mapa de caminhos numa thread separada.
## O cálculo é feito numa CÓPIA da navmesh, trocada só quando fica pronta: assim os
## animatrônicos nunca enxergam um mapa vazio ou pela metade no meio do caminho.
func pedir_reassar_navegacao() -> void:
	if _reassar_pendente:
		return
	_reassar_pendente = true
	await get_tree().create_timer(0.4).timeout
	while _assando or navegacao.is_baking():
		await get_tree().process_frame
	_reassar_pendente = false
	_assando = true
	var nova: NavigationMesh = navegacao.navigation_mesh.duplicate()
	var fonte := NavigationMeshSourceGeometryData3D.new()
	NavigationServer3D.parse_source_geometry_data(nova, fonte, navegacao)
	NavigationServer3D.bake_from_source_geometry_data_async(nova, fonte, func() -> void:
		navegacao.navigation_mesh = nova
		_assando = false
		navegacao.bake_finished.emit())


## A luz ambiente (o "luar" azulado) muda com a dificuldade: o Fácil fica um pouco mais claro.
func _aplicar_luz_da_dificuldade() -> void:
	var ambiente := get_node_or_null("Ambiente") as WorldEnvironment
	if ambiente == null or ambiente.environment == null or Jogo.dificuldade == null:
		return
	var env: Environment = ambiente.environment.duplicate()
	env.ambient_light_energy *= Jogo.dificuldade.luz_ambiente
	ambiente.environment = env

