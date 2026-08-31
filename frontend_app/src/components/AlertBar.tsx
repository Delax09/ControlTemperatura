import { mmss, nivel } from '../lib/umbrales'
import type { Puerta } from '../types'

interface Props {
  puertas: Puerta[]
  onSilenciar: () => void
  onRadio: () => void
}

export default function AlertBar({ puertas, onSilenciar, onRadio }: Props) {
  // Solo las puertas en falta cuyo silencio ya venció.
  const peores = puertas
    .filter((e) => nivel(e) === 'crit' && Date.now() > (e.ack ?? 0))
    .sort((a, b) => b.segundos_abierta - a.segundos_abierta)

  const p = peores[0]

  return (
    <div className={`alertbar${p ? ' on' : ''}`}>
      <span className="dot" style={{ background: 'var(--crit)', width: 12, height: 12 }} />
      <div className="txt">
        {p ? (
          <>
            {p.nombre} lleva <b>{mmss(p.segundos_abierta)}</b> con la puerta abierta{' '}
            <span>· umbral 07:00 · {p.zona}</span>
            {peores.length > 1 && <span> + {peores.length - 1} puerta(s) más en falta</span>}
          </>
        ) : (
          '—'
        )}
      </div>
      <div className="spacer" style={{ flex: 1 }} />
      <button className="btn" onClick={onSilenciar}>
        Silenciar 5 min
      </button>
      <button className="btn pri" onClick={onRadio}>
        Llamar por radio
      </button>
    </div>
  )
}
