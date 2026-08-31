/* ==== Formato compartido por la vista de reportes ==== */

/** Minutos como "1 h 05 min" o "42,5 min". */
export const minTexto = (m: number): string =>
  m >= 60
    ? `${Math.floor(m / 60)} h ${String(Math.round(m % 60)).padStart(2, '0')} min`
    : `${m.toFixed(1)} min`

/** Color de la deriva térmica según cuánto se aleja del set point. */
export const colorDeriva = (d: number): string =>
  d > 6 ? 'var(--crit)' : d > 3 ? 'var(--serious)' : d > 1.2 ? 'var(--warn)' : 'var(--good)'

/** Igual que colorDeriva, pero el tramo bajo umbral es neutro (barras del sparkline). */
export const colorDerivaBarra = (d: number): string =>
  d > 6 ? 'var(--crit)' : d > 3 ? 'var(--serious)' : d > 1.2 ? 'var(--warn)' : '#3a3a37'
