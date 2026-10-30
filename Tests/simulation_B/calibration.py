"""
calibration.py — Paso 5 del Protocolo de Simulación (MIRAI 2026) · VERSIÓN B

Calibración individual congelada: μ, σ e IAF se fijan una vez y no vuelven a cambiar (una media móvil sobre la
línea base borraría la fatiga tónica). Después, cada ventana válida actualiza una EWMA por feature y se emite
Z = (x̃ − μ) / σ_suav.

  * Chequeo de calidad (QC_S primeros segundos): criterio de load_file / h1_ds007537 sobre la std de cada canal.
  * Con marcadores de fase (protocolo AURA): μ y σ salen de `baseline_eyes_open`, la IAF y el Berger de
    `baseline_eyes_closed`. Sin marcadores: los CAL_S s siguientes al chequeo, que se asumen con ojos abiertos.
  * ≥ MIN_VALID ventanas válidas por feature; si no, se extiende EXTEND_S s (máx. MAX_EXTENSIONS) y luego se aborta.
  * EWMA: λ = 1 − e^(−S/τ), S = 1 s, τ = 60 s para θ (tónico) y 5 s para α (momentáneo); solo con ventanas válidas.
  * σ_suav = σ_crudo · √(λ / (2 − λ)) · factor (factor = 1 hasta que el Paso 7 lo mida en replays).
"""
import numpy as np

from spectral_features import band_per, bands

QC_S = 10.0
CAL_S = 90.0
EXTEND_S = 30.0
MAX_EXTENSIONS = 2
MIN_VALID = 45
TAU_S = {"theta": 60.0, "alpha": 5.0}
STEP_S = 1.0
BERGER_DB = 3.0
EYES_OPEN, EYES_CLOSED = "baseline_eyes_open", "baseline_eyes_closed"


def bad_channels(x, names):
    """Canales con std > 5× o < 0.05× la mediana de los canales (criterio de load_file / h1_ds007537)."""
    sd = x.std(axis=0)
    med = np.median(sd)
    return [c for c, s in zip(names, sd) if s > 5 * med or s < 0.05 * med]


def iaf_from(psd, f):
    """Como h1_ds007537.iaf(): pico de 7–13 Hz del espectro posterior; 10 Hz si cae en el borde (sin pico claro)."""
    m = (f >= 7) & (f <= 13)
    k = int(np.argmax(psd[m]))
    return float(f[m][k]) if 0 < k < m.sum() - 1 else 10.0


def ac_factor(x, lam, kmax=10):
    """√(1 + 2 Σ ρ_k (1 − λ)^k): cuánto subestima σ_suav la fórmula de entradas independientes, por la
    autocorrelación de las ventanas solapadas. Solo se reporta (el Paso 7 decide el factor)."""
    x = np.asarray(x, float) - np.mean(x)
    s = 0.0
    for k in range(1, min(kmax, len(x) - 2) + 1):
        r = float(np.dot(x[:-k], x[k:]) / np.dot(x, x))
        if r <= 0:
            break
        s += r * (1 - lam) ** k
    return float(np.sqrt(1 + 2 * s))


class Calibration:
    """Recibe cada ventana (válida o no) y devuelve None durante la calibración y {theta, alpha} = Z después.

    t_start: marca de tiempo de la primera ventana tras el chequeo de calidad; win_s: duración de la ventana."""

    def __init__(self, t_start, win_s, sigma_factor=1.0):
        self.t_start, self.win_s, self.sigma_factor = t_start, win_s, sigma_factor
        self.end, self.extensions = t_start + CAL_S, 0
        self.phases, self.rows, self.f = [], [], None
        self.state, self.msg, self.params, self.smooth = "calibrando", "", None, {}

    def marker(self, ts, label):
        if label.startswith("file:"):
            self.phases.append((ts, label[5:]))

    def phase(self, t0, t1):
        """Fase que contiene la ventana [t0, t1] completa; None si cruza un cambio de fase o no hay marcadores."""
        for i, (ts, p) in enumerate(self.phases):
            nxt = self.phases[i + 1][0] if i + 1 < len(self.phases) else np.inf
            if ts <= t0 and t1 <= nxt:
                return p
        return None

    def update(self, t1, o):
        """t1: fin de la ventana; o: salida de Features ({} si la ventana es inválida)."""
        if self.state == "calibrando":
            if o:
                self.f = o["f"]
            self.rows.append((t1, {k: o.get(k) for k in ("theta_ok", "alpha_ok", "theta_flat", "alpha_flat", "post_psd")}))
            self._maybe_freeze(t1)
            return None
        if self.state != "congelada":
            return None
        for n in ("theta", "alpha"):
            if o.get(f"{n}_ok"):
                x = band_per(o[f"{n}_flat"], o["f"], *self.params["bandas_hz"][n])
                self.smooth[n] += self.params[n]["lambda"] * (x - self.smooth[n])
        return {n: (self.smooth[n] - self.params[n]["mu"]) / self.params[n]["sigma_suav"] for n in ("theta", "alpha")}

    def _maybe_freeze(self, t1):
        if any(p == EYES_OPEN for _, p in self.phases):
            # Con fases: se congela cuando empieza una fase posterior a la línea base.
            if self.phases[-1][1] in (EYES_OPEN, EYES_CLOSED) or t1 < self.phases[-1][0]:
                return
            base = [r for t, r in self.rows if self.phase(t - self.win_s, t) == EYES_OPEN]
            closed = [r for t, r in self.rows if self.phase(t - self.win_s, t) == EYES_CLOSED]
            if not self._enough(base):
                return self._abort(f"menos de {MIN_VALID} ventanas válidas en {EYES_OPEN}")
            return self._freeze(base, closed, "fases AURA")
        if t1 < self.end:
            return
        base = [r for t, r in self.rows if t <= self.end]
        if self._enough(base):
            return self._freeze(base, [], f"primeros {self.end - self.t_start:.0f} s")
        if self.extensions < MAX_EXTENSIONS:
            self.extensions += 1
            self.end += EXTEND_S
            return
        self._abort(f"menos de {MIN_VALID} ventanas válidas tras {MAX_EXTENSIONS} extensiones de {EXTEND_S:.0f} s")

    @staticmethod
    def _enough(rows):
        return all(sum(bool(r[f"{n}_ok"]) for r in rows) >= MIN_VALID for n in ("theta", "alpha"))

    def _abort(self, why):
        self.state, self.msg = "abortada", why

    def _freeze(self, base, closed, source):
        f = self.f
        psd_iaf = [r["post_psd"] for r in (closed or base) if r["post_psd"] is not None]
        iaf = iaf_from(np.mean(psd_iaf, axis=0), f)
        b = bands(iaf)
        p = {"fuente": source, "iaf": iaf, "iaf_de": EYES_CLOSED if closed else "misma línea base",
             "bandas_hz": b, "sigma_factor": self.sigma_factor}
        for n in ("theta", "alpha"):
            x = [band_per(r[f"{n}_flat"], f, *b[n]) for r in base if r[f"{n}_ok"]]
            lam = 1 - np.exp(-STEP_S / TAU_S[n])
            sd = float(np.std(x))
            p[n] = {"mu": float(np.mean(x)), "sigma_crudo": sd, "ventanas_validas": len(x), "tau_s": TAU_S[n],
                    "lambda": float(lam), "sigma_suav": sd * np.sqrt(lam / (2 - lam)) * self.sigma_factor,
                    "factor_autocorrelacion": ac_factor(x, lam)}
            self.smooth[n] = p[n]["mu"]
        if closed:
            # Berger con potencia clásica de α (IAF ± 2 Hz) en la ROI posterior, ojos cerrados frente a abiertos.
            m = (f >= b["alpha"][0]) & (f < b["alpha"][1])
            po = np.mean([r["post_psd"] for r in base if r["post_psd"] is not None], axis=0)[m].sum()
            pc = np.mean(psd_iaf, axis=0)[m].sum()
            p["berger_db"] = float(10 * np.log10(pc / po))
            p["berger_ok"] = p["berger_db"] >= BERGER_DB
        self.params, self.state, self.rows = p, "congelada", []
