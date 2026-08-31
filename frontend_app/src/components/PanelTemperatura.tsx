/* ==== Panel numérico de temperatura ====
   La lectura actual es el último punto de la serie: el mismo donde termina el
   gráfico, para que el número y la curva nunca se contradigan. */

import { hhmm } from '../lib/umbrales'
import type { Muestra, Puerta } from '../types'

interface Props {
  puerta: Puerta
  serie: Muestra[]
}

export default function PanelTemperatura({ puerta, serie }: Props) {
  const vals = serie.map((p) => p.v)
  const min = Math.min(...vals)
  const max = Math.max(...vals)
  const fuera = serie.filter((p) => Math.abs(p.v - puerta.temp_objetivo) > 1.2).length

  const lectura = serie[serie.length - 1]
  const actual = lectura.v
  const deriva = actual - puerta.temp_objetivo
  const fueraDeRango = Math.abs(deriva) > 1.2

  // La barra representa la deriva sobre un rango de referencia de 6 °C.
  const pct = Math.min(100, (Math.abs(deriva) / 6) * 100)
  const color = Math.abs(deriva) > 3 ? 'var(--crit)' : fueraDeRango ? 'var(--serious)' : 'var(--good)'

  // Tendencia respecto de la lectura anterior.
  const previo = serie.length > 1 ? serie[serie.length - 2].v : actual
  const delta = actual - previo
  const flecha = Math.abs(delta) < 0.05 ? '→' : delta > 0 ? '↑' : '↓'
  const tendColor = Math.abs(delta) < 0.05 ? 'var(--muted)' : delta > 0 ? 'var(--serious)' : 'var(--good)'

  return (
    <div className="m-box">
      <div className="row">
        <span>
          Actual <small style={{ color: 'var(--muted)' }}>· lectura {hhmm(lectura.t)}</small>
        </span>
        <span>
          <b className={fueraDeRango ? 'drift' : ''}>{actual.toFixed(1)} °C</b>
          <b style={{ color: tendColor, fontWeight: 500, marginLeft: 6 }}>
            {flecha} {delta >= 0 ? '+' : ''}
            {delta.toFixed(1)}
          </b>
        </span>
      </div>
      <div className="m-gauge">
        <i style={{ width: `${pct}%`, background: color }} />
      </div>
      <div className="row">
        <span>Set point {puerta.temp_objetivo} °C</span>
        <span>
          Deriva{' '}
          <b className={fueraDeRango ? 'drift' : ''}>
            {deriva >= 0 ? '+' : ''}
            {deriva.toFixed(1)} °C
          </b>
        </span>
      </div>
      <div className="row">
        <span>
          Mín. {min.toFixed(1)} °C · máx. {max.toFixed(1)} °C
        </span>
        <span>
          {fuera} de {serie.length} min fuera de rango
        </span>
      </div>
      <div className="m-pending">
        <b>Serie simulada</b> (ver <code>tempSim.ts</code>): el backend solo entrega el valor actual, no el histórico. El
        número de arriba es el último punto del gráfico, así que ambos coinciden siempre. Siguen pendientes la causa de
        la apertura, la confianza de la detección y el acuse.
      </div>
    </div>
  )
}
