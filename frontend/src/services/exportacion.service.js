const EXPORT_API_URL =
  import.meta.env.VITE_EXPORT_API_URL ??
  (import.meta.env.DEV ? "http://localhost:3004" : "");

async function exportFetch(endpoint, options = {}) {
  const response = await fetch(`${EXPORT_API_URL}${endpoint}`, options);

  if (!response.ok) {
    const text = await response.text();
    try {
      const parsed = JSON.parse(text);
      throw new Error(parsed?.error || `Error ${response.status} en el servicio de exportación`);
    } catch (error) {
      if (error instanceof SyntaxError) {
        throw new Error(text || `Error ${response.status} en el servicio de exportación`);
      }
      throw error;
    }
  }

  return response;
}

export async function generarExportacion(formato, nombre, datos) {
  const response = await exportFetch(`/api/exportacion/${encodeURIComponent(formato)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nombre, datos }),
  });

  return response.json();
}

export async function descargarExportacion(nombreArchivo) {
  const response = await exportFetch(
    `/api/exportacion/descargar/${encodeURIComponent(nombreArchivo)}`,
  );
  return response.blob();
}
