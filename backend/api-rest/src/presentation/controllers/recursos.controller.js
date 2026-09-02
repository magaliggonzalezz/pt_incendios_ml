import { obtenerConfiguracionRecursos } from "../../application/services/recursos.service.js";
import { inspeccionarMunicipioDia2025 } from "../../application/services/parquet-r2.service.js";
import {
  descargarObjetoR2,
  obtenerMetadataObjetoR2,
  obtenerObjetoR2Stream,
} from "../../data/storage/r2.js";

const RELIEVE_MDE_PREFIX = "capas_web/inegi/relieve_mde";
const ELEVACION_MDE_PREFIX = "capas_web/inegi/elevacion_mde";
const MDE_ZOOM_MIN = 4;
const MDE_ZOOM_MAX = 10;

function parseTileCoordinate(value) {
  const number = Number(value);
  return Number.isInteger(number) ? number : null;
}

function sendR2Error(res, error) {
  const statusCode = error?.$metadata?.httpStatusCode || error.statusCode || 500;
  res.status(statusCode === 404 ? 404 : statusCode).json({ error: error.message });
}

async function sendManifest(res, prefix) {
  try {
    const bytes = await descargarObjetoR2(`${prefix}/manifest.json`);
    res.json(JSON.parse(bytes.toString("utf-8")));
  } catch (error) {
    sendR2Error(res, error);
  }
}

async function sendMdeTile(req, res, prefix) {
  const z = parseTileCoordinate(req.params.z);
  const x = parseTileCoordinate(req.params.x);
  const y = parseTileCoordinate(req.params.y);

  if (z === null || x === null || y === null || z < MDE_ZOOM_MIN || z > MDE_ZOOM_MAX) {
    return res.status(400).json({ error: `Tile MDE inválido. Zoom permitido: ${MDE_ZOOM_MIN}-${MDE_ZOOM_MAX}` });
  }

  const maxCoordinate = 2 ** z;
  if (x < 0 || y < 0 || x >= maxCoordinate || y >= maxCoordinate) {
    return res.status(400).json({ error: "Coordenadas XYZ fuera de rango" });
  }

  try {
    const objeto = await obtenerObjetoR2Stream(`${prefix}/${z}/${x}/${y}.png`);

    res.setHeader("Content-Type", objeto.contentType || "image/png");
    res.setHeader("Cache-Control", "public, max-age=86400, immutable");
    if (objeto.bytes !== null) res.setHeader("Content-Length", String(objeto.bytes));
    if (objeto.etag) res.setHeader("ETag", objeto.etag);
    if (objeto.ultimaModificacion) res.setHeader("Last-Modified", objeto.ultimaModificacion);

    objeto.body.on?.("error", (error) => {
      console.error("Error transmitiendo tile MDE desde R2:", error);
      res.destroy(error);
    });
    objeto.body.pipe(res);
  } catch (error) {
    sendR2Error(res, error);
  }
}

export class RecursosController {
  configuracion(req, res) {
    try {
      res.json(obtenerConfiguracionRecursos());
    } catch (error) {
      res.status(error.statusCode || 500).json({ error: error.message });
    }
  }

  async diagnosticoR2(req, res) {
    try {
      const key = "resultados/municipio_dia/app_municipio_dia_resultados_2025.parquet";
      const objeto = await obtenerMetadataObjetoR2(key);

      res.json({
        ok: true,
        mensaje: "La API REST puede acceder al objeto de prueba en Cloudflare R2",
        objeto,
      });
    } catch (error) {
      res.status(error.statusCode || 500).json({
        ok: false,
        error: error.message,
      });
    }
  }

  async inspeccionParquetR2(req, res) {
    try {
      res.json(await inspeccionarMunicipioDia2025());
    } catch (error) {
      console.error("Error inspeccionando Parquet en R2:", error);
      res.status(error.statusCode || 500).json({
        ok: false,
        error: error.message,
      });
    }
  }

  async manifestRelieveMde(req, res) {
    return sendManifest(res, RELIEVE_MDE_PREFIX);
  }

  async tileRelieveMde(req, res) {
    return sendMdeTile(req, res, RELIEVE_MDE_PREFIX);
  }

  async manifestElevacionMde(req, res) {
    return sendManifest(res, ELEVACION_MDE_PREFIX);
  }

  async tileElevacionMde(req, res) {
    return sendMdeTile(req, res, ELEVACION_MDE_PREFIX);
  }
}
