const API_URL = import.meta.env.VITE_API_URL;
console.log("API_URL:", API_URL);

export async function apiFetch(endpoint, options = {}) {
  const response = await fetch(`${API_URL}${endpoint}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Error en la petición");
  }
    console.log("Fetch URL:", `${API_URL}${endpoint}`);
  return response.json();
}