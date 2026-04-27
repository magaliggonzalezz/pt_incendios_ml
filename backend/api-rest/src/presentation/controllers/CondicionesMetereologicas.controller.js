import mongoose from "mongoose";
import { CondicionesMeteorologicasService } from "../../application/services/CondicionesMetereologicas.services.js";

const service = new CondicionesMeteorologicasService();

export class CondicionesMeteorologicasController {
  async obtenerTodos(req, res) {
    try {
      const data = await service.obtenerCondicionesMeteorologicas();
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

      const data = await service.obtenerCondicionMeteorologicaPorId(id);

      if (!data) {
        return res.status(404).json({ error: "Condición meteorológica no encontrada" });
      }

      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async crear(req, res) {
    try {
      const data = await service.crearCondicionMeteorologica(req.body);
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