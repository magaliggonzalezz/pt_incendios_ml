import mongoose from "mongoose";
import { SesionesAnalisisService } from "../../application/services/sesionesAnalisis.service.js";

const service = new SesionesAnalisisService();

export class SesionesAnalisisController {

  async obtenerTodos(req, res) {
    try {
      const data = await service.obtenerSesiones();
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

      const data = await service.obtenerSesionPorId(id);

      if (!data) {
        return res.status(404).json({ error: "Sesión no encontrada" });
      }

      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async crear(req, res) {
    try {
      const data = await service.crearSesion(req.body);
      res.status(201).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async actualizar(req, res) {
    try {
      const { id } = req.params;

      const data = await service.actualizarSesion(id, req.body);

      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async eliminar(req, res) {
    try {
      const { id } = req.params;

      await service.eliminarSesion(id);

      res.status(200).json({ mensaje: "Sesión eliminada" });
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