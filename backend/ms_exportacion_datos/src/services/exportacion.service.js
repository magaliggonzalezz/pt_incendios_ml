import fs from "fs/promises";
import path from "path";

export class ExportacionService {
  constructor() {
    this.exportsPath = process.env.EXPORTS_PATH || "./exports";
  }

  async asegurarCarpeta() {
    await fs.mkdir(this.exportsPath, { recursive: true });
  }

  async exportarJSON(payload) {
    await this.asegurarCarpeta();

    const { nombre = "exportacion", datos = [] } = payload;
    const fileName = `${nombre}_${Date.now()}.json`;
    const filePath = path.join(this.exportsPath, fileName);

    await fs.writeFile(filePath, JSON.stringify(datos, null, 2), "utf-8");

    return {
      mensaje: "Archivo JSON generado correctamente",
      formato: "JSON",
      archivo: fileName,
      ruta: filePath
    };
  }

  async exportarCSV(payload) {
    await this.asegurarCarpeta();

    const { nombre = "exportacion", datos = [] } = payload;

    if (!Array.isArray(datos) || datos.length === 0) {
      throw new Error("Se requiere un arreglo de datos para exportar");
    }

    const headers = Object.keys(datos[0]);
    const rows = datos.map((item) =>
      headers.map((header) => JSON.stringify(item[header] ?? "")).join(",")
    );

    const csv = [headers.join(","), ...rows].join("\n");

    const fileName = `${nombre}_${Date.now()}.csv`;
    const filePath = path.join(this.exportsPath, fileName);

    await fs.writeFile(filePath, csv, "utf-8");

    return {
      mensaje: "Archivo CSV generado correctamente",
      formato: "CSV",
      archivo: fileName,
      ruta: filePath
    };
  }

  async listarArchivos() {
    await this.asegurarCarpeta();

    const archivos = await fs.readdir(this.exportsPath);

    return {
      total: archivos.length,
      archivos
    };
  }

  obtenerRutaArchivo(nombreArchivo) {
  return path.join(this.exportsPath, nombreArchivo);
}
}