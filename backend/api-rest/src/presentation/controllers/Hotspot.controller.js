 import { HotspotService } from "../../application/services/hotspot.service.js";

const hotspotService = new HotspotService();

export class HotspotController {
  async obtenerTodos(req, res) {
    try {
      const hotspot = await hotspotService.obtenerHotspot();
      res.status(200).json(hotspot);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async obtenerPorId(req, res) {
    try {
      const { id } = req.params;
      const hotspot = await hotspotService.obtenerHotspotPorId(id);

      if (!hotspot) {
        return res.status(404).json({ error: "Hotspot no encontrado" });
      }

      res.status(200).json(hotspot);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async crear(req, res) {
    try {
      const nuevoHotspot = await hotspotService.crearHotspot(req.body);
      res.status(201).json(nuevoHotspot);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async actualizar(req, res) {
    try {
      const { id } = req.params;
      const hotspotActualizado = await hotspotService.actualizarHotspot(id, req.body);

      if (!hotspotActualizado) {
        return res.status(404).json({ error: "Hotspot no encontrado" });
      }

      res.status(200).json(hotspotActualizado);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async eliminar(req, res) {
    try {
      const { id } = req.params;
      const hotspotEliminado = await hotspotService.eliminarHotspot(id);

      if (!HotspotEliminado) {
        return res.status(404).json({ error: "Hotspot no encontrado" });
      }

      res.status(200).json({ mensaje: "Hotspot eliminado correctamente" });
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async buscarConFiltros(req, res) {
    try {
      const hotspot = await hotspotService.buscarConFiltros(req.query);
      res.status(200).json(hotspot);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }
}