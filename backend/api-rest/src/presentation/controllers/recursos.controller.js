import {
  obtenerConfiguracionRecursos,
  obtenerExportacionesPorAnio,
} from "../../application/services/recursos.service.js";

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
}
