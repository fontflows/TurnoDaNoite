"""
gerar_mundo_v2.py — cria a cena godot/cenas/mundo_v2.tscn a partir da planta da V2
(blender/scripts/planta_v2.py): cenário, marcadores, pilhas, câmeras, monitor, zona de
vitória, animatrônicos, jogador e HUD. Depois de criada, a cena é editada no Godot.

Uso (na pasta TurnoDaNoite):
    python ferramentas/gerar_mundo_v2.py            -> só cria se a cena ainda não existir
    python ferramentas/gerar_mundo_v2.py --forcar   -> recria (APAGA ajustes feitos à mão na cena)
"""

import math
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "blender" / "scripts"))
import planta_v2  # noqa: E402

DESTINO = RAIZ / "godot" / "cenas" / "mundo_v2.tscn"
GLBS = ["v2_predio", "v2_publico", "v2_diversao", "v2_servico", "v2_enchimento"]


def g(x, z, y=0.0):
    """Planta (x, z) + altura -> 'x, y, z' do Godot."""
    return f"{x - 30.0:g}, {y:g}, {z - 22.5:g}"


def transform(x, z, y=0.0, graus=0.0):
    """Transform3D com rotação em Y (graus; 0 = frente para -Z, 90 = frente para -X)."""
    r = math.radians(graus)
    c, s = round(math.cos(r), 6), round(math.sin(r), 6)
    return f"Transform3D({c:g}, 0, {s:g}, 0, 1, 0, {-s:g}, 0, {c:g}, {g(x, z, y)})"


def main():
    if DESTINO.exists() and "--forcar" not in sys.argv:
        print(f"{DESTINO.name} já existe (use --forcar para recriar e perder os ajustes feitos à mão)")
        return
    P = planta_v2.PONTOS
    ext, nos = [], []

    def recurso(tipo, caminho):
        ext.append((tipo, caminho))
        return f'ExtResource("{len(ext)}")'

    mundo_gd = recurso("Script", "res://scripts/mundo.gd")
    montador_gd = recurso("Script", "res://scripts/montador_mundo.gd")
    glbs = [(n, recurso("PackedScene", f"res://assets/cenario/{n}.glb")) for n in GLBS
            if (RAIZ / "godot" / "assets" / "cenario" / f"{n}.glb").exists()]
    pilha = recurso("PackedScene", "res://cenas/objetos/pilha.tscn")
    jogador = recurso("PackedScene", "res://cenas/jogador.tscn")
    hud = recurso("PackedScene", "res://ui/hud.tscn")
    pausa = recurso("PackedScene", "res://ui/pausa.tscn")
    tito = recurso("PackedScene", "res://cenas/animatronicos/tito.tscn")
    pipoca = recurso("PackedScene", "res://cenas/animatronicos/pipoca.tscn")
    monitor = recurso("PackedScene", "res://cenas/objetos/monitor_cameras.tscn")
    cam_gd = recurso("Script", "res://scripts/camera_seguranca.gd")
    ambiente_som = recurso("AudioStream", "res://assets/sons/ambiente_grave.wav")
    musica = recurso("AudioStream", "res://assets/sons/musica_pizzaria.wav")

    def no(cabecalho, *props):
        nos.append("[node " + cabecalho + "]\n" + "".join(p + "\n" for p in props))

    no('name="Mundo" type="Node3D"', f"script = {mundo_gd}", "segundos_por_hora = 0.0")
    no('name="Ambiente" type="WorldEnvironment" parent="."', 'environment = SubResource("Ambiente")')
    no('name="Navegacao" type="NavigationRegion3D" parent="."', 'navigation_mesh = SubResource("Malha_Navegacao")')
    no('name="Cenario" type="Node3D" parent="Navegacao"')
    for nome, r in glbs:
        no(f'name="{nome}" parent="Navegacao/Cenario" instance={r}')
    no('name="Disjuntores" type="Node3D" parent="."')
    no('name="Montador" type="Node" parent="."', f"script = {montador_gd}",
       'cenario = NodePath("../Navegacao/Cenario")', 'pasta_disjuntores = NodePath("../Disjuntores")')

    # Marcadores
    no('name="Marcadores" type="Node3D" parent="."')
    sx, sz, _ = P["spawn_jogador"]
    no('name="SpawnJogador" type="Marker3D" parent="Marcadores"', f"transform = {transform(sx, sz, 0.05, -90)}")
    no('name="Palco_Tito" type="Marker3D" parent="Marcadores"', f"transform = {transform(P['palco_tito'][0], P['palco_tito'][1], 0.6)}")
    no('name="Palco_Pipoca" type="Marker3D" parent="Marcadores"', f"transform = {transform(P['palco_pipoca'][0], P['palco_pipoca'][1], 0.6)}")
    no('name="Patrulha" type="Node3D" parent="Marcadores"')
    for i, (x, z) in enumerate(P["patrulha"], 1):
        no(f'name="ponto_patrulha_{i:02d}" type="Marker3D" parent="Marcadores/Patrulha" groups=["ponto_patrulha"]',
           f"transform = {transform(x, z)}")
    no('name="Fichas" type="Node3D" parent="Marcadores"')
    # Fichas e pilhas ficam no CHÃO de verdade: em cima do palco o chão está a 0,6 m
    # (planta_v2.altura_do_piso). Antes tudo ia para a altura 0 e a pilha do palco ficava
    # enterrada dentro da plataforma (só a luzinha verde aparecia).
    for i, (x, z) in enumerate(P["fichas"], 1):
        no(f'name="ponto_ficha_{i:02d}" type="Marker3D" parent="Marcadores/Fichas" groups=["ponto_ficha"]',
           f"transform = {transform(x, z, planta_v2.altura_do_piso(x, z))}")

    # Pilhas: todas as candidatas; o Mundo deixa só as primeiras conforme a dificuldade (as arriscadas vêm antes).
    no('name="Pilhas" type="Node3D" parent="."')
    for i, (x, z) in enumerate(P["pilhas"], 1):
        no(f'name="Pilha_{i:02d}" parent="Pilhas" instance={pilha}',
           f"transform = {transform(x, z, planta_v2.altura_do_piso(x, z))}")

    # Câmeras de segurança e monitor na mesa da sala de segurança
    no('name="CamerasSeguranca" type="Node3D" parent="."')
    for nome, x, z, h, ax, az, energia in P["cameras"]:
        no(f'name="{nome}" type="Camera3D" parent="CamerasSeguranca"', f"transform = {transform(x, z, h)}",
           "fov = 72.0", f"script = {cam_gd}", f"olhar_para = Vector3({g(ax, az, 1.0)})",
           f'metadata/energia = "{energia or ""}"')
    no('name="MonitorCameras" parent="." instance=' + monitor, f"transform = {transform(49.6, 28.25, 1.0)}",
       'no_moveis = NodePath("../Navegacao/Cenario")')

    # Zona de vitória (sala de segurança)
    no('name="ZonaSalaSeguranca" type="Area3D" parent="."', f"transform = {transform(48.5, 28.25, 1.2)}",
       "collision_layer = 0", "collision_mask = 2")
    no('name="Colisao" type="CollisionShape3D" parent="ZonaSalaSeguranca"', 'shape = SubResource("Caixa_Sala")')

    # Animatrônicos, vigia, interface e sons
    no('name="Animatronicos" type="Node3D" parent="."')
    no(f'name="Tito" parent="Animatronicos" instance={tito}', f"transform = {transform(P['palco_tito'][0], P['palco_tito'][1], 0.6)}",
       'ponto_palco = NodePath("../../Marcadores/Palco_Tito")')
    no(f'name="Pipoca" parent="Animatronicos" instance={pipoca}', f"transform = {transform(P['palco_pipoca'][0], P['palco_pipoca'][1], 0.6)}",
       'ponto_palco = NodePath("../../Marcadores/Palco_Pipoca")')
    no(f'name="Jogador" parent="." instance={jogador}', f"transform = {transform(sx, sz, 0.05, -90)}")
    no(f'name="HUD" parent="." instance={hud}')
    no(f'name="Pausa" parent="." instance={pausa}')
    no('name="Sons" type="Node3D" parent="."')
    no('name="SomAmbiente" type="AudioStreamPlayer" parent="Sons"', f"stream = {ambiente_som}", "volume_db = -12.0", "autoplay = true")
    no('name="MusicaPalco" type="AudioStreamPlayer3D" parent="Sons" groups=["som_musica"]', f"transform = {transform(27, 1.0, 1.5)}",
       f"stream = {musica}", "volume_db = -8.0", "unit_size = 3.0", "max_distance = 28.0", "autoplay = true")

    sub = """[sub_resource type="Environment" id="Ambiente"]
background_mode = 1
background_color = Color(0, 0, 0, 1)
ambient_light_source = 2
ambient_light_color = Color(0.32, 0.42, 0.68, 1)
ambient_light_energy = 0.38
fog_enabled = true
fog_light_color = Color(0.02, 0.025, 0.04, 1)
fog_density = 0.035
volumetric_fog_density = 0.025
volumetric_fog_albedo = Color(0.6, 0.65, 0.75, 1)

[sub_resource type="NavigationMesh" id="Malha_Navegacao"]
geometry_parsed_geometry_type = 1
geometry_collision_mask = 1
cell_size = 0.2
cell_height = 0.2
agent_height = 2.0
agent_radius = 0.4
agent_max_climb = 0.2
agent_max_slope = 40.0

[sub_resource type="BoxShape3D" id="Caixa_Sala"]
size = Vector3(2.8, 2.4, 2.3)
"""
    cab = f"[gd_scene load_steps={len(ext) + 4} format=3]\n\n"
    cab += "".join(f'[ext_resource type="{t}" path="{c}" id="{i}"]\n' for i, (t, c) in enumerate(ext, 1))
    DESTINO.write_text(cab + "\n" + sub + "\n" + "\n".join(nos), encoding="utf-8")
    print(f"criado: {DESTINO} ({len(nos)} nós, {len(glbs)} arquivos de cenário)")


if __name__ == "__main__":
    main()
