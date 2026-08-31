# frontend_app · Muro de control (React + TypeScript + Vite)

Servidor 2 del proyecto. Es una SPA independiente: no la sirve Django, habla con
`backend_api` por HTTP.

## Requisitos

Node.js 20 o superior (incluye npm). No está instalado en el equipo todavía:
descargar el instalador LTS desde <https://nodejs.org> y reabrir la terminal.

## Arranque

```bash
cd frontend_app
npm install        # solo la primera vez
npm run dev        # http://localhost:5173
```

En paralelo, el backend:

```bash
cd backend_api
python manage.py runserver     # http://localhost:8000
```

`npm run build` genera `dist/`, que es lo que se publica en Nginx / Vercel.
`npm run lint` corre solo el chequeo de tipos.

## Cómo habla con el backend

`vite.config.ts` deja un proxy de desarrollo: todo lo que pida el frontend a
`/api` y `/alertas` sale hacia `http://localhost:8000`. Por eso en desarrollo no
hay que tocar CORS ni escribir URLs absolutas.

En producción, donde no hay proxy, se define la base de la API en `.env`:

```
VITE_API_URL=https://api.miplanta.cl
```

Vacío = mismo origen. Las variables de Vite tienen que empezar con `VITE_` para
llegar al bundle.

## Estructura

```
src/
├── main.tsx, App.tsx        entrada y rutas (/ y /reportes)
├── types/                   contratos de datos (Puerta, Reporte, …)
├── lib/
│   ├── api.ts               llamadas a Django + dato de prueba
│   ├── umbrales.ts          cortes de tiempo, colores y escalamiento
│   ├── tempSim.ts           sensor de temperatura simulado (TEMPORAL)
│   ├── reportesDatos.ts     consolidado del reporte simulado (TEMPORAL)
│   └── formato.ts           helpers de formato del reporte
├── hooks/                   useReloj, usePuertas (polling), useToast
├── pages/                   Dashboard (muro), Reportes
├── components/              cards, modal, gráfico, barra de alerta…
└── styles/                  el CSS de siempre, sin cambios
```

## Pendientes heredados del backend

- `/api/eventos-camaras/` todavía no existe con la forma que espera el muro
  (ver `PUERTAS_DEMO` en `src/lib/api.ts`). Mientras no exista, el frontend cae
  a un dato de prueba y lo avisa por consola.
- No hay serie histórica de temperatura ni consolidado por puerta: los dos
  módulos marcados TEMPORAL los simulan. Cuando el backend los entregue, se
  borran y se reemplazan por llamadas a la API.
