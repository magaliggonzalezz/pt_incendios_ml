const API_URL = import.meta.env.VITE_API_URL || "http://localhost:3000";

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
    let message = errorText || "Error en la petición";

    try {
      const parsed = JSON.parse(errorText);
      message = parsed?.error || parsed?.message || message;
    } catch {
      // La API puede responder texto plano
    }

    throw new Error(message);
  }

  return response.json();
}
