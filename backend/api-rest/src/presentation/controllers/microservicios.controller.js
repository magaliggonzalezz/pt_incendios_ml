import { MicroserviciosService } from "../../application/services/microservicios.service.js";

const service = new MicroserviciosService();

export class MicroserviciosController {
  async fuentesPreprocesamiento(req, res) {
    try {
      const data = await service.obtenerFuentesPreprocesamiento();
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async reportesPreprocesamiento(req, res) {
    try {
      const { fuente } = req.params;
      const data = await service.obtenerReportesPreprocesamiento(fuente);
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async scriptsPreprocesamiento(req, res) {
    try {
      const { fuente } = req.params;
      const data = await service.obtenerScriptsPreprocesamiento(fuente);
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async resultadosML(req, res) {
    try {
      const data = await service.obtenerResultadosML();
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async reportesML(req, res) {
    try {
      const data = await service.obtenerReportesML();
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async archivosExportacion(req, res) {
    try {
      const data = await service.listarArchivosExportacion();
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async exportarCSV(req, res) {
    try {
      const data = await service.exportarCSV(req.body);
      res.status(201).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async exportarJSON(req, res) {
    try {
      const data = await service.exportarJSON(req.body);
      res.status(201).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async fuentesRecoleccion(req, res) {
  try {
    const data = await service.obtenerFuentesRecoleccion();
    res.status(200).json(data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
  }

  async archivosRecoleccion(req, res) {
  try {
    const { fuente } = req.params;
    const data = await service.obtenerArchivosRecoleccion(fuente);
    res.status(200).json(data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
  }
}