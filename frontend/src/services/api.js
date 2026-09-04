const API_URL = import.meta.env.VITE_API_URL || "http://localhost:3000";

function normalizeApiError(response, errorText) {
  if (!errorText) return `Error ${response.status} al consultar la API`;

  try {
    const parsed = JSON.parse(errorText);
    return parsed?.error || parsed?.message || `Error ${response.status} al consultar la API`;
  } catch {
    const isHtml = /<!doctype html>|<html[\s>]/i.test(errorText);
    if (isHtml) {
      if (response.status === 404) {
        return "La ruta solicitada no está disponible en el backend en ejecución. Reinicia la API después de actualizar la rama y vuelve a intentar.";
      }
      return `La API respondió con HTML inesperado (HTTP ${response.status}). Revisa el backend en ejecución.`;
    }
    return errorText;
  }
}

export async function apiFetch(endpoint, options = {}) {
  const response = await fetch(`${API_URL}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(normalizeApiError(response, errorText));
  }

  return response.json();
}
