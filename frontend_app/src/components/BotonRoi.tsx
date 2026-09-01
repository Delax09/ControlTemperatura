/* ==== Lanzador de la herramienta de zonas (ROI) ==== */

import { useState } from 'react'
import { definirRoi } from '../lib/api'

type Fase = 'idle' | 'lanzando' | 'abierta'

interface Props {
  onToast?: (mensaje: string) => void
}

export default function BotonRoi({ onToast }: Props) {
  const [fase, setFase] = useState<Fase>('idle')

  async function lanzar() {
    setFase('lanzando')
    try {
      const data = await definirRoi()
      if (data.status === 'ok') {
        setFase('abierta')
        onToast?.('Ventana de ROI abierta en el servidor. Guarda con "s" y cierra con "q".')
        // La herramienta es de un solo uso por sesión: se vuelve a habilitar
        // pasados unos segundos para poder relanzarla si se cerró sin guardar.
        setTimeout(() => setFase('idle'), 8000)
      } else {
        onToast?.(`No se pudo abrir la herramienta de ROI: ${data.message}`)
        setFase('idle')
      }
    } catch (error) {
      console.error('Error de red:', error)
      onToast?.('No se pudo contactar al servidor para abrir la herramienta de ROI.')
      setFase('idle')
    }
  }

  return (
    <button
      className="btn"
      disabled={fase !== 'idle'}
      title="Abre la ventana de OpenCV en el equipo del servidor para dibujar las zonas de cada puerta"
      onClick={(ev) => {
        ev.stopPropagation()
        void lanzar()
      }}
    >
      {fase === 'abierta' ? '✅ ROI abierta' : fase === 'lanzando' ? '⏳ Abriendo...' : '✏️ Definir ROI'}
    </button>
  )
}
