 import { AreaInteresService} from "../../application/services/areaInteres.services.js";

const areaInteresService = new AreaInteresService();

export class AreaController {
  async obtenerTodos(req, res) {
    try {
      const area = await areaInteresService.obtenerAreaInteres();
      res.status(200).json(area);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }
 
 async obtenerPorNombre(req, res) {
  try {
    const { nombre } = req.params;

    const data = await areaInteresService.obtenerPorNombre(nombre);

    res.status(200).json(data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
}

  async obtenerPorId(req, res) {
    try {
      const { id } = req.params;
      const area = await areaInteresService.obtenerAreaPorId(id);

      if (!area) {
        return res.status(404).json({ error: "Area de Interes no encontrada" });
      }

      res.status(200).json(area);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async crear(req, res) {
    try {
      const nuevoArea = await areaInteresService.crearArea(req.body);
      res.status(201).json(nuevoArea);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async actualizar(req, res) {
    try {
      const { id } = req.params;
      const areaActualizado = await areaInteresService.actualizarArea(id, req.body);

      if (!AreaActualizada) {
        return res.status(404).json({ error: "Area de Interes no encontrado" });
      }

      res.status(200).json(AreaActualizado);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async buscarConFiltros(req, res) {
    try {
      const area = await areaInteresService.buscarConFiltros(req.query);
      res.status(200).json(area);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async obtenerParaMapa(req, res) {
    try {
      const area = await areaInteresService.obtenerAreaParaMapa();
      res.status(200).json(area);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }
}