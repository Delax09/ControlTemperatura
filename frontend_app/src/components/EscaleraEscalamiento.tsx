import { REGLAS_ESCALAMIENTO, mmss } from '../lib/umbrales'

interface Props {
  segundos: number
  abierta: boolean
}

export default function EscaleraEscalamiento({ segundos, abierta }: Props) {
  const alcanzado = REGLAS_ESCALAMIENTO.filter((r) => segundos > r.t)
  const ultimo = alcanzado.length ? Math.max(...alcanzado.map((r) => r.t)) : null

  return (
    <div className="m-ladder">
      {REGLAS_ESCALAMIENTO.map((r) => {
        const hecho = segundos > r.t
        const activo = hecho && r.t === ultimo && abierta
        const clase = activo ? 'active' : hecho ? 'done' : 'pend'
        return (
          <div key={r.t} className={`m-step ${clase}`}>
            <b>
              {mmss(r.t)} · {r.titulo}
            </b>
            <span>
              {r.detalle}
              {hecho ? '' : ' — no alcanzado'}
            </span>
          </div>
        )
      })}
    </div>
  )
}
