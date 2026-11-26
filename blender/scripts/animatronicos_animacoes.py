"""
animatronicos_animacoes.py — etapa 2 dos animatrônicos finais: animações, GIFs e exportação para o Godot.

Usa o rig do endoesqueleto do colega (juntas dele + ossos essenciais que faltavam: mandíbula, olhos,
pálpebras, dedos, orelhas e saia). As animações são geradas quadro a quadro:
  - Pernas com IK (alvos nos pés, joelho apontando para a frente) e pés PLANTADOS: durante o apoio o pé
    vai para trás exatamente na velocidade de referência da animação (no jogo, o AnimationPlayer anda
    na proporção velocidade_real / velocidade_de_referência, então o pé não desliza).
  - O IK é "assado" (a pose visual de cada quadro vira chave de cada osso) e depois removido.
  - Estilo animatrônico: braços, cabeça, mandíbula e dedos andam em trancos de servo (seguram, pulam
    para a próxima posição, tremem um pouco ao parar); uma junta às vezes trava.

Animações: parado, andar, perseguir, procurar, jumpscare (+ atordoado na Pipoca).

Rodar (na pasta TurnoDaNoite; precisa de blender/personagens/<nome>_final.blend da animatronicos_v2.py):
    blender --background --factory-startup --python blender/scripts/animatronicos_animacoes.py -- tito gifs=<pasta> exportar
Saídas: blender/personagens/<nome>_final.blend (com as ações), godot/assets/personagens/<nome>.glb,
        godot/assets/personagens/animacoes_velocidades.json (velocidade de referência de cada animação).
"""

import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import animatronicos_finais as A  # noqa: E402
import animatronicos_v2 as V  # noqa: E402

FPS = 30
FRENTE = Vector((0, -1, 0))
X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)


def suave(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def servo(fn, t, passo, desloc=0, transicao=2.0, tremor=0.25):
    """
    Movimento de servo: segura a posição, pula para a próxima em 'transicao' quadros e treme um pouco
    ao parar. fn(t) é a curva lisa; o resultado continua cíclico se o ciclo for múltiplo de 'passo'.
    """
    k = math.floor((t - desloc) / passo)
    t0 = k * passo + desloc
    a, b = fn(t0 - passo), fn(t0)
    dt = t - t0
    v = a + (b - a) * suave(dt / transicao)
    if tremor:
        v += tremor * (b - a) * math.exp(-dt * 0.8) * math.sin(dt * 2.8)
    return v


class Animador:
    def __init__(self, chave):
        self.chave = chave
        self.N = "Tito" if chave == "tito" else "Pipoca"
        self.arm = bpy.data.objects[f"{self.N}_Rig"]
        self.arm.animation_data_create()
        self.arm.animation_data.action = None
        V.pose_descanso(self.arm, chave)
        bpy.context.view_layer.update()
        self.base = {pb.name: pb.rotation_quaternion.copy() for pb in self.arm.pose.bones}
        for pb in self.arm.pose.bones:
            pb.rotation_mode = "QUATERNION"
        self.lados = ("L", "R")
        self.velocidades = {}
        self._preparar_ik()

    # --- rotações "em eixo do mundo na pose de descanso" (como girar() da v1)
    def q_local(self, osso, eixo, graus):
        pb = self.arm.pose.bones[osso]
        rest = (self.arm.matrix_world.to_3x3() @ pb.bone.matrix_local.to_3x3()).normalized()
        q = Matrix.Rotation(math.radians(graus), 3, Vector(eixo))
        return (rest.inverted() @ q @ rest).to_quaternion()

    def tem(self, osso):
        return osso in self.arm.pose.bones

    # --- IK das pernas
    def _preparar_ik(self):
        arm = self.arm
        mw = arm.matrix_world
        self.alvos = {}
        for lado in self.lados:
            pe = arm.pose.bones[f"pe.{lado}"]
            can = arm.pose.bones[f"canela.{lado}"]
            alvo = bpy.data.objects.new(f"IK_Pe.{lado}", None)
            polo = bpy.data.objects.new(f"IK_Joelho.{lado}", None)
            for o in (alvo, polo):
                bpy.context.scene.collection.objects.link(o)
            alvo.matrix_world = mw @ pe.bone.matrix_local
            polo.location = mw @ can.bone.head_local + FRENTE * 0.8
            c = can.constraints.new("IK")
            c.target = alvo
            c.pole_target = polo
            c.chain_count = 2
            c.use_tail = True
            r = pe.constraints.new("COPY_ROTATION")
            r.target = alvo
            self.alvos[lado] = dict(alvo=alvo, polo=polo, ik=c, tornozelo=(mw @ pe.bone.matrix_local).to_translation(),
                                    rot=(mw @ pe.bone.matrix_local).to_3x3().normalized(), polo_base=polo.location.copy())
        self._calibrar_polo()

    def _erro_perna(self):
        bpy.context.view_layer.update()
        e = 0.0
        for lado in self.lados:
            for n in (f"coxa.{lado}", f"canela.{lado}"):
                pb = self.arm.pose.bones[n]
                e += pb.matrix.to_quaternion().rotation_difference(pb.bone.matrix_local.to_quaternion()).angle
        return e

    def _calibrar_polo(self):
        """Ângulo do polo que, agachado, leva o joelho para a FRENTE e sem torcer a perna para o lado."""
        def nota(graus):
            self._polo(graus)
            self.pose({}, (0, 0, -0.06))
            n = 0.0
            for lado in self.lados:
                pb = self.arm.pose.bones
                quadril = self.arm.matrix_world @ pb[f"coxa.{lado}"].head
                joelho = self.arm.matrix_world @ pb[f"canela.{lado}"].head
                n += joelho.y + 3 * abs(joelho.x - quadril.x)  # frente é −Y
            return n
        melhor = min(range(-180, 180, 5), key=nota)
        self._polo(melhor)
        self._zerar()
        print(f"[anim] {self.N}: ângulo do polo do joelho {melhor}°")

    def _polo(self, graus):
        for lado in self.lados:
            self.alvos[lado]["ik"].pole_angle = math.radians(graus)
        return graus

    def _zerar(self):
        for pb in self.arm.pose.bones:
            pb.rotation_quaternion = self.base[pb.name].copy()
            pb.location = (0, 0, 0)
        for lado in self.lados:
            a = self.alvos[lado]
            a["alvo"].matrix_world = Matrix.Translation(a["tornozelo"]) @ a["rot"].to_4x4()

    # --- um quadro
    def pose(self, giros, raiz=(0, 0, 0), pes=None):
        """
        giros: {osso: [(eixo, graus), ...]} somados à pose de exibição; raiz: deslocamento do quadril
        (x lado, y frente, z cima, em metros); pes: {lado: (x lado, y frente, z cima, inclinação graus)}.
        Devolve as transformações LOCAIS visuais de todos os ossos (já com o IK resolvido).
        """
        self._zerar()
        for osso, lista in giros.items():
            if not self.tem(osso):
                continue
            pb = self.arm.pose.bones[osso]
            q = pb.rotation_quaternion.copy()
            for eixo, graus in lista:
                q = self.q_local(osso, eixo, graus) @ q
            pb.rotation_quaternion = q
        # pré-dobra do joelho: na pose de descanso a perna está reta e o IK não saberia para que lado dobrar
        for lado in self.lados:
            for osso, graus in ((f"coxa.{lado}", 6.0), (f"canela.{lado}", -12.0)):
                pb = self.arm.pose.bones[osso]
                pb.rotation_quaternion = self.q_local(osso, X, graus) @ pb.rotation_quaternion
        quadril = self.arm.pose.bones["quadril"]
        desloc = Vector((raiz[0], -raiz[1], raiz[2]))
        quadril.location = quadril.bone.matrix_local.to_3x3().inverted() @ desloc
        for lado in self.lados:
            a = self.alvos[lado]
            dx, dy, dz, incl = (pes or {}).get(lado, (0, 0, 0, 0))
            pos = a["tornozelo"] + Vector((dx, -dy, dz))
            rot = Matrix.Rotation(math.radians(incl), 3, Vector(X)) @ a["rot"]
            a["alvo"].matrix_world = Matrix.Translation(pos) @ rot.to_4x4()
            a["polo"].location = a["polo_base"] + Vector((dx, -dy, 0))
        bpy.context.view_layer.update()
        for lado in self.lados:
            pb = self.arm.pose.bones[f"canela.{lado}"]
            erro = ((self.arm.matrix_world @ pb.tail) - self.alvos[lado]["alvo"].matrix_world.to_translation()).length
            self.erro_max = max(getattr(self, "erro_max", 0.0), erro)
        locais = {}
        for pb in self.arm.pose.bones:
            m = self.arm.convert_space(pose_bone=pb, matrix=pb.matrix, from_space="POSE", to_space="LOCAL")
            locais[pb.name] = (m.to_quaternion(), m.to_translation())
        return locais

    def gravar(self, nome, quadros, loop=True):
        """quadros: lista de dicionários de pose (um por quadro). Cria a ação 'nome'."""
        acao = bpy.data.actions.new(nome)
        acao.use_fake_user = True
        self.arm.animation_data.action = acao
        for i, locais in enumerate(quadros):
            for pb in self.arm.pose.bones:
                q, t = locais[pb.name]
                pb.rotation_quaternion = q
                pb.location = t
                pb.keyframe_insert("rotation_quaternion", frame=i + 1, group=pb.name)
                pb.keyframe_insert("location", frame=i + 1, group=pb.name)
        acao.frame_range = (1, len(quadros) + (1 if loop else 0))
        if loop:
            # quadro extra igual ao primeiro: o ciclo fecha sem pulo
            for pb in self.arm.pose.bones:
                q, t = quadros[0][pb.name]
                pb.rotation_quaternion = q
                pb.location = t
                pb.keyframe_insert("rotation_quaternion", frame=len(quadros) + 1, group=pb.name)
                pb.keyframe_insert("location", frame=len(quadros) + 1, group=pb.name)
        self.arm.animation_data.action = None
        print(f"[anim] {self.N}: ação '{nome}' com {len(quadros)} quadros; maior distância pé-alvo do IK "
              f"{getattr(self, 'erro_max', 0.0) * 100:.1f} cm (pé escorrega se passar de ~1 cm)")
        self.erro_max = 0.0
        return acao

    def finalizar_ik(self):
        for lado in self.lados:
            for n in (f"canela.{lado}", f"pe.{lado}"):
                pb = self.arm.pose.bones[n]
                for c in list(pb.constraints):
                    pb.constraints.remove(c)
            for k in ("alvo", "polo"):
                bpy.data.objects.remove(self.alvos[lado][k])


# ---------------------------------------------------------------------------------------------
# Partes comuns das animações

def ciclo_pe(fase, beta, D, altura, calcanhar=18.0):
    """Trajetória do pé num ciclo (fase 0..1): apoio (vai para trás colado no chão) e balanço."""
    fase %= 1.0
    if fase < beta:
        s = fase / beta
        x = D / 2 - D * s
        z, incl = 0.0, 0.0
        if s < 0.12:
            incl = -10.0 * (1 - s / 0.12)  # toca o chão com o calcanhar (ponta para cima)
        if s > 0.8:
            k = (s - 0.8) / 0.2
            z = 0.025 * k
            incl = calcanhar * k  # calcanhar sobe antes de sair do chão
        return x, z, incl
    s = (fase - beta) / (1 - beta)
    x = -D / 2 + D * (0.5 - 0.5 * math.cos(math.pi * s))
    z = 0.025 * (1 - s) ** 3 + altura * math.sin(math.pi * s) ** 1.2
    incl = calcanhar * (1 - s) ** 2 - 10.0 * math.sin(math.pi * s) ** 2 - 10.0 * s ** 4
    return x, z, incl


def dedos(giros, lado, dobra, polegar=None, abre=0.0):
    """Dobra os dedos (graus) — positivo fecha a mão, negativo abre."""
    sinal = 1 if lado == "L" else -1
    for g in ("dedo_meio", "dedo_a", "dedo_b"):
        giros.setdefault(f"{g}_1.{lado}", []).append((Y, sinal * dobra * 0.8))
        giros.setdefault(f"{g}_2.{lado}", []).append((Y, sinal * dobra))
    if abre:
        giros.setdefault(f"dedo_a_1.{lado}", []).append((Z, -abre))
        giros.setdefault(f"dedo_b_1.{lado}", []).append((Z, abre))
    p = dobra * 0.6 if polegar is None else polegar
    giros.setdefault(f"polegar_1.{lado}", []).append((Z, sinal * p * 0.6))
    giros.setdefault(f"polegar_2.{lado}", []).append((Z, sinal * p))


def add(giros, osso, eixo, graus):
    giros.setdefault(osso, []).append((eixo, graus))


def piscar(giros, t, momentos, duracao=6, fechado=38.0):
    """Pálpebras de cima descem (e as de baixo sobem um pouco) nos 'momentos' (quadros)."""
    k = 0.0
    for m0 in momentos:
        d = t - m0
        if 0 <= d <= duracao:
            k = max(k, math.sin(math.pi * d / duracao))
    if k:
        for lado in ("L", "R"):
            add(giros, f"palpebra_sup.{lado}", X, fechado * k)
            add(giros, f"palpebra_inf.{lado}", X, -10 * k)


def andar_generico(an, quadros_ciclo, ciclos, beta, D, altura_passo, agachar, cfg, extra=None):
    """Ciclo de passos com pés plantados. cfg: amplitudes do corpo e dos braços. extra(t, fase, giros)."""
    T = quadros_ciclo
    total = T * ciclos
    v_ref = D / (beta * T / FPS)
    largura_pe = cfg.get("largura_pe", 0.0)
    resultado = []
    for t in range(total):
        fase = t / T
        giros = {}
        pes = {}
        for lado, desloc in (("L", 0.0), ("R", 0.5)):
            x, z, incl = ciclo_pe(fase + desloc, beta, D, altura_passo, cfg.get("calcanhar", 18.0))
            pes[lado] = ((largura_pe if lado == "L" else -largura_pe), x, z, incl)
        fL = 2 * math.pi * (fase - beta / 2)
        bob = -agachar + cfg["bob"] * math.cos(2 * fL) + cfg.get("voo", 0.0) * max(0.0, -math.cos(2 * fL))
        lado_x = cfg["balanco"] * math.cos(fL)
        raiz = (lado_x, cfg.get("avanco", 0.0), bob)
        add(giros, "quadril", Y, cfg["rolar"] * math.cos(fL))
        add(giros, "quadril", Z, cfg["torcer"] * math.sin(2 * math.pi * fase))
        add(giros, "quadril", X, cfg.get("inclinar_quadril", 0.0))
        # tronco: compensa a torção, inclina para a frente
        add(giros, "tronco", Z, -cfg["torcer"] * 1.4 * math.sin(2 * math.pi * fase))
        add(giros, "tronco", Y, -cfg["rolar"] * 0.7 * math.cos(fL))
        add(giros, "tronco", X, cfg["inclinar"])
        # braços em trancos de servo: ombro, cotovelo e punho em tempos diferentes
        for lado, sinal in (("L", -1), ("R", 1)):
            def ombro(tt, sinal=sinal):
                return cfg["braco"] * sinal * math.cos(2 * math.pi * tt / T) + cfg.get("braco_frente", 0.0)

            def cotovelo(tt, sinal=sinal):
                return cfg["cotovelo"] + cfg["cotovelo_amp"] * (0.5 - 0.5 * sinal * math.cos(2 * math.pi * (tt / T - 0.12)))

            def punho(tt, sinal=sinal):
                return cfg["punho"] * sinal * math.cos(2 * math.pi * (tt / T - 0.25))
            passo = cfg["passo_servo"]
            add(giros, f"braco.{lado}", X, servo(ombro, t, passo, 0))
            add(giros, f"braco.{lado}", Y, cfg.get("cotovelos_abertos", 0.0) * (1 if lado == "L" else -1))
            add(giros, f"antebraco.{lado}", X, servo(cotovelo, t, passo, 1))
            add(giros, f"mao.{lado}", X, servo(punho, t, passo, 2))
            dedos(giros, lado, servo(lambda tt: cfg["dedos"] + 10 * math.sin(2 * math.pi * tt / T + (0 if lado == "L" else 2)), t, passo, 1))
        # cabeça estabilizada (compensa o balanço) em trancos
        add(giros, "pescoco", X, servo(lambda tt: cfg.get("cabeca_frente", 0.0) + cfg["cabeca_bob"] * math.cos(4 * math.pi * (tt / T - beta / 2)), t, cfg["passo_servo"], 1))
        add(giros, "cabeca", Y, servo(lambda tt: -cfg["rolar"] * 0.8 * math.cos(2 * math.pi * (tt / T - beta / 2)), t, cfg["passo_servo"] * 2, 0))
        if extra:
            extra(t, fase, giros, raiz)
        resultado.append(an.pose(giros, raiz, pes))
    return resultado, v_ref


# ---------------------------------------------------------------------------------------------
# TITO: pesado, lento, balançando o corpo

def tito_parado(an):
    q = []
    rnd = random.Random(3)
    olhar = [0, 0, 14, 14, 14, -10, -10, 0]  # cabeça vira devagar, em trancos (8 posições por ciclo)
    for t in range(120):
        g = {}
        fase = t / 120
        add(g, "quadril", Y, 1.4 * math.sin(2 * math.pi * fase))
        add(g, "tronco", X, servo(lambda tt: 1.2 * math.sin(2 * math.pi * tt / 60), t, 6, 0))  # "respira"
        add(g, "pescoco", Z, servo(lambda tt: olhar[int(tt // 15) % 8], t, 15, 0, transicao=4, tremor=0.3))
        add(g, "cabeca", X, servo(lambda tt: 3 * math.sin(2 * math.pi * tt / 40), t, 10, 3))
        add(g, "mandibula", X, -servo(lambda tt: 6.0 if 55 <= tt % 120 < 61 else 0.0, t, 3, 0, 1.0, 0.4))
        for lado in ("L", "R"):
            dedos(g, lado, servo(lambda tt, lado=lado: 15 + (12 if (tt + (0 if lado == "L" else 37)) % 120 < 8 else 0), t, 4, 0))
            add(g, f"antebraco.{lado}", X, 8 + servo(lambda tt: 3 * math.sin(2 * math.pi * tt / 120), t, 12, 5))
        piscar(g, t, [30, 95], 7, 30)
        q.append(an.pose(g, (0.012 * math.sin(2 * math.pi * fase), 0, -0.035)))
    return q


def tito_andar(an):
    cfg = dict(bob=0.012, balanco=0.035, rolar=5.0, torcer=6.0, inclinar=4.0, braco=22.0, cotovelo=14.0,
               cotovelo_amp=16.0, punho=10.0, dedos=18.0, cabeca_bob=2.0, passo_servo=4, largura_pe=0.0, calcanhar=14.0)

    def extra(t, fase, g, raiz):
        # o cotovelo esquerdo TRAVA por meio segundo no segundo ciclo e depois solta de uma vez
        if 32 <= t < 48:
            g["antebraco.L"] = [(X, 30.0 + 1.2 * math.sin(t * 2.3))]
        elif 48 <= t < 52:
            g["antebraco.L"] = [(X, 14.0 + 8 * math.exp(-(t - 48)) * math.sin((t - 48) * 3))]
        piscar(g, t, [60], 6, 30)
    q, v = andar_generico(an, 28, 3, 0.62, 0.34, 0.07, 0.065, cfg, extra)
    an.velocidades["andar"] = round(v, 3)
    return q


def tito_perseguir(an):
    cfg = dict(bob=0.018, balanco=0.04, rolar=6.0, torcer=8.0, inclinar=10.0, braco=16.0, braco_frente=52.0,
               cotovelo=22.0, cotovelo_amp=14.0, punho=8.0, dedos=30.0, cabeca_bob=3.0, cabeca_frente=-6.0,
               passo_servo=3, calcanhar=18.0)

    def extra(t, fase, g, raiz):
        # mandíbula "mastigando" duas vezes por ciclo
        add(g, "mandibula", X, -servo(lambda tt: 22.0 * (0.5 - 0.5 * math.cos(4 * math.pi * tt / 22)), t, 3, 0, 1.5, 0.3))
        for lado in ("L", "R"):
            dedos(g, lado, servo(lambda tt, lado=lado: 25 * (0.5 + 0.5 * math.sin(2 * math.pi * tt / 22 + (0 if lado == "L" else math.pi))), t, 3, 0))
    q, v = andar_generico(an, 22, 2, 0.5, 0.4, 0.09, 0.095, cfg, extra)
    an.velocidades["perseguir"] = round(v, 3)
    return q


def tito_procurar(an):
    q = []
    alvos = [0, 0, 38, 38, 38, 0, -42, -42, -42, -20, 0, 0]  # vira a cabeça em trancos, para, olha
    for t in range(120):
        g = {}
        yaw = servo(lambda tt: alvos[int(tt // 10) % 12], t, 10, 0, transicao=4, tremor=0.35)
        add(g, "pescoco", Z, yaw * 0.6)
        add(g, "cabeca", Z, yaw * 0.4)
        add(g, "tronco", Z, servo(lambda tt: alvos[int((tt - 5) // 10) % 12] * 0.35, t, 10, 5, transicao=6, tremor=0.2))
        add(g, "tronco", X, 6)
        add(g, "cabeca", X, servo(lambda tt: 8 if alvos[int(tt // 10) % 12] != 0 else -4, t, 10, 2))
        # mão direita perto do peito, dedos tamborilando
        add(g, "braco.R", X, 32)
        add(g, "antebraco.R", X, 70)
        dedos(g, "R", servo(lambda tt: 20 + 25 * (tt // 3 % 2), t, 3, 0, 1.0, 0.2))
        dedos(g, "L", 15)
        add(g, "mandibula", X, -servo(lambda tt: 10.0 if 70 <= tt < 78 else 0.0, t, 2, 0, 1.0, 0.5))
        piscar(g, t, [24, 88], 7, 30)
        q.append(an.pose(g, (0.015 * math.sin(2 * math.pi * t / 120), 0, -0.04)))
    return q


def jumpscare(an, pipoca=False):
    """Bote para a frente: tronco e braços para cima, dedos abertos, boca escancarada, tremendo."""
    q = []
    rnd = random.Random(7)
    for t in range(36):
        g = {}
        ini = suave(t / 5) * (1 - suave((t - 5) / 2))   # recua um pouco antes do bote
        bote = suave((t - 5) / 4)
        tremor = (rnd.uniform(-1, 1) if t >= 9 else 0.0)
        add(g, "tronco", X, -6 * ini + 24 * bote + 2 * tremor)
        add(g, "pescoco", X, -10 * bote + 3 * tremor)
        add(g, "cabeca", Z, 5 * tremor)
        add(g, "cabeca", Y, (9 if pipoca else 5) * bote + 3 * tremor)
        abre = 30 + 14 * (0.5 + 0.5 * math.sin(t * 1.9)) if t >= 9 else 36 * bote
        add(g, "mandibula", X, -abre)
        for lado, s in (("L", 1), ("R", -1)):
            add(g, f"braco.{lado}", X, -10 * ini + 95 * bote + 4 * tremor)
            add(g, f"braco.{lado}", Y, s * -25 * bote)
            add(g, f"antebraco.{lado}", X, 35 * bote + 6 * rnd.uniform(-1, 1) * (t >= 9))
            add(g, f"mao.{lado}", X, -20 * bote)
            dedos(g, lado, -12 * bote + (8 * rnd.uniform(-1, 1) if t >= 9 else 0), polegar=-15 * bote, abre=12 * bote)
            add(g, f"palpebra_sup.{lado}", X, -14 * bote)
            add(g, f"palpebra_inf.{lado}", X, 8 * bote)
        if pipoca:
            for lado, s in (("L", 1), ("R", -1)):
                add(g, f"orelha.{lado}", X, -30 * bote + 8 * tremor)
                add(g, f"orelha_ponta.{lado}", X, 20 * bote * math.sin(t * 1.3))
            add(g, "saia", X, 6 * bote * math.sin(t * 1.7))
        raiz = (0, 0.1 * bote, -0.03 - 0.05 * bote)
        pes = {"L": (0, 0, 0, 0), "R": (0, 0.0, 0, 0)}
        q.append(an.pose(g, raiz, pes))
    return q


# ---------------------------------------------------------------------------------------------
# PIPOCA: rápida, nervosa, desengonçada; orelhas e saia reagem

def orelhas_saia(g, t, T, amp_orelha, amp_saia, para_tras=0.0, fase0=0.0):
    """Orelhas balançam atrasadas em relação ao corpo (como mola); a saia acompanha o quadril."""
    for lado, s, d in (("L", 1, 0.0), ("R", -1, 0.17)):
        a = 2 * math.pi * (t / T - 0.15 - d + fase0)
        add(g, f"orelha.{lado}", X, -para_tras + amp_orelha * math.sin(2 * a))
        add(g, f"orelha.{lado}", Y, s * amp_orelha * 0.5 * math.sin(a))
        add(g, f"orelha_ponta.{lado}", X, -para_tras * 0.6 + amp_orelha * 1.3 * math.sin(2 * a - 0.9))
    add(g, "saia", X, amp_saia * math.sin(4 * math.pi * (t / T - 0.1)))
    add(g, "saia", Y, amp_saia * 1.2 * math.sin(2 * math.pi * (t / T - 0.2)))


def pipoca_parado(an):
    q = []
    rnd = random.Random(5)
    olhar = [0, -18, -18, 6, 22, 22, 0, 10, -8, 0, 15, 0]
    tique_orelha = {14, 47, 80, 101}
    for t in range(120):
        g = {}
        add(g, "quadril", Y, servo(lambda tt: 2.5 * math.sin(2 * math.pi * tt / 60), t, 5, 0))
        add(g, "tronco", X, servo(lambda tt: 2 * math.sin(2 * math.pi * tt / 40), t, 4, 0))
        yaw = servo(lambda tt: olhar[int(tt // 10) % 12], t, 10, 0, 1.5, 0.45)
        add(g, "pescoco", Z, yaw * 0.5)
        add(g, "cabeca", Z, yaw * 0.5)
        add(g, "cabeca", Y, servo(lambda tt: [0, 12, 0, -10][int(tt // 30) % 4], t, 30, 0, 2, 0.4))  # inclina curiosa
        for lado, s in (("L", 1), ("R", -1)):
            k = 1.0 if any(0 <= t - m < 4 for m in tique_orelha) and (lado == "L") == (t % 2 == 0) else 0.0
            add(g, f"orelha.{lado}", X, -12 * k + 2 * math.sin(t * 0.3))
            add(g, f"orelha_ponta.{lado}", X, 15 * k)
            # dedos tamborilando (nervosa)
            dedos(g, lado, servo(lambda tt, s=s: 12 + 20 * ((tt // 2 + (s > 0)) % 3 == 0), t, 2, 0, 1.0, 0.2))
            add(g, f"antebraco.{lado}", X, 18)
        add(g, "saia", Y, servo(lambda tt: 3 * math.sin(2 * math.pi * tt / 60), t, 5, 0))
        add(g, "mandibula", X, -servo(lambda tt: 8.0 if (tt % 40) < 3 else 0.0, t, 2, 0, 1.0, 0.5))
        piscar(g, t, [9, 40, 46, 92], 5, 26)
        q.append(an.pose(g, (0.01 * math.sin(2 * math.pi * t / 60), 0, -0.015)))
    return q


def pipoca_andar(an):
    cfg = dict(bob=0.022, balanco=0.02, rolar=4.0, torcer=7.0, inclinar=6.0, braco=28.0, cotovelo=16.0,
               cotovelo_amp=26.0, punho=16.0, dedos=12.0, cabeca_bob=4.0, passo_servo=2, cotovelos_abertos=6.0,
               calcanhar=20.0, largura_pe=0.0)

    def extra(t, fase, g, raiz):
        orelhas_saia(g, t, 22, 9.0, 6.0)
        add(g, "cabeca", Z, servo(lambda tt: [0, 14, -10, 0, 8, 0][int(tt // 11) % 6], t, 11, 0, 1.5, 0.4))
        piscar(g, t, [30], 5, 26)
    q, v = andar_generico(an, 22, 3, 0.58, 0.5, 0.11, 0.075, cfg, extra)
    an.velocidades["andar"] = round(v, 3)
    return q


def pipoca_perseguir(an):
    cfg = dict(bob=0.03, voo=0.035, balanco=0.015, rolar=4.0, torcer=10.0, inclinar=16.0, braco=42.0, braco_frente=8.0,
               cotovelo=62.0, cotovelo_amp=28.0, punho=20.0, dedos=28.0, cabeca_bob=5.0, cabeca_frente=-10.0,
               passo_servo=2, cotovelos_abertos=18.0, calcanhar=24.0)

    def extra(t, fase, g, raiz):
        orelhas_saia(g, t, 16, 12.0, 11.0, para_tras=35.0)
        add(g, "mandibula", X, -servo(lambda tt: 16.0 * (tt // 2 % 2), t, 2, 0, 1.0, 0.3))  # bate os dentes
    q, v = andar_generico(an, 16, 3, 0.38, 0.62, 0.16, 0.14, cfg, extra)
    an.velocidades["perseguir"] = round(v, 3)
    return q


def pipoca_procurar(an):
    q = []
    alvos = [0, 30, 30, -35, -35, 0, 18, -20, 0, 0, 40, 0]
    for t in range(120):
        g = {}
        yaw = servo(lambda tt: alvos[int(tt // 10) % 12], t, 10, 0, 1.5, 0.45)
        add(g, "pescoco", Z, yaw * 0.5)
        add(g, "cabeca", Z, yaw * 0.5)
        add(g, "cabeca", Y, servo(lambda tt: [16, -14, 0, 12][int(tt // 15) % 4], t, 15, 0, 2, 0.4))  # cabeça de lado
        add(g, "tronco", X, 12)
        add(g, "tronco", Z, yaw * 0.3)
        add(g, "pescoco", X, 10)
        for lado, s in (("L", 1), ("R", -1)):
            add(g, f"braco.{lado}", X, 28)
            add(g, f"antebraco.{lado}", X, 85)
            add(g, f"mao.{lado}", X, -25)
            dedos(g, lado, servo(lambda tt, s=s: 10 + 30 * ((tt // 3 + (s > 0)) % 2), t, 3, 0, 1.0, 0.2))
            # orelhas giram para os lados, "escutando"
            add(g, f"orelha.{lado}", Y, s * servo(lambda tt: [0, 20, 20, -10][int((tt + 7 * (s > 0)) // 15) % 4], t, 15, 0, 1.5, 0.5))
            add(g, f"orelha_ponta.{lado}", X, servo(lambda tt: [0, 18, 0, -8][int(tt // 15) % 4], t, 15, 3))
        add(g, "saia", X, 3 * math.sin(2 * math.pi * t / 60))
        piscar(g, t, [20, 26, 70], 5, 26)
        q.append(an.pose(g, (0.0, 0.0, -0.05)))
    return q


def pipoca_atordoada(an):
    """Atordoada: cabeça caída, braços moles, orelhas caídas, boca frouxa e espasmos de servo de vez em quando."""
    q = []
    espasmos = [12, 33, 49]
    for t in range(60):
        g = {}
        k = 0.0
        for m in espasmos:
            d = t - m
            if 0 <= d < 5:
                k = max(k, math.exp(-d * 0.7) * math.cos(d * 2.4))
        add(g, "pescoco", X, 30 - 22 * k)
        add(g, "cabeca", Y, 20 - 10 * k)
        add(g, "cabeca", Z, 8 * k)
        add(g, "tronco", X, 12 - 5 * k)
        add(g, "mandibula", X, -(16 + 8 * math.sin(t * 0.2)) + 10 * k)
        for lado, s in (("L", 1), ("R", -1)):
            add(g, f"braco.{lado}", Y, s * (14 - 6 * k))   # braços mais caídos
            add(g, f"braco.{lado}", X, 6 * k)
            add(g, f"antebraco.{lado}", X, 4 + 15 * k * (s > 0))
            dedos(g, lado, 35 - 30 * k)
            add(g, f"orelha.{lado}", Y, s * (35 - 15 * k))
            add(g, f"orelha_ponta.{lado}", X, 45 - 30 * k)
            add(g, f"palpebra_sup.{lado}", X, 20 + (14 if (t // 4) % 5 == 0 else 0))
        add(g, "saia", X, 4 * k)
        q.append(an.pose(g, (0.0, 0.02, -0.07 + 0.02 * k)))
    return q


ANIMACOES = {
    "tito": [("parado", tito_parado, True), ("andar", tito_andar, True), ("perseguir", tito_perseguir, True),
             ("procurar", tito_procurar, True), ("jumpscare", lambda an: jumpscare(an), False)],
    "pipoca": [("parado", pipoca_parado, True), ("andar", pipoca_andar, True), ("perseguir", pipoca_perseguir, True),
               ("procurar", pipoca_procurar, True), ("jumpscare", lambda an: jumpscare(an, True), False),
               ("atordoado", pipoca_atordoada, True)],
}


# ---------------------------------------------------------------------------------------------
# GIFs para a página de progresso

def renderizar_gifs(an, pasta, so=None):
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    cena = bpy.context.scene
    cam = A.estudio()
    # chão quadriculado (para ver que o pé não escorrega)
    chao = bpy.data.objects["Estudio_Chao"]
    mc = chao.data.materials[0]
    nt = mc.node_tree
    xad = nt.nodes.new("ShaderNodeTexChecker")
    xad.inputs["Scale"].default_value = 400 / 0.5 / 2
    xad.inputs["Color1"].default_value = (0.05, 0.045, 0.045, 1)
    xad.inputs["Color2"].default_value = (0.11, 0.1, 0.1, 1)
    nt.links.new(xad.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    cena.render.fps = FPS
    cena.eevee.taa_render_samples = 16
    altura = 2.2
    luzes = [(o, o.location.copy()) for o in cena.objects if o.type == "LIGHT"]
    saidas = []
    for nome, _f, loop in ANIMACOES[an.chave]:
        if so and nome not in so:
            continue
        acao = bpy.data.actions[nome]
        an.arm.animation_data.action = acao
        ini, fim = int(acao.frame_range[0]), int(acao.frame_range[1]) - (1 if loop else 0)
        v = an.velocidades.get(nome, 0.0)
        passo = 2
        arquivos = []
        for f in range(ini, fim + 1, passo):
            cena.frame_set(f)
            avanco = v * (f - ini) / FPS
            an.arm.location.y = -avanco  # anda de verdade para a frente (o pé plantado fica parado no chão)
            for luz, base in luzes:  # as luzes acompanham (senão ele sai da área iluminada)
                luz.location = base + Vector((0, -avanco, 0))
            alvo = (0, -avanco, altura * 0.45)
            ang = 30 if nome != "jumpscare" else 15
            A.fotografar(cam, pasta / f"_{an.chave}_{nome}_{f:03d}.png", alvo, altura * 2.4, ang, 6, 50, (400, 500))
            arquivos.append(pasta / f"_{an.chave}_{nome}_{f:03d}.png")
        an.arm.location.y = 0.0
        saidas.append((nome, arquivos, passo))
    an.arm.animation_data.action = None
    return saidas


# ---------------------------------------------------------------------------------------------
# Exportação para o Godot

def exportar(an, destino):
    """
    Junta todas as peças rígidas numa malha com pele (cada peça 100% no seu osso: o resultado é o
    mesmo que peças presas nos ossos, mas com poucas chamadas de desenho). Os olhos ficam como malhas
    próprias (o jogo pisca os olhos da Pipoca escondendo esses nós).
    """
    arm = an.arm
    arm.data.pose_position = "REST"
    bpy.context.view_layer.update()
    pecas = [o for o in bpy.data.objects if o.type == "MESH" and o.parent == arm]
    grupos = {}
    for ob in pecas:
        nome = ob.name if ob.name in (f"{an.N}_Olho_Esq", f"{an.N}_Olho_Dir") else f"{an.N}_Corpo"
        me = ob.data.copy()
        me.transform(ob.matrix_world)
        novo = bpy.data.objects.new(f"_exp_{ob.name}", me)
        bpy.context.scene.collection.objects.link(novo)
        vg = novo.vertex_groups.new(name=ob.parent_bone)
        vg.add(list(range(len(me.vertices))), 1.0, "REPLACE")
        grupos.setdefault(nome, []).append(novo)
    for ob in pecas:
        bpy.data.objects.remove(ob)
    finais = []
    for nome, obs in grupos.items():
        bpy.ops.object.select_all(action="DESELECT")
        for o in obs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = obs[0]
        if len(obs) > 1:
            bpy.ops.object.join()
        ob = bpy.context.view_layer.objects.active
        ob.name = nome
        ob.data.name = nome
        ob.parent = arm
        ob.matrix_parent_inverse = arm.matrix_world.inverted()
        mod = ob.modifiers.new("Esqueleto", "ARMATURE")
        mod.object = arm
        finais.append(ob)
    arm.data.pose_position = "POSE"
    for pb in arm.pose.bones:
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    # cada ação numa faixa NLA (o exportador leva todas)
    ad = arm.animation_data
    ad.action = None
    for nome, _f, _loop in ANIMACOES[an.chave]:
        trilha = ad.nla_tracks.new()
        trilha.name = nome
        trilha.strips.new(nome, 1, bpy.data.actions[nome])
        trilha.mute = True
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    for o in finais:
        o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    # Aspereza em valor fixo: o exportador junta a aspereza numa imagem nova que o leitor de JPEG do Godot
    # não aceita (e para pelúcia/metal a diferença é mínima).
    for o in finais:
        for m in o.data.materials:
            if not m or not m.use_nodes:
                continue
            p = m.node_tree.nodes.get("Principled BSDF")
            if p and p.inputs["Roughness"].is_linked:
                for ligacao in list(p.inputs["Roughness"].links):
                    m.node_tree.links.remove(ligacao)
                p.inputs["Roughness"].default_value = 0.5 if p.inputs["Metallic"].default_value > 0.5 else 0.85
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in finais)
    mats = sum(len(o.data.materials) for o in finais)
    destino.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(destino), export_format="GLB", use_selection=True,
                              export_animations=True, export_animation_mode="ACTIONS", export_force_sampling=True,
                              export_skins=True, export_yup=True, export_apply=False, export_image_format="JPEG",
                              export_jpeg_quality=88, export_lights=False, export_cameras=False, export_extras=False)
    print(f"[anim] exportado {destino} ({tris} triângulos, {mats} materiais, {len(arm.data.bones)} ossos)")


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["tito"]
    chave = args[0]
    opcoes = dict(a.split("=", 1) if "=" in a else (a, True) for a in args[1:])
    bpy.ops.wm.open_mainfile(filepath=str(RAIZ / "personagens" / f"{chave}_final.blend"))
    bpy.context.scene.render.fps = FPS
    # ao rodar de novo (ex.: depois de mudar uma cor no .blend), as ações antigas são refeitas do zero
    for nome, _f, _loop in ANIMACOES[chave]:
        if nome in bpy.data.actions:
            bpy.data.actions.remove(bpy.data.actions[nome])
    an = Animador(chave)
    so = opcoes.get("so", "").split(",") if opcoes.get("so") else None
    for nome, fn, loop in ANIMACOES[chave]:
        if so and nome not in so:
            continue
        an.gravar(nome, fn(an), loop)
    an.finalizar_ik()
    V.pose_descanso(an.arm, chave)
    print(f"[anim] velocidades de referência: {an.velocidades}")
    # velocidades de referência para o jogo (o AnimationPlayer anda na proporção da velocidade real)
    arq = RAIZ.parent / "godot" / "assets" / "personagens" / "animacoes_velocidades.json"
    dados = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else {}
    dados.setdefault(chave, {}).update(an.velocidades)
    arq.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    if not so:
        bpy.ops.wm.save_as_mainfile(filepath=str(RAIZ / "personagens" / f"{chave}_final.blend"))
    if opcoes.get("gifs"):
        saidas = renderizar_gifs(an, opcoes["gifs"], so)
        (Path(opcoes["gifs"]) / f"{chave}_gifs.json").write_text(json.dumps(
            [(n, [str(p) for p in arqs], passo) for n, arqs, passo in saidas]), encoding="utf-8")
    if opcoes.get("exportar"):
        exportar(an, RAIZ.parent / "godot" / "assets" / "personagens" / f"{chave}.glb")


if __name__ == "__main__":
    main()
