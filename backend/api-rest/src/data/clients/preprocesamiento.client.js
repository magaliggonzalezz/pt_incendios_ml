import { env } from "../../config/env.js";

export async function obtenerFuentesPreprocesamiento() {
  const response = await fetch(
    `${env.msPreprocesamientoUrl}/api/preprocesamiento/fuentes`
  );

  if (!response.ok) {
    throw new Error("Error al consultar ms-preprocesamiento");
  }

  return await response.json();
}

export async function obtenerReportesPreprocesamiento(fuente) {
  const response = await fetch(
    `${env.msPreprocesamientoUrl}/api/preprocesamiento/${fuente}/reportes`
  );

  if (!response.ok) {
    throw new Error("Error al consultar reportes de preprocesamiento");
  }

  return await response.json();
}

export async function obtenerScriptsPreprocesamiento(fuente) {
  const response = await fetch(
    `${env.msPreprocesamientoUrl}/api/preprocesamiento/${fuente}/scripts`
  );

  if (!response.ok) {
    throw new Error("Error al consultar scripts de preprocesamiento");
  }

  return await response.json();
}