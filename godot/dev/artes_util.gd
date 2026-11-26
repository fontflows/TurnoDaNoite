extends RefCounted
## FERRAMENTA DE DESENVOLVIMENTO — não entra no build.
## Funções usadas por validar_artes.gd e captura_artes.gd para achar e medir as
## "peças de leitura" do mapa: os planos de arte (Arte__<nome>) e os textos 3D que
## vêm do Blender (objetos com a propriedade "texto_3d", que o Godot importa como
## metadado "extras").
##
## Ideia de Computação Gráfica usada aqui: uma peça plana (pôster, placa) tem uma
## NORMAL (o lado da frente). Para ela aparecer, a normal tem que apontar para onde o
## jogador anda, e nada pode estar na frente dela nem "colado" nela (z-fighting).


## Todas as peças: [{no, tipo ("arte"/"texto"), nome, texto}]
static func listar(raiz: Node) -> Array[Dictionary]:
	var saida: Array[Dictionary] = []
	for no in raiz.find_children("*", "MeshInstance3D", true, false):
		var m := no as MeshInstance3D
		var nome := String(m.name)
		if nome.begins_with("Arte__"):
			saida.append({"no": m, "tipo": "arte", "nome": nome, "texto": ""})
			continue
		var corpo := texto_3d(m)
		if corpo != "":
			saida.append({"no": m, "tipo": "texto", "nome": nome, "texto": corpo})
	return saida


## Texto escrito num objeto de texto 3D do Blender ("" se não for um).
static func texto_3d(no: Node) -> String:
	for alvo: Object in [no, (no as MeshInstance3D).mesh if no is MeshInstance3D else null]:
		if alvo == null or not alvo.has_meta("extras"):
			continue
		var extras: Variant = alvo.get_meta("extras")
		if extras is Dictionary and (extras as Dictionary).has("texto_3d"):
			return String((extras as Dictionary)["texto_3d"])
	return ""


## Centro, normal (frente), eixos e tamanho de uma peça, no espaço do mundo.
## A normal é a média das normais dos vértices (peças planas). Se ela se anular
## (letras com volume: frente e verso se cancelam), usa a frente do objeto (+Z local).
static func geometria(m: MeshInstance3D) -> Dictionary:
	var xf := m.global_transform
	var soma_n := Vector3.ZERO
	var pontos: Array[Vector3] = []
	if m.mesh:
		for s in m.mesh.get_surface_count():
			var arr := m.mesh.surface_get_arrays(s)
			var vs: PackedVector3Array = arr[Mesh.ARRAY_VERTEX]
			var ns: Variant = arr[Mesh.ARRAY_NORMAL]
			for v in vs:
				pontos.append(xf * v)
			if ns is PackedVector3Array:
				for n in (ns as PackedVector3Array):
					soma_n += xf.basis * n
	var normal := soma_n.normalized() if soma_n.length() > 0.3 * maxf(pontos.size(), 1) else xf.basis.z.normalized()
	var direita := Vector3.UP.cross(normal)
	if direita.length() < 0.1:
		direita = Vector3.RIGHT  # peça deitada (capa em cima da mesa): o "direita" é o X do mundo
	direita = direita.normalized()
	var cima := normal.cross(direita).normalized()
	var mn := Vector3(INF, INF, INF)
	var mx := -mn
	var centro := Vector3.ZERO
	for p in pontos:
		centro += p
	centro /= maxf(pontos.size(), 1)
	for p in pontos:
		var d := p - centro
		var l := Vector3(d.dot(direita), d.dot(cima), d.dot(normal))
		mn = mn.min(l)
		mx = mx.max(l)
	var tam := (mx - mn) if not pontos.is_empty() else Vector3.ZERO
	# centro do retângulo (a média dos vértices puxa para onde há mais vértices nas letras)
	var meio := centro + direita * (mn.x + mx.x) / 2.0 + cima * (mn.y + mx.y) / 2.0 if not pontos.is_empty() else xf.origin
	return {"centro": meio, "normal": normal, "direita": direita, "cima": cima,
		"largura": tam.x, "altura": tam.y, "espessura": tam.z}


## Triângulos (no mundo) de todas as malhas visíveis que tocam a caixa 'caixa',
## menos as do nó 'ignorar' (e dos filhos dele). Cada malha é lida uma vez só (cache).
static func triangulos_perto(malhas: Array, caixa: AABB, ignorar: Node, cache: Dictionary) -> PackedVector3Array:
	var saida := PackedVector3Array()
	for mi in malhas:
		var m := mi as MeshInstance3D
		if ignorar and (m == ignorar or ignorar.is_ancestor_of(m)):
			continue  # a própria peça e as camadas dela (espessura do papelão)
		if not m.is_visible_in_tree() or m.mesh == null:
			continue
		if not (m.global_transform * m.get_aabb()).intersects(caixa):
			continue
		if not cache.has(m):
			var faces := m.mesh.get_faces()
			var xf := m.global_transform
			var mundo := PackedVector3Array()
			mundo.resize(faces.size())
			for i in faces.size():
				mundo[i] = xf * faces[i]
			cache[m] = mundo
		var tri: PackedVector3Array = cache[m]
		for i in range(0, tri.size(), 3):
			var a := tri[i]
			var b := tri[i + 1]
			var c := tri[i + 2]
			var t_caixa := AABB(a, Vector3.ZERO).expand(b).expand(c)
			if t_caixa.grow(0.001).intersects(caixa):
				saida.append(a)
				saida.append(b)
				saida.append(c)
	return saida


## Distância até o primeiro triângulo que o raio (origem, direção unitária) acerta; INF se nenhum.
static func raio(tri: PackedVector3Array, origem: Vector3, direcao: Vector3, alcance: float) -> float:
	var melhor := INF
	for i in range(0, tri.size(), 3):
		var p: Variant = Geometry3D.ray_intersects_triangle(origem, direcao, tri[i], tri[i + 1], tri[i + 2])
		if p is Vector3:
			var d := origem.distance_to(p as Vector3)
			if d < melhor and d <= alcance:
				melhor = d
	return melhor


## Nome curto para arquivos e relatórios ("Arte__lateral_arcade_003" -> "lateral_arcade_003").
static func nome_curto(nome: String) -> String:
	return nome.trim_prefix("Arte__").to_lower().replace(" ", "_")
