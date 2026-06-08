# ============================================================
# CONFIGURACIÓN PRINCIPAL — solo editar este archivo
# ============================================================

import os

# --- Módulos activos ---
ENABLE_PV    = True
ENABLE_BESS  = True
ENABLE_EV_CS = False

# --- Red a usar ---
NETWORK_NAME    = "18Bus"       # nombre de subcarpeta en data/networks/
NETWORK_FILE    = "master.dss"  # archivo principal de la red
TRANSFORMER_MVA = 60.0          # MVA del transformador principal

# --- Rutas (no editar) ---
BASE_DIR         = os.path.dirname(os.path.abspath(__file__))
NETWORK_DIR      = os.path.join(BASE_DIR, "data", "networks", NETWORK_NAME)
NETWORK_DSS_PATH = os.path.join(NETWORK_DIR, NETWORK_FILE)
IRRADIANCE_FILE  = os.path.join(BASE_DIR, "data", "irradiance", "Geracao_Solar.csv")
BESS_PROFILES_DIR = os.path.join(BASE_DIR, "data", "bess_profiles")
EV_PROFILES_DIR   = os.path.join(BASE_DIR, "data", "ev_profiles")
RESULTS_DIR      = os.path.join(BASE_DIR, "results")

# --- Monte Carlo ---
NUM_ITERATIONS   = 10          # iteraciones por nivel de penetración
RANDOM_SEED      = 25           # semilla (None = aleatorio)
ONLY_THREE_PHASE = True         # True = solo barras trifásicas para DERs

# --- Niveles de penetración PV (% de energía diaria de la red) ---
# BESS y EV/CS se calculan automáticamente con los ratios de abajo.
PENETRATION_LEVELS_PV = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

# --- Relación BESS y EV/CS respecto a PV ---
# Ejemplos:
#   BESS_PV_RATIO = 1.0  →  ratio 1:1  (BESS = 100% de la penetración PV)
#   BESS_PV_RATIO = 0.5  →  ratio 1:2  (BESS =  50% de la penetración PV)
#   BESS_PV_RATIO = 0.25 →  ratio 1:4  (BESS =  25% de la penetración PV)
BESS_PV_RATIO = 0.5     # penetración BESS = pen_pv * BESS_PV_RATIO
EV_PV_RATIO   = 0.25    # penetración EV   = pen_pv * EV_PV_RATIO

_max_pv   = max(PENETRATION_LEVELS_PV) if ENABLE_PV   else 0
_max_bess = round(_max_pv * BESS_PV_RATIO) if ENABLE_BESS  else 0
_max_ev   = round(_max_pv * EV_PV_RATIO)   if ENABLE_EV_CS else 0
RESULTS_FILE = os.path.join(RESULTS_DIR, f"resultados_{NETWORK_NAME}_PV{_max_pv}_BESS{_max_bess}_EV{_max_ev}.csv")

# --- PV ---
PV_SIZES_KW     = [300, 600, 1200, 1800, 2400]   # tamaños discretos [kW]
PV_PROBS        = [0.25, 0.30, 0.25, 0.15, 0.05] # probabilidades (deben sumar 1)
PV_POWER_FACTOR = 1.0

# --- BESS ---
BESS_SIZES_KWH    = [1200, 2400, 4800, 7200, 9600]  # tamaños discretos [kWh]
BESS_PROBS        = [0.25, 0.30, 0.25, 0.15, 0.05]  # probabilidades (deben sumar 1)
BESS_CHARGE_HOURS = 4            # horas de carga del BESS
BESS_POWER_FACTOR = 1.0
BESS_PLACEMENT    = "colocated"  # "colocated" = misma barra que PV / "free" = cualquier barra MT

# --- EV / Estaciones de carga ---
# Las curvas de carga vienen de archivos CSV en data/ev_profiles/
# Marcos: coloca tus curvas ahí (una por archivo, 24 valores, separados por coma)
# En cada iteración cada estación sortea una curva aleatoriamente.
EV_SIZES_KW       = [600, 1200, 2400]          # potencia máxima de estación [kW]
EV_PROBS          = [0.35, 0.45, 0.20]         # probabilidades (deben sumar 1)
EV_POWER_FACTOR   = 0.98
EV_ELIGIBLE_BUSES = []  # barras candidatas para EV/CS, Ejemplo: ["bus5", "bus9", "bus14"]
