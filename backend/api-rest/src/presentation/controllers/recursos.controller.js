import {
  obtenerConfiguracionRecursos,
  obtenerExportacionesPorAnio,
} from "../../application/services/recursos.service.js";
import { inspeccionarMunicipioDia2025 } from "../../application/services/parquet-r2.service.js";
import { obtenerMetadataObjetoR2 } from "../../data/storage/r2.js";

export class RecursosController {
  configuracion(req, res) {
    try {
      res.json(obtenerConfiguracionRecursos());
    } catch (error) {
      res.status(error.statusCode || 500).json({ error: error.message });
    }
  }

  exportaciones(req, res) {
    try {
      res.json(obtenerExportacionesPorAnio(req.query.anio));
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
}
