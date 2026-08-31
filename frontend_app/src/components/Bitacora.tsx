/* ==== Bitácora del evento, derivada del tiempo de apertura ==== */

import { REGLAS_ESCALAMIENTO, hhmm } from '../lib/umbrales'
import type { Puerta } from '../types'

export interface NotaTurno {
  hora: string
  texto: string
}

interface Props {
  puerta: Puerta
  segundos: number
  notas: NotaTurno[]
}

export default function Bitacora({ puerta, segundos, notas }: Props) {
  if (!puerta.abierta) {
    return (
      <div className="m-log">
        <div>
          <time>—</time>
          <span>La puerta está cerrada. Sin evento en curso.</span>
        </div>
      </div>
    )
  }

  const t0 = new Date(Date.now() - segundos * 1000)

  return (
    <div className="m-log">
      <div>
        <time>{hhmm(t0)}</time>
        <span>
          Visión computacional detecta <em>puerta abierta</em>
        </span>
      </div>
      {REGLAS_ESCALAMIENTO.map((r) => {
        const momento = new Date(+t0 + r.t * 1000)
        const alcanzado = segundos > r.t
        return (
          <div key={r.t}>
            <time>{alcanzado ? hhmm(momento) : '··:··'}</time>
            <span>{alcanzado ? r.titulo : <span className="fut">{r.titulo}</span>}</span>
          </div>
        )
      })}
      {notas.map((nt, i) => (
        <div key={`n${i}`}>
          <time>{nt.hora}</time>
          <span>
            Nota del turno: <em>{nt.texto}</em>
          </span>
        </div>
      ))}
    </div>
  )
}
