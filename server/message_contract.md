# CNS Storage Cluster — Message Contract (v1)

Este documento define el contrato oficial de mensajes entre:
- Clientes regionales (nodos de almacenamiento)
- Servidor central de monitoreo

## Transporte
- Protocolo: TCP
- Cada mensaje es un JSON en una sola línea, delimitado por `\n` (newline).
- Codificación: UTF-8

## Convenciones generales
- Todos los mensajes incluyen `type`.
- Identificación del nodo:
  - Campo preferido: `node_id` (string)
  - Compatibilidad: `node_code` (string)
- Timestamps:
  - `client_reported_at`: timestamp reportado por el cliente (puede estar desfasado si el reloj del nodo está mal).
  - `server_received_at`: timestamp del servidor (fuente de verdad para histórico y detección de “No reporta”).
- El cliente reporta solo **el primer disco** detectado.
- Extensibilidad: se permite añadir campos nuevos en `extra` sin romper el contrato.

---

## Tipos de mensajes

### 1) Client → Server: REPORT
Enviado periódicamente por cada cliente con métricas de disco y datos extra.

Campos:
- `type`: `"REPORT"`
- `node_code`: string (ej: `"LPZ-01"`)  (alias permitido: `node_id`)
- `client_reported_at`: ISO8601 UTC, ej: `"2026-03-03T12:00:00Z"`
- `interval_seconds`: integer (ej: 10)
- `disks`: array con 1 elemento (primer disco)
- `extra`: objeto con campos opcionales (RAM, IP, MAC, etc.)

Ejemplo:
```json
{
  "type": "REPORT",
  "node_code": "LPZ-01",
  "client_reported_at": "2026-03-03T12:00:00Z",
  "interval_seconds": 10,
  "disks": [
    {
      "disk_name": "C:\\",
      "disk_type": "SSD",
      "total_bytes": 512000000000,
      "used_bytes": 200000000000,
      "free_bytes": 312000000000,
      "iops": 1500
    }
  ],
  "extra": {
    "ip": "192.168.0.50",
    "mac": "AA:BB:CC:DD:EE:FF",
    "ram_total_bytes": 17179869184,
    "ram_used_bytes": 8589934592
  }
}