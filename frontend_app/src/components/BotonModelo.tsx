/* ==== Arranque del worker de visión (YOLO) ==== */

import { useState } from 'react'
import { ejecutarModelo } from '../lib/api'

type Fase = 'idle' | 'lanzando' | 'corriendo'

export default function BotonModelo() {
  const [fase, setFase] = useState<Fase>('idle')

  async function lanzar() {
    setFase('lanzando')
    try {
      const data = await ejecutarModelo()
      if (data.status === 'ok') {
        setFase('corriendo')
      } else {
        alert('Hubo un error al ejecutar el script: ' + data.message)
        setFase('idle')
      }
    } catch (error) {
      console.error('Error de red:', error)
      setFase('idle')
    }
  }

  const estilo =
    fase === 'corriendo'
      ? { background: 'var(--good)', borderColor: 'var(--good)' }
      : fase === 'lanzando'
        ? { background: 'var(--surface-2)' }
        : { background: '#3987e5', borderColor: '#3987e5' }

  const texto =
    fase === 'corriendo' ? '✅ MODELO EN EJECUCIÓN' : fase === 'lanzando' ? '⏳ Iniciando modelo...' : '▶ INICIAR CÁMARA YOLO'

  return (
    <button
      className="btn"
      disabled={fase !== 'idle'}
      // El click no debe abrir el modal de la card que lo contiene.
      onClick={(ev) => {
        ev.stopPropagation()
        void lanzar()
      }}
      style={{ ...estilo, color: 'white', fontWeight: 600, width: '100%', padding: 10 }}
    >
      {texto}
    </button>
  )
}
