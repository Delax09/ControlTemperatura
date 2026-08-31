/* ==== Botón de exportar reporte ====
   Dos destinos distintos, así que menú y no un botón directo: la jefatura que
   quiere leerlo pide PDF, la que quiere seguir cortando los datos pide Excel. */

import { useEffect, useRef, useState } from 'react'
import { exportarCSV, exportarPDF } from '../../lib/exportarReporte'
import type { Reporte } from '../../types'

interface Props {
  reporte: Reporte
  /** Aviso al usuario; en la práctica el toast del dashboard. */
  onAviso?: (mensaje: string) => void
}

export default function BotonExportar({ reporte, onAviso }: Props) {
  const [abierto, setAbierto] = useState(false)
  const caja = useRef<HTMLDivElement>(null)

  // Cerrar al hacer clic fuera o con Escape: es un menú, no un panel.
  useEffect(() => {
    if (!abierto) return
    const fuera = (e: MouseEvent) => {
      if (!caja.current?.contains(e.target as Node)) setAbierto(false)
    }
    const tecla = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setAbierto(false)
    }
    document.addEventListener('mousedown', fuera)
    document.addEventListener('keydown', tecla)
    return () => {
      document.removeEventListener('mousedown', fuera)
      document.removeEventListener('keydown', tecla)
    }
  }, [abierto])

  const pdf = () => {
    setAbierto(false)
    // exportarPDF avisa si el bloqueador de pop-ups obligó a descargar el HTML.
    const enPestana = exportarPDF(reporte)
    onAviso?.(
      enPestana
        ? 'Reporte abierto en una pestaña nueva · usa Imprimir → Guardar como PDF'
        : 'El navegador bloqueó la pestaña · se descargó el reporte como archivo HTML',
    )
  }

  const csv = () => {
    setAbierto(false)
    exportarCSV(reporte)
    onAviso?.(`Descargando CSV · ventana de ${reporte.horas} horas`)
  }

  return (
    <div className="exportar" ref={caja}>
      <button
        className="btn-exportar"
        onClick={() => setAbierto((v) => !v)}
        aria-expanded={abierto}
        aria-haspopup="menu"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
          <path d="M12 3v12M7 10l5 5 5-5M4 20h16" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        Exportar reporte
      </button>

      {abierto && (
        <div className="exportar-menu" role="menu">
          <button role="menuitem" onClick={pdf}>
            <b>PDF / Imprimir</b>
            <span>Documento de una página, listo para adjuntar a un correo</span>
          </button>
          <button role="menuitem" onClick={csv}>
            <b>Excel (CSV)</b>
            <span>Ranking más el detalle hora a hora de cada puerta</span>
          </button>
        </div>
      )}
    </div>
  )
}
