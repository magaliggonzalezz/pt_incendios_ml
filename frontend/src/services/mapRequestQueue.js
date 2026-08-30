const RESPONSE_CACHE_TTL_MS = 10 * 60 * 1000;

const responseCache = new Map();
let requestQueue = Promise.resolve();

function createAbortError() {
  if (typeof DOMException !== "undefined") {
    return new DOMException("The operation was aborted", "AbortError");
  }
  const error = new Error("The operation was aborted");
  error.name = "AbortError";
  return error;
}

function getCached(key) {
  const cached = responseCache.get(key);
  if (!cached) return null;
  if (Date.now() - cached.createdAt >= RESPONSE_CACHE_TTL_MS) {
    responseCache.delete(key);
    return null;
  }
  return cached.value;
}

function setCached(key, value) {
  responseCache.set(key, { createdAt: Date.now(), value });
  return value;
}

export function normalizeBbox(value, decimals = 4) {
  const parts = String(value || "")
    .split(",")
    .map(Number);
  if (parts.length !== 4 || parts.some((part) => !Number.isFinite(part))) {
    return String(value || "");
  }
  return parts.map((part) => part.toFixed(decimals)).join(",");
}

export function enqueueMapRequest({ key, request, signal, cache = true }) {
  const cached = cache ? getCached(key) : null;
  if (cached) return Promise.resolve(cached);

  const execute = async () => {
    if (signal?.aborted) throw createAbortError();

    // La petición real no recibe AbortSignal a propósito. Si el navegador cancela
    // una llamada mientras Node ya procesa GeoJSON/Parquet, el trabajo del backend
    // continúa de todos modos. Mantener esta cola esperando la respuesta evita
    // arrancar otra operación pesada en paralelo sobre el mismo proceso Node.
    const value = await request();

    if (cache) setCached(key, value);
    if (signal?.aborted) throw createAbortError();
    return value;
  };

  const result = requestQueue.then(execute, execute);
  requestQueue = result.catch(() => undefined);
  return result;
}
