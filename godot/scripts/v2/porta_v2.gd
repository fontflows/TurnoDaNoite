class_name PortaV2
extends StaticBody3D
## Lógica das portas especiais do mapa da V2. O MODELO (a folha da porta, com a origem na
## dobradiça) vem do Blender com o nome "Porta__<tipo>__<id>"; o montador cria esta lógica
## como FILHA da folha, então a colisão gira junto com a porta.
##
## Tipos (planta_v2.py, lista PORTAS):
##   vaivem    porta da cozinha: abre e fecha com E (range)
##   pesada    câmara fria: abre devagar e faz barulho
##   unica     atalho: só abre de DENTRO do cômodo indicado (depois fica aberta)
##   emperrada oficina: nunca abre (entra-se pelo duto)
##   corrente  depósito: precisa do alicate (cortar a corrente faz MUITO barulho)
##   chave     sala do gerente: precisa da chave (prêmio da garra)
##   teclado   sala elétrica: abre com a senha no teclado ao lado
##   aco       sala de segurança: começa aberta; fecha pelo botão vermelho (só com o gerador ligado)
##
## Porta fechada é parede para a navegação: quando uma porta muda, o mapa de caminhos é
## recalculado (os animatrônicos passam a usar o caminho novo).

signal mudou(aberta: bool)

## Ângulo (graus) da porta aberta.
@export var angulo_aberta := 95.0
## Tempo (s) para abrir ou fechar.
@export var duracao := 0.6

var tipo := ""
var id_porta := ""
## Para portas "unica": de dentro de qual cômodo ela abre.
var lado_unico := ""
var aberta := false
var trancada := false
var folha: Node3D
var _rot_fechada := 0.0
var _largura := 1.4
var _tween: Tween
var _som: AudioStreamPlayer3D
## Ligação de navegação pelo vão: deixa os animatrônicos planejarem o caminho ATRAVÉS da porta
## fechada (quando chegam nela, abrem). Só existe nas portas que eles podem abrir.
var _ligacao: NavigationLink3D

## Portas que os animatrônicos sabem abrir (as outras são puzzle do vigia ou a porta de aço).
const ANIMATRONICOS_ABREM := ["vaivem", "pesada", "corrente", "chave", "teclado"]

const SONS := {
	"abrir": "res://assets/sons/porta_rangido.wav",
	"corrente": "res://assets/sons/corrente_cortada.wav",
	"aco": "res://assets/sons/porta_aco.wav",
	"trancada": "res://assets/sons/porta_trancada.wav",
}


## Cria a lógica da porta dentro da folha vinda do Blender.
static func montar(no_folha: Node3D, tipo_porta: String, id: String) -> PortaV2:
	var p := PortaV2.new()
	p.name = "Logica_Porta"
	p.tipo = tipo_porta
	p.id_porta = id
	p.folha = no_folha
	no_folha.add_child(p)
	return p


func _ready() -> void:
	add_to_group("porta")
	add_to_group("interagivel")
	collision_layer = 1  # "Mundo": bloqueia o vigia, os animatrônicos e a navegação (só fechada)
	collision_mask = 0
	_rot_fechada = folha.rotation.y
	# Colisão do tamanho da folha (a malha começa na dobradiça e vai até a largura).
	var aabb := AABB(Vector3.ZERO, Vector3(1.4, 2.2, 0.05))
	if folha is MeshInstance3D:
		aabb = (folha as MeshInstance3D).get_aabb()
	_largura = aabb.size.x
	var forma := CollisionShape3D.new()
	var caixa := BoxShape3D.new()
	caixa.size = aabb.size.max(Vector3(0.05, 0.05, 0.08))
	forma.shape = caixa
	forma.position = aabb.get_center()
	add_child(forma)
	_som = AudioStreamPlayer3D.new()
	_som.unit_size = 4.0
	_som.position = aabb.get_center()
	add_child(_som)
	match tipo:
		"corrente", "chave", "teclado", "emperrada":
			trancada = true
		"aco":
			duracao = 1.4
			_girar(true, false)  # a porta de aço começa aberta
		"pesada":
			duracao = 1.3
		"unica":
			lado_unico = id_porta.get_slice("_", 0).capitalize().replace(" ", "_")
	if tipo in ANIMATRONICOS_ABREM:
		_criar_ligacao.call_deferred()


func _criar_ligacao() -> void:
	# Centro do vão e direção "através" da porta, calculados com a porta FECHADA.
	var pai := folha.get_parent_node_3d()
	var base := (pai.global_basis if pai else Basis()) * Basis(Vector3.UP, _rot_fechada)
	var dobradica := folha.global_position
	var centro := dobradica + base * Vector3(_largura * 0.5, 0, 0)
	var atraves := (base * Vector3(0, 0, 1)).normalized()
	_ligacao = NavigationLink3D.new()
	_ligacao.name = "Ligacao_Porta_" + id_porta
	_ligacao.bidirectional = true
	_ligacao.set_meta("porta", self)
	get_tree().get_first_node_in_group("mundo").add_child(_ligacao)
	_ligacao.global_position = Vector3(centro.x, 0.0, centro.z)
	_ligacao.start_position = -atraves * 0.9
	_ligacao.end_position = atraves * 0.9
	_atualizar_ligacao()


## A ligação vale sempre que a porta está destrancada (aberta ou fechada): logo depois de abrir,
## o mapa de caminhos ainda está sendo recalculado, e é a ligação que mantém o caminho pelo vão.
func _atualizar_ligacao() -> void:
	if _ligacao:
		_ligacao.enabled = not trancada


func texto_dica() -> String:
	var jogador := get_tree().get_first_node_in_group("jogador") as Node3D
	match tipo:
		"emperrada":
			return "Emperrada. Tem entulho do outro lado... (deve dar para entrar por outro lugar)"
		"corrente":
			if trancada:
				return "Aperte E para cortar a corrente (vai fazer MUITO barulho!)" if Jogo.tem_item("alicate") \
					else "Corrente com cadeado. Precisa de um alicate."
		"chave":
			if trancada:
				return "Aperte E para destrancar com a chave do gerente" if Jogo.tem_item("chave_gerente") \
					else "Trancada. Precisa da chave do gerente."
		"teclado":
			if trancada:
				return "Trancada. Use o teclado numérico ao lado da porta."
		"aco":
			return "Porta de aço: aperte o botão vermelho dentro da sala de segurança."
		"unica":
			if not aberta and jogador and PlantaV2.comodo_em(jogador.global_position) != lado_unico:
				return "Não abre deste lado."
	return "Aperte E para %s a porta" % ("fechar" if aberta else "abrir")


func interagir(jogador: Node) -> void:
	if _tween and _tween.is_running():
		return
	match tipo:
		"emperrada", "aco":
			_tocar("trancada")
			return
		"corrente":
			if trancada:
				if not Jogo.tem_item("alicate"):
					_tocar("trancada")
					return
				_cortar_corrente()
				return
		"chave":
			if trancada:
				if not Jogo.tem_item("chave_gerente"):
					_tocar("trancada")
					return
				trancada = false
				_atualizar_ligacao()
				Jogo.mensagem.emit("Porta do gerente destrancada.", 2.0)
		"teclado":
			if trancada:
				_tocar("trancada")
				return
		"unica":
			if not aberta and PlantaV2.comodo_em((jogador as Node3D).global_position) != lado_unico:
				_tocar("trancada")
				return
			if aberta:
				return  # atalho aberto fica aberto
	alternar(jogador as Node3D)


## Abre ou fecha. A porta abre para o lado oposto de quem abriu.
func alternar(quem: Node3D = null) -> void:
	_girar(not aberta, true, quem)


func destrancar() -> void:
	trancada = false
	_atualizar_ligacao()


func _cortar_corrente() -> void:
	trancada = false
	_atualizar_ligacao()
	_tocar("corrente")
	Jogo.emitir_ruido(global_position, 22.0, 1.0)
	Jogo.mensagem.emit("CLANK! A corrente caiu... alguém deve ter ouvido.", 3.0)
	for nome in ["_Corrente", "_Cadeado"]:
		var peca := folha.find_child(String(folha.name) + nome, false, false) as Node3D
		if peca:
			var queda := create_tween()
			queda.tween_property(peca, "position:y", peca.position.y - 0.9, 0.35).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
			queda.tween_callback(peca.hide)


func _girar(abrir: bool, animar: bool, quem: Node3D = null) -> void:
	aberta = abrir
	var alvo := _rot_fechada
	if abrir:
		alvo = _rot_fechada + deg_to_rad(_lado_de_abrir(quem) * angulo_aberta)
	if _tween:
		_tween.kill()
	# Porta aberta fica só na camada 4 "Interativos": sem colisão (não enrosca em quem passa nem
	# atrapalha a navegação). Fechando, a colisão volta na hora.
	if not abrir:
		collision_layer = 1
	if not animar:
		folha.rotation.y = alvo
		collision_layer = 8 if abrir else 1
	else:
		_tocar("aco" if tipo == "aco" else "abrir")
		_tween = create_tween().set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
		_tween.tween_property(folha, "rotation:y", alvo, duracao)
		if abrir:
			_tween.tween_callback(func() -> void: collision_layer = 8)
		_tween.tween_callback(_avisar_navegacao)
		# Só o vigia "denuncia" a própria posição abrindo portas (o animatrônico não se ouve).
		if quem == null or quem.is_in_group("jogador"):
			Jogo.emitir_ruido(global_position, 4.0 if tipo != "pesada" else 8.0, 0.3)
	_atualizar_ligacao()
	mudou.emit(aberta)


## +1 ou −1: o lado para onde a folha gira, escolhido para longe de quem abriu
## (a porta de aço abre para o corredor, longe do centro da sala de segurança).
func _lado_de_abrir(quem: Node3D) -> float:
	var referencia := PlantaV2.mundo(48.5, 28.25) if tipo == "aco" else (quem.global_position if quem else global_position)
	var dobradica := folha.global_position
	var base_pai := folha.get_parent_node_3d().global_basis if folha.get_parent_node_3d() else Basis()
	var melhor := 1.0
	var maior := -INF
	for lado in [1.0, -1.0]:
		var base := base_pai * Basis(Vector3.UP, _rot_fechada + deg_to_rad(lado * angulo_aberta))
		var ponta := dobradica + base * Vector3(_largura * 0.5, 0, 0)
		var d := ponta.distance_to(referencia)
		if d > maior:
			maior = d
			melhor = lado
	return melhor


func _avisar_navegacao() -> void:
	var mundo := get_tree().get_first_node_in_group("mundo")
	if mundo and mundo.has_method("pedir_reassar_navegacao"):
		mundo.pedir_reassar_navegacao()


func _tocar(chave: String) -> void:
	var reserva: String = SONS.get(chave, "")
	var externo: String = {"abrir": "porta_rangido", "corrente": "corrente_cortada", "aco": "porta_aco",
		"trancada": "porta_trancada"}.get(chave, "")
	var caminho := SomExterno.caminho("res://assets/audio_externo/efeitos/" + externo, reserva)
	if caminho != "":
		_som.stream = load(caminho)
		_som.play()


## Debug e testes: destranca e abre (menos a de aço e a emperrada, que é para o duto).
func abrir_para_teste() -> void:
	if tipo in ["aco", "emperrada"]:
		return
	trancada = false
	if not aberta:
		_girar(true, false)
	_atualizar_ligacao()
