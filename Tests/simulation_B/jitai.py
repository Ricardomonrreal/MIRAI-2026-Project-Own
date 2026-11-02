"""
jitai.py — Paso 6 del Protocolo de Simulación (MIRAI 2026) · VERSIÓN B

Escalera de intervención a partir de Z (Paso 5) y de marcadores de conducta:
  * Nivel 1 · cue de conciencia: Z_α ≥ 1.5 sostenido 5 s de ventanas válidas; sale con Z_α < 1.0; refractario 60 s.
  * Nivel 2 · fricción: 2 eventos de conducta (`nogo:error`, `nogo:slow`) en 60 s; sale tras 60 s sin eventos;
    refractario 120 s. No usa EEG; se puede desactivar (escenario H1 ✅ H2 ❌).
  * Nivel 3 · pausa: Z_θ ≥ 1.5 sostenido 30 s de ventanas válidas; sale con Z_θ < 1.0; refractario 300 s.
  * Histéresis por nivel: el contador de persistencia suma con Z ≥ 1.5, se mantiene entre 1.0 y 1.5 y se reinicia
    con Z < 1.0. Ventanas inválidas (Paso 3), R² < 0.75 (Paso 4) o bloqueo de calidad mantienen el contador;
    más de 5 s seguidos sin ventanas válidas lo reinician.
  * Prioridad 3 > 2 > 1: una sola intervención activa; un nivel superior desplaza al inferior, y el inferior no se
    activa mientras el superior esté activo o en su refractario.
  * Refractario: cuenta desde la activación (como máximo una activación por refractario).
  * Calidad con χ (movido desde el Paso 4): χ posterior < μ_χ − 3σ_χ de la calibración junto con EMG > su umbral
    (μ + 3σ de los primeros 90 s) bloquea las intervenciones EEG mientras dure. Sin EMG medible (fs < 100) no aplica.
Todos los valores están en CONFIG y se guardan en config.json: son valores iniciales a ajustar en el Paso 7.
"""
import copy

CONFIG = {
    "z_on": 1.5,
    "z_off": 1.0,
    "perdida_s": 5.0,
    "niveles": {
        1: {"nombre": "cue de conciencia", "feature": "alpha", "persistencia_s": 5.0, "refractario_s": 60.0},
        2: {"nombre": "fricción", "eventos": 2, "ventana_s": 60.0, "salida_s": 60.0, "refractario_s": 120.0,
            "activo": True, "marcadores": ["nogo:error", "nogo:slow"]},
        3: {"nombre": "pausa restaurativa", "feature": "theta", "persistencia_s": 30.0, "refractario_s": 300.0},
    },
    "calidad_chi_sigmas": 3.0,
}


class Jitai:
    """`window()` por cada ventana y `behavior()` por cada marcador de conducta; ambos devuelven la lista de
    eventos emitidos [(t, nivel, 'on'|'off', motivo)]."""

    def __init__(self, cfg=None, hop_s=1.0):
        self.cfg = copy.deepcopy(cfg or CONFIG)
        self.hop = hop_s
        self.active = None  # nivel activo (una sola intervención a la vez)
        self.since = {}  # t de la última activación por nivel (refractario)
        self.count = {1: 0.0, 3: 0.0}  # persistencia acumulada (s de ventanas válidas)
        self.invalid = {1: 0.0, 3: 0.0}  # s seguidos sin ventanas válidas
        self.behav = []  # t de los eventos de conducta recientes
        self.log = []

    def _blocked(self, lvl, t):
        """Un nivel no se activa en refractario propio, ni con uno superior activo o en su refractario."""
        nv = self.cfg["niveles"]
        if t - self.since.get(lvl, -1e9) < nv[lvl]["refractario_s"]:
            return True
        for hi in (2, 3):
            if hi > lvl and (self.active == hi or t - self.since.get(hi, -1e9) < nv[hi]["refractario_s"]):
                return True
        return lvl == 2 and not nv[2]["activo"]

    def _on(self, lvl, t, why, out):
        if self.active is not None:
            out.append((t, self.active, "off", f"desplazado por nivel {lvl}"))
        self.active = lvl
        self.since[lvl] = t
        out.append((t, lvl, "on", why))

    def _off(self, t, why, out):
        out.append((t, self.active, "off", why))
        self.active = None

    def window(self, t, z, ok, quality_block=False):
        """t: fin de la ventana; z: {'theta', 'alpha'} o None (calibrando); ok: {'theta', 'alpha'} → feature válida."""
        out = []
        c = self.cfg
        if z is not None:
            for lvl in (3, 1):  # el superior primero: si se activa, el inferior queda bloqueado
                f = c["niveles"][lvl]["feature"]
                if not ok.get(f) or quality_block:
                    self.invalid[lvl] += self.hop
                    if self.invalid[lvl] > c["perdida_s"]:
                        self.count[lvl] = 0.0
                    continue
                self.invalid[lvl] = 0.0
                if z[f] >= c["z_on"]:
                    self.count[lvl] += self.hop
                elif z[f] < c["z_off"]:
                    self.count[lvl] = 0.0
                    if self.active == lvl:
                        self._off(t, f"Z_{f} < {c['z_off']}", out)
                if (self.active != lvl and self.count[lvl] >= c["niveles"][lvl]["persistencia_s"]
                        and not self._blocked(lvl, t)):
                    self._on(lvl, t, f"Z_{f} ≥ {c['z_on']} durante {self.count[lvl]:.0f} s", out)
        # Nivel 2: salida tras salida_s sin eventos de conducta.
        n2 = c["niveles"][2]
        if self.active == 2 and self.behav and t - self.behav[-1] >= n2["salida_s"]:
            self._off(t, f"{n2['salida_s']:.0f} s sin eventos de conducta", out)
        self.log += out
        return out

    def behavior(self, t, label):
        out = []
        n2 = self.cfg["niveles"][2]
        if label in n2["marcadores"]:
            self.behav = [x for x in self.behav if t - x < n2["ventana_s"]] + [t]
            if (len(self.behav) >= n2["eventos"] and self.active != 2 and not self._blocked(2, t)):
                self._on(2, t, f"{len(self.behav)} eventos de conducta en {n2['ventana_s']:.0f} s", out)
        self.log += out
        return out


def chi_flat(chi, chi_mu, chi_sd, emg_db, emg_lim, n_sigmas):
    """Bloqueo de calidad: aplanamiento brusco de χ posterior junto con EMG alto (no aplica sin EMG)."""
    if chi is None or chi_sd is None or emg_db is None or emg_lim is None:
        return False
    return chi < chi_mu - n_sigmas * chi_sd and emg_db > emg_lim
