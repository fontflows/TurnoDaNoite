"""
gerar_sons_garra_conserto.py — sons dos minigames GARRA e CONSERTO DO DISJUNTOR.

Tudo é feito por síntese, só com a biblioteca padrão do Python (sem numpy):
cada som é uma lista de números entre -1 e 1 (as "amostras"), montada somando
ondas simples (senoide, quadrada, triângulo, dente de serra, ruído) e moldando
o volume no tempo (envelopes).

Como rodar (a partir da pasta TurnoDaNoite):
    python ferramentas/gerar_sons_garra_conserto.py

Os .wav vão para godot/assets/sons/minigames/ com prefixo garra_ e conserto_.
As sementes aleatórias são fixas: rodar de novo gera exatamente os mesmos arquivos.

Sons em LOOP (música da garra, motor, zumbido) são "circulares": o fim emenda
no começo sem estalo, e o .wav leva um bloco 'smpl' com os pontos de loop, que o
Godot lê sozinho (Loop Mode: Detect From WAV).
"""

import math
import random
import struct
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "godot" / "assets" / "sons" / "minigames"

SR = 22050  # taxa de amostragem (amostras por segundo); 22 kHz basta para sons de máquina
DOIS_PI = 2.0 * math.pi


# ---------------------------------------------------------------------------
# Ferramentas básicas
# ---------------------------------------------------------------------------

def silencio(duracao):
    """Lista de zeros com 'duracao' segundos."""
    return [0.0] * int(round(duracao * SR))


def midi_para_hz(nota):
    """Nota MIDI (60 = dó central) para frequência em Hz."""
    return 440.0 * 2.0 ** ((nota - 69) / 12.0)


def quadrada(fase, ciclo=0.5):
    """Onda quadrada (pulso). 'ciclo' é a fração do tempo em que fica em +1: 0,25 soa mais 'chip'."""
    return 1.0 if (fase % 1.0) < ciclo else -1.0


def triangulo(fase):
    """Onda triangular: suave, boa para baixo de videogame antigo."""
    f = fase % 1.0
    return 4.0 * f - 1.0 if f < 0.5 else 3.0 - 4.0 * f


def serra(fase):
    """Dente de serra: áspera, boa para motores."""
    return 2.0 * (fase % 1.0) - 1.0


def passa_baixas(x, corte, circular=False):
    """
    Filtro passa-baixas de 1 polo (suaviza, tira os agudos).
    circular=True roda o filtro duas vezes, começando a 2ª passada com o estado do
    fim da 1ª: assim o começo do resultado "continua" o fim, e o loop não estala.
    """
    a = 1.0 - math.exp(-DOIS_PI * corte / SR)
    y = 0.0
    if circular:
        for v in x:
            y += a * (v - y)
    saida = []
    for v in x:
        y += a * (v - y)
        saida.append(y)
    return saida


def passa_altas(x, corte, circular=False):
    """Passa-altas = sinal original menos a parte grave (o passa-baixas)."""
    graves = passa_baixas(x, corte, circular)
    return [v - g for v, g in zip(x, graves)]


def ruido(n, r):
    """Ruído branco: números aleatórios entre -1 e 1."""
    return [r.uniform(-1.0, 1.0) for _ in range(n)]


def normalizar(x, db):
    """Ajusta o volume para o pico ficar em 'db' dBFS (0 = máximo)."""
    pico = max(abs(v) for v in x) or 1.0
    ganho = 10.0 ** (db / 20.0) / pico
    return [v * ganho for v in x]


def fades(x, entrada=0.002, saida=0.02):
    """Rampas curtas no começo e no fim, para não estalar."""
    x = list(x)
    a = max(1, int(entrada * SR))
    b = max(1, int(saida * SR))
    for i in range(min(a, len(x))):
        x[i] *= i / a
    for i in range(min(b, len(x))):
        x[-1 - i] *= i / b
    return x


def colocar(destino, som, inicio, ganho=1.0, circular=False):
    """Mistura 'som' dentro de 'destino' a partir da amostra 'inicio'.
    circular=True faz o que passar do fim "dar a volta" para o começo (para loops)."""
    n = len(destino)
    for i, v in enumerate(som):
        j = inicio + i
        if circular:
            j %= n
        elif j >= n:
            break
        destino[j] += v * ganho


def nota(freq, duracao, forma, ataque=0.005, decaimento=0.25, sustentar=0.0, ciclo=0.5, vibrato=0.0):
    """
    Uma nota com envelope simples: sobe em 'ataque' segundos e cai exponencialmente
    (constante 'decaimento'); 'sustentar' é o nível mínimo enquanto a nota dura.
    """
    n = int(round(duracao * SR))
    som = []
    fase = 0.0
    for i in range(n):
        t = i / SR
        f = freq * (1.0 + vibrato * math.sin(DOIS_PI * 5.5 * t))
        fase += f / SR
        if forma == "quadrada":
            v = quadrada(fase, ciclo)
        elif forma == "triangulo":
            v = triangulo(fase)
        elif forma == "serra":
            v = serra(fase)
        else:
            v = math.sin(DOIS_PI * fase)
        env = min(1.0, t / ataque) * max(sustentar, math.exp(-t / decaimento))
        som.append(v * env)
    return fades(som, 0.001, 0.01)


def estalo(r, duracao=0.006, tau=0.001):
    """Um estalinho de ruído que morre rápido (faísca, crepitar)."""
    n = int(duracao * SR)
    return [r.uniform(-1, 1) * math.exp(-(i / SR) / tau) for i in range(n)]


# ---------------------------------------------------------------------------
# Gravação do WAV (PCM 16 bits mono, com bloco 'smpl' opcional)
# ---------------------------------------------------------------------------

def salvar_wav(nome, x, loop=False):
    amostras = [max(-32768, min(32767, int(round(v * 32767.0)))) for v in x]
    dados = struct.pack("<%dh" % len(amostras), *amostras)
    blocos = b"fmt " + struct.pack("<I", 16) + struct.pack("<HHIIHH", 1, 1, SR, SR * 2, 2, 16)
    blocos += b"data" + struct.pack("<I", len(dados)) + dados
    if loop:
        smpl = struct.pack("<9I", 0, 0, int(1e9 / SR), 60, 0, 0, 0, 1, 0)
        smpl += struct.pack("<6I", 0, 0, 0, len(amostras) - 1, 0, 0)
        blocos += b"smpl" + struct.pack("<I", len(smpl)) + smpl
    conteudo = b"RIFF" + struct.pack("<I", 4 + len(blocos)) + b"WAVE" + blocos
    (PASTA / nome).write_bytes(conteudo)
    return len(amostras) / SR


# ---------------------------------------------------------------------------
# GARRA
# ---------------------------------------------------------------------------

def garra_musica():
    """
    Musiquinha de máquina de pelúcia: chiptune alegre em dó maior, 150 BPM,
    4 compassos (6,4 s) em loop. Melodia em onda quadrada fina (25%), baixo em
    triângulo, "caixinha" de sino nas notas agudas e um chimbal de ruído.
    """
    r = random.Random(101)
    colcheia = 60.0 / 150.0 / 2.0  # 0,2 s
    total = silencio(32 * colcheia)
    melodia = [72, 76, 79, 76, 72, 76, 79, 84,
               77, 81, 84, 81, 77, 81, 79, 77,
               79, 83, 86, 83, 79, 77, 76, 74,
               76, 79, 72, 76, 74, 71, 72, None]
    for i, m in enumerate(melodia):
        if m is None:
            continue
        som = nota(midi_para_hz(m), colcheia * 0.95, "quadrada", decaimento=0.12, sustentar=0.25, ciclo=0.25)
        colocar(total, som, int(i * colcheia * SR), 0.30, circular=True)
        if i % 4 == 0:  # brilho de caixinha de música a cada tempo
            sino = nota(midi_para_hz(m + 12), 0.6, "seno", decaimento=0.18)
            colocar(total, sino, int(i * colcheia * SR), 0.18, circular=True)
    baixo = [48, 55, 48, 55, 53, 60, 53, 60, 55, 62, 55, 62, 48, 55, 43, 48]
    for i, m in enumerate(baixo):
        som = nota(midi_para_hz(m), colcheia * 1.9, "triangulo", decaimento=0.3, sustentar=0.5)
        colocar(total, som, int(i * 2 * colcheia * SR), 0.45, circular=True)
    for i in range(32):  # chimbal: ruído agudo curtinho em todas as colcheias
        som = passa_altas([v * math.exp(-k / SR / 0.015) for k, v in enumerate(ruido(int(0.05 * SR), r))], 5000)
        colocar(total, som, int(i * colcheia * SR), 0.10 if i % 2 else 0.18, circular=True)
    return normalizar(total, -4.0), True


def garra_motor():
    """Motor do carrinho da garra: zumbido de dente de serra + engrenagem. Loop de 1 s.
    Todas as frequências completam ciclos inteiros em 1 s, então o loop emenda certinho."""
    r = random.Random(102)
    n = SR
    x = []
    for i in range(n):
        t = i / SR
        f_mod = 1.0 + 0.02 * math.sin(DOIS_PI * 6.0 * t)
        v = 0.55 * serra(90.0 * t + 0.02 * math.sin(DOIS_PI * 6.0 * t) / DOIS_PI)
        v += 0.25 * serra(180.0 * t)
        v += 0.12 * math.sin(DOIS_PI * 640.0 * t) * f_mod * (0.5 + 0.5 * math.sin(DOIS_PI * 12.0 * t))
        x.append(v)
    x = passa_baixas(x, 1800, circular=True)
    chiado = passa_baixas(ruido(n, r), 2500, circular=True)
    x = [math.tanh(1.6 * (a + 0.25 * b)) for a, b in zip(x, chiado)]
    return normalizar(x, -8.0), True


def garra_fechar():
    """A garra fechando: 'clanc' metálico (parciais fora da série harmônica) + baque."""
    r = random.Random(103)
    x = silencio(0.35)
    for i in range(len(x)):
        t = i / SR
        metal = sum(a * math.sin(DOIS_PI * f * t + k) * math.exp(-t / tau) for k, (f, a, tau) in
                    enumerate([(910, 1.0, 0.08), (1370, 0.7, 0.06), (2210, 0.5, 0.04), (3180, 0.3, 0.03)]))
        baque = math.sin(DOIS_PI * (70 + 60 * math.exp(-t / 0.03)) * t) * math.exp(-t / 0.05)
        x[i] = 0.5 * metal + 0.8 * baque
    colocar(x, passa_altas(estalo(r, 0.01, 0.002), 2000), 0, 1.2)
    return normalizar(fades(x), -2.0), False


def garra_premio():
    """Fanfarra de prêmio: arpejo subindo (dó-mi-sol-dó) e acorde final com brilho."""
    x = silencio(1.8)
    for i, m in enumerate([72, 76, 79, 84, 88]):
        colocar(x, nota(midi_para_hz(m), 0.18, "quadrada", decaimento=0.1, sustentar=0.3, ciclo=0.25),
                int(i * 0.09 * SR), 0.35)
    inicio = int(0.48 * SR)
    for m in [72, 76, 79, 84]:
        colocar(x, nota(midi_para_hz(m), 1.2, "quadrada", decaimento=0.5, sustentar=0.0, ciclo=0.5, vibrato=0.006),
                inicio, 0.18)
    for i, m in enumerate([96, 100, 103, 108, 103, 108]):
        colocar(x, nota(midi_para_hz(m), 0.35, "seno", decaimento=0.1), inicio + int(i * 0.08 * SR), 0.15)
    return normalizar(fades(x, 0.002, 0.15), -2.0), False


def garra_errou():
    """'Uón-uón-uóóón': trombone triste de dente de serra, descendo, com vibrato."""
    x = silencio(1.6)
    for i, (m, dur) in enumerate([(62, 0.3), (61, 0.3), (60, 0.8)]):
        som = nota(midi_para_hz(m - 12), dur, "serra", ataque=0.03, decaimento=0.6, sustentar=0.6, vibrato=0.015 * (i + 1))
        colocar(x, passa_baixas(som, 1200), int(i * 0.34 * SR), 0.5)
    return normalizar(fades(x, 0.002, 0.2), -3.0), False


# ---------------------------------------------------------------------------
# CONSERTO DO DISJUNTOR
# ---------------------------------------------------------------------------

def conserto_zumbido():
    """Zumbido elétrico da caixa aberta: 120 Hz e harmônicos com distorção. Loop de 2 s."""
    r = random.Random(201)
    n = 2 * SR
    x = []
    for i in range(n):
        t = i / SR
        v = sum(a * math.sin(DOIS_PI * 120.0 * k * t + k) for k, a in [(1, 1.0), (2, 0.5), (3, 0.35), (5, 0.15)])
        v = math.tanh(2.0 * v) * (0.85 + 0.15 * math.sin(DOIS_PI * 0.5 * t))
        x.append(v)
    chiado = passa_altas(ruido(n, r), 3000, circular=True)
    x = [a * 0.8 + b * 0.06 for a, b in zip(x, chiado)]
    for _ in range(6):
        colocar(x, estalo(r), r.randrange(n), r.uniform(0.2, 0.5), circular=True)
    return normalizar(x, -9.0), True


def conserto_faisca():
    """Faísca: estouro (o 'susto') + chuva de estalos agudos + zap curto."""
    r = random.Random(202)
    x = silencio(0.55)
    estouro = [r.uniform(-1, 1) * math.exp(-(i / SR) / 0.03) for i in range(int(0.12 * SR))]
    colocar(x, passa_baixas(estouro, 3500), 0, 1.0)
    for _ in range(40):
        inicio = int(abs(r.gauss(0.0, 0.12)) * SR)
        colocar(x, passa_altas(estalo(r, 0.005, 0.0008), 2500), inicio, r.uniform(0.3, 1.0))
    for i in range(int(0.15 * SR)):
        t = i / SR
        x[i] += 0.35 * serra((900 - 2500 * t) * t) * math.exp(-t / 0.05)
    return normalizar(fades(x, 0.0005, 0.05), -1.0), False


def conserto_choque():
    """Choque: zumbido forte de 60 Hz distorcido, ruído e um 'zap' caindo de tom."""
    r = random.Random(203)
    x = silencio(1.0)
    for i in range(len(x)):
        t = i / SR
        env = min(1.0, t / 0.01) * math.exp(-t / 0.35)
        zumbido = math.tanh(4.0 * sum(a * math.sin(DOIS_PI * 60.0 * k * t) for k, a in [(1, 1.0), (2, 0.6), (3, 0.5), (4, 0.3)]))
        zap = serra((1500 * math.exp(-t / 0.15) + 80) * t)
        x[i] = env * (0.6 * zumbido + 0.35 * zap + 0.3 * r.uniform(-1, 1))
    for _ in range(25):
        colocar(x, estalo(r, 0.006, 0.001), int(r.uniform(0, 0.6) * SR), r.uniform(0.3, 0.9))
    return normalizar(fades(x, 0.001, 0.1), -1.0), False


def conserto_encaixe():
    """Encaixe: dois cliques de plástico/metal e um 'tum' grave (o fio/fusível entrou)."""
    r = random.Random(204)
    x = silencio(0.3)
    for inicio, ganho in [(0, 1.0), (int(0.045 * SR), 0.7)]:
        colocar(x, passa_altas(estalo(r, 0.008, 0.0015), 1500), inicio, ganho)
    for i in range(len(x)):
        t = i / SR
        x[i] += 0.6 * math.sin(DOIS_PI * (110 + 80 * math.exp(-t / 0.02)) * t) * math.exp(-t / 0.06)
        x[i] += 0.2 * math.sin(DOIS_PI * 1800 * t) * math.exp(-t / 0.03)
    return normalizar(fades(x), -2.0), False


SONS = {
    "garra_musica.wav": garra_musica,
    "garra_motor.wav": garra_motor,
    "garra_fechar.wav": garra_fechar,
    "garra_premio.wav": garra_premio,
    "garra_errou.wav": garra_errou,
    "conserto_zumbido.wav": conserto_zumbido,
    "conserto_faisca.wav": conserto_faisca,
    "conserto_choque.wav": conserto_choque,
    "conserto_encaixe.wav": conserto_encaixe,
}


def main():
    PASTA.mkdir(parents=True, exist_ok=True)
    print(f"{'arquivo':<24}{'dur (s)':>9}  loop")
    for nome, funcao in SONS.items():
        x, loop = funcao()
        duracao = salvar_wav(nome, x, loop)
        emenda = ""
        if loop:
            # O salto do fim para o começo não pode ser maior que o maior passo "normal" do sinal.
            salto = abs(x[-1] - x[0])
            maior_passo = max(abs(b - a) for a, b in zip(x, x[1:]))
            emenda = f"emenda {'ok' if salto <= maior_passo * 1.05 else 'RUIM'} ({salto:.3f} / {maior_passo:.3f})"
        print(f"{nome:<24}{duracao:>9.2f}  {'sim ' + emenda if loop else '-'}")
    print(f"Sons gerados em {PASTA}")


if __name__ == "__main__":
    main()
