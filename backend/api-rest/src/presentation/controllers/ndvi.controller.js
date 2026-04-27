import mongoose from "mongoose";
import { NDVIService } from "../../application/services/ndvi.service.js";

const service = new NDVIService();

export class NDVIController {

  async obtenerTodos(req, res) {
    try {
      const data = await service.obtenerNDVI();
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async obtenerPorId(req, res) {
    try {
      const { id } = req.params;

      if (!mongoose.Types.ObjectId.isValid(id)) {
        return res.status(400).json({ error: "Id no válido" });
      }

      const data = await service.obtenerNDVIPorId(id);

      if (!data) {
        return res.status(404).json({ error: "NDVI no encontrado" });
      }

      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async crear(req, res) {
    try {
      const data = await service.crearNDVI(req.body);
      res.status(201).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async buscarConFiltros(req, res) {
    try {
      const data = await service.buscarConFiltros(req.query);
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }
}