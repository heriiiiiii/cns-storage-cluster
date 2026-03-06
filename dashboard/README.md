# CNS Storage Dashboard

Dashboard web para monitorear el cluster de almacenamiento regional.

## Fuente de datos
Lee directamente desde **Supabase** (tablas `nodes`, `reports`, `disk_metrics`).
Para enviar comandos a nodos, conecta al **servidor CNS** via HTTP (puerto 3001).

## Requisitos

```bash
pip install -r requirements.txt
```

## Configuración

Edita el archivo `.env`:

```
SUPABASE_URL=<tu url>
SUPABASE_KEY=<tu key>
SERVER_HOST=<ip del servidor CNS>
SERVER_ADMIN_PORT=3001
```

## Ejecutar

```bash
streamlit run app.py
```

Se abre en http://localhost:8501

## Funcionalidades

- Estado en tiempo real de los 9 nodos regionales
- Totales del cluster (capacidad, uso, libre, % utilización)
- Detalle por nodo: discos, timestamps, IP/MAC/RAM
- Auto-refresco configurable (5s / 10s / 30s / 60s)
- Envío de comandos a nodos via servidor CNS
