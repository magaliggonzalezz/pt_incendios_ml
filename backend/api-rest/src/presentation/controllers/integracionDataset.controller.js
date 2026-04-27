import { IntegracionDatasetService } from "../../application/services/integracionDataset.service.js";

const service = new IntegracionDatasetService();

export class IntegracionDatasetController {
  async procesar(req, res) {
    try {
      const data = await service.procesarDataset(req.body);
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }
}