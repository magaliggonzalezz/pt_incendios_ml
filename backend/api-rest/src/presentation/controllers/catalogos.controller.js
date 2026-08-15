import { CatalogosService } from "../../application/services/catalogos.service.js";

const service = new CatalogosService();

function esCveEntidadValida(value) {
  return /^\d{2}$/.test(value);
}

export class CatalogosController {
  async obtenerClusters(req, res) {
    try {
      const data = await service.obtenerClusters();
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async obtenerEstados(req, res) {
    try {
      const data = await service.obtenerEstados();
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async obtenerMunicipios(req, res) {
    try {
      const { cve_ent: cveEnt } = req.query;

      if (cveEnt && !esCveEntidadValida(cveEnt)) {
        return res.status(400).json({
          error: "cve_ent debe tener exactamente 2 dígitos, por ejemplo 01",
        });
      }

      const data = await service.obtenerMunicipios(cveEnt);
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }
}
