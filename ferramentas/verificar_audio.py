"""
verificar_audio.py — confere os áudios externos (voz e efeitos) de docs/PROMPTS_AUDIO.md.

Lista o que está PRESENTE, FALTANDO ou com NOME ERRADO em godot/assets/audio_externo/,
e ajusta o volume dos WAV para ficarem parecidos com o resto do jogo (o volume dos MP3 é
medido pelo próprio jogo, que compensa na hora de tocar).

Uso (na pasta TurnoDaNoite):
    python ferramentas/verificar_audio.py              (só confere e ajusta o volume)
    python ferramentas/verificar_audio.py --corrigir   (também renomeia/move nomes quase certos)
Grava o relatório em godot/assets/audio_externo/RELATORIO_AUDIO.txt.
"""

import difflib
import json
import re
import struct
import sys
import unicodedata
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "godot" / "assets" / "audio_externo"
MANIFESTO = PASTA / "manifesto_audio.json"
EXTENSOES = (".wav", ".mp3", ".ogg")
# Volume-alvo (pico em dBFS) por tipo: a voz e os sustos mais altos, ambientes mais baixos.
ALVO_DB = {"voz": -3.0, "efeitos": -3.0, "loop": -9.0}


def normalizar_nome(texto):
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    texto = re.sub(r"\(\d+\)", "", texto)
    texto = re.sub(r"[^a-z0-9]+", "_", texto).strip("_")
    return texto


def arquivos_esperados(manifesto):
    """[(nome sem extensão, pasta, prioridade, id, loop)] — uma linha por arquivo (variações incluídas)."""
    saida = []
    for item in manifesto["audios"]:
        for nome in item["arquivos"]:
            saida.append((nome, item["pasta"], item["prioridade"], item["id"], item.get("loop", False)))
    return saida


def ler_wav(caminho):
    """Lê PCM 16/24/32 bits ou float32. Devolve (amostras float em -1..1, canais, taxa, bits, formato) ou None."""
    dados = caminho.read_bytes()
    if dados[:4] != b"RIFF" or dados[8:12] != b"WAVE":
        return None
    pos, fmt, corpo = 12, None, None
    while pos + 8 <= len(dados):
        ident, tam = dados[pos:pos + 4], struct.unpack("<I", dados[pos + 4:pos + 8])[0]
        if ident == b"fmt ":
            fmt = struct.unpack("<HHIIHH", dados[pos + 8:pos + 24])
        elif ident == b"data":
            corpo = dados[pos + 8:pos + 8 + tam]
        pos += 8 + tam + (tam % 2)
    if fmt is None or corpo is None:
        return None
    formato, canais, taxa, _, _, bits = fmt
    if formato == 3 and bits == 32:
        x = np.frombuffer(corpo, dtype="<f4").astype(np.float64)
    elif bits == 16:
        x = np.frombuffer(corpo, dtype="<i2").astype(np.float64) / 32768.0
    elif bits == 24:
        b = np.frombuffer(corpo[:len(corpo) // 3 * 3], dtype=np.uint8).reshape(-1, 3)
        x = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
        x = np.where(x >= 1 << 23, x - (1 << 24), x).astype(np.float64) / (1 << 23)
    elif bits == 32:
        x = np.frombuffer(corpo, dtype="<i4").astype(np.float64) / 2147483648.0
    else:
        return None
    return x, canais, taxa


def gravar_wav(caminho, x, canais, taxa):
    amostras = np.clip(np.round(x * 32767.0), -32768, 32767).astype("<i2").tobytes()
    blocos = b"fmt " + struct.pack("<I", 16) + struct.pack("<HHIIHH", 1, canais, taxa, taxa * 2 * canais, 2 * canais, 16)
    blocos += b"data" + struct.pack("<I", len(amostras)) + amostras
    caminho.write_bytes(b"RIFF" + struct.pack("<I", 4 + len(blocos)) + b"WAVE" + blocos)


def ajustar_volume(caminho, alvo_db):
    """Ajusta o pico do WAV para alvo_db (só mexe se estiver mais de 1,5 dB fora). Devolve texto do que fez."""
    lido = ler_wav(caminho)
    if lido is None:
        return "formato WAV não reconhecido (fica como está)"
    x, canais, taxa = lido
    pico = float(np.max(np.abs(x))) if len(x) else 0.0
    if pico <= 1e-6:
        return "ARQUIVO MUDO?"
    pico_db = 20 * np.log10(pico)
    if abs(pico_db - alvo_db) <= 1.5:
        return f"volume ok ({pico_db:.1f} dB)"
    gravar_wav(caminho, x * (10 ** (alvo_db / 20.0) / pico), canais, taxa)
    return f"volume ajustado ({pico_db:.1f} -> {alvo_db:.1f} dB)"


GODOT = Path.home() / "AppData/Local/Microsoft/WinGet/Packages/GodotEngine.GodotEngine_Microsoft.Winget.Source_8wekyb3d8bbwe/Godot_v4.7.2-stable_win64_console.exe"


def medir_no_godot(presentes):
    """Importa os arquivos novos e mede o volume de todos (WAV e MP3) pelo próprio Godot."""
    import os
    import subprocess
    if presentes == 0:
        return
    godot = os.environ.get("GODOT", str(GODOT))
    if not Path(godot).exists():
        print("\n(Para ajustar o volume dos MP3: abra o Godot uma vez e rode res://dev/medir_audio_externo.tscn)")
        return
    pasta = str(RAIZ / "godot")
    subprocess.run([godot, "--headless", "--path", pasta, "--import"], capture_output=True)
    r = subprocess.run([godot, "--headless", "--path", pasta, "res://dev/medir_audio_externo.tscn"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    linhas = [l for l in r.stdout.splitlines() if l.startswith("[medir]")]
    print("\nVolume medido no Godot (vale para WAV e MP3):")
    print("\n".join("  " + l for l in linhas))


def main():
    corrigir = "--corrigir" in sys.argv
    manifesto = json.loads(MANIFESTO.read_text(encoding="utf-8"))
    esperados = arquivos_esperados(manifesto)
    por_nome = {nome: (pasta, prio, id_, loop) for nome, pasta, prio, id_, loop in esperados}
    achados = [p for p in PASTA.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSOES]
    linhas, presentes, faltando, errados = [], [], [], []
    usados = set()
    for nome, (pasta, prio, id_, loop) in por_nome.items():
        # Variação única sem número (ex.: passo_azulejo.mp3) vale como a _01.
        sem_numero = nome[:-3] if re.search(r"_0[1-9]$", nome) and nome.endswith("_01") else None
        certo = [p for p in achados if (p.stem == nome or p.stem == sem_numero) and p.parent == PASTA / pasta]
        if certo:
            presentes.append((nome, certo[0], pasta, loop))
            usados.add(certo[0])
    for p in achados:
        if p in usados:
            continue
        chave = normalizar_nome(p.stem)
        parecido = difflib.get_close_matches(chave, list(por_nome), n=1, cutoff=0.75)
        if chave in por_nome or parecido:
            alvo_nome = chave if chave in por_nome else parecido[0]
            pasta = por_nome[alvo_nome][0]
            destino = PASTA / pasta / (alvo_nome + p.suffix.lower())
            if corrigir and not destino.exists():
                destino.parent.mkdir(parents=True, exist_ok=True)
                p.rename(destino)
                presentes.append((alvo_nome, destino, pasta, por_nome[alvo_nome][3]))
                linhas.append(f"  corrigido: {p.relative_to(PASTA)}  ->  {destino.relative_to(PASTA)}")
            else:
                errados.append(f"  {p.relative_to(PASTA)}  ->  deveria ser {pasta}/{alvo_nome}{p.suffix.lower()}")
        else:
            errados.append(f"  {p.relative_to(PASTA)}  ->  não reconheci este nome (confira na tabela do PROMPTS_AUDIO.md)")
    nomes_presentes = {n for n, *_ in presentes}
    opcionais = []
    for nome, pasta, prio, id_, _ in esperados:
        if nome not in nomes_presentes:
            base = nome[:-3] if re.search(r"_0[2-9]$", nome) else None
            if base and (base + "_01") in nomes_presentes:
                opcionais.append(f"  {pasta}/{nome} (variação extra; o jogo usa as que existem)")
            else:
                faltando.append(f"  [{prio:5s}] {id_:8s} {pasta}/{nome}")
    volumes = []
    for nome, caminho, pasta, loop in presentes:
        if caminho.suffix.lower() == ".wav":
            alvo = ALVO_DB["loop"] if loop else ALVO_DB.get(pasta, -3.0)
            volumes.append(f"  {pasta}/{caminho.name}: {ajustar_volume(caminho, alvo)}")
        else:
            volumes.append(f"  {pasta}/{caminho.name}: {caminho.suffix[1:].upper()} (o jogo mede e compensa o volume)")
    texto = ["ÁUDIOS EXTERNOS (docs/PROMPTS_AUDIO.md)", ""]
    texto += [f"Presentes: {len(nomes_presentes)} de {len(por_nome)}"] + volumes + [""]
    texto += [f"Com nome errado ou na pasta errada: {len(errados)}"] + errados
    if errados and not corrigir:
        texto.append("  (rode com --corrigir para arrumar os nomes quase certos)")
    texto += linhas + ["", f"Faltando: {len(faltando)} (o jogo usa o som atual no lugar)"] + faltando
    texto += ["", f"Variações extras não feitas (tudo bem): {len(opcionais)}"] + opcionais
    saida = "\n".join(texto)
    (PASTA / "RELATORIO_AUDIO.txt").write_text(saida + "\n", encoding="utf-8")
    print(saida)
    medir_no_godot(len(nomes_presentes))
    print(f"\nResumo: {len(nomes_presentes)} presentes, {len(errados)} com nome errado, {len(faltando)} faltando (de {len(por_nome)}).")


if __name__ == "__main__":
    main()
