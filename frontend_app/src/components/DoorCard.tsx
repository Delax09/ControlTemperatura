import CamThumb from './CamThumb'
import BotonAnalizarVideo from './BotonAnalizarVideo'
import BotonModelo from './BotonModelo'
import { COLOR, UMBRAL_CRIT, UMBRAL_SER, UMBRAL_WARN, mmss, nivel } from '../lib/umbrales'
import type { Puerta } from '../types'

/** La puerta que tiene el worker de visión conectado. */
const PUERTA_CON_MODELO = 'PSP-01'

function Badge({ e }: { e: Puerta }) {
  const n = nivel(e)
  if (!e.abierta) return <span className="badge b-closed">● CERRADA</span>
  if (n === 'crit') return <span className="badge b-crit">▲ FALTA · PUERTA ABIERTA</span>
  if (n === 'serious') return <span className="badge b-serious">▲ ABIERTA PROLONGADA</span>
  return <span className="badge b-open">◐ ABIERTA</span>
}

const colorApertura = (s: number) =>
  s >= UMBRAL_CRIT ? 'var(--crit)' : s >= UMBRAL_SER ? 'var(--serious)' : s >= UMBRAL_WARN ? 'var(--warn)' : '#3a3a37'

interface Props {
  e: Puerta
  onAbrir: (id: string) => void
  onToast?: (mensaje: string) => void
}

export default function DoorCard({ e, onAbrir, onToast }: Props) {
  const n = nivel(e)
  const pct = Math.min(100, e.abierta ? (e.segundos_abierta / UMBRAL_CRIT) * 100 : 0)
  const drift = Math.abs(e.temp_actual - e.temp_objetivo) > 1.2
  const hist = e.historial_aperturas ?? []
  const maxh = hist.length ? Math.max(...hist) : 1

  return (
    <article
      className={`card${e.offline ? ' offline' : ''}`}
      data-state={n}
      data-id={e.id}
      data-open={e.abierta ? 1 : 0}
      tabIndex={0}
      role="button"
      aria-label={`Ver detalle de ${e.nombre}`}
      onClick={() => onAbrir(e.id)}
      onKeyDown={(ev) => {
        if (ev.key !== 'Enter' && ev.key !== ' ') return
        ev.preventDefault()
        onAbrir(e.id)
      }}
    >
      <div className="cam">
        <CamThumb cam={e.cam} tipo={e.tipo} />
        <div className="noise" />
        <div className="scrim" />
        <div className="osd">{e.nombre}</div>
        <div className="rec">
          <i />
          REC · {e.id}
        </div>
        <div className="doorstate">
          <Badge e={e} />
        </div>
        <div className="timer" style={{ color: e.abierta ? COLOR[n] : 'var(--ink-2)' }}>
          {e.abierta ? mmss(e.segundos_abierta) : '—'}
        </div>
      </div>

      <div className="body">
        <div className="rowtop">
          <div>
            <div className="name">{e.nombre}</div>
            <div className="zone">{e.zona}</div>
          </div>
          <div className={`temp${drift ? ' drift' : ''}`}>
            <b>{e.temp_actual.toFixed(1)}°</b>
            <small>set {e.temp_objetivo}°</small>
          </div>
        </div>

        <div className="slabar">
          <div className="slalabels">
            <span>Tiempo vs. umbral operacional</span>
            <span className="cnt">{e.abierta ? `${mmss(e.segundos_abierta)} / 07:00` : '—'}</span>
          </div>
          <div className="track">
            <div className="fill" style={{ width: `${pct}%`, background: COLOR[n] }} />
            <span className="tick" style={{ left: `${(UMBRAL_WARN / UMBRAL_CRIT) * 100}%` }} />
            <span className="tick" style={{ left: `${(UMBRAL_SER / UMBRAL_CRIT) * 100}%` }} />
          </div>
        </div>

        <div className="foot" style={{ flexDirection: 'column', alignItems: 'stretch', gap: 14 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', width: '100%' }}>
            <div style={{ display: 'flex', gap: 22 }}>
              <div className="kv">
                Aperturas hoy<b>{e.aperturas_hoy}</b>
              </div>
              <div className="kv">
                Min. abierta<b>{e.minutos_hoy.toFixed(1)}</b>
              </div>
            </div>
            <div className="sparkwrap">
              <div className="spark">
                {hist.map((h, i) => (
                  <div
                    key={i}
                    style={{ height: Math.max(4, (h / maxh) * 30), background: colorApertura(h) }}
                    title={mmss(h)}
                  />
                ))}
              </div>
              <small>últimas aperturas</small>
            </div>
          </div>
          {e.id === PUERTA_CON_MODELO && (
            <>
              <BotonAnalizarVideo puertaId={e.id} onToast={onToast} />
              <BotonModelo />
            </>
          )}
        </div>
      </div>

      <div className="ghost">⚠ Cámara sin señal — verificar PoE</div>
    </article>
  )
}
