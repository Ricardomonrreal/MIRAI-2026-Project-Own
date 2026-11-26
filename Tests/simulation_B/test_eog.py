"""Chequeo de EogRegression (26 nov): parpadeo sintético con topografía conocida, tras el CAR.

Uso: python test_eog.py  → 'ok' si recupera la corrección (residual < 25 µV frente a ~50 µV de parpadeo) y si no
ajusta cuando un canal bueno pasa EOG_GUARD_UV en todos los bloques.
"""
import numpy as np
import realtime_pipeline as rp

fs = hop = 250
rng = np.random.default_rng(1)
n = int(70 * fs)
eeg = rng.normal(0, 5, (n, 8))
blink = np.zeros(n); blink[::300] = 1
blink = np.convolve(blink, np.hanning(40), "same") * -200
x = eeg + np.outer(blink, [1, .3, .3, .3, .2, .1, .05, .05])
car = lambda v: v - v[:, 1:].mean(1, keepdims=True)  # noqa: E731  (CAR sin Fp1, como el pipeline)
x = car(x)
e = rp.EogRegression(fs, hop, list(range(8)))
for k in range(6 * fs, n + 1, hop):
    y, _ = e(x[k - 6 * fs:k])
assert e.b is not None and e.b[0] == 0 and abs(e.b[1:].sum()) < 1e-9
res = y - car(eeg[k - 6 * fs:k])
assert np.ptp(res[:, 1:], 0).max() < 25, np.ptp(res, 0)

e2 = rp.EogRegression(fs, hop, list(range(8)))
x[:, 3] += np.where(np.arange(n) % fs < fs // 2, 5000, 0)  # F3 salta 5 mV en cada bloque de 1 s
assert not any(e2(x[k - 6 * fs:k])[1] for k in range(6 * fs, n + 1, hop)) and e2.b is None
print("ok")
