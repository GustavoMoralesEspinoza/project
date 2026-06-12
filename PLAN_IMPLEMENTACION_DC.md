# Plan de Implementación — Módulo Data Center
> 4 prompts secuenciales para Claude Code (VS Code)
> Modelo recomendado: **Sonnet 4.6**
> Ejecutar en orden. Verificar cada fase antes de pasar a la siguiente.

---

## Prompt 0 — Carga de contexto

> **Cuándo:** al iniciar la sesión de Claude Code, ANTES de cualquier cambio.
> **Qué hace:** carga el contexto del proyecto sin modificar nada.

```
Lee los siguientes archivos para entender la estructura del proyecto. NO modifiques nada todavía — solo confirma que entiendes la arquitectura:

1. PROJECT_CONTEXT.md — descripción completa del framework
2. EXTENSION_GUIDE.md — guía para agregar módulos nuevos
3. DISENO_MODULO_DATACENTER.md — diseño del módulo DC que vamos a implementar
4. config.py — configuración actual
5. core/monte_carlo.py — loop principal
6. core/network.py — interfaz OpenDSS
7. results/reporter.py — escritura CSV
8. modules/bess/bess_allocation.py — plantilla de referencia (el DC sigue un patrón similar)
9. modules/ev_cs/ev_allocation.py — otra referencia

Confirma: (a) cuántas columnas tiene el CSV actual, (b) qué archivos .dss se generan hoy, (c) cómo se calcula pen_bess a partir de pen_pv, (d) la firma de run_with_ders().
```

**Verificación:** Claude debe responder correctamente: 17 columnas, 3 archivos cenario_*.dss, pen_bess = pen_pv × BESS_PV_RATIO, y la firma completa de run_with_ders.

---

## Prompt 1 — Archivos de datos + módulo DC (profiles + allocation)

> **Qué hace:** crea la carpeta del módulo, los CSVs de perfiles, y los dos archivos Python del módulo DC.
> **Archivos creados:** 7 archivos nuevos. 0 archivos modificados.

```
Implementa el módulo Data Center siguiendo el diseño en DISENO_MODULO_DATACENTER.md y la plantilla de EXTENSION_GUIDE.md. En esta fase SOLO crea archivos nuevos, NO modifiques ningún archivo existente.

### 1. Crear carpeta data/dc_profiles/ con 3 CSVs de 24 valores (uno por línea, sin cabecera):

**diurnal.csv** — arquetipo "Diurnal" (inference/business): valle de madrugada, rampa matinal, pico vespertino.
Valores normalizados (max=1.0):
0.35,0.30,0.28,0.30,0.35,0.42,0.55,0.70,0.82,0.88,0.92,0.95,0.93,0.90,0.88,0.85,0.90,0.95,1.00,0.95,0.85,0.70,0.55,0.42

**flat.csv** — arquetipo "Flat" (training/hyperscale): cuasi-plano alto 24h.
Valores normalizados (max=1.0):
0.88,0.86,0.85,0.85,0.86,0.88,0.90,0.92,0.95,0.97,0.98,1.00,1.00,0.99,0.98,0.97,0.96,0.95,0.94,0.93,0.92,0.91,0.90,0.89

**gen_flat.csv** — curva del generador BTM opcional (despachable, casi plano):
0.90,0.90,0.90,0.90,0.90,0.90,0.92,0.95,1.00,1.00,1.00,1.00,1.00,1.00,1.00,1.00,1.00,0.98,0.95,0.93,0.92,0.91,0.90,0.90

### 2. Crear modules/dc/__init__.py (vacío)

### 3. Crear modules/dc/dc_profiles.py

Funciones:
- load_dc_profiles(profiles_dir) → lee los CSVs de 24 valores. Retorna (profiles: list[list[float]], names: list[str]). Fallback si carpeta vacía: curva plana de 0.90 × 24. Excluir archivos que empiecen con "gen_" (esos son para el generador BTM, no para workload).
- sample_dc_workload(profiles, names) → sortea un perfil. Retorna (profile[24], name).
- load_dc_gen_profile(profiles_dir) → busca archivos gen_*.csv en la carpeta. Retorna (profile[24], name) del primero encontrado. Fallback: curva plana 0.95 × 24.

Sigue las convenciones del proyecto: listas de 24 floats (no numpy arrays en la interfaz), snake_case, prints de aviso/info.

### 4. Crear modules/dc/dc_allocation.py

Funciones:

**allocate_dc(energy_kwh, penetration_pct, mt_buses, mt_kv, mt_phases, num_dc, profiles, profile_names, pue_range, noise_band, excluded_buses=None):**
- Calcula E_objetivo = energy_kwh × penetration_pct / 100.
- Si E_objetivo <= 0 o num_dc <= 0: retorna [], 0.0
- Reparte E_objetivo entre num_dc DCs con fracciones aleatorias (si num_dc=1, fracción=1.0; si num_dc=2, sortear f∈[0.3,0.7], el otro recibe 1−f; si num_dc>2, sortear N uniformes y normalizar).
- Por cada DC:
  - Sortea barra MT aleatoria (excluyendo excluded_buses si aplica)
  - Sortea arquetipo con sample_dc_workload
  - Sortea PUE uniforme en pue_range
  - Aplica ruido: profile[h] *= (1 + uniform(-noise_band, +noise_band)) por hora
  - Normaliza el perfil para que la energía del DC sea exactamente su fracción asignada:
    P_dc[h] = E_dc_asignada × profile[h] / sum(profile)
  - Almacena P_dc[24] como el perfil final en kW (ya escalado, listo para el .dss)
  - Retro-calcula n_servidores = max(P_dc) / PUE / 0.6 (P_peak=600W) para referencia
- Retorna (units: list[dict], total_energy: float)
  Cada dict: {name, bus, phases, kv_ll, profile_kw[24], profile_name, pue, n_servers_equiv, energy_kwh, peak_kw}

**generate_cenario_dc(units, output_path, penetration_pct, enable_dc_gen=False, dc_self_supply_frac=0.0, dc_gen_profile=None):**
- Escribe cenario_DC.dss con elementos Load (model=1, fases, kv, kw=peak de la curva, daily=loadshape con perfil normalizado al pico).
- IMPORTANTE: el loadshape debe estar normalizado al PICO (max=1.0) y el kw del Load es el pico. Así OpenDSS escala correctamente. Formula: loadshape_mult[h] = profile_kw[h] / max(profile_kw), y kw = max(profile_kw).
- Si enable_dc_gen=True y dc_gen_profile no es None:
  - Por cada DC, agrega 2 líneas extras: un Loadshape para el generador y un Generator co-ubicado en la misma barra.
  - Potencia del generador: dc_self_supply_frac × energy_kwh_del_dc / sum(dc_gen_profile) → escalar igual que el DC.
  - El Generator usa: New Generator.GenDC_{name} bus1={bus} phases={phases} kv={kv} kw={gen_peak} pf=1.0 model=1 daily={gen_shape}
- Si units vacío: solo comentario.
- Convenciones: encoding="utf-8", newline="\n", valores con f"{v:.5f}".

Sigue el patrón de bess_allocation.py y ev_allocation.py como referencia de estilo.
```

**Verificación antes de continuar:**
```
.venv\Scripts\python.exe -c "from modules.dc.dc_profiles import load_dc_profiles, load_dc_gen_profile; p,n = load_dc_profiles('data/dc_profiles'); print(f'Perfiles: {len(p)}, nombres: {n}'); g,gn = load_dc_gen_profile('data/dc_profiles'); print(f'Gen: {gn}, len={len(g)}')"
```
Debe imprimir: `Perfiles: 2, nombres: ['diurnal', 'flat']` y `Gen: gen_flat, len=24`.

---

## Prompt 2 — Integración en config.py + monte_carlo.py + network.py

> **Qué hace:** conecta el módulo DC al framework existente.
> **Archivos modificados:** 3 (config.py, core/monte_carlo.py, core/network.py). 0 archivos creados.

```
Ahora integra el módulo DC en el framework. Modifica estos 3 archivos:

### 1. config.py — agregar parámetros DC

Agregar junto a los otros módulos DER, DESPUÉS de los parámetros EV:

# ─── Data Center ───────────────────────────────────────
ENABLE_DC = False                    # Activar módulo Data Center

DC_PV_RATIO = 0.20                  # pen_dc = pen_pv × DC_PV_RATIO

NUM_DC = 1                          # Número de DCs por iteración (1, 2, ...)

# Parámetros físicos del DC
DC_PUE_RANGE = (1.2, 1.8)          # PUE sorteado uniforme por DC
DC_NOISE_BAND = 0.05               # ±5% ruido horario
DC_POWER_FACTOR = 0.95             # Factor de potencia del DC

# Autogeneración behind-the-meter (opcional)
ENABLE_DC_GEN = False               # Activar generación on-site del DC
DC_SELF_SUPPLY_FRAC = 0.20         # Fracción de energía del DC autogenerada

# Directorios
DC_PROFILES_DIR = os.path.join(BASE_DIR, "data", "dc_profiles")

Actualizar el cálculo de RESULTS_FILE para incluir DC:
- Calcular _max_dc = round(_max_pv * DC_PV_RATIO) if ENABLE_DC else 0
- Agregar _DC{_max_dc} al nombre del archivo CSV, después de _EV{_max_ev}

### 2. core/monte_carlo.py — conectar el módulo DC

Seguir EXACTAMENTE el patrón de BESS/EV (ver EXTENSION_GUIDE.md Paso 6). Los cambios son:

a) Pre-carga (junto a BESS/EV):
   - Si ENABLE_DC: importar load_dc_profiles, load_dc_gen_profile, allocate_dc, generate_cenario_dc
   - Cargar perfiles: dc_profiles, dc_profile_names = load_dc_profiles(cfg.DC_PROFILES_DIR)
   - Si ENABLE_DC_GEN: dc_gen_profile, dc_gen_name = load_dc_gen_profile(cfg.DC_PROFILES_DIR)
   - Crear path_dc y archivo vacío si no existe

b) Loop externo — calcular pen_dc:
   pen_dc = round(pen_pv * cfg.DC_PV_RATIO, 4) if cfg.ENABLE_DC else 0

c) Loop interno — asignación y generación:
   - Si ENABLE_DC: llamar allocate_dc con los parámetros del config (energy, pen_dc, mt_buses, mt_kv, mt_phases, cfg.NUM_DC, dc_profiles, dc_profile_names, cfg.DC_PUE_RANGE, cfg.DC_NOISE_BAND, excluded_buses=cfg.EXCLUDED_BUSES)
   - Llamar generate_cenario_dc(dc_units, path_dc, pen_dc, enable_dc_gen=cfg.ENABLE_DC_GEN, dc_self_supply_frac=cfg.DC_SELF_SUPPLY_FRAC, dc_gen_profile=dc_gen_profile si existe)
   - Si no ENABLE_DC: vaciar el archivo

d) Llamada a run_with_ders: agregar enable_dc=cfg.ENABLE_DC, path_dc=path_dc

e) Llamada a append_row: agregar pen_dc como parámetro

f) Print de progreso: incluir pen_dc junto a pen_bess y pen_ev

### 3. core/network.py — agregar redirect DC en run_with_ders

- Agregar parámetros enable_dc=False, path_dc=None a la firma de run_with_ders
- Después de los redirects existentes (PV, BESS, EV), agregar:
  if enable_dc and path_dc:
      dss.text(f"redirect [{path_dc}]")
- NO cambiar nada más en network.py
```

**Verificación:** No se puede correr aún (falta reporter). Pero verifica que config.py importa sin errores:
```
.venv\Scripts\python.exe -c "import config as cfg; print(f'DC={cfg.ENABLE_DC}, ratio={cfg.DC_PV_RATIO}, NUM_DC={cfg.NUM_DC}')"
```

---

## Prompt 3 — Reporter + verify.py + smoke test

> **Qué hace:** cierra el circuito: CSV con columna DC, verify.py con parámetros DC, y test.
> **Archivos modificados:** 3 (results/reporter.py, verify.py, plots/test_smoke.py). 0 archivos creados.

```
Cierra la integración del módulo DC modificando el reporter, verify y smoke test.

### 1. results/reporter.py

a) Agregar "Pen_DC" a la lista COLUMNS, DESPUÉS de "Pen_EV" y ANTES de "B_Vmin":
   Nuevo orden: Pen_PV, Pen_BESS, Pen_EV, Pen_DC, B_Vmin, ...

b) Actualizar la firma de append_row para recibir pen_dc:
   def append_row(filepath, pen_pv, pen_bess, pen_ev, pen_dc, sim_results, seed_it):

c) Agregar "Pen_DC": pen_dc al dict row.

d) Actualizar init_csv si es necesario (debería auto-adaptarse si COLUMNS está correcto).

IMPORTANTE: verificar que el número total de columnas sea 18 (17 existentes + Pen_DC).

### 2. verify.py

a) Agregar al inicio (junto a PEN_PV, PEN_BESS, PEN_EV):
   PEN_DC = 0       # penetración DC [%]

b) Importar el módulo DC (igual que se importan PV/BESS/EV).

c) Agregar la lógica de DC dentro del bloque de simulación, DESPUÉS de EV y ANTES de run_with_ders:
   - Si PEN_DC > 0: cargar perfiles, llamar allocate_dc, generate_cenario_dc, pasar a run_with_ders.
   - Imprimir reporte DC: número de DCs, energía total, pico, PUE, servidores equivalentes, arquetipo.

d) Actualizar la llamada a run_with_ders con enable_dc y path_dc.

e) Actualizar la llamada a append_row (si verify.py la usa) con pen_dc.

f) Actualizar los nombres de figuras para incluir DC: _DC{pen_dc}_ en el patrón de nombres.

g) En los prints de reporte, agregar sección "Data Center":
   Data Center
      DCs instalados        : N
      Energía total DC      : xx,xxx.x kWh
      Pico máximo           : xx,xxx.x kW
      PUE promedio          : x.xx
      Servidores equiv.     : x,xxx
      Arquetipo(s)          : diurnal, flat

### 3. plots/test_smoke.py

Agregar un bloque de test para el módulo DC (siguiendo el patrón de los tests existentes):
- Verificar que load_dc_profiles retorna 2 perfiles
- Verificar que allocate_dc con datos sintéticos retorna units con los campos esperados
- Verificar que generate_cenario_dc escribe un archivo .dss no vacío
- Verificar que reporter genera CSV con 18 columnas (la nueva Pen_DC)
- Print "DC module: OK" al pasar

NO modifiques ningún otro archivo. Solo reporter.py, verify.py y test_smoke.py.
```

**Verificación final — 3 tests en secuencia:**

```bash
# Test 1: smoke test sin OpenDSS
.venv\Scripts\python.exe plots/test_smoke.py

# Test 2: verify con DC desactivado (debe funcionar igual que antes)
# Editar verify.py: PEN_DC = 0
.venv\Scripts\python.exe verify.py

# Test 3: verify con DC activado
# Editar verify.py: PEN_DC = 20
.venv\Scripts\python.exe verify.py
```

El Test 3 debe mostrar la sección "Data Center" en el reporte y las figuras deben tener _DC20_ en el nombre.

---

## Resumen de impacto

| Fase | Archivos creados | Archivos modificados | Riesgo |
|---|---|---|---|
| Prompt 1 | 7 (carpeta dc/, CSVs, módulo Python) | 0 | Nulo — no toca nada existente |
| Prompt 2 | 0 | 3 (config, monte_carlo, network) | Medio — es el wiring central |
| Prompt 3 | 0 | 3 (reporter, verify, smoke test) | Bajo — solo agrega columna y prints |

**Total: 7 archivos nuevos, 6 archivos modificados, 0 archivos eliminados.**

Si algo falla en el Prompt 2 (el más delicado), los archivos del Prompt 1 no se pierden y el código existente sigue funcionando porque ENABLE_DC=False por default.
