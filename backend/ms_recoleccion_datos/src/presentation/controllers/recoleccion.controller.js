import { RecoleccionService } from "../../application/services/recoleccion.services.js";

const service = new RecoleccionService();

export class RecoleccionController {
  async listarFuentes(req, res) {
    try {
      const data = await service.listarFuentes();
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async obtenerArchivosFuente(req, res) {
    try {
      const { fuente } = req.params;
      const data = await service.obtenerArchivosFuente(fuente);
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async obtenerArchivo(req, res) {
    try {
      const { fuente, nombreArchivo } = req.params;
      const data = await service.obtenerArchivo(fuente, nombreArchivo);
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }
}