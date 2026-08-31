/* ==== Historial de aperturas (dato real de la API) ==== */

import { UMBRAL_CRIT, UMBRAL_SER, UMBRAL_WARN, mmss } from '../lib/umbrales'

const color = (s: number) =>
  s >= UMBRAL_CRIT ? 'var(--crit)' : s >= UMBRAL_SER ? 'var(--serious)' : s >= UMBRAL_WARN ? 'var(--warn)' : '#3a3a37'

export default function HistorialAperturas({ historial }: { historial: number[] }) {
  if (!historial.length) {
    return (
      <>
        <div className="m-hist" />
        <div className="m-hist-foot">
          <span>Sin aperturas registradas</span>
        </div>
      </>
    )
  }

  const max = Math.max(...historial)
  const prom = historial.reduce((a, b) => a + b, 0) / historial.length

  return (
    <>
      <div className="m-hist">
        {historial.map((s, i) => (
          <div key={i} style={{ height: Math.max(6, (s / max) * 60), background: color(s) }} title={mmss(s)} />
        ))}
      </div>
      <div className="m-hist-foot">
        <span>
          {historial.length} aperturas · promedio {mmss(prom)}
        </span>
        <span>máx. {mmss(max)}</span>
      </div>
    </>
  )
}
