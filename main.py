# project/main.py
"""
Punto de entrada del framework Monte Carlo HC.
Jhon y Marcos solo editan config.py — nunca este archivo.

Uso:
    python main.py
"""

import config
from core.monte_carlo import run_monte_carlo

if __name__ == "__main__":
    print("=" * 55)
    print("  Framework Monte Carlo HC — PV + BESS + EV/CS")
    print("=" * 55)
    print(f"  Red:            {config.NETWORK_NAME}")
    print(f"  Transformador:  {config.TRANSFORMER_MVA} MVA")
    print(f"  Iteraciones:    {config.NUM_ITERATIONS}")
    print(f"  PV activo:      {config.ENABLE_PV}")
    print(f"  BESS activo:    {config.ENABLE_BESS}  "
          f"(placement: {config.BESS_PLACEMENT})")
    print(f"  EV/CS activo:   {config.ENABLE_EV_CS}")
    print(f"  Semilla:        {config.RANDOM_SEED}")
    print("=" * 55)

    run_monte_carlo(config)
