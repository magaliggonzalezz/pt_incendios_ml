# Preparación de datos v2

Este directorio contiene la transformación previa a la carga de los resultados finales del pipeline ML a MongoDB.

## Objetivo

Partir de los cinco JSONL finales de consulta y producir:

- `clusters.jsonl`
- `estados.jsonl`
- `municipios.jsonl`
- `resultados_estado_dia.jsonl`
- `resultados_estado_mes.jsonl`
- `resultados_estado_anio.jsonl`
- `resultados_municipio_mes.jsonl`
- `resultados_municipio_anio.jsonl`
- `reporte_transformacion.json`

La transformación elimina de cada observación los textos descriptivos que pertenecen a catálogos y conserva las métricas originales. No se conecta a MongoDB ni modifica Atlas.

## Archivos de entrada esperados

La carpeta indicada con `--input-dir` debe contener exactamente estos archivos:

```text
app_estado_anio_resultados.jsonl
app_estado_mes_resultados.jsonl
app_estado_dia_resultados.jsonl
app_municipio_anio_resultados.jsonl
app_municipio_mes_resultados.jsonl
```

Los JSONL originales no deben subirse al repositorio.

## Ejecución

Desde la raíz del repositorio, en PowerShell:

```powershell
python .\backend\scripts\preparar_datos_v2\transformar_resultados.py `
  --input-dir "C:\RUTA\A\evaluation\app_query_exports" `
  --output-dir ".\data_v2_generada"
```

Si la carpeta de salida ya existe y se desea regenerarla:

```powershell
python .\backend\scripts\preparar_datos_v2\transformar_resultados.py `
  --input-dir "C:\RUTA\A\evaluation\app_query_exports" `
  --output-dir ".\data_v2_generada" `
  --overwrite
```

## Validaciones incluidas

El script:

1. comprueba que existan los cinco archivos requeridos;
2. procesa los JSONL en streaming;
3. normaliza `cve_ent`, `cve_mun` y `cvegeo` preservando ceros a la izquierda;
4. comprueba que `cvegeo == cve_ent + cve_mun`;
5. detecta inconsistencias en los catálogos extraídos;
6. informa el archivo y la línea exactos si encuentra un registro inválido;
7. genera un reporte con conteos y tamaños de los artefactos resultantes.

## Antes de importar a MongoDB

No importar automáticamente los resultados. Primero revisar `reporte_transformacion.json`, validar algunos documentos de muestra y comparar conteos/tamaños con los exports originales. La creación de colecciones e índices es una fase posterior.
