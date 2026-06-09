# project/plot_voltage.py

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


def plot_voltage_heatmap(perfil_tension_barras, pen_pv, pen_bess, pen_ev,
                         seed, output_dir, network_name):
    buses = list(perfil_tension_barras.keys())
    matrix = np.array([perfil_tension_barras[b] for b in buses], dtype=float)

    # Ordenar filas por tensión promedio ascendente
    order = np.argsort(matrix.mean(axis=1))
    matrix = matrix[order]
    buses_sorted = [buses[i] for i in order]

    fig, ax = plt.subplots(figsize=(12, 7))
    im = ax.imshow(matrix, aspect="auto", cmap="RdYlGn",
                   vmin=0.90, vmax=1.10,
                   extent=[-0.5, 23.5, -0.5, len(buses_sorted) - 0.5])

    for h in (6, 12, 18):
        ax.axvline(h, color="white", linestyle="--", linewidth=0.8, alpha=0.5)

    cb = fig.colorbar(im, ax=ax)
    cb.set_label("Tensión (pu)")

    ax.set_xticks(range(24))
    ax.set_xticklabels(range(24))
    ax.set_yticks(range(len(buses_sorted)))
    ax.set_yticklabels(buses_sorted, fontsize=7)
    ax.set_xlabel("Hora")
    ax.set_title(
        f"Tensión por Barra 24h — {network_name}\n"
        f"PV={pen_pv}%  BESS={pen_bess}%  EV={pen_ev}%  (seed={seed})"
    )

    filename = f"heatmap_PV{pen_pv}_BESS{pen_bess}_EV{pen_ev}_seed{seed}.png"
    filepath = os.path.join(output_dir, filename)
    fig.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Figura guardada: {filepath}")


def plot_voltage_lines(perfil_tension_barras, pen_pv, pen_bess, pen_ev,
                       seed, output_dir, network_name):
    horas = list(range(24))

    fig, ax = plt.subplots(figsize=(12, 6))

    for bus, perfil in perfil_tension_barras.items():
        if any(v < 0.95 for v in perfil):
            color, alpha, lw = "red",    0.8, 1.5
        elif any(v > 1.05 for v in perfil):
            color, alpha, lw = "orange", 0.8, 1.5
        else:
            color, alpha, lw = "green",  0.3, 1.0
        ax.plot(horas, perfil, color=color, alpha=alpha, linewidth=lw)

    ax.axhline(0.95, color="black", linestyle="--", linewidth=1.0,
               label="Límite inf. 0.95 pu")
    ax.axhline(1.05, color="black", linestyle=":",  linewidth=1.0,
               label="Límite sup. 1.05 pu")

    legend_handles = [
        Line2D([0], [0], color="red",    linewidth=1.5, label="Subtensión (<0.95 pu)"),
        Line2D([0], [0], color="orange", linewidth=1.5, label="Sobretensión (>1.05 pu)"),
        Line2D([0], [0], color="green",  linewidth=1.0, label="Normal"),
        Line2D([0], [0], color="black",  linewidth=1.0, linestyle="--",
               label="Límite inf. 0.95 pu"),
        Line2D([0], [0], color="black",  linewidth=1.0, linestyle=":",
               label="Límite sup. 1.05 pu"),
    ]
    ax.legend(handles=legend_handles, loc="upper right", fontsize=8)

    ax.set_xlim(0, 23)
    ax.set_xticks(horas)
    ax.set_xticklabels(horas)
    ax.set_xlabel("Hora")
    ax.set_ylabel("Tensión (pu)")
    ax.set_title(
        f"Perfil de Tensión por Barra 24h — {network_name}\n"
        f"PV={pen_pv}%  BESS={pen_bess}%  EV={pen_ev}%  (seed={seed})"
    )
    ax.grid(True, alpha=0.3)

    filename = f"lines_PV{pen_pv}_BESS{pen_bess}_EV{pen_ev}_seed{seed}.png"
    filepath = os.path.join(output_dir, filename)
    fig.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Figura guardada: {filepath}")


def plot_voltage_profile(perfil_tension_barras, pen_pv, pen_bess, pen_ev,
                         seed, output_dir, network_name):
    os.makedirs(output_dir, exist_ok=True)
    #plot_voltage_heatmap(perfil_tension_barras, pen_pv, pen_bess, pen_ev, seed, output_dir, network_name)
    plot_voltage_lines(perfil_tension_barras, pen_pv, pen_bess, pen_ev,
                       seed, output_dir, network_name)
