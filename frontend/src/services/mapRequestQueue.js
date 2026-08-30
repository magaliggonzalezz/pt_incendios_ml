const RESPONSE_CACHE_TTL_MS = 10 * 60 * 1000;

const responseCache = new Map();
const inFlight = new Map();
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

function waitForShared(promise, signal) {
  if (!signal) return promise;
  if (signal.aborted) return Promise.reject(createAbortError());

  return new Promise((resolve, reject) => {
    const onAbort = () => reject(createAbortError());
    signal.addEventListener("abort", onAbort, { once: true });
    promise.then(
      (value) => {
        signal.removeEventListener("abort", onAbort);
        if (signal.aborted) reject(createAbortError());
        else resolve(value);
      },
      (error) => {
        signal.removeEventListener("abort", onAbort);
        reject(error);
      },
    );
  });
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

  const existing = inFlight.get(key);
  if (existing) return waitForShared(existing, signal);

  const execute = async () => {
    if (signal?.aborted) throw createAbortError();

    // No propagamos AbortSignal al fetch real: una vez que Node empieza a procesar
    // GeoJSON/Parquet, cancelar el navegador no detiene ese CPU. La cola evita que
    // una nueva operación pesada se ejecute en paralelo y la deduplicación evita
    // repetir el mismo trabajo mientras ya está en curso.
    const value = await request();
    if (cache) setCached(key, value);
    return value;
  };

  const shared = requestQueue.then(execute, execute);
  inFlight.set(key, shared);
  requestQueue = shared.catch(() => undefined);

  shared.finally(() => {
    if (inFlight.get(key) === shared) inFlight.delete(key);
  });

  return waitForShared(shared, signal);
}
