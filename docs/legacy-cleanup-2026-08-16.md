# Inventario de limpieza legacy — 2026-08-16

Este documento registra la limpieza realizada en `feat/integracion-resultados-ml` durante el rediseño de la aplicación.

## Puntos de recuperación

- Respaldo previo al rediseño/integración: `backup-pre-integracion-ml`.
- `main` permanece fuera de los cambios del rediseño mientras la rama no sea fusionada.
- Estado estable reciente previo a la limpieza: `b90a5c33aa80b6f272e9fdb7aed270acc6e65b79`.
- Todo lo eliminado continúa recuperable desde el historial de Git.

## Eliminado por estar confirmado como legacy

### Pipeline anterior

- `ml-pipeline/` completo.

### Microservicios anteriores

- `backend/ms_analisis_ml/`
- `backend/ms_preprocesamiento/`
- `backend/ms_recoleccion_datos/`

### API REST: integración anterior

Se eliminó la cadena model/service/controller/route asociada al esquema anterior para:

- incendios
- áreas de interés
- hotspots
- condiciones meteorológicas
- sesiones de análisis
- NDVI
- datasets
- análisis ML
- orquestación de microservicios

También se eliminó:

- `backend/api-rest/src/data/clients/preprocesamiento.client.js`
- `backend/api-rest/src/data/models/` completo, ya que sus modelos correspondían al esquema anterior.

`backend/api-rest/src/app.js` dejó de importar y montar esas rutas antiguas.

## Conservado deliberadamente por no estar 100 % confirmado como prescindible

- `backend/ms_exportacion_datos/`
- `backend/api-rest/src/application/services/importacion.service.js`
- `backend/api-rest/src/presentation/controllers/importacion.controller.js`
- `backend/api-rest/src/presentation/routes/importacion.routes.js`
- `backend/scripts/preparar_datos_v2/`
- `backend/api-rest/src/domain/`

Estos elementos deben revisarse por separado antes de decidir si se eliminan.

## Flujo vigente preservado

Se conservan la API y componentes relacionados con:

- catálogos
- resultados estatales
- resultados municipales
- geometrías INEGI
- recursos/exportaciones
- conexión MongoDB v2
- preparación de datos v2
- frontend renovado y mapa nacional

## Nota sobre MongoDB

La API anterior todavía montaba rutas que importaban modelos Mongoose legacy. Su eliminación evita que el arranque normal del backend siga cargando esa cadena antigua. Las colecciones MongoDB se administran por separado del historial Git.
