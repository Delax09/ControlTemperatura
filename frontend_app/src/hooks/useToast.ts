import { useCallback, useEffect, useRef, useState } from 'react'

const DURACION = 2600

/** Mensaje efímero en la esquina inferior. */
export function useToast() {
  const [mensaje, setMensaje] = useState<string | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const toast = useCallback((texto: string) => {
    setMensaje(texto)
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => setMensaje(null), DURACION)
  }, [])

  useEffect(() => () => { if (timer.current) clearTimeout(timer.current) }, [])

  return { mensaje, toast }
}
