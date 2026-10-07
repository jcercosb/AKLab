SAT.mdb — verified F0.2 inspection
==================================

Source file
-----------

- Type: Microsoft Access Database.
- Size observed: approximately 10–11 MB.
- SHA-256: `e682ec32475183ec7eb0569d048edc4aa0deff6189ee946c2558a315fe33cc85`.

Verified tables
---------------

The real database was read with `mdbtools`. Tables observed include:

- `CONSULTAS`
- `HISTORICO`
- `DOCUMENTOS`
- `IMAGENES`
- `CLASIFICACION`
- `PRIORIDAD`
- `SITUACION`
- `CLIENTES`
- `CONTROL`
- `HISTORIACLI`
- `SATSERV`
- `TECNICOS`
- `Usuarios`
- additional operational tables

CONSULTAS
---------

`CONSULTAS` contains 3,249 rows and 22 fields:

- `ID_CONSULTA`
- `CABECERA`
- `TECNICO`
- `FECHA`
- `PROGRAMA`
- `MODULO`
- `SINTOMAS`
- `ENTORNO`
- `SOLUCION`
- `OBSERVACIONES`
- `BORRADO`
- `REPARA`
- `ULTIMA`
- `ID_PRI`
- `ID_SIT`
- `ESPERA`
- `QUIEN`
- `IMPRESO`
- `PUBLICADO`
- `FECHAAVISO`
- `HORAAVISO`
- `CodigoWeb`

The last three fields were not present in the initial conceptual reconstruction,
which validated the decision to preserve complete source rows in `raw_content`.

HISTORICO
---------

`HISTORICO` contains 10,369 rows with:

- `ID_HISTORICO`
- `ID_BOLETIN`
- `FECHA`
- `HORA`
- `DESCRIPCION`
- `EXPLICACION`
- `ID_TECNICO`

`HORA` is stored as text in the Access schema.

All 10,369 `ID_HISTORICO` values are present and unique. 10,188 rows reference
an existing consultation through `ID_BOLETIN`; 181 are orphan references in the
current snapshot. The orphans are retained as source records.

Encoding and NULLs
------------------

The raw `mdb-export` output for CONSULTAS decoded as strict UTF-8 with zero
replacement characters. Text containing line breaks and non-breaking spaces was
preserved.

The extractor was changed to use an explicit NULL sentinel. In the validated
CONSULTAS export this produced 12,095 `NULL` values and zero empty strings,
preventing source NULLs from being silently collapsed into empty text.

Neutral export
--------------

The verified export produced:

- `CONSULTAS.jsonl`: 3,249 rows.
- `HISTORICO.jsonl`: 10,369 rows.
- `manifest.json`: source fingerprint and extraction metadata.

This neutral representation is the reproducible boundary between Access and the
knowledge system.
