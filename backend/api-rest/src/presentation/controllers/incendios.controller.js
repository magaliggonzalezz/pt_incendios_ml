 import { IncendiosService } from "../../application/services/incendios.services.js";

const incendiosService = new IncendiosService();

export class IncendiosController {
  async obtenerTodos(req, res) {
    try {
      const incendios = await incendiosService.obtenerIncendios();
      res.status(200).json(incendios);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async obtenerPorId(req, res) {
    try {
      const { id } = req.params;
      const incendio = await incendiosService.obtenerIncendioPorId(id);

      if (!incendio) {
        return res.status(404).json({ error: "Incendio no encontrado" });
      }

      res.status(200).json(incendio);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async crear(req, res) {
    try {
      const nuevoIncendio = await incendiosService.crearIncendio(req.body);
      res.status(201).json(nuevoIncendio);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async actualizar(req, res) {
    try {
      const { id } = req.params;
      const incendioActualizado = await incendiosService.actualizarIncendio(id, req.body);

      if (!incendioActualizado) {
        return res.status(404).json({ error: "Incendio no encontrado" });
      }

      res.status(200).json(incendioActualizado);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async eliminar(req, res) {
    try {
      const { id } = req.params;
      const incendioEliminado = await incendiosService.eliminarIncendio(id);

      if (!incendioEliminado) {
        return res.status(404).json({ error: "Incendio no encontrado" });
      }

      res.status(200).json({ mensaje: "Incendio eliminado correctamente" });
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async buscarConFiltros(req, res) {
    try {
      const incendios = await incendiosService.buscarConFiltros(req.query);
      res.status(200).json(incendios);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async obtenerParaMapa(req, res) {
    try {
      const incendios = await incendiosService.obtenerIncendiosParaMapa();
      res.status(200).json(incendios);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }
}