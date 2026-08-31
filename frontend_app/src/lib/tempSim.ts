/* ==== Simulación de sensor de temperatura ====
   TEMPORAL: el backend hoy solo entrega `temp_actual` (un valor puntual), no la
   serie histórica. Este módulo genera una serie por minuto plausible para poder
   diseñar y probar el gráfico del modal.

   Cuando exista el sensor real se borra este archivo completo y `serieDe()`
   pasa a leer los datos que entregue la API. Nada más cambia.

   El modelo no es ruido aleatorio: es enfriamiento/calentamiento newtoniano
   (T += (objetivo - T) * k) donde el objetivo es la temperatura ambiente si la
   puerta está abierta, o el set point si está cerrada. Las aperturas del
   histórico real (`historial_aperturas`) se usan para ubicar los picos, así que
   el gráfico refleja eventos que de verdad ocurrieron. */

import type { Muestra, Puerta } from '../types'

const TEMP_AMBIENTE = -13 // °C del andén con la puerta abierta
export const TEMP_MUESTRAS = 60 // ventana de 60 minutos
export const TEMP_INTERVALO = 60000 // una muestra por minuto
const K_ABIERTA = 0.1 // sube rápido al abrir
const K_CERRADA = 0.06 // el equipo de frío recupera más lento
const RUIDO_SENSOR = 0.15 // ±0,15 °C de ruido de lectura

/** id de puerta -> serie. Vive fuera de React: es un sensor falso, no estado de UI. */
const seriesTemp = new Map<string, Muestra[]>()

/** Un paso del modelo térmico. */
function pasoTermico(valor: number, abierta: boolean, setPoint: number): number {
  const objetivo = abierta ? TEMP_AMBIENTE : setPoint
  const k = abierta ? K_ABIERTA : K_CERRADA
  const ruido = (Math.random() * 2 - 1) * RUIDO_SENSOR
  const siguiente = valor + (objetivo - valor) * k + ruido
  // Se acota al rango físico del andén.
  return Math.max(setPoint - 1, Math.min(TEMP_AMBIENTE + 0.5, siguiente))
}

/** Marca en qué minutos de la ventana la puerta estuvo abierta. */
function ventanaAperturas(e: Puerta): boolean[] {
  const abierta = new Array<boolean>(TEMP_MUESTRAS).fill(false)
  const hist = e.historial_aperturas ?? []

  // Las aperturas del histórico se reparten en los primeros 50 minutos.
  hist.forEach((dur, i) => {
    const inicio = Math.floor(((i + 0.5) / Math.max(1, hist.length)) * 50)
    const minutos = Math.max(1, Math.round(dur / 60))
    for (let m = inicio; m < Math.min(inicio + minutos, TEMP_MUESTRAS); m++) abierta[m] = true
  })

  // Si está abierta ahora, se marcan los minutos finales.
  if (e.abierta) {
    const minutos = Math.max(1, Math.round(e.segundos_abierta / 60))
    for (let m = Math.max(0, TEMP_MUESTRAS - minutos); m < TEMP_MUESTRAS; m++) abierta[m] = true
  }
  return abierta
}

/**
 * Siembra la serie de una puerta: 59 minutos de historia simulada más el valor
 * actual que entrega la API, para que el gráfico cierre en el número que se
 * muestra en el panel.
 */
function sembrarSerie(e: Puerta): Muestra[] {
  const abierta = ventanaAperturas(e)
  const ahora = Date.now()
  const serie: Muestra[] = []
  let v = e.temp_objetivo

  for (let m = 0; m < TEMP_MUESTRAS - 1; m++) {
    v = pasoTermico(v, abierta[m], e.temp_objetivo)
    serie.push({ t: new Date(ahora - (TEMP_MUESTRAS - 1 - m) * TEMP_INTERVALO), v })
  }
  serie.push({ t: new Date(ahora), v: e.temp_actual })
  return serie
}

/** Serie de una puerta, creándola la primera vez que se pide. */
export function serieDe(e: Puerta): Muestra[] {
  let s = seriesTemp.get(e.id)
  if (!s) {
    s = sembrarSerie(e)
    seriesTemp.set(e.id, s)
  }
  return s
}

/**
 * Agrega una muestra nueva a cada serie ya sembrada y devuelve las puertas con
 * la lectura nueva escrita en `temp_actual`, para que la card del muro, el
 * panel del modal y el gráfico muestren siempre el mismo número.
 */
export function avanzarSeries(puertas: Puerta[]): Puerta[] {
  return puertas.map((e) => {
    const s = seriesTemp.get(e.id)
    if (!s) return e
    const ultimo = s[s.length - 1].v
    const nuevo = pasoTermico(ultimo, e.abierta, e.temp_objetivo)
    s.push({ t: new Date(), v: nuevo })
    if (s.length > TEMP_MUESTRAS) s.shift()
    return { ...e, temp_actual: nuevo }
  })
}
