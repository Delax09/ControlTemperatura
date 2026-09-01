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
