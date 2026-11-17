# Plan de implementación · App móvil Go/NoGo + base de datos de sesiones

**Estado:** plan validado el 16 nov 2026. Fases 1 a 3 cerradas; sigue la Fase 4 (validación en el teléfono real).
**Origen:** paso 1 de "Next Steps" del 2nd Progress Report y diapositiva 9 (Go/NoGo Protocol Design).
**Para qué sirve:** H2 y H3 no se pueden probar sin esta tarea (errores de comisión y theta fásica en NoGo, antes y después del scrolling).

---

## 1. Qué se va a construir

| Pieza | Qué es | Dónde vive |
|---|---|---|
| App Go/NoGo | Una página web de un solo archivo que el teléfono del laboratorio abre en su navegador. Sin instalación, sin frameworks, sin imágenes. | `Tests/simulation_B/web/gonogo.html` (nuevo) |
| Base de datos | Un archivo SQLite con participantes, sesiones, bloques y ensayos. Usa `sqlite3`, que ya viene con Python. | `Tests/simulation_B/gonogo_db.py` (nuevo) + `Tests/simulation_B/data/mirai.db` (fuera de git) |
| Integración | Rutas nuevas en el servidor Flask que ya existe, tarjeta Go/NoGo en el dashboard y vista de resultados. | `sesion_aura_web.py` y `web/sesion_aura.html` (se modifican) |
| Prueba | Un teléfono simulado que manda un bloque completo y comprueba el resumen. | `Tests/simulation_B/test_gonogo.py` (nuevo) |

No se agrega ninguna dependencia: Flask y `pylsl` ya están en `requirements.txt`.

**Sobre "localhost":** el teléfono no puede usar `localhost` (eso apunta al propio teléfono). Usa la IP de la PC en la red local, por ejemplo `http://192.168.x.x:8000/gng`. El servidor ya tiene el modo `--lan` para esto.

---

## 2. Cómo se logra la precisión de tiempo

La idea central: **el tiempo se mide en el teléfono, no en la red.** Así la velocidad del Wi-Fi no afecta ni el tiempo de reacción ni la alineación con el EEG.

1. **Inicio del estímulo:** se pinta dentro de `requestAnimationFrame` y se guarda la marca de ese cuadro. Error máximo: un cuadro (≈ 17 ms a 60 Hz).
2. **Toque:** evento `pointerdown` con `touch-action: none` (sin el retraso de 300 ms del clic). Se usa `event.timeStamp`, que está en el mismo reloj que el estímulo.
3. **Tiempo de reacción** = toque − inicio, calculado en el teléfono.
4. **Sincronización de relojes teléfono ↔ PC:** intercambio tipo NTP. El teléfono manda su hora, el servidor responde con `pylsl.local_clock()` (el mismo reloj que usa el pipeline) y se calcula el desfase. Se hacen ~10 intercambios al inicio y al final de cada bloque y se usa el de menor ida y vuelta. Con dos puntos se corrige la deriva del reloj durante el bloque.
5. **Envío al final (cambiado el 16 nov):** durante la tarea el teléfono no manda nada. Al terminar el bloque salen todos los ensayos juntos en un solo HTTP POST, con las marcas del teléfono; el servidor las convierte al reloj LSL y las guarda. Antes se mandaba un ensayo a la vez, en cada pausa.
6. **Reintentos:** ese envío espera en una cola hasta que el servidor confirma. Si el Wi-Fi está caído al terminar, se reintenta cada segundo. La base de datos ignora duplicados (clave bloque + número de ensayo). Contrapartida: si la página se cierra antes de terminar el bloque, ese bloque se pierde entero.

**Por qué HTTP y no WebSocket:** como las marcas de tiempo se toman en el teléfono, la latencia del transporte solo afecta qué tan rápido se ve el ensayo en el dashboard. HTTP no necesita instalar nada. Si la medición de la Fase 4 no cumple el criterio, se cambia a WebSocket (`flask-sock`, requiere tu aprobación para instalarlo).

**Límite que el software no puede medir:** la latencia propia de la pantalla y del panel táctil del teléfono (decenas de ms, constante por dispositivo). Suma un valor fijo al tiempo de reacción. No afecta la comparación antes/después si siempre se usa el mismo teléfono. Se puede medir aparte con video en cámara lenta (240 fps).

---

## 3. La tarea (valores definitivos)

| Parámetro | Valor | Origen |
|---|---|---|
| Ensayos por bloque | 144 (16 pasadas de los dígitos 1 a 9) | Ajustado al bloque de 3 min; Perzl usó 135 (15 pasadas) |
| Estímulos | Dígitos del 1 al 9, blancos, centrados, fondo negro, un solo tamaño | Perzl et al. (2024), Figura 1 |
| NoGo | El dígito 3: 1 de cada 9 (16 NoGo, 128 Go) | Perzl et al. (2024): la proporción está en el texto; el dígito 3 sale de la regla del SART original que citan y de su Figura 1 |
| Estímulo en pantalla | 250 ms | Perzl et al. (2024) |
| Entre dígitos | Pantalla negra 900 ms, sin máscara ni cruz | Perzl et al. (2024) |
| Tiempo entre inicios | Fijo, 1150 ms | Perzl et al. (2024) |
| Ventana de respuesta | Hasta el inicio del siguiente dígito | |
| Duración | 10 s de preparación + 165.6 s de tarea = 175.6 s | Bloque de 180 s del dashboard, con 4.4 s de margen |
| Secuencia | 16 pasadas barajadas de 1 a 9, con semilla guardada; nunca dos 3 seguidos; semillas distintas en pre y post | Cambio propio: en Perzl el orden era aleatorio puro y el número de NoGo variaba (7.88 ± 1.76 en 72 ensayos). Fijarlo en 16 hace comparables pre y post |
| Respuesta | Tocar en cualquier parte de la pantalla | Perzl: "touch screen", sin botón |
| Orientación | Vertical | Mismo agarre que al hacer scrolling; Perzl usó horizontal |
| Retroalimentación | Ninguna, ni en la práctica ni en la tarea | Decisión del 16 nov |
| Práctica | 18 ensayos (2 pasadas), antes de iniciar la sesión EEG | Sin retroalimentación: el investigador revisa en el dashboard que el participante entendió la regla |
| Idioma de la app | Inglés | Igual que el dashboard |

**Cómo se calculan los 144 ensayos:** pasadas completas que caben en el bloque menos la preparación: (180 − 10) / 1.15 = 147.8 ensayos → 16 pasadas de 9.

**Medidas por bloque:** errores de comisión (n y %) y tiempo de reacción medio en Go correctos, que son las dos que Perzl validó. Además: omisiones, mediana y desviación del TR, y anticipaciones (TR < 100 ms, el mismo corte que usan Perzl y Jacquet), marcadas aparte.

**Marcadores:** los eventos de esta tarea usan el prefijo `gng:` y no `nogo:error` / `nogo:slow`. Así el Nivel 2 del JITAI no se dispara durante los bloques Go/NoGo, como dice la diapositiva 9 ("JITAI interventions run only here", sobre el scrolling).

### 3.1 Qué dice la literatura de respaldo (revisado el 16 nov)

**Perzl, Riedl & Thomas (2024)** es la validación en teléfono. Lo que hicieron:

- 46 estudiantes, una vez al día durante 14 días, 559 mediciones válidas de la tarea.
- Android 7.0, pantalla de 5.0" (1080 × 1920), teléfono en horizontal según la Figura 1 (el texto no lo dice), software Presentation 18.0 dentro de movisensXS.
- En la versión de 90 s (72 ensayos, ≈ 8 NoGo): 5.13 ± 2.34 errores de comisión y TR correcto de 285 ± 67 ms.
- Fiabilidad del cambio: TR "sustancial" desde 30 s (Rc = 0.84); errores de comisión "aceptable" desde 8 NoGo (Rc = 0.42).
- Con la práctica el TR baja (−1.46 ms por sesión), pero los errores de comisión no cambian. Por eso los errores de comisión son la medida principal de H2.

Lo que **no** validaron: la precisión de tiempo del teléfono, la equivalencia con una tarea de laboratorio, ni el uso con EEG. "Validada para uso en campo" significa fiabilidad y validez de constructo, no exactitud en milisegundos.

Su código es gratuito, pero está hecho para Presentation (software comercial), no para web. Sirven los parámetros, no el código.

**Jacquet et al. (2023)** es el precedente del efecto de H2, pero en computadora:

- Triángulo blanco (Go) o círculo blanco (NoGo) sobre fondo negro, a la izquierda o derecha de una cruz de fijación blanca.
- 150 ensayos, 20 % NoGo (30), estímulo 100 ms, intervalo 2500 ms, ≈ 6.5 min, barra espaciadora, 30 ensayos de práctica.
- Errores en NoGo: 3.55 → 4.92 tras 45 min de teléfono; 3.45 → 3.65 tras documental. Interacción F(1, 78) = 5.23, p = .025.

---

## 4. Base de datos

Un archivo SQLite. Sin nombres ni datos personales: solo un código por participante. Sin campos de notas y sin condición (todas las sesiones son de scrolling).

| Tabla | Columnas |
|---|---|
| `participantes` | `id`, `codigo` (único, p. ej. P01), `creado` |
| `sesiones` | `id`, `participante_id`, `inicio`, `run_dir` (carpeta del pipeline en `runs/`), `telefono` (user agent) |
| `bloques` | `id`, `sesion_id`, `tipo` (practica / pre / post), `semilla`, `secuencia` (los dígitos en orden), `parametros` (JSON), `inicio_lsl`, `fin_lsl`, `desfase_inicio`, `tel_sync_inicio`, `desfase_fin`, `tel_sync_fin`, `ida_vuelta_ms`, `cuadro_ms` |
| `ensayos` | `bloque_id`, `n`, `estimulo` (el dígito), `inicio_tel`, `inicio_lsl`, `respondio`, `tr_ms`, `resultado` (acierto / omision / comision / rechazo / anticipacion), `recibido_lsl` |
| vista `resumen_bloque` | Una fila por bloque: comisiones, omisiones, anticipaciones, TR medio y `completo` (llegaron todos los ensayos y la sincronización final). Es la tabla "one table per participant" de la diapositiva 9. |

`run_dir` enlaza cada sesión con `ventanas.csv` y `eventos.csv` del pipeline. Los tiempos `*_lsl` están en el mismo reloj que esos archivos.

El servidor decide el `resultado` de cada ensayo a partir de la secuencia que él mismo generó; el teléfono solo manda si hubo toque y cuándo.

Exportación a CSV por participante o completa. Respaldo: copiar el archivo `.db`.

---

## 5. Cambios en el dashboard

1. **Antes de iniciar:** campo de código de participante. La sesión no arranca sin código.
2. **Tarjeta Go/NoGo:** estado del teléfono (conectado o no) y, al terminar cada bloque, ensayos, comisiones, omisiones y TR medio. Durante el bloque solo avisa que está corriendo, porque los datos llegan al final.
3. **Arranque automático:** cuando la línea de tiempo llega a `gonogo_pre` o `gonogo_post`, el servidor manda la orden al teléfono con los parámetros y la semilla. El participante no tiene que configurar nada.
4. **Botón de práctica:** lanza los 18 ensayos de práctica sin sesión activa.
5. **Botón de resultados:** un botón nuevo debajo de "Clear console", en la tarjeta Session. Abre las tablas y registros de resultados por participante dentro del mismo dashboard, en una ruta nueva, con los mismos colores y estilos del resto de la interfaz.
6. **Acceso del teléfono:** el token de `--lan` se guarda en un archivo local para que no cambie en cada arranque. El teléfono lo abre una vez y deja un acceso directo en la pantalla de inicio.
7. **Scrolling de 45 min:** el protocolo queda en baseline 2 min → Go/NoGo 3 min → scrolling 45 min → Go/NoGo 3 min (53 min en total). Aplicado el 16 nov.

---

## 6. Fases y criterio de cierre

| Fase | Contenido | Se cierra cuando | Estado |
|---|---|---|---|
| 0 | Validar este plan y sus decisiones | Todas las decisiones tienen respuesta | Cerrada el 16 nov |
| 1 | Base de datos y rutas del servidor (sincronización, recepción de ensayos, orden de inicio) | `test_gonogo.py` manda 144 ensayos simulados, los reenvía duplicados y el resumen coincide | Cerrada el 16 nov: la prueba pasa. Falta la mediana y la desviación del TR, que se calcularán en la exportación (Fase 3) |
| 2 | App móvil (motor de la tarea, cola de envío, pantalla de espera, práctica) | En modo de autoprueba, un respondedor automático con TR conocidos se recupera con error ≤ 1 cuadro | Cerrada el 16 nov en el navegador de la PC (ver 6.1). Falta el teléfono real, que es la Fase 4 |
| 3 | Integración con el dashboard (sección 5) | Una sesión sintética completa deja en la base un bloque pre y uno post enlazados a su `run_dir` | Cerrada el 16 nov con la sesión simulada de `test_gonogo.py` (ver 6.2). Falta una sesión con el pipeline real |
| 4 | Validación de tiempo en el teléfono real | Ida y vuelta mediana < 20 ms; cuadros perdidos < 1 %; el bloque llega completo aunque el Wi-Fi esté caído al terminar | En curso, a mano (ver 6.3) |
| 5 | Piloto contigo como participante con la AURA puesta | Bloques pre y post completos y tabla de resultados correcta | Pendiente |

### 6.1 Resultado de la Fase 2 (16 nov, navegador de la PC a 60 Hz)

La app es `web/gonogo.html` y se abre en `/gng`. La autoprueba se lanza con `/gng?demo=practica` (18 ensayos, 30 s) o `/gng?demo=pre` (144 ensayos, 3 min): abre un bloque del participante DEMO, responde sola con tiempos conocidos y compara lo medido con lo que guardó el servidor.

| Medida | Bloque completo (144 ensayos) |
|---|---|
| Ensayos presentados | 144 de 144, ninguno saltado |
| Error del tiempo de reacción | máximo 12.9 ms, media 4.2 ms (límite: 1 cuadro = 16.6 ms) |
| Intervalo entre dígitos | media 1150.00 ms, de 1147.6 a 1164.5 ms (un cuadro de variación) |
| Servidor | 8 de 8 comisiones, 12 de 12 omisiones, mismo TR medio, bloque completo |
| Toques reales (clic, no simulados) | 3 de 3 registrados en su ensayo |

Dos cosas que salieron de la prueba:

- **La página debe estar en primer plano.** Con la página oculta, el navegador solo da un cuadro por segundo y la app se salta los dígitos (13 de 18 en la primera corrida). Un ensayo saltado no se manda y el bloque queda incompleto en la base, así que se nota. En el teléfono: pantalla encendida, la app al frente y sin notificaciones.
- **Tolerancia de atraso:** un dígito que se atrasa menos de 100 ms se presenta igual y su inicio real queda guardado; con más atraso se salta.

El error medido aquí es el del programa. No incluye la latencia de la pantalla táctil ni del panel del teléfono, que se mide en la Fase 4.

### 6.2 Resultado de la Fase 3 (16 nov)

Qué quedó en el dashboard:

- **Código de participante** en la tarjeta Session. Sin código, Start session no arranca. Cada Start session abre una sesión nueva en la base y la enlaza con la carpeta del pipeline.
- **Tarjeta Go/NoGo** junto al registro: teléfono conectado o no, ensayo actual, comisiones, omisiones y TR medio, en vivo. El inicio y el final de cada bloque quedan también en el registro.
- **Arranque automático:** al llegar a `gonogo_pre` y `gonogo_post`, el servidor manda la orden al teléfono. Si no hay teléfono conectado, el bloque no arranca y queda un aviso en rojo en el registro.
- **Botón Practice block** en la tarjeta Go/NoGo (solo sin sesión en vivo).
- **Botón Results** debajo de Clear console: muestra en la ruta `/resultados`, sin recargar, una fila por bloque y, al elegir una, sus ensayos uno por uno. Filtra por participante y exporta a CSV el resumen o los ensayos, con mediana y desviación del TR. Las dos tablas se ordenan por columna: un clic en el encabezado ordena de menor a mayor y otro clic invierte; se ordena por el valor real y los vacíos quedan al final.
- **Token fijo** para `--lan`, guardado en `data/token.txt` (fuera de git). El servidor imprime la dirección de la app para el teléfono con cada IP de la PC.
- **Enlace corto del teléfono** (16 nov): `<IP>:8000/<clave>`, con una clave de 6 letras y dígitos guardada en `data/telefono.txt`. Pasó de 47 a 25 caracteres. La clave queda en el teléfono un año y solo abre la tarea Go/NoGo: no da acceso al tablero ni a sus acciones, que siguen pidiendo el token largo. `servidor_web.bat` arranca siempre en modo red.

Cómo se comprobó:

| Comprobación | Resultado |
|---|---|
| `test_gonogo.py`, sesión simulada: Start session con código, bloques pre y post lanzados por el plan, teléfono simulado | Los dos bloques quedan completos, en la misma sesión y enlazados a su `run_dir` |
| Práctica con el servidor real y la app en el navegador | La tarjeta pasó de 7/18 a 18/18 en vivo y el registro anotó inicio y final |
| Vista de resultados | Abre por botón, por dirección directa y con el botón Atrás del navegador; la tabla y los ensayos cargan |
| Sin scroll | 1366 × 768 y 1920 × 1080, en la vista de sesión y en la de resultados |

Lo que no se probó: una sesión con el pipeline y la diadema (o el emulador) reales. El enlace con `run_dir` y el reloj de la sesión dependen de las mismas líneas del pipeline que el dashboard ya leía, pero no se ha visto correr de punta a punta.

Para usarlo con el teléfono hay que arrancar el servidor con `--lan`; sin esa opción la tarjeta Go/NoGo lo avisa.

### 6.3 Fase 4: lo que hay hasta ahora (16 nov)

**Bloque de prueba manual.** `<IP>:8000/<clave>?demo=pre` abre en el teléfono un bloque completo de 144 ensayos sin necesidad de iniciar una sesión, para hacerlo a mano (participante TEST; `&code=OTRO` lo cambia; `demo=practica` son 18 ensayos). Al terminar muestra lo que contó el teléfono, si coincide con lo que guardó el servidor, la ida y vuelta de la sincronización y el intervalo entre cuadros. El respondedor automático de la Fase 2 solo corre si se agrega `&auto=1`.

**Primeros 4 bloques de práctica a mano** (Android 10, Chrome 157, pantalla de 60 Hz):

| Medida | Resultado |
|---|---|
| Ensayos recibidos | 18 de 18 en los cuatro |
| Intervalo entre dígitos | de 1134 a 1161 ms: un cuadro de variación, ningún dígito saltado |
| TR | mediana de 305 a 343 ms |
| Ida y vuelta de la sincronización | de 36 a 43 ms: **no cumple** el criterio de 20 ms |

**Por qué la ida y vuelta sale alta.** El servidor responde `Connection: close`, así que cada medición abre una conexión nueva. Eso infla la medida y la hace asimétrica: el sesgo estimado en la alineación con el EEG es de unos 10 ms fijos (una cuarta parte de la ida y vuelta). No afecta al TR ni a la clasificación. Se corrige activando conexiones persistentes en el servidor; pendiente de decidir.

**Un "Correct stop" dudoso.** En un bloque, un toque que el participante creyó dar sobre un 3 no quedó registrado. Lo más probable es un toque adelantado al dígito, que cae en la ventana del anterior y se descarta por ser el segundo. No se puede confirmar: la app no guarda los toques descartados.

---

## 7. Decisiones tomadas (16 nov 2026)

| # | Decisión | Respuesta |
|---|---|---|
| 1 | Tipo de app | Web en el navegador del teléfono |
| 2 | Estímulos | Propuesta C: dígitos, como Perzl (2024) |
| 3 | Proporción NoGo | 1 de cada 9, como Perzl |
| 4 | Ritmo | Fijo 1150 ms, como Perzl |
| 5 | Longitud del bloque | Ajustada a los 3 min: 144 ensayos |
| 6 | Orientación | Vertical |
| 7 | Retroalimentación | Nunca |
| 8 | Idioma de la app | Inglés |
| 9 | Datos del participante | Solo el código; sin condición (solo scrolling) |
| 10 | Duración del scrolling | 45 min |

---

## 8. Riesgos

1. **Red del laboratorio.** Muchas redes universitarias aíslan los dispositivos entre sí. Plan B: activar la zona Wi-Fi de la PC y conectar el teléfono a ella (IP fija `192.168.137.1`). Windows pedirá permiso de firewall para Python la primera vez; ese permiso lo das tú.
2. **Theta fásica de H2.** El pipeline no guarda el EEG crudo: solo `ventanas.csv` y `eventos.csv`. Para cortar épocas alrededor de cada NoGo hoy habría que alinear el CSV de Aura por parpadeos, y en una sesión esa alineación derivó ~1100 ppm. Hace falta guardar el crudo con marcas LSL desde el pipeline. No es parte de la app, pero sin eso la app solo cubre la parte conductual de H2.
3. **Pocos NoGo por bloque.** Con 16 NoGo, y solo unas 5 o 6 inhibiciones correctas si se repite la tasa de error de Perzl, la theta fásica por persona no es interpretable. Solo sirve a nivel de grupo (20 personas ≈ 320 NoGo por momento) y hay que decirlo así en el reporte.
4. **Sin condición control.** Al quitar el documental, un cambio entre pre y post no se puede atribuir solo al scrolling: también puede ser práctica o cansancio por el paso del tiempo. Perzl ayuda en parte (los errores de comisión no cambian con la práctica), pero es una limitación que hay que declarar.
5. **Sin retroalimentación en la práctica.** Si el participante entiende mal la regla, la app no se lo dice. El investigador debe revisar el resultado de la práctica en el dashboard antes de iniciar la sesión.
6. **Pantalla que se apaga.** La función que mantiene la pantalla encendida exige HTTPS. No hace falta: los toques la mantienen activa. Poner el tiempo de apagado del teléfono al máximo y activar No molestar.
7. **Latencia fija del teléfono.** Ver sección 2. Usar siempre el mismo teléfono.

---

## 9. Fuera de este plan

- Tarjetas NoGo dentro del feed de videos (Scroll-NoGo).
- Guardado del EEG crudo en el pipeline (riesgo 2).
- La aplicación de AR.
