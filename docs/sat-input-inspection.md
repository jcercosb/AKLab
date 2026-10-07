# SAT.mdb — inspeccion inicial de F0.2

## Fichero recibido

- Tipo detectado: Microsoft Access Database
- Tamano: 10588160 bytes
- SHA-256: `e682ec32475183ec7eb0569d048edc4aa0deff6189ee946c2558a315fe33cc85`

## Estructura confirmada directamente en el binario

La inspeccion del fichero confirma, como minimo, los siguientes identificadores esperados:

- `CONSULTAS`
- `HISTORICO`
- `DOCUMENTOS`
- `IMAGENES`
- `ID_CONSULTA`
- `ID_HISTORICO`
- `CABECERA`
- `SINTOMAS`
- `SOLUCION`
- `OBSERVACIONES`

Tambien aparecen referencias internas a campos como `CONSULTAS.PROGRAMA` y `CONSULTAS.MODULO`.

## Limite de esta inspeccion

Esto valida que estamos trabajando con el SAT esperado, pero no sustituye una lectura tabular. El entorno actual no incorpora `mdbtools` y no permite descargar paquetes externos. F0.2-B debe validar tipos, conteos y filas reales con un extractor disponible en el entorno de desarrollo.
