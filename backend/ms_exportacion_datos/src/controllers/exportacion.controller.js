import { ExportacionService } from "../services/exportacion.service.js";

const service = new ExportacionService();

export class ExportacionController {
  async exportarJSON(req, res) {
    try {
      const resultado = await service.exportarJSON(req.body);
      res.status(201).json(resultado);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async exportarCSV(req, res) {
    try {
      const resultado = await service.exportarCSV(req.body);
      res.status(201).json(resultado);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async listarArchivos(req, res) {
    try {
      const archivos = await service.listarArchivos();
      res.status(200).json(archivos);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async descargarArchivo(req, res) {
  try {
    const { nombreArchivo } = req.params;
    const filePath = await service.obtenerRutaArchivo(nombreArchivo);

    res.download(filePath, nombreArchivo);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
}
}