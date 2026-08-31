/* ==== Miniatura de cámara ====
   Si hay una captura real para esa cámara se usa; si no, un placeholder SVG
   teñido según el tipo de recinto. */

import type { TipoRecinto } from '../types'

/** Capturas reales disponibles. Viven en public/img. */
const CAM_THUMBS: Record<string, string> = {
  anden1: '/img/anden1.png',
}

const FONDO: Record<TipoRecinto, string> = {
  anden: '#20303f',
  pasillo: '#2b2e33',
  congelado: '#1b2a33',
  tunel: '#161f2b',
  mp: '#26302a',
  sala: '#2e2b26',
}

function PlaceholderCam({ tipo }: { tipo: TipoRecinto }) {
  const g = FONDO[tipo] ?? '#222'
  return (
    <svg viewBox="0 0 320 180" width="100%" height="100%" preserveAspectRatio="xMidYMid slice">
      <rect width="320" height="180" fill={g} />
      <rect x="0" y="120" width="320" height="60" fill="#000" opacity=".22" />
      <rect x="196" y="34" width="86" height="112" rx="3" fill="#1d3b6b" opacity=".75" />
      <rect x="196" y="34" width="86" height="112" rx="3" fill="none" stroke="#3f5f92" strokeWidth="2" />
      {Array.from({ length: 9 }, (_, i) => (
        <rect key={`l${i}`} x="198" y={38 + i * 12} width="82" height="4" fill="#7fa8dd" opacity={0.1 + 0.06 * (i % 3)} />
      ))}
      {Array.from({ length: 5 }, (_, i) => (
        <rect key={`p${i}`} x={16 + i * 30} y={96 - i * 4} width="26" height={44 + i * 4} rx="2" fill="#3d6fa8" opacity=".55" />
      ))}
      <circle cx="46" cy="16" r="7" fill="#111" opacity=".6" />
      <circle cx="66" cy="16" r="7" fill="#111" opacity=".6" />
    </svg>
  )
}

export default function CamThumb({ cam, tipo }: { cam?: string; tipo: TipoRecinto }) {
  const src = cam ? CAM_THUMBS[cam] : undefined
  return src ? <img src={src} alt="" /> : <PlaceholderCam tipo={tipo} />
}
