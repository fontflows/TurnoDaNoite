class_name OlharAlvo
extends SkeletonModifier3D
## Faz a cabeça e os olhos do animatrônico seguirem um ponto (o vigia), por cima da animação.
##
## Como animatrônico: o alvo é atualizado em "trancos" (a cada 'intervalo_servo' segundos) e a cabeça
## pula rápido para a nova direção, em vez de acompanhar suave. Com 'congelado' = true a cabeça fica
## exatamente onde está (o Tito congela quando o vigia olha para ele).
##
## O animatrônico controla: alvo (posição global), peso (0 = só a animação, 1 = olhando o alvo) e congelado.

## Ponto (global) para onde olhar.
var alvo := Vector3.ZERO
## Quanto olhar para o alvo (0 a 1). Muda devagar (não dá tranco no peso).
var peso := 0.0
## Segura a cabeça e os olhos na última posição calculada.
var congelado := false

@export var limite_cabeca_graus := 60.0
@export var limite_olhos_graus := 22.0
@export var intervalo_servo := 0.14

var _ossos := {}          # papel -> índice do osso
var _frente := {}         # índice -> direção da frente do rosto no espaço do osso
var _ultima := {}         # índice -> última rotação local aplicada (para congelar)
var _peso_atual := 0.0
var _alvo_passo := Vector3.ZERO
var _alvo_suave := Vector3.ZERO
var _tempo_servo := 0.0
var _pronto := false


func _preparar() -> bool:
	var sk := get_skeleton()
	if sk == null:
		return false
	for papel in ["cabeca", "olho.L", "olho.R"]:
		var i := _achar_osso(sk, papel)
		if i >= 0:
			_ossos[papel] = i
	if not _ossos.has("cabeca"):
		return false
	# A frente do modelo é +Z (do nó raiz do personagem). Em cada osso, guarda essa direção no espaço do osso, na pose de descanso.
	var raiz := sk.get_parent() as Node3D
	while raiz and raiz.get_parent() is Node3D and not (raiz is CharacterBody3D):
		raiz = raiz.get_parent() as Node3D
	var frente_global := (raiz.global_transform.basis.z if raiz else Vector3.FORWARD).normalized()
	for papel in _ossos:
		var i: int = _ossos[papel]
		var base_global := sk.global_transform.basis * sk.get_bone_global_rest(i).basis
		_frente[i] = (base_global.inverse() * frente_global).normalized()
	_pronto = true
	return true


static func _achar_osso(sk: Skeleton3D, nome: String) -> int:
	for candidato in [nome, nome.replace(".", "_"), nome.replace(".", "")]:
		var i := sk.find_bone(candidato)
		if i >= 0:
			return i
	return -1


func _process_modification_with_delta(delta: float) -> void:
	if not _pronto and not _preparar():
		return
	var sk := get_skeleton()
	_peso_atual = move_toward(_peso_atual, peso, delta * 2.5)
	if not congelado:
		_tempo_servo -= delta
		if _tempo_servo <= 0.0:
			_tempo_servo = intervalo_servo
			_alvo_passo = alvo
		if _alvo_suave == Vector3.ZERO:
			_alvo_suave = _alvo_passo
		_alvo_suave = _alvo_suave.lerp(_alvo_passo, clampf(delta * 20.0, 0.0, 1.0))
	if _peso_atual <= 0.001 and not congelado:
		_ultima.clear()
		return
	_virar(sk, "cabeca", limite_cabeca_graus)
	_virar(sk, "olho.L", limite_olhos_graus)
	_virar(sk, "olho.R", limite_olhos_graus)


func _virar(sk: Skeleton3D, papel: String, limite: float) -> void:
	if not _ossos.has(papel):
		return
	var i: int = _ossos[papel]
	if congelado:
		if _ultima.has(i):
			sk.set_bone_pose_rotation(i, _ultima[i])
		return
	var global_osso := sk.global_transform * sk.get_bone_global_pose(i)
	var frente: Vector3 = (global_osso.basis.orthonormalized() * _frente[i]).normalized()
	var desejado := (_alvo_suave - global_osso.origin).normalized()
	if desejado.length() < 0.5:
		return
	var angulo := frente.angle_to(desejado)
	var lim := deg_to_rad(limite)
	if angulo > lim:
		desejado = frente.slerp(desejado, lim / angulo)
	var giro := Quaternion(frente, desejado) if frente.cross(desejado).length() > 0.0001 else Quaternion.IDENTITY
	giro = Quaternion.IDENTITY.slerp(giro, _peso_atual)
	var nova := Basis(giro) * global_osso.basis.orthonormalized()
	var no_esqueleto := sk.global_transform.basis.orthonormalized().inverse() * nova
	var pai := sk.get_bone_parent(i)
	var local := no_esqueleto
	if pai >= 0:
		local = sk.get_bone_global_pose(pai).basis.orthonormalized().inverse() * no_esqueleto
	var q := local.get_rotation_quaternion()
	sk.set_bone_pose_rotation(i, q)
	_ultima[i] = q
