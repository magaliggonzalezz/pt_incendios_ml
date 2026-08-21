# Preparación de almacenamiento externo

Este módulo genera una versión de despliegue (`data_deploy/`) a partir de los datasets finales e integrados del proyecto.

## Objetivo

Reducir el volumen que se subiría a object storage sin modificar los archivos originales. La estrategia actual es:

- `municipio_dia`: convertir los 25 CSV anuales a Parquet con ZSTD y eliminar `anio` y `mes` por ser derivables de la fecha/partición.
- `detalle_exportacion`: convertir los 25 CSV anuales a Parquet con ZSTD y eliminar únicamente `anio` y `mes`; el resto se conserva para exportación analítica detallada.
- FIRMS: conservar una sola representación canónica completa en Parquet; no desplegar simultáneamente completo + anuales + CSV + GeoJSON.
- CONAFOR: conservar una sola representación canónica completa en Parquet.
- INEGI: conservar `inegi_contexto_municipal.csv` convertido a Parquet. Las capas GeoJSON fuente pesadas quedan fuera del deploy base hasta definir cuáles se mostrarán realmente en la web.
- SMN: conservar `smn_estaciones.geojson` como capa web ligera.

Las geometrías grandes para Leaflet se optimizarán en una fase posterior; no se copian a `data_deploy/` en esta etapa.

## Dependencias

```powershell
python -m pip install pandas pyarrow
```

## Ejecución

Desde la raíz del repositorio:

```powershell
python .\backend\scripts\preparar_almacenamiento_externo\generar_datasets_deploy.py
```

La salida se genera en:

```text
data_deploy/
├── resultados/municipio_dia/
├── exportaciones/municipio_dia_detalle/
├── fuentes/firms/
├── fuentes/conafor/
├── contexto/
├── capas_web/smn/
└── reporte_generacion_deploy.json
```

## Seguridad de datos

El script solo lee los datasets originales y escribe archivos nuevos en `data_deploy/`. No sobrescribe ni elimina los archivos del pipeline.

## Siguiente fase

Después de generar `data_deploy/`, se mide su tamaño real y se decide qué geometrías requieren formato web optimizado (por ejemplo PMTiles u otra representación adecuada) antes de seleccionar/configurar definitivamente el proveedor de object storage.
