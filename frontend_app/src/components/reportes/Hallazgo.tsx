/* ==== Hallazgo automático: ¿coinciden los dos rankings? ==== */

import { minTexto } from '../../lib/formato'
import type { Reporte } from '../../types'

export default function Hallazgo({ reporte }: { reporte: Reporte }) {
  const lider = reporte.filas[0]
  const termico = reporte.peorDeriva

  if (lider.id === termico.id) {
    return (
      <div className="hallazgo">
        <b>{lider.nombre}</b> lidera en tiempo abierto y además acumula la mayor deriva térmica (+{termico.derivaMax}{' '}
        °C). Es la puerta a intervenir primero.
      </div>
    )
  }

  return (
    <div className="hallazgo">
      La puerta más tiempo abierta no es la más castigada térmicamente. <b>{lider.nombre}</b> acumula{' '}
      {minTexto(lider.minutos)} con +{lider.derivaMax} °C de deriva, mientras <b>{termico.nombre}</b> llega a{' '}
      <b>+{termico.derivaMax} °C</b> con solo {minTexto(termico.minutos)} — su set point de {termico.setPoint} °C deja
      un salto mucho mayor contra el ambiente, así que cada minuto abierta cuesta más. Para cadena de frío, priorizar
      por deriva y no por tiempo.
    </div>
  )
}
