class_name Enfeites
extends RefCounted
## Desenhos simples feitos só com formas geométricas (círculos, elipses, polígonos e linhas),
## usados pelas artes feitas por código (ArteExterna) enquanto a imagem do gerador não existe.
##
## Tudo é desenhado num "espaço de projeto" e escalado para o tamanho da imagem:
## posições em fração da largura/altura (0 a 1) e raios em fração da LARGURA.
## Cada desenho usa uma semente fixa, então sai sempre igual.


static func desenhar(c: CanvasItem, tipo: String, s: Vector2, fundo: Color, semente: int) -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = semente
	match tipo:
		"estrelas":
			_estrelas(c, s, rng)
		"piratas":
			_piratas(c, s, rng)
		"princesas":
			_princesas(c, s, rng)
		"baloes":
			_baloes(c, s, rng)
		"mapa":
			_mapa(c, s, rng)
		"urso":
			_urso(c, s)
		"foto_riscada":
			_foto_riscada(c, s, rng)
	# Moldura fina (todo cartaz impresso tem uma margem), menos na figura recortada.
	if tipo != "urso":
		c.draw_rect(Rect2(Vector2.ZERO, s).grow(-s.x * 0.025), fundo.lightened(0.35), false, maxf(s.x * 0.008, 2.0))


# ---------------------------------------------------------------------------
# Formas básicas
# ---------------------------------------------------------------------------

## Ponto em fração do tamanho (0..1) -> pixels.
static func P(s: Vector2, x: float, y: float) -> Vector2:
	return Vector2(x * s.x, y * s.y)


static func elipse_pontos(centro: Vector2, raio: Vector2, giro := 0.0, n := 40) -> PackedVector2Array:
	var pts := PackedVector2Array()
	for k in n:
		var a := TAU * k / n
		pts.append(centro + Vector2(cos(a) * raio.x, sin(a) * raio.y).rotated(giro))
	return pts


static func elipse(c: CanvasItem, centro: Vector2, raio: Vector2, cor: Color, giro := 0.0) -> void:
	c.draw_colored_polygon(elipse_pontos(centro, raio, giro), cor)


static func estrela(c: CanvasItem, centro: Vector2, r_fora: float, r_dentro: float, cor: Color, giro := 0.0, pontas := 5) -> void:
	var pts := PackedVector2Array()
	for k in pontas * 2:
		var a := giro - PI / 2.0 + k * PI / pontas
		var r := r_fora if k % 2 == 0 else r_dentro
		pts.append(centro + Vector2(cos(a), sin(a)) * r)
	c.draw_colored_polygon(pts, cor)


# ---------------------------------------------------------------------------
# Desenhos
# ---------------------------------------------------------------------------

static func _estrelas(c: CanvasItem, s: Vector2, rng: RandomNumberGenerator) -> void:
	for i in 45:
		var p := Vector2(rng.randf() * s.x, rng.randf() * s.y)
		var r := s.x * rng.randf_range(0.008, 0.025)
		estrela(c, p, r, r * 0.45, Color(1, 0.95, 0.6, rng.randf_range(0.5, 1.0)), rng.randf() * TAU)
	# Lua crescente: um círculo amarelo "mordido" por outro da cor do céu.
	var lua := P(s, 0.66, 0.44)
	c.draw_circle(lua, s.x * 0.17, Color(1, 0.88, 0.45))
	c.draw_circle(lua + Vector2(s.x * 0.08, -s.x * 0.04), s.x * 0.15, Color(0.08, 0.1, 0.3))
	# Planeta com anel
	var planeta := P(s, 0.3, 0.56)
	c.draw_polyline(elipse_pontos(planeta, Vector2(s.x * 0.16, s.x * 0.04), -0.3, 48) + PackedVector2Array([planeta + Vector2(s.x * 0.16, 0).rotated(-0.3)]),
		Color(0.95, 0.75, 0.4), s.x * 0.012)
	c.draw_circle(planeta, s.x * 0.09, Color(0.95, 0.5, 0.3))
	# Foguetinho
	var f := P(s, 0.28, 0.36)
	var giro := 0.6
	c.draw_colored_polygon(PackedVector2Array([f + Vector2(0, -s.x * 0.09).rotated(giro), f + Vector2(s.x * 0.035, -s.x * 0.03).rotated(giro),
		f + Vector2(s.x * 0.035, s.x * 0.06).rotated(giro), f + Vector2(-s.x * 0.035, s.x * 0.06).rotated(giro),
		f + Vector2(-s.x * 0.035, -s.x * 0.03).rotated(giro)]), Color(0.9, 0.9, 0.95))
	c.draw_circle(f + Vector2(0, -s.x * 0.01).rotated(giro), s.x * 0.015, Color(0.3, 0.6, 0.95))
	elipse(c, f + Vector2(0, s.x * 0.085).rotated(giro), Vector2(s.x * 0.022, s.x * 0.035), Color(1, 0.55, 0.15), giro)


static func _piratas(c: CanvasItem, s: Vector2, rng: RandomNumberGenerator) -> void:
	c.draw_circle(P(s, 0.2, 0.33), s.x * 0.08, Color(1, 0.85, 0.3))
	for nuvem in [Vector2(0.65, 0.3), Vector2(0.8, 0.36)]:
		for k in 3:
			c.draw_circle(P(s, nuvem.x + 0.05 * k, nuvem.y), s.x * 0.05, Color(1, 1, 1, 0.9))
	# Mar com ondas
	var mar := PackedVector2Array()
	for k in 33:
		var x := s.x * k / 32.0
		mar.append(Vector2(x, s.y * 0.6 + sin(k * 0.9) * s.y * 0.012))
	mar.append(Vector2(s.x, s.y * 0.74))
	mar.append(Vector2(0, s.y * 0.74))
	c.draw_colored_polygon(mar, Color(0.12, 0.35, 0.65))
	# Navio: casco, mastro, velas e bandeira
	var base := P(s, 0.5, 0.59)
	var w := s.x * 0.3
	c.draw_colored_polygon(PackedVector2Array([base + Vector2(-w, -s.y * 0.04), base + Vector2(w, -s.y * 0.04),
		base + Vector2(w * 0.75, s.y * 0.03), base + Vector2(-w * 0.75, s.y * 0.03)]), Color(0.45, 0.25, 0.1))
	c.draw_line(base + Vector2(0, -s.y * 0.04), base + Vector2(0, -s.y * 0.3), Color(0.35, 0.2, 0.08), s.x * 0.015)
	c.draw_colored_polygon(PackedVector2Array([base + Vector2(-s.x * 0.01, -s.y * 0.28), base + Vector2(-s.x * 0.2, -s.y * 0.08),
		base + Vector2(-s.x * 0.01, -s.y * 0.08)]), Color(0.97, 0.95, 0.88))
	c.draw_colored_polygon(PackedVector2Array([base + Vector2(s.x * 0.01, -s.y * 0.26), base + Vector2(s.x * 0.17, -s.y * 0.1),
		base + Vector2(s.x * 0.01, -s.y * 0.1)]), Color(0.97, 0.95, 0.88))
	var bandeira := base + Vector2(0, -s.y * 0.33)
	c.draw_rect(Rect2(bandeira, Vector2(s.x * 0.1, s.y * 0.04)), Color(0.08, 0.08, 0.08))
	c.draw_circle(bandeira + Vector2(s.x * 0.05, s.y * 0.02), s.x * 0.014, Color(1, 1, 1))
	for k in 6:
		c.draw_circle(Vector2(rng.randf() * s.x, s.y * rng.randf_range(0.63, 0.72)), s.x * 0.008, Color(1, 1, 1, 0.6))


static func _princesas(c: CanvasItem, s: Vector2, rng: RandomNumberGenerator) -> void:
	var lilas := Color(0.82, 0.72, 0.95)
	var rosa := Color(0.9, 0.35, 0.6)
	# Castelo: corpo, duas torres com telhado e porta em arco
	c.draw_rect(Rect2(P(s, 0.3, 0.46), P(s, 0.4, 0.26)), lilas)
	for x in [0.22, 0.7]:
		c.draw_rect(Rect2(P(s, x, 0.4), P(s, 0.08, 0.32)), lilas.darkened(0.08))
		c.draw_colored_polygon(PackedVector2Array([P(s, x - 0.02, 0.4), P(s, x + 0.1, 0.4), P(s, x + 0.04, 0.29)]), rosa)
	for k in 4:
		c.draw_rect(Rect2(P(s, 0.3 + 0.1 * k, 0.43), P(s, 0.06, 0.03)), lilas)
	c.draw_rect(Rect2(P(s, 0.45, 0.62), P(s, 0.1, 0.1)), Color(0.45, 0.25, 0.35))
	c.draw_circle(P(s, 0.5, 0.62), s.x * 0.05, Color(0.45, 0.25, 0.35))
	# Coroa em cima
	var cx := s.x * 0.5
	var y0 := s.y * 0.36
	var pts := PackedVector2Array([Vector2(cx - s.x * 0.12, y0), Vector2(cx - s.x * 0.12, y0 - s.y * 0.06), Vector2(cx - s.x * 0.06, y0 - s.y * 0.03),
		Vector2(cx, y0 - s.y * 0.08), Vector2(cx + s.x * 0.06, y0 - s.y * 0.03), Vector2(cx + s.x * 0.12, y0 - s.y * 0.06),
		Vector2(cx + s.x * 0.12, y0)])
	c.draw_colored_polygon(pts, Color(1, 0.8, 0.25))
	for k in 3:
		c.draw_circle(Vector2(cx + (k - 1) * s.x * 0.07, y0 - s.y * 0.015), s.x * 0.014, [Color(0.9, 0.2, 0.4), Color(0.3, 0.6, 1), Color(0.9, 0.2, 0.4)][k])
	for k in 14:
		var p := Vector2(rng.randf() * s.x, rng.randf_range(0.25, 0.75) * s.y)
		estrela(c, p, s.x * 0.02, s.x * 0.005, Color(1, 1, 1, 0.85), 0.0, 4)


static func _baloes(c: CanvasItem, s: Vector2, rng: RandomNumberGenerator) -> void:
	var cores := [Color(0.95, 0.25, 0.3), Color(1, 0.8, 0.2), Color(0.3, 0.65, 1), Color(0.4, 0.85, 0.45), Color(0.85, 0.45, 0.95)]
	var no := P(s, 0.5, 0.72)
	for k in 5:
		var centro := P(s, 0.2 + 0.15 * k, 0.4 + (0.06 if k % 2 else 0.0))
		c.draw_line(centro + Vector2(0, s.x * 0.1), no, Color(1, 1, 1, 0.8), maxf(s.x * 0.003, 1.0))
		elipse(c, centro, Vector2(s.x * 0.075, s.x * 0.095), cores[k])
		elipse(c, centro + Vector2(-s.x * 0.025, -s.x * 0.035), Vector2(s.x * 0.015, s.x * 0.025), Color(1, 1, 1, 0.45))
	for k in 60:
		var p := Vector2(rng.randf() * s.x, rng.randf() * s.y)
		c.draw_rect(Rect2(p, Vector2(s.x * 0.012, s.x * 0.006)), cores[k % cores.size()])


static func _mapa(c: CanvasItem, s: Vector2, rng: RandomNumberGenerator) -> void:
	# Ilha de contorno irregular
	var ilha := PackedVector2Array()
	var centro := P(s, 0.5, 0.58)
	for k in 48:
		var a := TAU * k / 48
		var r := 1.0 + 0.12 * sin(a * 3.0 + 1.0) + 0.06 * sin(a * 7.0)
		ilha.append(centro + Vector2(cos(a) * s.x * 0.32, sin(a) * s.y * 0.26) * r)
	c.draw_colored_polygon(ilha, Color(0.78, 0.66, 0.42))
	c.draw_polyline(ilha + PackedVector2Array([ilha[0]]), Color(0.45, 0.3, 0.15), maxf(s.x * 0.005, 2.0))
	# Coqueiro
	var tronco := P(s, 0.32, 0.55)
	c.draw_line(tronco, tronco + Vector2(s.x * 0.02, -s.y * 0.14), Color(0.45, 0.3, 0.15), s.x * 0.012)
	for k in 5:
		var a := -PI / 2 + (k - 2) * 0.55
		var topo := tronco + Vector2(s.x * 0.02, -s.y * 0.14)
		c.draw_line(topo, topo + Vector2(cos(a), sin(a) + 0.4) * s.x * 0.07, Color(0.25, 0.5, 0.2), s.x * 0.012)
	# Caminho pontilhado até o X
	var a0 := P(s, 0.25, 0.72)
	var a1 := P(s, 0.45, 0.48)
	var a2 := P(s, 0.68, 0.55)
	for k in 18:
		var t := k / 17.0
		var p := a0.lerp(a1, t).lerp(a1.lerp(a2, t), t)
		if k % 2 == 0:
			c.draw_circle(p, s.x * 0.007, Color(0.4, 0.2, 0.1))
	var d := s.x * 0.03
	c.draw_line(a2 + Vector2(-d, -d), a2 + Vector2(d, d), Color(0.8, 0.1, 0.1), s.x * 0.012)
	c.draw_line(a2 + Vector2(-d, d), a2 + Vector2(d, -d), Color(0.8, 0.1, 0.1), s.x * 0.012)
	# Rosa dos ventos
	var rv := P(s, 0.85, 0.78)
	c.draw_arc(rv, s.x * 0.05, 0, TAU, 24, Color(0.4, 0.25, 0.12), maxf(s.x * 0.004, 1.0))
	estrela(c, rv, s.x * 0.06, s.x * 0.012, Color(0.4, 0.25, 0.12), 0.0, 4)
	for k in 8:
		c.draw_circle(Vector2(rng.randf() * s.x, rng.randf_range(0.25, 0.95) * s.y), s.x * 0.004, Color(0.4, 0.3, 0.2, 0.4))


static func _foto_riscada(c: CanvasItem, s: Vector2, rng: RandomNumberGenerator) -> void:
	var foto := Rect2(P(s, 0.22, 0.26), P(s, 0.56, 0.44))
	c.draw_rect(foto, Color(0.55, 0.6, 0.62))
	c.draw_circle(foto.get_center() + Vector2(0, -foto.size.y * 0.12), foto.size.x * 0.18, Color(0.75, 0.62, 0.5))
	elipse(c, foto.get_center() + Vector2(0, foto.size.y * 0.35), Vector2(foto.size.x * 0.32, foto.size.y * 0.25), Color(0.25, 0.3, 0.45))
	for k in 14:
		var y := foto.position.y + foto.size.y * (0.15 + 0.05 * k)
		c.draw_line(Vector2(foto.position.x + rng.randf() * 20, y), Vector2(foto.end.x - rng.randf() * 20, y + rng.randf_range(-20, 20)),
			Color(0.05, 0.05, 0.1, 0.9), maxf(s.x * 0.012, 2.0))


## Figura de papelão do Tito (silhueta simples) sobre fundo VERDE: o shader apaga o verde.
## Ordem: 1) borda branca de "impressão" em volta de tudo, 2) contorno escuro, 3) cores, 4) detalhes.
static func _urso(c: CanvasItem, s: Vector2) -> void:
	var k := Vector2(s.x / 432.0, s.y / 768.0)  # projeto feito numa tela de 432 x 768
	var m := minf(k.x, k.y)
	var marrom := Color(0.62, 0.39, 0.22)
	var bege := Color(0.95, 0.82, 0.62)
	# [centro, raio (x, y), cor, giro] das partes que formam a silhueta
	var partes := [
		[Vector2(140, 150), Vector2(40, 40), marrom, 0.0], [Vector2(292, 150), Vector2(40, 40), marrom, 0.0],
		[Vector2(216, 480), Vector2(140, 170), marrom, 0.0],
		[Vector2(165, 650), Vector2(52, 70), marrom, 0.0], [Vector2(267, 650), Vector2(52, 70), marrom, 0.0],
		[Vector2(158, 712), Vector2(62, 30), marrom, 0.0], [Vector2(274, 712), Vector2(62, 30), marrom, 0.0],
		[Vector2(100, 330), Vector2(34, 85), marrom, 0.55], [Vector2(80, 252), Vector2(32, 32), marrom, 0.0],
		[Vector2(338, 452), Vector2(34, 85), marrom, -0.35], [Vector2(362, 525), Vector2(30, 30), marrom, 0.0],
		[Vector2(372, 506), Vector2(64, 16), Color(0.75, 0.75, 0.78), 0.0],
		[Vector2(216, 215), Vector2(98, 98), marrom, 0.0],
		[Vector2(216, 88), Vector2(58, 40), Color(0.97, 0.97, 0.95), 0.0],
	]
	for passo in 3:
		for p: Array in partes:
			var extra: float = [12.0, 3.5, 0.0][passo]
			var cor: Color = [Color(1, 1, 1), Color(0.18, 0.1, 0.06), p[2]][passo]
			elipse(c, (p[0] as Vector2) * k, ((p[1] as Vector2) + Vector2(extra, extra)) * m, cor, p[3])
	# Chapéu de pizzaiolo: faixa de baixo
	c.draw_rect(Rect2(Vector2(166, 104) * k, Vector2(100, 30) * m), Color(0.92, 0.92, 0.9))
	# Orelhas por dentro, barriga e focinho
	for x in [140.0, 292.0]:
		c.draw_circle(Vector2(x, 152) * k, 22 * m, bege)
	elipse(c, Vector2(216, 500) * k, Vector2(92, 118) * m, bege)
	elipse(c, Vector2(216, 252) * k, Vector2(46, 34) * m, bege)
	elipse(c, Vector2(216, 236) * k, Vector2(18, 13) * m, Color(0.1, 0.06, 0.05))
	c.draw_arc(Vector2(216, 250) * k, 20 * m, 0.35, PI - 0.35, 12, Color(0.25, 0.12, 0.08), 4 * m)
	# Olhos com brilho e bochechas
	for x in [178.0, 254.0]:
		c.draw_circle(Vector2(x, 200) * k, 17 * m, Color(1, 1, 1))
		c.draw_circle(Vector2(x + 2, 203) * k, 10 * m, Color(0.08, 0.06, 0.05))
		c.draw_circle(Vector2(x + 6, 198) * k, 3.5 * m, Color(1, 1, 1))
		c.draw_circle(Vector2(x - 28 if x < 216 else x + 28, 240) * k, 14 * m, Color(0.95, 0.45, 0.45, 0.6))
	# Lenço vermelho e gravata borboleta amarela
	c.draw_colored_polygon(PackedVector2Array([Vector2(176, 322) * k, Vector2(256, 322) * k, Vector2(216, 372) * k]), Color(0.85, 0.15, 0.15))
	c.draw_colored_polygon(PackedVector2Array([Vector2(216, 318) * k, Vector2(170, 294) * k, Vector2(170, 342) * k]), Color(0.95, 0.75, 0.15))
	c.draw_colored_polygon(PackedVector2Array([Vector2(216, 318) * k, Vector2(262, 294) * k, Vector2(262, 342) * k]), Color(0.95, 0.75, 0.15))
	c.draw_circle(Vector2(216, 318) * k, 11 * m, Color(0.8, 0.6, 0.1))
	# Pizza na bandeja e almofadinhas dos pés
	elipse(c, Vector2(372, 498) * k, Vector2(48, 11) * m, Color(0.95, 0.7, 0.3))
	for x in [350.0, 372.0, 394.0]:
		c.draw_circle(Vector2(x, 497) * k, 5 * m, Color(0.75, 0.15, 0.1))
	for x in [158.0, 274.0]:
		elipse(c, Vector2(x, 716) * k, Vector2(30, 14) * m, bege)
