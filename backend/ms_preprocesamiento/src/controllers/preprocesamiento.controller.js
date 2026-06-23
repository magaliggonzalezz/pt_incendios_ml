import { PreprocesamientoService } from "../services/preprocesamiento.service.js";

const service = new PreprocesamientoService();

export class PreprocesamientoController {
  async listarFuentes(req, res) {
    try {
      const data = await service.listarFuentes();
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async obtenerReportes(req, res) {
    try {
      const { fuente } = req.params;
      const data = await service.obtenerArchivos(fuente, "reports");
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async obtenerScripts(req, res) {
    try {
      const { fuente } = req.params;
      const data = await service.obtenerArchivos(fuente, "scripts");
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }
}