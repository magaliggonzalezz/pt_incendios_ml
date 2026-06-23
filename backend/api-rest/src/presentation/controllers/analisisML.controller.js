import mongoose from "mongoose";
import { AnalisisMLService } from "../../application/services/analisisML.services.js";

const service = new AnalisisMLService();

export class AnalisisMLController {
  async obtenerTodos(req, res) {
    try {
      const data = await service.obtenerTodos();
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

      const data = await service.obtenerPorId(id);

      if (!data) {
        return res.status(404).json({ error: "Análisis ML no encontrado" });
      }

      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async crear(req, res) {
    try {
      const data = await service.crear(req.body);
      res.status(201).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async eliminar(req, res) {
    try {
      const { id } = req.params;

      if (!mongoose.Types.ObjectId.isValid(id)) {
        return res.status(400).json({ error: "Id no válido" });
      }

      const data = await service.eliminar(id);

      if (!data) {
        return res.status(404).json({ error: "Análisis ML no encontrado" });
      }

      res.status(200).json({ mensaje: "Análisis ML eliminado correctamente" });
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