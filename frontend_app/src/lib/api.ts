/* ==== Cliente de la API de Django ====
   La base sale de VITE_API_URL. Vacía = mismo origen, que en desarrollo
   resuelve el proxy de vite.config.ts hacia localhost:8000. */

import type { Puerta } from '../types'

const BASE = import.meta.env.VITE_API_URL ?? ''

const url = (path: string) => `${BASE}${path}`

/**
 * Estado de todas las puertas.
 *
 * El backend todavía no expone este endpoint con la forma que espera el muro
 * (ver `PUERTAS_DEMO`). Mientras tanto la llamada falla y el hook cae a los
 * datos de demostración.
 */
export async function getPuertas(): Promise<Puerta[]> {
  const res = await fetch(url('/api/eventos-camaras/'))
  if (!res.ok) throw new Error(`La API respondió ${res.status}`)
  return (await res.json()) as Puerta[]
}

export interface RespuestaScript {
  status: string
  message: string
}

/** Arranca el worker de visión (YOLO) en el servidor. */
export async function ejecutarModelo(): Promise<RespuestaScript> {
  const res = await fetch(url('/api/ejecutar-modelo/'))
  return (await res.json()) as RespuestaScript
}

/**
 * Abre la herramienta interactiva para dibujar las zonas (ROI) de las puertas.
 *
 * Ojo: la ventana de OpenCV se abre en la máquina donde corre Django, no en el
 * navegador. Solo tiene sentido cuando el muro se opera desde el mismo equipo.
 */
export async function definirRoi(): Promise<RespuestaScript> {
  const res = await fetch(url('/api/definir-roi/'))
  return (await res.json()) as RespuestaScript
}

/**
 * Dato de prueba mientras no exista `/api/eventos-camaras/`.
 * Incluye una apertura larga a propósito: hace que la curva simulada de
 * temperatura recorra el rango completo y el gráfico del modal muestre una
 * excursión real en vez de una línea plana.
 */
export const PUERTAS_DEMO: Puerta[] = [
  {
    id: 'PSP-01',
    nombre: 'ANDÉN PSP 1',
    zona: 'Andén despacho',
    cam: 'anden1',
    tipo: 'anden',
    temp_objetivo: -20.0,
    temp_actual: -19.5,
    abierta: true,
    segundos_abierta: 190,
    aperturas_hoy: 10,
    minutos_hoy: 15.2,
    offline: false,
    historial_aperturas: [60, 900, 240, 1500],
    ack: 0,
  },
]

/* ---- Analisis del video en vivo (boton "Analizar video" de cada puerta) ---- */

/** Estado de una zona (ROI) tal como lo reporta el worker de visión. */
export interface ZonaAnalisis {
  nombre: string
  estado: 'abierta' | 'cerrada'
  segundos_abierta: number
  confianza: number
  en_alerta: boolean
}

/** Lo último que escribió el worker en su archivo de estado. */
export interface AnalisisWorker {
  puerta: string
  pid: number
  origen: string
  en_vivo: boolean
  iniciado: string
  estado: 'iniciando' | 'corriendo' | 'detenido' | 'error'
  mensaje: string
  ultimo_latido: string
  fps_analisis: number
  /** Si el visor del video anotado está abierto ahora en el servidor. */
  ventana: boolean
  eventos_registrados: number
  eventos_sin_enviar: number
  reconexiones: number
  zonas: ZonaAnalisis[]
}

/**
 * Respuesta de los tres endpoints de análisis. Comparten forma a propósito:
 * el botón lee siempre lo mismo, sin importar qué acción disparó.
 *
 * `corriendo` lo decide el backend por la antigüedad del latido del worker, no
 * por si el proceso existe: un worker colgado no cuenta como corriendo.
 */
export interface RespuestaAnalisis {
  status: 'ok' | 'iniciado' | 'ya_corriendo' | 'ocupado' | 'no_corriendo' | 'detencion_pedida' | 'error'
  message: string
  puerta: string
  corriendo: boolean
  analisis: AnalisisWorker | null
}

async function pedirAnalisis(
  path: string,
  method: 'GET' | 'POST',
  cuerpo?: unknown,
): Promise<RespuestaAnalisis> {
  const res = await fetch(url(path), {
    method,
    ...(cuerpo === undefined
      ? {}
      : { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cuerpo) }),
  })
  const data = (await res.json()) as RespuestaAnalisis
  if (!res.ok && !data?.message) throw new Error(`La API respondió ${res.status}`)
  return data
}

/**
 * Arranca el análisis del video en tiempo real de la cámara de esta puerta.
 *
 * Con `ventana` se abre además el visor del video anotado (ROI, cajas y
 * confianza) para comprobar a ojo que el modelo está encuadrando la puerta.
 * Ojo: esa ventana se abre en la máquina donde corre Django, no en el
 * navegador, igual que la herramienta de ROI.
 */
export function iniciarAnalisisVideo(puertaId: string, ventana = false): Promise<RespuestaAnalisis> {
  return pedirAnalisis(`/api/vision/analizar/${encodeURIComponent(puertaId)}/`, 'POST', { ventana })
}

/** Consulta si el análisis sigue vivo y qué lleva registrado. */
export function estadoAnalisisVideo(puertaId: string): Promise<RespuestaAnalisis> {
  return pedirAnalisis(`/api/vision/analizar/${encodeURIComponent(puertaId)}/estado/`, 'GET')
}

/**
 * Pide al worker que termine. No lo mata: el worker cierra la apertura que
 * tenga en curso y recién entonces sale, así no queda un evento sin cierre.
 */
export function detenerAnalisisVideo(puertaId: string): Promise<RespuestaAnalisis> {
  return pedirAnalisis(`/api/vision/detener/${encodeURIComponent(puertaId)}/`, 'POST')
}
