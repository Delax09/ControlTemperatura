import { Link } from 'react-router-dom'
import type { Filtro } from '../types'

const OPCIONES: { f: Filtro; label: string }[] = [
  { f: 'all', label: 'Todas' },
  { f: 'open', label: 'Solo abiertas' },
  { f: 'alert', label: 'Solo en falta' },
]

interface Props {
  filtro: Filtro
  onFiltro: (f: Filtro) => void
}

export default function Toolbar({ filtro, onFiltro }: Props) {
  return (
    <div className="toolbar">
      <div className="seg">
        {OPCIONES.map((o) => (
          <button key={o.f} aria-pressed={filtro === o.f} onClick={() => onFiltro(o.f)}>
            {o.label}
          </button>
        ))}
      </div>
      <div className="seg">
        <button aria-pressed="true">Modo en vivo (API)</button>
      </div>
      <Link className="btn" to="/reportes" style={{ textDecoration: 'none' }}>
        📊 Reporte general
      </Link>
      <div className="spacer" />
      <div className="legend">
        <span>
          <i style={{ background: 'var(--good)' }} />
          Cerrada
        </span>
        <span>
          <i style={{ background: 'var(--warn)' }} />
          Abierta &lt; 3 min
        </span>
        <span>
          <i style={{ background: 'var(--serious)' }} />
          3–5 min
        </span>
        <span>
          <i style={{ background: 'var(--crit)' }} />
          &gt; 5 min (falta)
        </span>
      </div>
    </div>
  )
}
