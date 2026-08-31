import { FLOTA } from '../../lib/reportesDatos'
import { minTexto } from '../../lib/formato'
import type { Reporte } from '../../types'

export default function Kpis({ reporte }: { reporte: Reporte }) {
  const lider = reporte.filas[0]
  const termico = reporte.peorDeriva
  // El dato interesante: no siempre son la misma puerta.
  const coinciden = lider.id === termico.id

  return (
    <div className="rep-kpis">
      <div className="kpi">
        <div className="l">Tiempo total abierto</div>
        <div className="v">
          {(reporte.totalMinutos / 60).toFixed(1)}
          <small> h</small>
        </div>
        <div className="n">
          {reporte.totalAperturas} aperturas · {FLOTA.length} puertas
        </div>
      </div>

      <div className="kpi">
        <div className="l">Más tiempo abierta</div>
        <div className="v" style={{ fontSize: 19 }}>
          {lider.id}
        </div>
        <div className="n">
          {minTexto(lider.minutos)} · {lider.aperturas} aperturas
        </div>
      </div>

      <div className="kpi alerta">
        <div className="l">Mayor deriva térmica</div>
        <div className="v" style={{ fontSize: 19 }}>
          {termico.id}
        </div>
        <div className="n">
          +{termico.derivaMax} °C sobre set point{coinciden ? '' : ' · no es la más abierta'}
        </div>
      </div>

      <div className={`kpi${reporte.puertasFuera > 3 ? ' critico' : ''}`}>
        <div className="l">Puertas con deriva fuera de rango</div>
        <div className="v">
          {reporte.puertasFuera}
          <small> / {FLOTA.length}</small>
        </div>
        <div className="n">al menos una hora sobre 1,2 °C</div>
      </div>

      <div className="kpi">
        <div className="l">Promedio por apertura</div>
        <div className="v">
          {(reporte.totalMinutos / Math.max(1, reporte.totalAperturas)).toFixed(1)}
          <small> min</small>
        </div>
        <div className="n">ventana de {reporte.horas} h</div>
      </div>
    </div>
  )
}
