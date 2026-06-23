import { ImportacionService } from "../../application/services/importacion.service.js";

const service = new ImportacionService();

export class ImportacionController {
  async importarResultadosML(req, res) {
    try {
      const data = await service.importarResultadosML();
      res.status(201).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async importarIncendiosConafor(req, res) {
  try {
    const data = await service.importarIncendiosConaforCSV();
    res.status(201).json(data);
  } catch (error) {
    res.status(500).json({
      error: error.message
    });
  }
}
}
