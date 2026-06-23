import fs from "fs/promises";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export class PreprocesamientoService {
  constructor() {
    this.basePath = path.resolve(
      __dirname,
      "../../../../ml-pipeline/03_data-preparation"
    );
  } 

  async listarFuentes() {
    const carpetas = await fs.readdir(this.basePath, { withFileTypes: true });

    return {
      tipo: "fuentes_preprocesamiento",
      ruta: this.basePath,
      fuentes: carpetas
        .filter((item) => item.isDirectory())
        .map((item) => item.name)
    };
  }

  async obtenerArchivos(fuente, tipoCarpeta) {
    const ruta = path.resolve(this.basePath, fuente, tipoCarpeta);
    const archivos = await fs.readdir(ruta);

    return {
      fuente,
      tipo: tipoCarpeta,
      ruta,
      totalArchivos: archivos.length,
      archivos
    };
  }
}