/* ==== Umbrales operacionales y helpers de formato ====
   Única fuente de verdad de los cortes de tiempo y sus colores: el muro, el
   modal y la escalera de escalamiento leen todos desde aquí. */

import type { Nivel, Puerta } from '../types'

export const UMBRAL_WARN = 180 // 3 min
export const UMBRAL_SER = 300 // 5 min
export const UMBRAL_CRIT = 420 // 7 min

export const COLOR: Record<Nivel, string> = {
  ok: 'var(--good)',
  open: 'var(--warn)',
  warn: 'var(--warn)',
  serious: 'var(--serious)',
  crit: 'var(--crit)',
}

export const NIVEL_NOMBRE: Record<Nivel, string> = {
  crit: 'Cadena de frío',
  serious: 'Crítica',
  warn: 'Alta',
  open: 'Media',
  ok: 'Normal',
}

/** mm:ss a partir de segundos. */
export const mmss = (s: number): string =>
  String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(Math.floor(s % 60)).padStart(2, '0')

/** hh:mm local (24 h). */
export const hhmm = (d: Date): string => d.toLocaleTimeString('es-CL', { hour12: false }).slice(0, 5)

export function nivelDe(segundos: number, abierta: boolean): Nivel {
  if (!abierta) return 'ok'
  if (segundos >= UMBRAL_CRIT) return 'crit'
  if (segundos >= UMBRAL_SER) return 'serious'
  if (segundos >= UMBRAL_WARN) return 'warn'
  return 'open'
}

export const nivel = (e: Puerta): Nivel => nivelDe(e.segundos_abierta, e.abierta)

/** Orden del muro: primero lo más grave, y dentro del nivel lo más antiguo. */
export function ordenar(a: Puerta, b: Puerta): number {
  const r: Record<Nivel, number> = { crit: 0, serious: 1, warn: 2, open: 3, ok: 4 }
  return r[nivel(a)] - r[nivel(b)] || b.segundos_abierta - a.segundos_abierta
}

/** Escalones de escalamiento, en segundos de puerta abierta. */
export const REGLAS_ESCALAMIENTO = [
  {
    t: 60,
    titulo: 'Aviso en tablero',
    detalle: 'Se marca la puerta en el muro de control y en la app del operador de zona.',
  },
  {
    t: UMBRAL_WARN,
    titulo: 'Notificación al operador',
    detalle: 'Push al HT del operador responsable de la zona y tono en el andén.',
  },
  {
    t: UMBRAL_SER,
    titulo: 'Escalamiento a supervisor',
    detalle: 'Llamado por radio y WhatsApp al supervisor de turno.',
  },
  {
    t: UMBRAL_CRIT,
    titulo: 'Escalamiento a jefe de planta',
    detalle: 'Se abre incidente formal y queda registro para revisión HACCP.',
  },
  {
    t: 900,
    titulo: 'Alerta de cadena de frío',
    detalle: 'Se notifica a Aseguramiento de Calidad y se marca el lote expuesto.',
  },
] as const
