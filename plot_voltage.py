# project/plot_voltage.py

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_voltage_profile(perfil_vmin, perfil_vmax,
                         pen_pv, pen_bess, pen_ev, seed,
                         output_dir, network_name):
    os.makedirs(output_dir, exist_ok=True)

    horas = list(range(24))

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.fill_between(horas, perfil_vmin, perfil_vmax,
                    color="blue", alpha=0.10)
    ax.plot(horas, perfil_vmin, color="blue",  linewidth=1.5, label="V mín sistema")
    ax.plot(horas, perfil_vmax, color="red",   linewidth=1.5, label="V máx sistema")
    ax.axhline(0.95, color="gray", linestyle="--", linewidth=1.0,
               label="Límite inferior (0.95 pu)")
    ax.axhline(1.05, color="gray", linestyle=":",  linewidth=1.0,
               label="Límite superior (1.05 pu)")

    ax.set_xlim(0, 23)
    ax.set_ylim(0.90, 1.10)
    ax.set_xticks(horas)
    ax.set_xlabel("Hora")
    ax.set_ylabel("Tensión [pu]")
    ax.set_title(
        f"Perfil de Tensión 24h — {network_name}\n"
        f"PV={pen_pv}%  BESS={pen_bess}%  EV={pen_ev}%  (seed={seed})"
    )
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)

    filename = f"voltage_PV{pen_pv}_BESS{pen_bess}_EV{pen_ev}_seed{seed}.png"
    filepath = os.path.join(output_dir, filename)
    fig.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"Figura guardada: {filepath}")
