extends Node
## FERRAMENTA DE DESENVOLVIMENTO: confere os animatrônicos finais no jogo.
##   animações do .glb (nomes, loop, velocidade de referência) · esqueleto e olhar seguindo o vigia ·
##   olhos da Pipoca (para piscar) · animação certa em cada estado da IA · Tito congelando ·
##   modo observação (eles patrulham e ignoram o vigia, nem com ele colado).
## Rodar: godot --headless --path godot res://dev/teste_animatronicos.tscn

var _mundo: Node3D
var _jogador: CharacterBody3D
var _tito: Animatronico
var _pipoca: Animatronico
var _falhas := 0


func _conferir(ok: bool, texto: String) -> void:
	if not ok:
		_falhas += 1
	print("[anim] %s %s" % ["ok   " if ok else "FALHA", texto])


func _por(quem: Node3D, x: float, z: float, olhar_x: float, olhar_z: float) -> void:
	quem.global_position = PlantaV2.mundo(x, z, 0.05)
	var d := PlantaV2.mundo(olhar_x, olhar_z) - quem.global_position
	quem.rotation.y = atan2(d.x, d.z) if quem is Animatronico else atan2(-d.x, -d.z)
	quem.velocity = Vector3.ZERO


func _quadros(n: int) -> void:
	for i in n:
		await get_tree().physics_frame


func _anims(a: Animatronico) -> AnimationPlayer:
	return a.modelo.find_children("*", "AnimationPlayer", true, false)[0] if not a.modelo.find_children("*", "AnimationPlayer", true, false).is_empty() else null


func _ready() -> void:
	Jogo.trocar_cena_ao_terminar = false
	Config.dificuldade = 1
	_mundo = load("res://cenas/mundo_v2.tscn").instantiate()
	add_child(_mundo)
	await _quadros(20)
	_jogador = _mundo.get_node("Jogador")
	_tito = _mundo.get_node("Animatronicos/Tito")
	_pipoca = _mundo.get_node("Animatronicos/Pipoca")
	Jogo.hora = 2
	Jogo.invencivel = false

	# --- O que veio do Blender -------------------------------------------------
	for par in [[_tito, ["parado", "andar", "perseguir", "procurar", "jumpscare"]],
			[_pipoca, ["parado", "andar", "perseguir", "procurar", "jumpscare", "atordoado"]]]:
		var a: Animatronico = par[0]
		var ap := _anims(a)
		_conferir(ap != null, "%s tem AnimationPlayer" % a.nome_exibicao)
		if ap == null:
			continue
		for nome in par[1]:
			_conferir(ap.has_animation(nome), "%s tem a animação '%s'" % [a.nome_exibicao, nome])
		if ap.has_animation("andar"):
			_conferir(ap.get_animation("andar").loop_mode == Animation.LOOP_LINEAR, "%s: 'andar' em loop" % a.nome_exibicao)
		_conferir(float(a._vel_ref.get("andar", 0.0)) > 0.3 and float(a._vel_ref.get("perseguir", 0.0)) > 0.5,
			"%s: velocidades de referência %s" % [a.nome_exibicao, a._vel_ref])
		_conferir(a.olhar != null, "%s: cabeça e olhos seguem o vigia (OlharAlvo no esqueleto)" % a.nome_exibicao)
		var esq := a.modelo.find_children("*", "Skeleton3D", true, false)
		_conferir(not esq.is_empty() and (esq[0] as Skeleton3D).get_bone_count() > 30,
			"%s: esqueleto com %d ossos" % [a.nome_exibicao, (esq[0] as Skeleton3D).get_bone_count() if not esq.is_empty() else 0])
	_conferir(_pipoca._olhos.size() == 2, "olhos da Pipoca achados para piscar (%d)" % _pipoca._olhos.size())

	# --- Pipoca: animação de cada estado ---------------------------------------
	_tito.set_physics_process(false)
	_por(_tito, 59, 44, 59, 40)
	_jogador.lanterna_ligada = false
	_por(_pipoca, 20, 6, 20, 14)
	_por(_jogador, 20, 13, 20, 6)
	await _quadros(30)
	var ap_p := _anims(_pipoca)
	_conferir(_pipoca.estado == 3 and ap_p.current_animation == "perseguir",
		"Pipoca vendo o vigia: persegue com a animação 'perseguir' (estado %d, animação %s, ritmo %.2f)" % [
			_pipoca.estado, ap_p.current_animation, ap_p.speed_scale])
	_conferir(_pipoca.olhar.peso > 0.5, "Pipoca perseguindo olha para o vigia (peso %.1f)" % _pipoca.olhar.peso)
	_pipoca._atordoar()
	await _quadros(10)
	_conferir(ap_p.current_animation == "atordoado", "Pipoca atordoada: animação 'atordoado' (%s)" % ap_p.current_animation)
	_pipoca.mudar_estado(1)
	await _quadros(5)

	# --- Tito: congela quando é visto ------------------------------------------
	_tito.set_physics_process(true)
	var ap_t := _anims(_tito)
	_tito.tocar("andar", 1.0)
	_tito.parar(1.0 / 60.0, false)
	_conferir(ap_t.speed_scale == 0.0, "Tito visto: a animação congela (ritmo %.1f)" % ap_t.speed_scale)
	_tito.tocar("perseguir", 2.0)
	_conferir(ap_t.speed_scale > 1.0, "Tito correndo a 2 m/s: animação acelera junto (ritmo %.2f)" % ap_t.speed_scale)

	# --- Modo observação: eles ignoram o vigia ----------------------------------
	Jogo.modo_observacao = true
	_por(_pipoca, 20, 6, 20, 14)
	_por(_jogador, 20, 7.0, 20, 6)   # colado nela, de frente
	_pipoca.mudar_estado(1)
	var inicio_p := _pipoca.global_position
	_por(_tito, 24, 6, 20, 6)
	var inicio_t := _tito.global_position
	await _quadros(240)
	_conferir(Jogo.em_partida, "modo observação: ninguém pega o vigia, mesmo colado (em partida: %s)" % Jogo.em_partida)
	_conferir(_pipoca.estado == 1, "modo observação: Pipoca segue patrulhando (estado %d)" % _pipoca.estado)
	_conferir(_pipoca.global_position.distance_to(inicio_p) > 1.0 and _tito.global_position.distance_to(inicio_t) > 0.4,
		"modo observação: os dois continuam andando (Pipoca %.1f m, Tito %.1f m)" % [
			_pipoca.global_position.distance_to(inicio_p), _tito.global_position.distance_to(inicio_t)])
	_conferir(ap_p.current_animation in ["andar", "procurar"], "modo observação: Pipoca anima andando/procurando (%s)" % ap_p.current_animation)
	Jogo.emitir_ruido(_jogador.global_position, 10.0, 1.0)
	_conferir(_pipoca.estado == 1, "modo observação: ela não vai atrás de barulho do vigia")
	Jogo.modo_observacao = false

	print("[anim] %d falha(s)" % _falhas)
	get_tree().quit(1 if _falhas > 0 else 0)
