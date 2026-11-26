"""
gerar_sons.py — gera TODOS os sons do jogo por síntese (nada é baixado da internet).

Como rodar (a partir da pasta TurnoDaNoite):
    blender --background --factory-startup --python ferramentas/gerar_sons.py
ou, se o seu Python tiver numpy instalado:
    python ferramentas/gerar_sons.py

Os arquivos .wav vão para godot/assets/sons/. O resultado é sempre igual
(as "sementes" aleatórias são fixas), então rodar de novo não muda nada à toa.

Ideia geral: cada som é montado somando ondas simples (senoides, dentes de serra,
ruído) e moldando o volume ao longo do tempo (envelopes). Para os sons em LOOP,
o sinal é feito "circular": o fim emenda exatamente no começo, sem estalo. Além
disso, gravamos no .wav um bloco 'smpl' com os pontos de loop, que o Godot lê
sozinho (Loop Mode: Detect From WAV).
"""

import struct
import wave
from pathlib import Path

import numpy as np

# Raiz do projeto = pasta acima de ferramentas/
RAIZ = Path(__file__).resolve().parents[1]
PASTA_SONS = RAIZ / "godot" / "assets" / "sons"

SR = 44100        # taxa padrão (qualidade de CD)
SR_LONGO = 22050  # sons longos (ambiente e música) usam metade, para o arquivo ficar menor

DOIS_PI = 2.0 * np.pi


# ---------------------------------------------------------------------------
# Ferramentas básicas
# ---------------------------------------------------------------------------

def gerador(semente):
    """Gerador aleatório com semente fixa: o mesmo som sai sempre igual."""
    return np.random.default_rng(semente)


def tempo(duracao, sr=SR):
    """Vetor com o instante (em segundos) de cada amostra."""
    return np.arange(int(round(duracao * sr))) / sr


def filtrar(x, sr, passa_altas=None, passa_baixas=None, ordem=2, circular=False):
    """
    Filtro feito no domínio da frequência (FFT).
    passa_altas: corta os graves abaixo desse valor (Hz).
    passa_baixas: corta os agudos acima desse valor (Hz).
    circular=True mantém o sinal emendável em loop (o filtro "dá a volta").
    circular=False põe silêncio depois do som, para o fim não vazar no começo.
    """
    n = len(x)
    if not circular:
        x = np.concatenate([x, np.zeros(n)])
    espectro = np.fft.rfft(x)
    f = np.maximum(np.fft.rfftfreq(len(x), 1.0 / sr), 1e-6)
    ganho = np.ones_like(f)
    if passa_altas:
        ganho *= 1.0 / np.sqrt(1.0 + (passa_altas / f) ** (2 * ordem))
    if passa_baixas:
        ganho *= 1.0 / np.sqrt(1.0 + (f / passa_baixas) ** (2 * ordem))
    return np.fft.irfft(espectro * ganho, len(x))[:n]


def normalizar(x, db):
    """Ajusta o volume para o pico ficar em 'db' dBFS (0 = máximo possível)."""
    pico = np.max(np.abs(x))
    return x if pico == 0 else x / pico * (10.0 ** (db / 20.0))


def fades(x, sr, entrada=0.002, saida=0.01):
    """Rampas curtas de volume no começo e no fim, para não dar estalo."""
    x = x.copy()
    a = int(entrada * sr)
    b = int(saida * sr)
    if a > 0:
        x[:a] *= np.linspace(0.0, 1.0, a)
    if b > 0:
        x[-b:] *= np.linspace(1.0, 0.0, b)
    return x


def colocar(destino, som, inicio, circular=False):
    """Mistura 'som' dentro de 'destino' a partir da amostra 'inicio'."""
    if circular:
        idx = (np.arange(len(som)) + inicio) % len(destino)
        np.add.at(destino, idx, som)
        return
    if inicio >= len(destino):
        return
    fim = min(len(destino), inicio + len(som))
    destino[inicio:fim] += som[:fim - inicio]


def fase_de(freq, sr):
    """Fase acumulada de uma frequência que muda com o tempo (vetor de Hz)."""
    return DOIS_PI * np.cumsum(freq) / sr


def serra(fase):
    """Onda dente de serra a partir da fase (som áspero, bom para motores)."""
    return 2.0 * ((fase / DOIS_PI) % 1.0) - 1.0


def estalo(sr, r, duracao=0.004, tau=0.0008):
    """Um estalinho curto de ruído (faísca, crepitar)."""
    t = tempo(duracao, sr)
    return r.standard_normal(len(t)) * np.exp(-t / tau)


def midi_para_hz(nota):
    return 440.0 * 2.0 ** ((nota - 69) / 12.0)


def nota_caixinha(freq, sr, duracao=2.5, oscilacao=None, brilho=1.0):
    """
    Uma nota de caixinha de música: uma lâmina de metal beliscada.
    Soma de parciais (algumas fora da série harmônica, como numa lâmina real),
    cada uma morrendo num ritmo. 'oscilacao' é um vetor multiplicador de
    frequência (wow/flutter de fita velha); se for None, a nota é estável.
    """
    n = int(round(duracao * sr))
    t = np.arange(n) / sr
    if oscilacao is None or len(oscilacao) < n:
        oscilacao = np.ones(n)
    acumulado = np.cumsum(oscilacao[:n]) / sr  # "tempo distorcido" pela oscilação
    escala_tau = np.sqrt(440.0 / freq)  # notas graves soam por mais tempo
    parciais = [(1.0, 1.0, 1.4), (2.0, 0.22, 0.6), (3.0, 0.10, 0.35), (5.4, 0.06 * brilho, 0.12), (8.9, 0.03 * brilho, 0.05)]
    som = np.zeros(n)
    for razao, amp, tau in parciais:
        f = freq * razao
        if f > sr * 0.45:
            continue
        som += amp * np.sin(DOIS_PI * f * acumulado) * np.exp(-t / (tau * escala_tau))
    ataque = np.clip(t / 0.002, 0.0, 1.0)
    return som * ataque


# ---------------------------------------------------------------------------
# Gravação do WAV (com bloco de loop 'smpl')
# ---------------------------------------------------------------------------

def salvar_wav(nome, x, sr, loop=False):
    """
    Grava PCM 16 bits mono. Se loop=True, acrescenta o bloco 'smpl' com
    início do loop = 0 e fim = última amostra (padrão do formato WAV).
    """
    amostras = np.clip(np.round(x * 32767.0), -32768, 32767).astype("<i2")
    dados = amostras.tobytes()
    blocos = b"fmt " + struct.pack("<I", 16) + struct.pack("<HHIIHH", 1, 1, sr, sr * 2, 2, 16)
    blocos += b"data" + struct.pack("<I", len(dados)) + dados
    if loop:
        smpl = struct.pack("<9I", 0, 0, int(1e9 / sr), 60, 0, 0, 0, 1, 0)
        smpl += struct.pack("<6I", 0, 0, 0, len(amostras) - 1, 0, 0)
        blocos += b"smpl" + struct.pack("<I", len(smpl)) + smpl
    conteudo = b"RIFF" + struct.pack("<I", 4 + len(blocos)) + b"WAVE" + blocos
    caminho = PASTA_SONS / nome
    caminho.write_bytes(conteudo)
    return caminho


# ---------------------------------------------------------------------------
# Os sons
# ---------------------------------------------------------------------------

def zumbido_lampada():
    """Lâmpada fluorescente velha: zumbido de 120 Hz (rede de 60 Hz) + chiado + crepitar. Loop de 3 s."""
    sr, dur, r = SR, 3.0, gerador(1)
    t = tempo(dur, sr)
    n = len(t)
    # Harmônicos de 120 Hz: 120 * 3 s = número inteiro de ciclos, então emenda perfeito.
    zumbido = sum(a * np.sin(DOIS_PI * 120.0 * k * t + k) for k, a in
                  [(1, 1.0), (2, 0.55), (3, 0.35), (4, 0.22), (5, 0.12), (6, 0.08), (8, 0.05)])
    zumbido = np.tanh(2.2 * zumbido)  # distorção leve = "bzzz" de reator
    zumbido *= 0.85 + 0.1 * np.sin(DOIS_PI * t / 3.0) + 0.05 * np.sin(DOIS_PI * 7.0 * t / 3.0)
    chiado = filtrar(r.standard_normal(n), sr, 3000, 9000, circular=True)
    chiado = chiado / np.max(np.abs(chiado)) * 0.05
    crepitar = np.zeros(n)
    for _ in range(9):
        colocar(crepitar, estalo(sr, r) * r.uniform(0.3, 1.0), int(r.integers(n)), circular=True)
    crepitar = filtrar(crepitar, sr, passa_altas=1500, circular=True)
    crepitar = crepitar / np.max(np.abs(crepitar)) * 0.25
    return normalizar(zumbido * 0.8 + chiado + crepitar, -6.0), sr, True


def estatica():
    """Chiado de TV fora do ar, com o 'zumbido' de 60 Hz da tela. Loop de 2 s."""
    sr, dur, r = SR, 2.0, gerador(2)
    t = tempo(dur, sr)
    n = len(t)
    chiado = filtrar(r.standard_normal(n), sr, 400, 9000, circular=True)
    brilho = filtrar(r.standard_normal(n), sr, 4000, 12000, circular=True) * 0.6
    pulsacao = 0.75 + 0.25 * np.abs(np.sin(DOIS_PI * 60.0 * t))  # 60 Hz * 2 s = ciclos inteiros
    estalos = np.zeros(n)
    for _ in range(25):
        colocar(estalos, estalo(sr, r) * r.uniform(1.0, 4.0), int(r.integers(n)), circular=True)
    return normalizar((chiado + brilho) * pulsacao + estalos, -4.0), sr, True


def passo(semente, tom):
    """Passo do jogador: calcanhar (baque + impacto) e, logo depois, a ponta do pé."""
    sr, r = SR, gerador(semente)
    t = tempo(0.28, sr)
    n = len(t)
    x = np.zeros(n)
    impacto = filtrar(r.standard_normal(n) * np.exp(-t / 0.012), sr, 120, 1800 * tom)
    baque = np.sin(DOIS_PI * 85.0 * tom * t) * np.exp(-t / 0.035)
    colocar(x, impacto / np.max(np.abs(impacto)) * 0.8 + baque * 0.6, 0)
    ponta = filtrar(r.standard_normal(n) * np.exp(-t / 0.008), sr, 300, 3000 * tom)
    colocar(x, ponta / np.max(np.abs(ponta)) * 0.45, int(r.uniform(0.045, 0.07) * sr))
    arranhado = filtrar(r.standard_normal(n), sr, 1500, 6000) * np.exp(-t / 0.05)
    x += arranhado / np.max(np.abs(arranhado)) * 0.08
    return normalizar(fades(x, sr, 0.001, 0.03), -3.0), sr, False


def tito_passo():
    """Passo metálico pesado do Tito: baque grave, ressonância de chapa e rangido de junta."""
    sr, r = SR, gerador(4)
    t = tempo(0.6, sr)
    n = len(t)
    baque = np.sin(fase_de(40.0 + 70.0 * np.exp(-t / 0.25), sr)) * np.exp(-t / 0.12)
    impacto = filtrar(r.standard_normal(n) * np.exp(-t / 0.02), sr, 60, 900)
    impacto /= np.max(np.abs(impacto))
    # Parciais "fora da série" = som de metal (não de instrumento afinado)
    metal = sum(a * np.sin(DOIS_PI * f * t + i) * np.exp(-t / tau) for i, (f, a, tau) in enumerate(
        [(312, 1.0, 0.35), (527, 0.7, 0.28), (851, 0.55, 0.22), (1294, 0.4, 0.16), (1903, 0.3, 0.1), (2780, 0.2, 0.07)]))
    clank = filtrar(r.standard_normal(n) * np.exp(-t / 0.004), sr, 2000, 8000)
    clank /= np.max(np.abs(clank))
    envelope_junta = np.clip((t - 0.08) / 0.05, 0, 1) * np.exp(-np.clip(t - 0.08, 0, None) / 0.12)
    junta = filtrar(serra(fase_de(140.0 - 30.0 * t, sr)), sr, 600, 2500) * envelope_junta
    x = baque * 1.0 + impacto * 0.6 + metal * 0.35 + clank * 0.3 + junta * 0.4
    x = np.tanh(1.5 * x)
    return normalizar(fades(x, sr, 0.001, 0.05), -1.0), sr, False


def pipoca_chiado():
    """Servo motor da Pipoca andando: motor que oscila, assobio agudo e tique de engrenagem. Loop de 2 s."""
    sr, dur, r = SR, 2.0, gerador(5)
    t = tempo(dur, sr)
    n = len(t)
    # Todas as oscilações completam ciclos inteiros em 2 s -> a fase volta ao mesmo ponto.
    freq_motor = 180.0 + 25.0 * np.sin(DOIS_PI * 0.5 * t) + 8.0 * np.sin(DOIS_PI * 3.5 * t)
    fase = fase_de(freq_motor, sr)
    motor = filtrar(serra(fase), sr, 150, 2500, circular=True)
    assobio = np.sin(fase * 7.0) * 0.25
    engrenagem = filtrar(r.standard_normal(n), sr, 1200, 4000, circular=True)
    engrenagem = engrenagem / np.max(np.abs(engrenagem)) * (0.5 + 0.5 * np.sin(DOIS_PI * 14.0 * t)) ** 4
    tiques = np.zeros(n)
    for k in range(16):
        colocar(tiques, estalo(sr, r, 0.003, 0.0006), k * n // 16, circular=True)
    tiques = filtrar(tiques, sr, passa_altas=2500, circular=True)
    tiques /= np.max(np.abs(tiques))
    x = motor / np.max(np.abs(motor)) * 0.6 + assobio * 0.3 + engrenagem * 0.35 + tiques * 0.3
    x = np.tanh(1.8 * x) * (0.8 + 0.2 * np.sin(DOIS_PI * 0.5 * t))
    return normalizar(x, -6.0), sr, True


def pipoca_pane():
    """Pane elétrica (Pipoca atordoada): zumbido caindo de tom, falhando, com faíscas e um estouro."""
    sr, r = SR, gerador(6)
    t = tempo(1.5, sr)
    n = len(t)
    fase = fase_de(60.0 + 340.0 * np.exp(-t / 0.45), sr)  # de ~400 Hz caindo até 60 Hz
    zumbido = np.tanh(4.0 * np.sin(fase)) + 0.5 * serra(fase)
    # Falhas: blocos curtos ligado/desligado, suavizados para não estalar demais
    porta = np.zeros(n)
    pos = 0
    while pos < n:
        bloco = int(r.uniform(0.02, 0.08) * sr)
        porta[pos:pos + bloco] = 1.0 if r.random() < 0.7 else 0.1
        pos += bloco
    janela = int(0.002 * sr)
    porta = np.convolve(porta, np.ones(janela) / janela, mode="same")
    faiscas = np.zeros(n)
    for _ in range(70):
        colocar(faiscas, estalo(sr, r, 0.006, 0.001) * r.uniform(0.3, 1.0), int((r.random() ** 1.5) * n))
    faiscas = filtrar(faiscas, sr, passa_altas=1800)
    faiscas /= np.max(np.abs(faiscas))
    estouro = np.zeros(n)
    te = tempo(0.3, sr)
    som_estouro = filtrar(r.standard_normal(len(te)) * np.exp(-te / 0.015), sr, 100, 5000)
    som_estouro = som_estouro / np.max(np.abs(som_estouro)) + np.sin(DOIS_PI * 70.0 * te) * np.exp(-te / 0.06)
    colocar(estouro, som_estouro, int(1.18 * sr))
    final = np.clip((1.5 - t) / 0.3, 0.0, 1.0)
    x = zumbido * porta * 0.6 * np.clip((1.2 - t) / 0.25, 0.0, 1.0) + faiscas * 0.5 * final + estouro * 0.8
    return normalizar(fades(x, sr, 0.002, 0.05), -2.0), sr, False


def disjuntor_clique():
    """Disjuntor religado: claque mecânico duplo + 'thunk' grave + zumbido da energia voltando."""
    sr, r = SR, gerador(7)
    t = tempo(0.5, sr)
    n = len(t)
    x = np.zeros(n)

    def claque(forca):
        tc = tempo(0.08, sr)
        ruido = filtrar(r.standard_normal(len(tc)) * np.exp(-tc / 0.002), sr, passa_altas=1200)
        ruido /= np.max(np.abs(ruido))
        ping = np.sin(DOIS_PI * 2400 * tc) * np.exp(-tc / 0.02) + 0.6 * np.sin(DOIS_PI * 3700 * tc) * np.exp(-tc / 0.012)
        return (ruido + ping * 0.5) * forca

    colocar(x, claque(1.0), 0)
    colocar(x, claque(0.55), int(0.022 * sr))
    tt = tempo(0.45, sr)
    thunk = np.sin(fase_de(55.0 + 30.0 * np.exp(-tt / 0.05), sr)) * np.exp(-tt / 0.12)
    colocar(x, thunk * 0.9, int(0.025 * sr))
    te = tempo(0.42, sr)
    energia = np.tanh(2.0 * (np.sin(DOIS_PI * 120 * te) + 0.5 * np.sin(DOIS_PI * 240 * te) + 0.3 * np.sin(DOIS_PI * 360 * te)))
    energia *= np.clip(te / 0.03, 0, 1) * np.exp(-te / 0.15)
    colocar(x, energia * 0.35, int(0.04 * sr))
    return normalizar(fades(x, sr, 0.0005, 0.05), -1.0), sr, False


def lanterna_clique():
    """Clique curto do botão da lanterna."""
    sr, r = SR, gerador(8)
    t = tempo(0.08, sr)
    x = np.zeros(len(t))
    tc = tempo(0.03, sr)
    for atraso, forca in [(0.0, 1.0), (0.012, 0.45)]:
        clique = filtrar(r.standard_normal(len(tc)) * np.exp(-tc / 0.0007), sr, 1000, 9000)
        clique = clique / np.max(np.abs(clique)) + 0.5 * np.sin(DOIS_PI * 1800 * tc) * np.exp(-tc / 0.004)
        colocar(x, clique * forca, int(atraso * sr))
    return normalizar(fades(x, sr, 0.0005, 0.01), -4.0), sr, False


def pegar_pilha():
    """Blip agradável subindo (três notas rápidas)."""
    sr = SR
    t = tempo(0.32, sr)
    x = np.zeros(len(t))
    for i, (inicio, freq) in enumerate([(0.0, 880.0), (0.07, 1318.5), (0.14, 1760.0)]):
        tn = tempo(0.32 - inicio, sr)
        f = freq * (1.0 + 0.02 * tn)  # sobe um pouquinho dentro da nota
        fase = fase_de(f, sr)
        onda = np.sin(fase) + 0.3 * np.sin(2 * fase) + 0.12 * np.sign(np.sin(fase))
        tau = 0.12 if i == 2 else 0.06
        colocar(x, onda * np.clip(tn / 0.003, 0, 1) * np.exp(-tn / tau), int(inicio * sr))
    return normalizar(fades(x, sr, 0.001, 0.03), -4.0), sr, False


def badalada():
    """Badalada grave de relógio (sino), com batimento leve entre parciais quase iguais."""
    sr, r = SR, gerador(9)
    t = tempo(3.0, sr)
    n = len(t)
    f0 = 146.83  # Ré grave
    parciais = [(0.5, 0.5, 2.8), (1.0, 1.0, 2.2), (1.183, 0.55, 1.6), (1.506, 0.4, 1.2), (2.0, 0.45, 1.0),
                (2.514, 0.25, 0.7), (3.011, 0.2, 0.5), (4.166, 0.12, 0.35), (5.433, 0.08, 0.25)]
    x = np.zeros(n)
    for i, (razao, amp, tau) in enumerate(parciais):
        f = f0 * razao
        # Duas cópias levemente desafinadas -> o "uóóóm" ondulado de sino
        x += amp * 0.5 * (np.sin(DOIS_PI * f * t + i) + np.sin(DOIS_PI * (f + 0.7) * t)) * np.exp(-t / tau)
    golpe = filtrar(r.standard_normal(n) * np.exp(-t / 0.005), sr, 500, 5000)
    x += golpe / np.max(np.abs(golpe)) * 0.3
    return normalizar(fades(x, sr, 0.001, 0.2), -2.0), sr, False


def jumpscare():
    """Rugido eletrônico distorcido do susto (sem voz humana): serras + FM metálica + ruído + grave."""
    sr, r = SR, gerador(10)
    dur = 1.3
    t = tempo(dur, sr)
    n = len(t)
    envelope = np.clip(t / 0.005, 0, 1) * np.clip((dur - t) / 0.35, 0, 1)
    base = 110.0 * (1.0 + 0.6 * np.clip(t / 0.25, 0, 1)) * (1.0 + 0.04 * np.sin(DOIS_PI * 9.0 * t))
    rugido = sum(serra(fase_de(base * d, sr)) for d in (1.0, 1.012, 0.497, 1.5045))
    portadora = 1100.0 * (1.0 + 0.3 * np.sin(DOIS_PI * 5.5 * t))
    fm = np.sin(fase_de(portadora, sr) + 6.0 * np.sin(DOIS_PI * 173.0 * t))
    anel = rugido * np.sin(DOIS_PI * 317.0 * t)
    ruido = filtrar(r.standard_normal(n), sr, 300, 9000)
    ruido /= np.max(np.abs(ruido))
    grave = np.sin(fase_de(45.0 + 40.0 * np.exp(-t / 0.08), sr)) * np.exp(-t / 0.4)
    x = rugido * 0.25 + fm * 0.45 + anel * 0.15 + ruido * 0.35 + grave * 0.9
    x = np.tanh(3.5 * x)
    x = 0.6 * x + 0.4 * np.round(x * 32.0) / 32.0  # um pouco de "bitcrush" (som digital quebrado)
    return normalizar(x * envelope, -0.3), sr, False


def ambiente_grave():
    """Drone grave e escuro para o fundo, com respiração lenta. Loop de 20 s."""
    sr, dur, r = SR_LONGO, 20.0, gerador(11)
    t = tempo(dur, sr)
    n = len(t)
    # Frequências múltiplas de 0,05 Hz completam ciclos inteiros em 20 s -> emenda perfeita.
    tons = [(36.7, 0.4), (55.0, 0.5), (55.15, 0.35), (82.4, 0.25), (110.05, 0.15)]
    drone = sum(a * np.sin(DOIS_PI * f * t + i) for i, (f, a) in enumerate(tons))
    respiracao = (0.7 + 0.3 * np.sin(DOIS_PI * 0.05 * t)) * (0.85 + 0.15 * np.sin(DOIS_PI * 0.15 * t + 1.0))
    marrom = filtrar(r.standard_normal(n), sr, 20, 180, circular=True)
    marrom /= np.max(np.abs(marrom))
    vento = filtrar(r.standard_normal(n), sr, 200, 600, circular=True)
    vento = vento / np.max(np.abs(vento)) * (0.5 + 0.5 * np.sin(DOIS_PI * 0.1 * t)) ** 2
    x = (drone * 0.6 + marrom * 0.8) * respiracao + vento * 0.15
    return normalizar(x, -6.0), sr, True


# Melodia original da pizzaria, em 3/4 (valsinha), 108 batidas por minuto, 12 compassos = 20 s.
# Cada compasso: lista de (batida dentro do compasso, nota MIDI). 72 = Dó5.
MELODIA = [
    [(0, 76), (1, 79), (1.5, 77), (2, 76)],
    [(0, 72), (1, 76), (2, 81)],
    [(0, 77), (1, 76), (1.5, 74), (2, 72)],
    [(0, 74), (2, 71)],
    [(0, 76), (1, 79), (1.5, 81), (2, 79)],
    [(0, 80), (1, 81), (1.5, 83), (2, 84)],
    [(0, 81), (1, 77), (2, 74)],
    [(0, 79), (1, 77), (1.5, 74), (2, 71)],
    [(0, 72), (0.5, 77), (1, 81), (2, 77)],
    [(0, 79), (0.5, 76), (1, 72), (2, 76)],
    [(0, 74), (1, 79), (2, 77), (2.5, 74)],
    [(0, 72)],
]
# Acompanhamento: (baixo no 1º tempo, duas notas do acorde no 2º e 3º tempos)
ACORDES = [
    (48, (64, 67)), (45, (64, 69)), (41, (65, 69)), (43, (62, 67)),
    (48, (64, 67)), (40, (64, 68)), (50, (62, 65)), (43, (62, 67)),
    (41, (65, 69)), (48, (64, 67)), (43, (62, 67)), (48, (64, 67)),
]


def musica_pizzaria():
    """Caixinha de música alegre, mas desafinada e com 'wow' de fita velha. Loop de 20 s."""
    sr, r = SR_LONGO, gerador(12)
    batida = 60.0 / 108.0
    duracao = len(MELODIA) * 3 * batida  # = 20 s
    n = int(round(duracao * sr))
    cauda = int(2.5 * sr)  # as notas do fim continuam soando "por cima" do começo do loop
    total = n + cauda
    tt = np.arange(total) / sr
    # Wow/flutter: oscilações de afinação com ciclos inteiros em 20 s (emendam no loop)
    oscilacao = 1.0 + 0.0045 * np.sin(DOIS_PI * 0.5 * tt) + 0.0015 * np.sin(DOIS_PI * 7.0 * tt)
    buf = np.zeros(total)

    def tocar(nota_midi, instante, volume, brilho=1.0):
        # Cada nota sai um pouco desafinada (até ±12 cents); algumas bem mais (caixinha velha)
        cents = r.uniform(-12, 12) + (r.choice([0, 0, 0, -22, 18]))
        freq = midi_para_hz(nota_midi) * 2.0 ** (cents / 1200.0)
        inicio = int(round(instante * sr))
        som = nota_caixinha(freq, sr, 2.5, oscilacao[inicio:inicio + int(2.5 * sr)], brilho)
        # tiquinho mecânico do pino batendo na lâmina
        tique = estalo(sr, r, 0.003, 0.0005) * 0.04
        colocar(buf, som * volume, inicio)
        colocar(buf, tique, inicio)

    for c, (compasso, (baixo, acorde)) in enumerate(zip(MELODIA, ACORDES)):
        inicio_compasso = c * 3 * batida
        for tempo_nota, nota in compasso:
            tocar(nota, inicio_compasso + tempo_nota * batida, 0.9)
        tocar(baixo, inicio_compasso, 0.55, brilho=0.5)
        for b in (1, 2):
            for nota in acorde:
                tocar(nota, inicio_compasso + b * batida, 0.22, brilho=0.6)

    # Dá a volta: o que passou do fim é somado no começo -> loop sem emenda
    x = buf[:n].copy()
    x[:cauda] += buf[n:]
    chiado = filtrar(r.standard_normal(n), sr, 2000, 8000, circular=True)
    x += chiado / np.max(np.abs(chiado)) * 0.006
    return normalizar(x, -3.0), sr, True


def vitoria():
    """Jingle curto e alegre de vitória (arpejo subindo + acorde final)."""
    sr, r = SR, gerador(13)
    dur = 2.0
    t = tempo(dur, sr)
    n = len(t)
    x = np.zeros(n)
    notas = [(0.0, 72), (0.11, 76), (0.22, 79), (0.33, 84), (0.55, 81), (0.66, 83), (0.8, 84)]
    for instante, nota in notas:
        f = midi_para_hz(nota)
        som = nota_caixinha(f, sr, dur - instante)
        tn = tempo(dur - instante, sr)
        quadrada = np.sign(np.sin(DOIS_PI * f * tn)) * np.exp(-tn / 0.15) * 0.12  # brilho de "videogame"
        colocar(x, som + quadrada, int(instante * sr))
    # Acorde de fundo (onda triangular suave) segurando o final
    tc = tempo(dur - 0.8, sr)
    env = np.clip(tc / 0.02, 0, 1) * np.exp(-tc / 0.6)
    acorde = np.zeros(len(tc))
    for nota in (60, 64, 67, 72):
        fase = DOIS_PI * midi_para_hz(nota) * tc
        acorde += (2.0 / np.pi) * np.arcsin(np.sin(fase))
    colocar(x, acorde * env * 0.18, int(0.8 * sr))
    return normalizar(fades(x, sr, 0.001, 0.3), -2.0), sr, False


SONS = {
    "zumbido_lampada.wav": zumbido_lampada,
    "estatica.wav": estatica,
    "passo_1.wav": lambda: passo(21, 1.0),
    "passo_2.wav": lambda: passo(22, 0.92),
    "passo_3.wav": lambda: passo(23, 1.08),
    "tito_passo.wav": tito_passo,
    "pipoca_chiado.wav": pipoca_chiado,
    "pipoca_pane.wav": pipoca_pane,
    "disjuntor_clique.wav": disjuntor_clique,
    "lanterna_clique.wav": lanterna_clique,
    "pegar_pilha.wav": pegar_pilha,
    "badalada.wav": badalada,
    "jumpscare.wav": jumpscare,
    "ambiente_grave.wav": ambiente_grave,
    "musica_pizzaria.wav": musica_pizzaria,
    "vitoria.wav": vitoria,
}


# ---------------------------------------------------------------------------
# Conferência: lê os arquivos de volta e mostra um resumo
# ---------------------------------------------------------------------------

def ler_loop(caminho):
    """Procura o bloco 'smpl' no WAV e devolve (inicio, fim) do loop, ou None."""
    dados = caminho.read_bytes()
    pos = 12
    while pos + 8 <= len(dados):
        ident = dados[pos:pos + 4]
        tamanho = struct.unpack("<I", dados[pos + 4:pos + 8])[0]
        if ident == b"smpl":
            corpo = dados[pos + 8:pos + 8 + tamanho]
            if struct.unpack("<I", corpo[28:32])[0] >= 1:
                return struct.unpack("<II", corpo[36 + 8:36 + 16])
        pos += 8 + tamanho + (tamanho % 2)
    return None


def conferir():
    print(f"{'arquivo':<24}{'dur (s)':>9}{'taxa':>8}{'pico dBFS':>11}  loop")
    for nome in SONS:
        caminho = PASTA_SONS / nome
        with wave.open(str(caminho), "rb") as w:
            sr = w.getframerate()
            quadros = w.getnframes()
            amostras = np.frombuffer(w.readframes(quadros), dtype="<i2").astype(np.float64) / 32768.0
            assert w.getnchannels() == 1 and w.getsampwidth() == 2
        pico = 20 * np.log10(max(np.max(np.abs(amostras)), 1e-9))
        loop = ler_loop(caminho)
        texto_loop = "-"
        if loop:
            # Emenda: o salto do fim para o começo deve ser do tamanho de um passo normal do sinal
            salto = abs(amostras[-1] - amostras[0])
            passo_tipico = np.percentile(np.abs(np.diff(amostras)), 99)
            texto_loop = f"smpl {loop[0]}-{loop[1]} emenda {'ok' if salto <= passo_tipico * 1.5 else 'RUIM'}"
        print(f"{nome:<24}{quadros / sr:>9.2f}{sr:>8}{pico:>11.1f}  {texto_loop}")


def main():
    PASTA_SONS.mkdir(parents=True, exist_ok=True)
    for nome, funcao in SONS.items():
        x, sr, loop = funcao()
        salvar_wav(nome, x, sr, loop)
    print(f"Sons gerados em {PASTA_SONS}")
    conferir()


if __name__ == "__main__":
    main()
