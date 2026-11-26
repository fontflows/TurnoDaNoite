"""
gerar_sons_kart.py — gera os sons de fliperama do TITO KART e do SPACE PIZZA.

Como rodar (a partir da pasta TurnoDaNoite):
    python ferramentas/gerar_sons_kart.py

Usa só a biblioteca padrão do Python (math, random, struct, array): não precisa
de numpy. Os .wav vão para godot/assets/sons/minigames/. As sementes aleatórias
são fixas, então rodar de novo gera exatamente os mesmos arquivos.

Ideia geral (igual à de gerar_sons.py, só que no estilo "chip" dos anos 80):
  - ondas quadradas e triangulares, que são o som típico dos chips de fliperama;
  - ruído branco para batidas, turbo e explosões;
  - envelopes (o volume ao longo do tempo) para cada nota não "estalar".
O som do motor é um LOOP: ele tem um número inteiro de ciclos, de modo que o fim
emenda no começo sem estalo, e gravamos o bloco 'smpl' para o Godot saber que é loop.
"""

import math
import random
import struct
from array import array
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "godot" / "assets" / "sons" / "minigames"

SR = 22050  # taxa de amostragem: sons de chip não precisam de mais que isso
DOIS_PI = 2.0 * math.pi


# ---------------------------------------------------------------------------
# Ferramentas básicas
# ---------------------------------------------------------------------------

def amostras(duracao):
    """Quantidade de amostras para uma duração em segundos."""
    return int(round(duracao * SR))


def quadrada(fase, ciclo=0.5):
    """Onda quadrada (pulso). 'ciclo' é a fração do período em que ela fica em +1."""
    return 1.0 if (fase / DOIS_PI) % 1.0 < ciclo else -1.0


def triangular(fase):
    """Onda triangular: mais suave que a quadrada; os chips usavam para o baixo."""
    p = (fase / DOIS_PI) % 1.0
    return 4.0 * p - 1.0 if p < 0.5 else 3.0 - 4.0 * p


def envelope(i, n, ataque=0.005, soltura=0.05):
    """Volume de 0 a 1: sobe rápido no começo (ataque) e desce no fim (soltura)."""
    t = i / SR
    resto = (n - i) / SR
    v = 1.0
    if t < ataque:
        v = t / ataque
    if resto < soltura:
        v = min(v, resto / soltura)
    return max(0.0, v)


def passa_baixas(sinal, corte_hz):
    """Filtro passa-baixas de um polo: tira os agudos (deixa o ruído mais "grave")."""
    a = 1.0 - math.exp(-DOIS_PI * corte_hz / SR)
    saida = []
    y = 0.0
    for x in sinal:
        y += a * (x - y)
        saida.append(y)
    return saida


def normalizar(sinal, pico_db=-3.0):
    """Ajusta o volume para o maior pico ficar em 'pico_db' dBFS."""
    pico = max(abs(x) for x in sinal) or 1.0
    alvo = 10.0 ** (pico_db / 20.0)
    return [x / pico * alvo for x in sinal]


def nota_hz(midi):
    """Número de nota MIDI -> frequência (69 = Lá 440 Hz)."""
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


def tocar_nota(destino, inicio_s, duracao_s, freq, volume=0.5, onda="quadrada", ciclo=0.5):
    """Mistura uma nota de chip dentro de 'destino' (lista de amostras)."""
    inicio = amostras(inicio_s)
    n = amostras(duracao_s)
    fase = 0.0
    passo = DOIS_PI * freq / SR
    for i in range(n):
        if inicio + i >= len(destino):
            break
        if onda == "quadrada":
            v = quadrada(fase, ciclo)
        else:
            v = triangular(fase)
        destino[inicio + i] += v * volume * envelope(i, n, 0.004, min(0.06, duracao_s * 0.4))
        fase += passo


def salvar_wav(nome, sinal, loop=False):
    """Grava PCM 16 bits mono. Com loop=True acrescenta o bloco 'smpl' (loop do começo ao fim)."""
    dados = array("h", (max(-32768, min(32767, int(round(x * 32767.0)))) for x in sinal))
    corpo = dados.tobytes()  # Windows/x86 já é little-endian, como o WAV pede
    blocos = b"fmt " + struct.pack("<I", 16) + struct.pack("<HHIIHH", 1, 1, SR, SR * 2, 2, 16)
    blocos += b"data" + struct.pack("<I", len(corpo)) + corpo
    if loop:
        smpl = struct.pack("<9I", 0, 0, int(1e9 / SR), 60, 0, 0, 0, 1, 0)
        smpl += struct.pack("<6I", 0, 0, 0, len(dados) - 1, 0, 0)
        blocos += b"smpl" + struct.pack("<I", len(smpl)) + smpl
    conteudo = b"RIFF" + struct.pack("<I", 4 + len(blocos)) + b"WAVE" + blocos
    PASTA.mkdir(parents=True, exist_ok=True)
    caminho = PASTA / nome
    caminho.write_bytes(conteudo)
    print("  gerado:", caminho.relative_to(RAIZ), f"({len(dados) / SR:.2f} s)")


# ---------------------------------------------------------------------------
# Os sons
# ---------------------------------------------------------------------------

def kart_motor():
    """
    Motor do carrinho, em loop. 0,4 s com 28 ciclos de 70 Hz (número inteiro de
    ciclos = emenda perfeita). O "ronco" vem de alguns harmônicos somados e de
    uma modulação de volume de 35 Hz (14 ciclos no loop, também inteiro).
    No jogo, o pitch_scale do AudioStreamPlayer sobe com a velocidade.
    """
    n = amostras(0.4)
    sinal = []
    for i in range(n):
        t = i / SR
        f = 70.0
        v = 0.0
        for harm, amp in ((1, 1.0), (2, 0.55), (3, 0.35), (4, 0.2), (6, 0.1)):
            v += amp * math.sin(DOIS_PI * f * harm * t)
        pulso = 0.65 + 0.35 * math.sin(DOIS_PI * 35.0 * t)
        sinal.append(v * pulso)
    salvar_wav("kart_motor.wav", normalizar(sinal, -6.0), loop=True)


def kart_bip():
    """Bip da contagem regressiva (3, 2, 1)."""
    sinal = [0.0] * amostras(0.18)
    tocar_nota(sinal, 0.0, 0.16, 880.0, 0.6)
    salvar_wav("kart_bip.wav", normalizar(sinal, -4.0))


def kart_largada():
    """O "JÁ!" da largada: bip agudo e mais longo, uma oitava acima."""
    sinal = [0.0] * amostras(0.5)
    tocar_nota(sinal, 0.0, 0.48, 1760.0, 0.5)
    tocar_nota(sinal, 0.0, 0.48, 880.0, 0.25, onda="triangular")
    salvar_wav("kart_largada.wav", normalizar(sinal, -4.0))


def kart_turbo():
    """Turbo: ruído "soprado" com uma serra que sobe de tom (o carrinho dispara)."""
    r = random.Random(7)
    n = amostras(0.7)
    ruido = passa_baixas([r.uniform(-1.0, 1.0) for _ in range(n)], 2500.0)
    sinal = []
    fase = 0.0
    for i in range(n):
        t = i / SR
        f = 180.0 + 700.0 * (t / 0.7) ** 0.7
        fase += DOIS_PI * f / SR
        serra = 2.0 * ((fase / DOIS_PI) % 1.0) - 1.0
        env = envelope(i, n, 0.02, 0.3)
        sinal.append((0.6 * ruido[i] * 3.0 + 0.35 * serra) * env)
    salvar_wav("kart_turbo.wav", normalizar(sinal, -4.0))


def kart_pizza():
    """Pegou a fatia de pizza: arpejo rapidinho subindo (Dó-Mi-Sol-Dó)."""
    sinal = [0.0] * amostras(0.3)
    for k, nota in enumerate((72, 76, 79, 84)):
        tocar_nota(sinal, k * 0.055, 0.08, nota_hz(nota), 0.5, ciclo=0.25)
    salvar_wav("kart_pizza.wav", normalizar(sinal, -5.0))


def kart_batida():
    """Batida entre carrinhos: ruído grave e curto."""
    r = random.Random(11)
    n = amostras(0.14)
    ruido = passa_baixas([r.uniform(-1.0, 1.0) for _ in range(n)], 900.0)
    sinal = [ruido[i] * math.exp(-(i / SR) / 0.035) for i in range(n)]
    salvar_wav("kart_batida.wav", normalizar(sinal, -5.0))


def kart_vitoria():
    """Jingle de vitória em chiptune: melodia em onda quadrada e baixo triangular."""
    batida = 0.13
    melodia = [(72, 1), (76, 1), (79, 1), (84, 2), (79, 1), (84, 4)]
    baixo = [(48, 3), (55, 3), (48, 4)]
    total = sum(d for _, d in melodia) * batida + 0.3
    sinal = [0.0] * amostras(total)
    t = 0.0
    for nota, dur in melodia:
        tocar_nota(sinal, t, dur * batida * 0.95, nota_hz(nota), 0.38, ciclo=0.25)
        t += dur * batida
    t = 0.0
    for nota, dur in baixo:
        tocar_nota(sinal, t, dur * batida * 0.95, nota_hz(nota), 0.45, onda="triangular")
        t += dur * batida
    salvar_wav("kart_vitoria.wav", normalizar(sinal, -3.0))


def kart_derrota():
    """Perdeu: três notas descendo, a última mais longa e "murcha"."""
    sinal = [0.0] * amostras(1.2)
    for k, nota in enumerate((67, 63, 60)):
        dur = 0.22 if k < 2 else 0.6
        tocar_nota(sinal, k * 0.25, dur, nota_hz(nota), 0.45, ciclo=0.5)
        tocar_nota(sinal, k * 0.25, dur, nota_hz(nota - 12), 0.35, onda="triangular")
    salvar_wav("kart_derrota.wav", normalizar(sinal, -4.0))


def sp_tiro():
    """Tiro da nave-fatia: onda quadrada que cai de tom bem rápido ("piu!")."""
    n = amostras(0.13)
    sinal = []
    fase = 0.0
    for i in range(n):
        t = i / SR
        f = 1600.0 * math.exp(-t / 0.05) + 300.0
        fase += DOIS_PI * f / SR
        sinal.append(quadrada(fase, 0.3) * envelope(i, n, 0.002, 0.04))
    salvar_wav("sp_tiro.wav", normalizar(sinal, -8.0))


def sp_explosao():
    """Explosão da azeitona: ruído que vai ficando grave e morrendo."""
    r = random.Random(23)
    n = amostras(0.4)
    ruido = [r.uniform(-1.0, 1.0) for _ in range(n)]
    metade_1 = passa_baixas(ruido, 1800.0)
    metade_2 = passa_baixas(ruido, 400.0)
    sinal = []
    for i in range(n):
        t = i / SR
        mistura = min(1.0, t / 0.25)  # começa agudo, termina grave
        v = metade_1[i] * (1.0 - mistura) + metade_2[i] * 2.5 * mistura
        sinal.append(v * math.exp(-t / 0.12) * envelope(i, n, 0.002, 0.05))
    salvar_wav("sp_explosao.wav", normalizar(sinal, -4.0))


def main():
    print("Gerando sons dos minigames em", PASTA.relative_to(RAIZ))
    kart_motor()
    kart_bip()
    kart_largada()
    kart_turbo()
    kart_pizza()
    kart_batida()
    kart_vitoria()
    kart_derrota()
    sp_tiro()
    sp_explosao()
    print("Pronto.")


if __name__ == "__main__":
    main()
