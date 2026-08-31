/* ==== Muro de control ====
   Equivalente de la antigua index.html + dashboard.js. */

import { useMemo, useState } from 'react'
import Header from '../components/Header'
import AlertBar from '../components/AlertBar'
import Toolbar from '../components/Toolbar'
import DoorCard from '../components/DoorCard'
import ModalAlerta from '../components/ModalAlerta'
import Toast from '../components/Toast'
import { usePuertas } from '../hooks/usePuertas'
import { useToast } from '../hooks/useToast'
import { nivel, ordenar } from '../lib/umbrales'
import type { Filtro } from '../types'

export default function Dashboard() {
  const { puertas, ultimaActualizacion, silenciar } = usePuertas()
  const { mensaje, toast } = useToast()
  const [filtro, setFiltro] = useState<Filtro>('all')
  const [seleccion, setSeleccion] = useState<string | null>(null)

  const lista = useMemo(
    () =>
      [...puertas]
        .sort(ordenar)
        .filter((e) =>
          filtro === 'all' ? true : filtro === 'open' ? e.abierta : nivel(e) === 'crit' || nivel(e) === 'serious',
        ),
    [puertas, filtro],
  )

  // La puerta del modal se relee de `puertas` en cada poll, así el detalle se
  // mantiene al día sin lógica extra de refresco.
  const puertaSel = puertas.find((e) => e.id === seleccion) ?? null

  function radio() {
    alert(
      'Prototipo: aquí se dispararía el aviso al HT del supervisor de turno o mensaje al grupo de WhatsApp de operaciones.',
    )
  }

  return (
    <div className="wrap">
      <Header puertas={puertas} />

      <AlertBar puertas={puertas} onSilenciar={() => silenciar()} onRadio={radio} />

      <Toolbar filtro={filtro} onFiltro={setFiltro} />

      <div className="grid">
        {lista.map((e) => (
          <DoorCard key={e.id} e={e} onAbrir={setSeleccion} />
        ))}
      </div>

      <footer>
        Muro de control en vivo conectado a Django API · Click en una puerta para ver el detalle · Pensado para pantalla
        de 55" en sala de despacho · <kbd>F11</kbd> pantalla completa
      </footer>

      <ModalAlerta
        puerta={puertaSel}
        ultimaActualizacion={ultimaActualizacion}
        onCerrar={() => setSeleccion(null)}
        onSilenciar={silenciar}
        onToast={toast}
      />
      <Toast mensaje={mensaje} />
    </div>
  )
}
