import { apiFetch } from "./api";

export function obtenerArchivosExportacion() {
  return apiFetch(
    "/api/microservicios/exportacion/archivos"
  );
}

export function exportarCSV(payload) {
  return apiFetch(
    "/api/microservicios/exportacion/csv",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export function exportarJSON(payload) {
  return apiFetch(
    "/api/microservicios/exportacion/json",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}