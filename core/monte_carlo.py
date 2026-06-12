# project/core/monte_carlo.py
"""
Loop principal Monte Carlo.
Itera sobre los niveles de penetración PV definidos en config.
BESS y EV/CS se calculan automáticamente con los ratios BESS_PV_RATIO y EV_PV_RATIO.
"""

import os
import random
import numpy as np

from core.network import run_base_case, run_with_ders
from results.reporter import init_csv, append_row


def run_monte_carlo(cfg):
    """
    Ejecuta el loop Monte Carlo completo.

    Parámetro
    ---------
    cfg : module o SimpleNamespace — configuración (import config as cfg)
    """
    # --- Importar módulos activos y pre-cargar datos ---
    if cfg.ENABLE_PV:
        from modules.pv.pv_profiles   import load_irradiance_matrices, sample_monthly_profile
        from modules.pv.pv_allocation  import allocate_pv, generate_cenario_pv
        irr_matrix, temp_matrix = load_irradiance_matrices(cfg.IRRADIANCE_FILE)

    if cfg.ENABLE_BESS:
        from modules.bess.bess_profiles   import load_bess_profiles
        from modules.bess.bess_allocation import allocate_bess, generate_cenario_bess
        bess_profiles, bess_profile_names = load_bess_profiles(cfg.BESS_PROFILES_DIR)
        print(f"  Curvas BESS cargadas: {bess_profile_names}")

    if cfg.ENABLE_EV_CS:
        from modules.ev_cs.ev_profiles    import load_ev_profiles
        from modules.ev_cs.ev_allocation  import allocate_ev, generate_cenario_ev
        # Cargar todas las curvas EV una sola vez al inicio
        ev_profiles, ev_profile_names = load_ev_profiles(cfg.EV_PROFILES_DIR)
        print(f"  Curvas EV cargadas: {ev_profile_names}")

    # --- Rutas de los archivos .dss generados ---
    path_pv   = os.path.join(cfg.NETWORK_DIR, "cenario_PV.dss")
    path_bess = os.path.join(cfg.NETWORK_DIR, "cenario_BESS.dss")
    path_ev   = os.path.join(cfg.NETWORK_DIR, "cenario_EV.dss")

    for path in [path_pv, path_bess, path_ev]:
        if not os.path.exists(path):
            open(path, "w").close()

    # --- Inicializar CSV ---
    init_csv(cfg.RESULTS_FILE)

    # --- Loop principal ---
    levels_pv = cfg.PENETRATION_LEVELS_PV if cfg.ENABLE_PV else [0]
    total     = len(levels_pv) * cfg.NUM_ITERATIONS
    count     = 0

    for pen_pv in levels_pv:
        # Calcular penetraciones de BESS y EV desde los ratios
        pen_bess = round(pen_pv * cfg.BESS_PV_RATIO, 4) if cfg.ENABLE_BESS  else 0
        pen_ev   = round(pen_pv * cfg.EV_PV_RATIO,   4) if cfg.ENABLE_EV_CS else 0

        for it in range(cfg.NUM_ITERATIONS):
            count += 1
            print(
                f"[{count}/{total}] "
                f"PV={pen_pv}%  BESS={pen_bess}%  EV={pen_ev}%  "
                f"iter={it + 1}/{cfg.NUM_ITERATIONS}"
            )

            # Semilla por iteración para reproducibilidad
            if cfg.RANDOM_SEED is not None:
                seed_it = cfg.RANDOM_SEED + count
                random.seed(seed_it)
                np.random.seed(seed_it)
            else:
                seed_it = 0

            # --- Caso base (sin DERs) ---
            base = run_base_case(
                cfg.NETWORK_DSS_PATH,
                cfg.TRANSFORMER_MVA,
                cfg.ONLY_THREE_PHASE,
                excluded_buses=cfg.EXCLUDED_BUSES,
            )
            mt_buses   = base["mt_buses"]
            mt_kv      = base["mt_kv"]
            mt_phases  = base["mt_phases"]
            energy     = base["energy_kwh"]
            n_mt_total = base["n_mt_total"]

            # --- PV ---
            pv_units = []
            if cfg.ENABLE_PV:
                irrad_pu, temp_c, psh, mes = sample_monthly_profile(irr_matrix, temp_matrix)
                pv_units, _ = allocate_pv(
                    energy, pen_pv, psh,
                    mt_buses, mt_kv, mt_phases,
                    cfg.PV_SIZES_KW, cfg.PV_PROBS,
                    cfg.PV_POWER_FACTOR,
                )
                generate_cenario_pv(pv_units, irrad_pu, temp_c, path_pv, pen_pv, mes)
            else:
                open(path_pv, "w").close()

            # --- BESS ---
            if cfg.ENABLE_BESS:
                bess_units, _ = allocate_bess(
                    energy, pen_bess,
                    mt_buses, mt_kv, mt_phases,
                    cfg.BESS_SIZES_KWH, cfg.BESS_PROBS,
                    cfg.BESS_CHARGE_HOURS, cfg.BESS_PLACEMENT,
                    bess_profiles, bess_profile_names,
                    pv_units=pv_units,
                    power_factor=cfg.BESS_POWER_FACTOR,
                )
                generate_cenario_bess(bess_units, path_bess, pen_bess)
            else:
                open(path_bess, "w").close()

            # --- EV/CS ---
            if cfg.ENABLE_EV_CS:
                ev_units, _ = allocate_ev(
                    energy, pen_ev,
                    mt_buses, mt_kv, mt_phases,
                    cfg.EV_SIZES_KW, cfg.EV_PROBS,
                    cfg.EV_ELIGIBLE_BUSES,
                    ev_profiles, ev_profile_names,
                    cfg.EV_POWER_FACTOR,
                )
                generate_cenario_ev(ev_units, path_ev, pen_ev)
            else:
                open(path_ev, "w").close()

            # --- Simulación con DERs ---
            # Solo carga los módulos activos — el master.dss queda limpio
            sim = run_with_ders(
                cfg.NETWORK_DSS_PATH,
                cfg.TRANSFORMER_MVA,
                enable_pv=cfg.ENABLE_PV,    path_pv=path_pv,
                enable_bess=cfg.ENABLE_BESS, path_bess=path_bess,
                enable_ev=cfg.ENABLE_EV_CS,  path_ev=path_ev,
                n_mt_total=n_mt_total,
            )

            # --- Guardar fila en CSV ---
            append_row(cfg.RESULTS_FILE, pen_pv, pen_bess, pen_ev, sim, seed_it)

    print(f"\nSimulacion completa. Resultados en: {cfg.RESULTS_FILE}")
