# project/results/reporter.py
"""
Inicializa el archivo CSV de resultados y agrega filas por iteración.
Una fila = una iteración Monte Carlo completa.
"""

import os
import csv
import numpy as np

COLUMNS = [
    "Pen_PV", "Pen_BESS", "Pen_EV",
    "B_Vmin", "B_Vmax", "B_VminVmax",
    "Max_PLosses", "Min_PLosses", "Energy_Losses",
    "Min_Fluxo_Subestacao",
    "Trafo_Loading_pct",
    "Vmin_24h", "Vmax_24h",
    "Sev_Vmin_pct", "Sev_Vmax_pct", "Sev_VminVmax_pct",
    "Seed",
]


def init_csv(filepath):
    """
    Crea el archivo CSV con la cabecera.
    Si ya existe, lo sobreescribe.
    Crea la carpeta results/ si no existe.
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()


def append_row(filepath, pen_pv, pen_bess, pen_ev, sim_results, seed_it):
    """
    Agrega una fila al CSV de resultados.

    Parámetros
    ----------
    filepath     : str   — ruta del CSV
    pen_pv       : float — penetración PV usada en esta iteración
    pen_bess     : float — penetración BESS usada en esta iteración
    pen_ev       : float — penetración EV usada en esta iteración
    sim_results  : dict  — resultado de core.network.run_with_ders()
    seed_it      : int   — semilla usada en esta iteración

    Contadores de tensión (barras únicas afectadas en al menos 1h de las 24h):
        B_Vmin    : barras con subtensión  (<0.95 pu) en al menos 1 hora
        B_Vmax    : barras con sobretensión (>1.05 pu) en al menos 1 hora
        B_VminVmax: barras con sub O sobretensión en al menos 1 hora (unión de los dos sets)
    """
    buses_vmin = sim_results["buses_vmin"]   # set de nombres de barra
    buses_vmax = sim_results["buses_vmax"]   # set de nombres de barra

    b_vmin     = len(buses_vmin)
    b_vmax     = len(buses_vmax)
    b_vminvmax = len(buses_vmin | buses_vmax)   # unión — evita doble conteo

    row = {
        "Pen_PV":               pen_pv,
        "Pen_BESS":             pen_bess,
        "Pen_EV":               pen_ev,
        "B_Vmin":               b_vmin,
        "B_Vmax":               b_vmax,
        "B_VminVmax":           b_vminvmax,
        "Max_PLosses":          round(float(np.max(sim_results["perfil_losses"])), 4),
        "Min_PLosses":          round(float(np.min(sim_results["perfil_losses"])), 4),
        "Energy_Losses":        round(float(np.sum(sim_results["perfil_losses"])), 4),
        "Min_Fluxo_Subestacao": round(float(sim_results["fluxo_min"]),             4),
        "Trafo_Loading_pct":    round(float(np.max(sim_results["perfil_trafo"])),   4),
        "Vmin_24h":             round(float(sim_results["vmin_24h"]),              4),
        "Vmax_24h":             round(float(sim_results["vmax_24h"]),              4),
        "Sev_Vmin_pct":         round(float(sim_results["sev_vmin_pct"]),          4),
        "Sev_Vmax_pct":         round(float(sim_results["sev_vmax_pct"]),          4),
        "Sev_VminVmax_pct":     round(float(sim_results["sev_union_pct"]),         4),
        "Seed":                 seed_it,
    }

    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writerow(row)
