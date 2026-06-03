# project/test_smoke.py
"""
Prueba de humo: verifica toda la lógica Python del framework
sin necesitar la red OpenDSS real.

Testea:
  - config.py importa correctamente (con BESS_PV_RATIO y EV_PV_RATIO)
  - pv_allocation genera unidades y archivo cenario_PV.dss
  - bess_allocation genera unidades y archivo cenario_BESS.dss
  - ev_profiles carga CSVs de carpeta (y fallback si está vacía)
  - ev_allocation genera unidades con curva por estación y archivo cenario_EV.dss
  - reporter genera CSV con 11 columnas y 1 fila
  - los ratios calculan penetraciones correctamente

Ejecutar con:
    python test_smoke.py
"""

import os
import csv
import tempfile
import numpy as np

print("=" * 55)
print("  Smoke Test — Framework Monte Carlo HC")
print("=" * 55)

# -----------------------------------------------------------------------
# 1. config importa y tiene todos los campos requeridos
# -----------------------------------------------------------------------
import config
required = [
    "NETWORK_NAME", "TRANSFORMER_MVA",
    "PENETRATION_LEVELS_PV",
    "BESS_PV_RATIO", "EV_PV_RATIO",
    "BESS_PLACEMENT", "EV_ELIGIBLE_BUSES",
    "EV_PROFILES_DIR", "BESS_PROFILES_DIR",
]
for attr in required:
    assert hasattr(config, attr), f"ERROR: config falta {attr}"

# Verificar que los ratios calculan bien
pen_pv = 50
pen_bess_esperado = round(pen_pv * config.BESS_PV_RATIO, 4)
pen_ev_esperado   = round(pen_pv * config.EV_PV_RATIO,   4)
assert pen_bess_esperado == round(50 * 0.5,  4), "ERROR: BESS_PV_RATIO no calcula bien"
assert pen_ev_esperado   == round(50 * 0.25, 4), "ERROR: EV_PV_RATIO no calcula bien"
print("[1/6] config.py ................. OK")

# -----------------------------------------------------------------------
# 2. PV allocation + generate_cenario_pv
# -----------------------------------------------------------------------
from modules.pv.pv_allocation import allocate_pv, generate_cenario_pv

mt_buses  = ["bus1", "bus2", "bus3", "bus4", "bus5"]
mt_kv     = [7.967] * 5
mt_phases = [3] * 5
energy    = 1_000_000.0

irrad_pu = [0.0]*6 + [0.1, 0.3, 0.6, 0.9, 1.0, 0.9, 0.8, 0.6, 0.4, 0.2, 0.1] + [0.0]*7
temp_c   = [20.0] * 24

pv_units, p_total = allocate_pv(
    energy, 10, psh=5.4,
    mt_buses=mt_buses, mt_kv=mt_kv, mt_phases=mt_phases,
    pv_sizes_kw=[300, 600, 1200],
    pv_probs=[0.33, 0.34, 0.33],
)
assert len(pv_units) > 0, "ERROR: allocate_pv no generó ninguna unidad"
assert p_total > 0,       "ERROR: p_total PV debe ser > 0"

with tempfile.NamedTemporaryFile(suffix=".dss", delete=False, mode="w") as f:
    tmp_pv = f.name
generate_cenario_pv(pv_units, irrad_pu, temp_c, tmp_pv, 10, 6)
assert "PVSystem." in open(tmp_pv).read(), "ERROR: cenario_PV.dss no contiene PVSystem"
os.remove(tmp_pv)
print("[2/6] pv_allocation ............. OK")

# -----------------------------------------------------------------------
# 3. BESS allocation + generate_cenario_bess
# -----------------------------------------------------------------------
from modules.bess.bess_profiles   import load_bess_profiles
from modules.bess.bess_allocation import allocate_bess, generate_cenario_bess

bess_profiles_t, bess_names_t = load_bess_profiles(config.BESS_PROFILES_DIR)
pen_bess = round(10 * config.BESS_PV_RATIO, 4)   # calculado con ratio
bess_units, e_bess = allocate_bess(
    energy, pen_bess,
    mt_buses=mt_buses, mt_kv=mt_kv, mt_phases=mt_phases,
    bess_sizes_kwh=[1200, 2400, 4800],
    bess_probs=[0.33, 0.34, 0.33],
    charge_hours=4,
    placement="colocated",
    profiles=bess_profiles_t,
    profile_names=bess_names_t,
    pv_units=pv_units,
)
assert len(bess_units) > 0, "ERROR: allocate_bess no generó ninguna unidad"
pv_bus_set = {u["bus"] for u in pv_units}
for bu in bess_units:
    assert bu["bus"] in pv_bus_set, \
        f"ERROR: BESS bus {bu['bus']} no está en barras PV (colocated)"

with tempfile.NamedTemporaryFile(suffix=".dss", delete=False, mode="w") as f:
    tmp_bess = f.name
generate_cenario_bess(bess_units, tmp_bess, pen_bess)
assert "Storage." in open(tmp_bess).read(), "ERROR: cenario_BESS.dss no contiene Storage"
os.remove(tmp_bess)
print("[3/6] bess_allocation ........... OK")

# -----------------------------------------------------------------------
# 4. ev_profiles — fallback cuando carpeta vacía
# -----------------------------------------------------------------------
from modules.ev_cs.ev_profiles import load_ev_profiles, sample_ev_profile

with tempfile.TemporaryDirectory() as empty_dir:
    profiles_empty, names_empty = load_ev_profiles(empty_dir)
assert len(profiles_empty) == 1,       "ERROR: fallback debe tener exactamente 1 perfil"
assert len(profiles_empty[0]) == 24,   "ERROR: perfil fallback debe tener 24 valores"
assert max(profiles_empty[0]) == 1.0,  "ERROR: perfil fallback debe estar normalizado"

# Probar con un CSV real
with tempfile.TemporaryDirectory() as csv_dir:
    # Escribir un CSV de prueba con 24 valores
    test_curve = [float(i) for i in range(1, 25)]   # 1..24
    csv_path = os.path.join(csv_dir, "curva_test.csv")
    with open(csv_path, "w") as f:
        f.write(",".join(str(v) for v in test_curve))
    profiles_real, names_real = load_ev_profiles(csv_dir)
assert len(profiles_real) == 1,        "ERROR: debe cargar exactamente 1 CSV"
assert names_real[0] == "curva_test",  "ERROR: nombre incorrecto"
assert max(profiles_real[0]) == 1.0,   "ERROR: perfil CSV debe estar normalizado"
assert len(profiles_real[0]) == 24,    "ERROR: perfil CSV debe tener 24 valores"

# Sorteo
p, n = sample_ev_profile(profiles_real, names_real)
assert len(p) == 24, "ERROR: perfil sorteado debe tener 24 valores"
print("[4/6] ev_profiles ............... OK")

# -----------------------------------------------------------------------
# 5. EV allocation + generate_cenario_ev (curva por estación)
# -----------------------------------------------------------------------
from modules.ev_cs.ev_allocation import allocate_ev, generate_cenario_ev

pen_ev = round(10 * config.EV_PV_RATIO, 4)   # calculado con ratio
ev_units, e_ev = allocate_ev(
    energy, pen_ev,
    mt_buses=mt_buses, mt_kv=mt_kv, mt_phases=mt_phases,
    ev_sizes_kw=[600, 1200],
    ev_probs=[0.5, 0.5],
    ev_eligible_buses=[],
    profiles=profiles_empty,
    profile_names=names_empty,
)
assert len(ev_units) > 0, "ERROR: allocate_ev no generó ninguna unidad"
# Verificar que cada unidad tiene su propia curva
for u in ev_units:
    assert "profile" in u,        "ERROR: unidad EV sin campo 'profile'"
    assert len(u["profile"]) == 24, "ERROR: curva EV no tiene 24 valores"

with tempfile.NamedTemporaryFile(suffix=".dss", delete=False, mode="w") as f:
    tmp_ev = f.name
generate_cenario_ev(ev_units, tmp_ev, pen_ev)
content = open(tmp_ev).read()
assert "Load." in content,      "ERROR: cenario_EV.dss no contiene Load"
assert "Loadshape." in content, "ERROR: cenario_EV.dss no contiene Loadshape"
# Verificar que hay una Loadshape por estación
n_loads     = content.count("New Load.")
n_loadshapes = content.count("New Loadshape.")
assert n_loads == n_loadshapes, \
    f"ERROR: {n_loadshapes} curvas para {n_loads} estaciones — deben ser iguales"
os.remove(tmp_ev)
print("[5/6] ev_allocation ............. OK")

# -----------------------------------------------------------------------
# 6. reporter — contadores de tensión correctos + CSV con 11 columnas
# -----------------------------------------------------------------------
from results.reporter import init_csv, append_row

with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
    tmp_csv = f.name

init_csv(tmp_csv)

# Simular resultado con sets de barras afectadas:
# - bus1 y bus2 tuvieron subtensión
# - bus3 tuvo sobretensión
# - bus2 tuvo AMBAS (subtensión Y sobretensión en distintas horas)
# → B_Vmin    = 2  (bus1, bus2)
# → B_Vmax    = 2  (bus2, bus3)
# → B_VminVmax = 3  (bus1, bus2, bus3) — unión, sin doble conteo
fake_sim = {
    "perfil_vmin":      [0.97] * 24,
    "perfil_vmax":      [1.02] * 24,
    "perfil_pactiva":   [45000.0] * 24,
    "perfil_preactiva": [10000.0] * 24,
    "perfil_losses":    [200.0] * 24,
    "perfil_trafo":     [78.5] * 24,
    "buses_vmin":       {"bus1", "bus2"},
    "buses_vmax":       {"bus2", "bus3"},
    "fluxo_min":        40000.0,
}
pen_bess_csv = round(50 * config.BESS_PV_RATIO, 4)
pen_ev_csv   = round(50 * config.EV_PV_RATIO,   4)
append_row(tmp_csv, 50, pen_bess_csv, pen_ev_csv, fake_sim)

with open(tmp_csv, newline="") as f:
    rows = list(csv.DictReader(f))

assert len(rows) == 1, f"ERROR: se esperaba 1 fila, hay {len(rows)}"

expected_cols = [
    "Pen_PV", "Pen_BESS", "Pen_EV",
    "B_Vmin", "B_Vmax", "B_VminVmax",
    "Max_PLosses", "Min_PLosses", "Energy_Losses",
    "Min_Fluxo_Subestacao", "Trafo_Loading_pct",
]
for col in expected_cols:
    assert col in rows[0], f"ERROR: falta columna '{col}'"

assert int(rows[0]["B_Vmin"])    == 2, f"ERROR: B_Vmin esperado 2, got {rows[0]['B_Vmin']}"
assert int(rows[0]["B_Vmax"])    == 2, f"ERROR: B_Vmax esperado 2, got {rows[0]['B_Vmax']}"
assert int(rows[0]["B_VminVmax"])== 3, f"ERROR: B_VminVmax esperado 3 (union), got {rows[0]['B_VminVmax']}"
assert float(rows[0]["Trafo_Loading_pct"]) == 78.5, "ERROR: Trafo_Loading_pct incorrecto"
os.remove(tmp_csv)
print("[6/6] reporter CSV .............. OK")

# -----------------------------------------------------------------------
print("=" * 55)
print("  Smoke Test PASADO — todos los modulos OK")
print("=" * 55)
print()
print("Proximos pasos:")
print("  1. Copiar los archivos .dss de la red 18Bus a:")
print(f"     {config.NETWORK_DIR}/")
print("  2. Agregar al final del master.dss las 3 lineas:")
print("       redirect cenario_PV.dss")
print("       redirect cenario_BESS.dss")
print("       redirect cenario_EV.dss")
print("  3. Copiar Geracao_Solar.csv a data/irradiance/")
print("  4. Jhon:  poner curvas BESS en data/bess_profiles/ (CSV, 24 valores)")
print("  5. Marcos: poner curvas EV  en data/ev_profiles/  (CSV, 24 valores)")
print("  6. Ejecutar: python main.py")
