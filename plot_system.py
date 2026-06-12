# project/plot_system.py

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_substation_flow(perfil_pactiva, pen_pv, pen_bess, pen_ev,
                         seed, output_dir, network_name):
    horas = list(range(24))
    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(horas, perfil_pactiva, color="blue", linewidth=1.5,
            label="Flujo Subestación")
    ax.axhline(0, color="red", linestyle="--", linewidth=1.0,
               label="Flujo reverso = 0 kW")

    if any(v < 0 for v in perfil_pactiva):
        ax.fill_between(horas, perfil_pactiva, 0,
                        where=[v < 0 for v in perfil_pactiva],
                        color="red", alpha=0.15)
        # Texto en la zona de flujo reverso
        idx = next(i for i, v in enumerate(perfil_pactiva) if v < 0)
        ax.text(idx, min(perfil_pactiva) * 0.5, "Flujo Reverso",
                color="red", fontsize=9, ha="center")

    ax.set_xlim(0, 23)
    ax.set_xticks(horas)
    ax.set_xticklabels(horas)
    ax.set_xlabel("Hora")
    ax.set_ylabel("Potencia Activa (kW)")
    ax.set_title(
        f"Flujo en Subestación 24h — {network_name}\n"
        f"PV={pen_pv}%  BESS={pen_bess}%  EV={pen_ev}%  (seed={seed})"
    )
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    filename = f"flow_PV{pen_pv}_BESS{pen_bess}_EV{pen_ev}_seed{seed}.png"
    filepath = os.path.join(output_dir, filename)
    fig.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Figura guardada: {filepath}")


def plot_transformer_loading(perfil_trafo, transformer_mva, pen_pv, pen_bess,
                             pen_ev, seed, output_dir, network_name):
    horas = list(range(24))
    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(horas, perfil_trafo, color="orange", linewidth=1.5,
            marker="o", markersize=4, label="Cargamento Trafo")
    ax.axhline(100, color="red",  linestyle="--", linewidth=1.0,
               label="Límite 100%")
    ax.axhline(80,  color="gray", linestyle="--", linewidth=1.0,
               label="Límite recomendado 80%")

    if any(v > 100 for v in perfil_trafo):
        ax.fill_between(horas, perfil_trafo, 100,
                        where=[v > 100 for v in perfil_trafo],
                        color="red", alpha=0.10)

    ax.set_xlim(0, 23)
    ax.set_xticks(horas)
    ax.set_xticklabels(horas)
    ax.set_xlabel("Hora")
    ax.set_ylabel("Cargamento (%)")
    ax.set_title(
        f"Cargamento del Transformador 24h — {network_name}\n"
        f"Base {transformer_mva} MVA | PV={pen_pv}%  BESS={pen_bess}%  "
        f"EV={pen_ev}%  (seed={seed})"
    )
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    filename = f"trafo_PV{pen_pv}_BESS{pen_bess}_EV{pen_ev}_seed{seed}.png"
    filepath = os.path.join(output_dir, filename)
    fig.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Figura guardada: {filepath}")


def plot_losses(perfil_losses, pen_pv, pen_bess, pen_ev,
                seed, output_dir, network_name):
    horas = list(range(24))
    max_loss    = max(perfil_losses)
    total_loss  = sum(perfil_losses)

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.bar(horas, perfil_losses, color="blue", alpha=0.7,
           label="Pérdidas por hora")
    ax.axhline(max_loss, color="red", linestyle="--", linewidth=1.0,
               label=f"Máximo: {max_loss:.1f} kW")
    ax.text(0.02, 0.96, f"Energía pérdidas: {total_loss:.1f} kWh/día",
            transform=ax.transAxes, fontsize=9,
            verticalalignment="top", color="black")

    ax.set_xlim(-0.5, 23.5)
    ax.set_xticks(horas)
    ax.set_xticklabels(horas)
    ax.set_xlabel("Hora")
    ax.set_ylabel("Pérdidas Activas (kW)")
    ax.set_title(
        f"Perfil de Pérdidas Activas 24h — {network_name}\n"
        f"PV={pen_pv}%  BESS={pen_bess}%  EV={pen_ev}%  (seed={seed})"
    )
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    filename = f"losses_PV{pen_pv}_BESS{pen_bess}_EV{pen_ev}_seed{seed}.png"
    filepath = os.path.join(output_dir, filename)
    fig.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Figura guardada: {filepath}")


def plot_system_profile(sim_results, transformer_mva, pen_pv, pen_bess,
                        pen_ev, seed, output_dir, network_name):
    os.makedirs(output_dir, exist_ok=True)
    plot_substation_flow(sim_results["perfil_pactiva"],
                         pen_pv, pen_bess, pen_ev, seed, output_dir, network_name)
    plot_transformer_loading(sim_results["perfil_trafo"], transformer_mva,
                             pen_pv, pen_bess, pen_ev, seed, output_dir, network_name)
    plot_losses(sim_results["perfil_losses"],
                pen_pv, pen_bess, pen_ev, seed, output_dir, network_name)
