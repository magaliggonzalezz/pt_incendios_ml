import {
  obtenerConaforMapa,
  obtenerFirmsMapa,
} from "../../application/services/puntos-mapa.service.js";

export class PuntosMapaController {
  async firms(req, res) {
    try {
      const data = await obtenerFirmsMapa(req.query);
      res.json(data);
    } catch (error) {
      res.status(error.statusCode || 502).json({ error: error.message });
    }
  }

  async conafor(req, res) {
    try {
      const data = await obtenerConaforMapa(req.query);
      res.json(data);
    } catch (error) {
      res.status(error.statusCode || 502).json({ error: error.message });
    }
  }
}
