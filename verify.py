# project/verify.py
"""
Corre exactamente 1 iteración Monte Carlo con parámetros editables,
imprime un reporte detallado en consola y genera el gráfico de tensión.
NO escribe al CSV de resultados.

Ejecutar con:
    python verify.py
"""

# ============================================================
# PARÁMETROS EDITABLES
# ============================================================
PEN_PV   = 20    # penetración PV   [%]
PEN_BESS = 10    # penetración BESS [%]
PEN_EV   = 0     # penetración EV   [%]
SEED     = 55    # semilla
# ============================================================

import os
import random
import numpy as np

# 1. Semilla
random.seed(SEED)
np.random.seed(SEED)

# 2. Configuración
import config as cfg

# Rutas .dss generados
path_pv   = os.path.join(cfg.NETWORK_DIR, "cenario_PV.dss")
path_bess = os.path.join(cfg.NETWORK_DIR, "cenario_BESS.dss")
path_ev   = os.path.join(cfg.NETWORK_DIR, "cenario_EV.dss")

for path in [path_pv, path_bess, path_ev]:
    if not os.path.exists(path):
        open(path, "w").close()

# 3. Caso base
from core.network import run_base_case, run_with_ders

base = run_base_case(
    cfg.NETWORK_DSS_PATH,
    cfg.TRANSFORMER_MVA,
    cfg.ONLY_THREE_PHASE,
)
mt_buses  = base["mt_buses"]
mt_kv     = base["mt_kv"]
mt_phases = base["mt_phases"]
energy    = base["energy_kwh"]

# 4. PV
pv_units   = []
p_total_pv = 0.0
if cfg.ENABLE_PV:
    from modules.pv.pv_profiles  import load_irradiance_matrices, sample_monthly_profile
    from modules.pv.pv_allocation import allocate_pv, generate_cenario_pv

    irr_matrix, temp_matrix = load_irradiance_matrices(cfg.IRRADIANCE_FILE)
    irrad_pu, temp_c, psh, mes = sample_monthly_profile(irr_matrix, temp_matrix)
    pv_units, p_total_pv = allocate_pv(
        energy, PEN_PV, psh,
        mt_buses, mt_kv, mt_phases,
        cfg.PV_SIZES_KW, cfg.PV_PROBS,
        cfg.PV_POWER_FACTOR,
    )
    generate_cenario_pv(pv_units, irrad_pu, temp_c, path_pv, PEN_PV, mes)
else:
    open(path_pv, "w").close()

# 5. BESS
bess_units   = []
e_total_bess = 0.0
if cfg.ENABLE_BESS:
    from modules.bess.bess_profiles   import load_bess_profiles
    from modules.bess.bess_allocation import allocate_bess, generate_cenario_bess

    bess_profiles, bess_profile_names = load_bess_profiles(cfg.BESS_PROFILES_DIR)
    bess_units, e_total_bess = allocate_bess(
        energy, PEN_BESS,
        mt_buses, mt_kv, mt_phases,
        cfg.BESS_SIZES_KWH, cfg.BESS_PROBS,
        cfg.BESS_CHARGE_HOURS, cfg.BESS_PLACEMENT,
        bess_profiles, bess_profile_names,
        pv_units=pv_units,
        power_factor=cfg.BESS_POWER_FACTOR,
    )
    generate_cenario_bess(bess_units, path_bess, PEN_BESS)
else:
    open(path_bess, "w").close()

# 6. EV/CS
ev_units = []
if cfg.ENABLE_EV_CS:
    from modules.ev_cs.ev_profiles   import load_ev_profiles
    from modules.ev_cs.ev_allocation import allocate_ev, generate_cenario_ev

    ev_profiles, ev_profile_names = load_ev_profiles(cfg.EV_PROFILES_DIR)
    ev_units, _ = allocate_ev(
        energy, PEN_EV,
        mt_buses, mt_kv, mt_phases,
        cfg.EV_SIZES_KW, cfg.EV_PROBS,
        cfg.EV_ELIGIBLE_BUSES,
        ev_profiles, ev_profile_names,
        cfg.EV_POWER_FACTOR,
    )
    generate_cenario_ev(ev_units, path_ev, PEN_EV)
else:
    open(path_ev, "w").close()

# 7. Simulación con DERs
sim = run_with_ders(
    cfg.NETWORK_DSS_PATH,
    cfg.TRANSFORMER_MVA,
    enable_pv=cfg.ENABLE_PV,    path_pv=path_pv,
    enable_bess=cfg.ENABLE_BESS, path_bess=path_bess,
    enable_ev=cfg.ENABLE_EV_CS,  path_ev=path_ev,
)

# 8. Reporte en consola
SEP = "═" * 48

b_vmin    = len(sim["buses_vmin"])
b_vmax    = len(sim["buses_vmax"])
b_vminvmax = len(sim["buses_vmin"] | sim["buses_vmax"])

max_losses    = float(np.max(sim["perfil_losses"]))
energy_losses = float(np.sum(sim["perfil_losses"]))
trafo_max     = float(np.max(sim["perfil_trafo"]))

rel_pv   = os.path.relpath(path_pv,   cfg.BASE_DIR).replace("\\", "/")
rel_bess = os.path.relpath(path_bess, cfg.BASE_DIR).replace("\\", "/")
rel_ev   = os.path.relpath(path_ev,   cfg.BASE_DIR).replace("\\", "/")

print(SEP)
print(f" VERIFY — {cfg.NETWORK_NAME} | PV={PEN_PV}%  BESS={PEN_BESS}%  EV={PEN_EV}%  seed={SEED}")
print(SEP)

print(" Red")
print(f"   Energía diaria        : {energy:,.1f} kWh")
print(f"   Demanda máxima        : {base['p_max_kw']:,.1f} kW")
print(f"   Barras MT candidatas  : {len(mt_buses)}")
print()

if cfg.ENABLE_PV:
    print(" PV instalado")
    print(f"   Unidades              : {len(pv_units)}")
    print(f"   Potencia total        : {p_total_pv:,.1f} kW")
    print()

if cfg.ENABLE_BESS:
    print(" BESS instalado")
    print(f"   Unidades              : {len(bess_units)}")
    print(f"   Energía total         : {e_total_bess:,.1f} kWh")
    print()

print(" EV/CS instalado")
print(f"   Estaciones            : {len(ev_units)}")
print()

print(" KPIs simulación")
print(f"   B_Vmin                : {b_vmin}  barras con subtensión")
print(f"   B_Vmax                : {b_vmax}  barras con sobretensión")
print(f"   B_VminVmax            : {b_vminvmax}  barras afectadas (unión)")
print(f"   Max pérdidas activas  : {max_losses:,.1f} kW")
print(f"   Energía pérdidas      : {energy_losses:,.1f} kWh")
print(f"   Cargamento trafo máx  : {trafo_max:.1f} %")
print()

print(" Archivos DSS generados en:")
print(f"   {rel_pv}")
print(f"   {rel_bess}")
print(f"   {rel_ev}")
print(SEP)

# 9. Gráfico de tensión
from plot_voltage import plot_voltage_profile

figures_dir = os.path.join(cfg.RESULTS_DIR, "figures")
plot_voltage_profile(
    sim["perfil_vmin"], sim["perfil_vmax"],
    PEN_PV, PEN_BESS, PEN_EV, SEED,
    figures_dir, cfg.NETWORK_NAME,
)
