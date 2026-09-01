import { useReloj } from '../hooks/useReloj'
import { nivel } from '../lib/umbrales'
import type { Puerta } from '../types'

export default function Header({ puertas }: { puertas: Puerta[] }) {
  const ahora = useReloj()

  const abiertas = puertas.filter((e) => e.abierta).length
  const crit = puertas.filter((e) => nivel(e) === 'crit' || nivel(e) === 'serious').length
  const minTotales = puertas.reduce((a, e) => a + (e.minutos_hoy || 0), 0)

  return (
    <header>
      <div className="brand">
        <div className="logo">MV</div>
        <div>
          <h1>Muro de Control · Puertas Cámaras de Frío</h1>
        </div>
      </div>
      <div className="hstats">
        <div className="pill">
          <span className="dot" style={{ background: 'var(--good)' }} />
          Cerradas <b>{puertas.length - abiertas}</b>
        </div>
        <div className="pill">
          <span className="dot" style={{ background: 'var(--warn)' }} />
          Abiertas <b>{abiertas}</b>
        </div>
        <div className="pill">
          <span className="dot" style={{ background: 'var(--crit)' }} />
          En falta <b>{crit}</b>
        </div>
        <div className="pill">
          Min·puerta hoy <b>{minTotales.toFixed(0)}</b>
        </div>
      </div>
      <div className="clock">
        <span>{ahora.toLocaleTimeString('es-CL', { hour12: false })}</span>
        <small>{ahora.toLocaleDateString('es-CL', { weekday: 'long', day: 'numeric', month: 'long' })}</small>
      </div>
    </header>
  )
}
