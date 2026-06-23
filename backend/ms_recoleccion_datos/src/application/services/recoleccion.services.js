import fs from "fs/promises";
import path from "path";
import { env } from "../../config/env.js";

export class RecoleccionService {
  constructor() {
    this.basePath = path.resolve(env.dataUnderstandingPath);
  }

  async listarFuentes() {
    const carpetas = await fs.readdir(this.basePath, { withFileTypes: true });

    return {
      tipo: "fuentes_recoleccion",
      ruta: this.basePath,
      fuentes: carpetas
        .filter((item) => item.isDirectory())
        .map((item) => item.name)
    };
  }

  async obtenerArchivosFuente(fuente) {
    const ruta = path.resolve(this.basePath, fuente);
    const archivos = await fs.readdir(ruta);

    return {
      fuente,
      ruta,
      totalArchivos: archivos.length,
      archivos
    };
  }

  async obtenerArchivo(fuente, nombreArchivo) {
    const ruta = path.resolve(this.basePath, fuente, nombreArchivo);
    const contenido = await fs.readFile(ruta, "utf-8");

    return {
      fuente,
      archivo: nombreArchivo,
      ruta,
      contenido
    };
  }
}