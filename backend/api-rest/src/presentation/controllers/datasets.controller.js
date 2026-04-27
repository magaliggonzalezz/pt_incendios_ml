import mongoose from "mongoose";
import { DatasetsService } from "../../application/services/datasets.service.js";

const service = new DatasetsService();

export class DatasetsController {
  async obtenerTodos(req, res) {
    try {
      const data = await service.obtenerDatasets();
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

      const data = await service.obtenerDatasetPorId(id);

      if (!data) {
        return res.status(404).json({ error: "Dataset no encontrado" });
      }

      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async crear(req, res) {
    try {
      const data = await service.crearDataset(req.body);
      res.status(201).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async actualizar(req, res) {
    try {
      const { id } = req.params;

      if (!mongoose.Types.ObjectId.isValid(id)) {
        return res.status(400).json({ error: "Id no válido" });
      }

      const data = await service.actualizarDataset(id, req.body);

      if (!data) {
        return res.status(404).json({ error: "Dataset no encontrado" });
      }

      res.status(200).json(data);
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

      const data = await service.eliminarDataset(id);

      if (!data) {
        return res.status(404).json({ error: "Dataset no encontrado" });
      }

      res.status(200).json({ mensaje: "Dataset eliminado correctamente" });
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