import {
  obtenerEstacionesSmn,
  obtenerGeometriasEstados,
  obtenerGeometriasMunicipios,
} from "../../application/services/geometrias.service.js";

export class GeometriasController {
  async estados(req, res) {
    try {
      const data = await obtenerGeometriasEstados();
      res.json(data);
    } catch (error) {
      res.status(error.statusCode || 502).json({ error: error.message });
    }
  }

  async municipios(req, res) {
    try {
      const data = await obtenerGeometriasMunicipios(req.query.cve_ent);
      res.json(data);
    } catch (error) {
      res.status(error.statusCode || 502).json({ error: error.message });
    }
  }

  async smn(req, res) {
    try {
      const data = await obtenerEstacionesSmn();
      res.json(data);
    } catch (error) {
      res.status(error.statusCode || 502).json({ error: error.message });
    }
  }
}
