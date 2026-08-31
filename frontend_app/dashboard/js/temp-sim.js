/* ==== Simulación de sensor de temperatura ====
   TEMPORAL: el backend hoy solo entrega `temp_actual` (un valor puntual), no la
   serie histórica. Este módulo genera una serie por minuto plausible para poder
   diseñar y probar el gráfico del modal.

   Cuando exista el sensor real, se borra este archivo completo y `serieDe()`
   pasa a leer los datos que entregue la API. Nada más cambia.

   El modelo no es ruido aleatorio: es enfriamiento/calentamiento newtoniano
   (T += (objetivo - T) * k) donde el objetivo es la temperatura ambiente si la
   puerta está abierta, o el set point si está cerrada. Las aperturas del
   histórico real (`historial_aperturas`) se usan para ubicar los picos, así que
   el gráfico refleja eventos que de verdad ocurrieron. */

const TEMP_AMBIENTE   = -13;      // °C del andén con la puerta abierta
const TEMP_MUESTRAS   = 60;      // ventana de 60 minutos
const TEMP_INTERVALO  = 60000;   // una muestra por minuto
const K_ABIERTA       = 0.10;    // sube rápido al abrir
const K_CERRADA       = 0.06;    // el equipo de frío recupera más lento
const RUIDO_SENSOR    = 0.15;    // ±0,15 °C de ruido de lectura

const seriesTemp = {};  // id de puerta -> [{ t: Date, v: number }]

/* Un paso del modelo térmico. */
function pasoTermico(valor, abierta, setPoint){
  const objetivo = abierta ? TEMP_AMBIENTE : setPoint;
  const k = abierta ? K_ABIERTA : K_CERRADA;
  const ruido = (Math.random() * 2 - 1) * RUIDO_SENSOR;
  const siguiente = valor + (objetivo - valor) * k + ruido;
  // Se acota al rango físico del andén.
  return Math.max(setPoint - 1, Math.min(TEMP_AMBIENTE + 0.5, siguiente));
}

/* Marca en qué minutos de la ventana la puerta estuvo abierta, usando las
   aperturas reales del histórico y el estado actual. */
function ventanaAperturas(e){
  const abierta = new Array(TEMP_MUESTRAS).fill(false);
  const hist = e.historial_aperturas || [];

  // Las aperturas del histórico se reparten en los primeros 50 minutos.
  hist.forEach((dur, i) => {
    const inicio = Math.floor((i + 0.5) / Math.max(1, hist.length) * 50);
    const minutos = Math.max(1, Math.round(dur / 60));
    for(let m = inicio; m < Math.min(inicio + minutos, TEMP_MUESTRAS); m++) abierta[m] = true;
  });

  // Si está abierta ahora, se marcan los minutos finales.
  if(e.abierta){
    const minutos = Math.max(1, Math.round(e.segundos_abierta / 60));
    for(let m = Math.max(0, TEMP_MUESTRAS - minutos); m < TEMP_MUESTRAS; m++) abierta[m] = true;
  }
  return abierta;
}

/* Siembra la serie de una puerta: 59 minutos de historia simulada más el valor
  actual que entrega la API, para que el gráfico cierre en el número que se
   muestra en el panel. */
function sembrarSerie(e){
  const abierta = ventanaAperturas(e);
  const ahora = Date.now();
  const serie = [];
  let v = e.temp_objetivo;

  for(let m = 0; m < TEMP_MUESTRAS - 1; m++){
    v = pasoTermico(v, abierta[m], e.temp_objetivo);
    serie.push({ t: new Date(ahora - (TEMP_MUESTRAS - 1 - m) * TEMP_INTERVALO), v });
  }
  serie.push({ t: new Date(ahora), v: e.temp_actual });
  return serie;
}

/* Serie de una puerta, creándola la primera vez que se pide. */
function serieDe(e){
  if(!seriesTemp[e.id]) seriesTemp[e.id] = sembrarSerie(e);
  return seriesTemp[e.id];
}

/* Agrega una muestra nueva a cada serie ya sembrada. Corre cada minuto y usa el
  estado real de la puerta, así que el gráfico reacciona a las aperturas de
   verdad. */
function avanzarSeries(){
  if(typeof estado === 'undefined') return;
  estado.forEach(e => {
    const s = seriesTemp[e.id];
    if(!s) return;
    const ultimo = s[s.length - 1].v;
    const nuevo = pasoTermico(ultimo, e.abierta, e.temp_objetivo);
    s.push({ t: new Date(), v: nuevo });
    if(s.length > TEMP_MUESTRAS) s.shift();
    // El simulador hace de sensor: escribe la lectura en la puerta para que la
    // card del muro, el panel del modal y el gráfico muestren el mismo número.
    e.temp_actual = nuevo;
  });
  if(typeof render === 'function') render();
}

setInterval(avanzarSeries, TEMP_INTERVALO);
