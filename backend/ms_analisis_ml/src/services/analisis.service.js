import fs from "fs/promises";
import path from "path";

export class AnalisisService {
  async listarArchivos(carpeta) {
    const ruta = path.resolve(carpeta);
    const archivos = await fs.readdir(ruta);

    return archivos.map((archivo) => ({
      nombre: archivo,
      ruta: path.join(ruta, archivo)
    }));
  }

  async obtenerResultados() {
    const resultsPath = process.env.ML_RESULTS_PATH;

    if (!resultsPath) {
      throw new Error("ML_RESULTS_PATH no está definido");
    }

    const archivos = await this.listarArchivos(resultsPath);

    return {
      tipo: "resultados_ml",
      totalArchivos: archivos.length,
      archivos
    };
  }

  async obtenerReportes() {
    const reportsPath = process.env.ML_REPORTS_PATH;

    if (!reportsPath) {
      throw new Error("ML_REPORTS_PATH no está definido");
    }

    const archivos = await this.listarArchivos(reportsPath);

    return {
      tipo: "reportes_ml",
      totalArchivos: archivos.length,
      archivos
    };
  }
}