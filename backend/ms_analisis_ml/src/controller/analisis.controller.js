import { AnalisisService } from "../services/analisis.service.js";

const service = new AnalisisService();

export class AnalisisController {
  async obtenerResultados(req, res) {
    try {
      const data = await service.obtenerResultados();
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async obtenerReportes(req, res) {
    try {
      const data = await service.obtenerReportes();
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }
}