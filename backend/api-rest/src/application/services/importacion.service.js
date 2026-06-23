import { obtenerResultadosML } from "../../data/clients/analisisMl.client.js";
import { MongoAnalisisMLRepository } from "../../data/repositories/MongoAnalisisMLRepository.js";
import fs from "fs";
import path from "path";
import { parse } from "csv-parse";
import { MongoIncendioRepository } from "../../data/repositories/MongoIncendioRepository.js";

const analisisMLRepository = new MongoAnalisisMLRepository();
const incendioRepository = new MongoIncendioRepository();

// AQUÍ VAN LAS FUNCIONES AUXILIARES
function limpiarValor(valor) {
  if (valor === undefined || valor === null || valor === "") return null;
  return String(valor).trim();
}

function numero(valor) {
  if (valor === undefined || valor === null || valor === "") return null;

  const n = Number(String(valor).replace(",", "."));
  return Number.isNaN(n) ? null : n;
}

function formatearHora(valor) {
  if (!valor) return null;

  const texto = String(valor).trim();

  if (/^\d{1,2}:\d{2}:\d{2}$/.test(texto)) {
    const [h, m, s] = texto.split(":");
    return `${h.padStart(2, "0")}:${m}:${s}`;
  }

  if (/^\d{1,2}:\d{2}$/.test(texto)) {
    const [h, m] = texto.split(":");
    return `${h.padStart(2, "0")}:${m}:00`;
  }

  return texto;
}

function parseFecha(valor) {
  if (!valor) return null;

  const texto = String(valor).trim();

  if (/^\d{4}-\d{2}-\d{2}$/.test(texto)) {
    return new Date(`${texto}T00:00:00`);
  }

  return new Date(texto);
}

export class ImportacionService {
  async importarResultadosML() {
    const resultados = await obtenerResultadosML();

    const documentos = [];

    const archivos = resultados.archivos || [];

    for (const archivo of archivos) {
      documentos.push({
        tipoAnalisis: "resultado_ml",
        algoritmo: "pipeline_ml",
        periodo: {
          inicio: 2001,
          fin: 2025
        },
        fuente: "ml-pipeline",
        archivoOrigen: archivo.nombre || archivo,
        resultado: archivo
      });
    }

    const guardados = [];

    for (const doc of documentos) {
      const creado = await analisisMLRepository.crear(doc);
      guardados.push(creado);
    }

    return {
      mensaje: "Resultados ML importados correctamente",
      totalArchivos: archivos.length,
      totalGuardados: guardados.length,
      guardados
    };
  }

 async importarIncendiosConaforCSV() {
  const carpetaCSV = path.resolve(
    process.cwd(),
    "../../data-import/conafor"
  );

  const archivos = await fs.promises.readdir(carpetaCSV);

  const csvFiles = archivos.filter((archivo) =>
    archivo.endsWith(".csv")
  );

  let totalProcesados = 0;
  let totalGuardados = 0;
  const archivosProcesados = [];
  
  await incendioRepository.eliminarPorFuente("CONAFOR");

  for (const archivo of csvFiles) {
    const rutaArchivo = path.join(carpetaCSV, archivo);
    const registros = [];

    await new Promise((resolve, reject) => {
      fs.createReadStream(rutaArchivo)
        .pipe(
          parse({
            columns: true,
            skip_empty_lines: true,
            trim: true
          })
        )
        .on("data", (row) => {
          const latitud = Number(row.latitud);
          const longitud = Number(row.longitud);

          if (!latitud || !longitud) return;

          registros.push({
          claveIncendio: limpiarValor(row.clave_incendio),
          anio: numero(row.anio),

          fechaInicio: parseFecha(row.fecha_inicio),
          fechaTermino: parseFecha(row.fecha_termino),

          estado: limpiarValor(row.estado),
          municipio: limpiarValor(row.municipio),

          cveEnt: limpiarValor(row.cve_ent),
          cveMun: limpiarValor(row.cve_mun),
          cvegeo: limpiarValor(row.cvegeo),

          latitud,
          longitud,

          ubicacion: {
          type: "Point",
          coordinates: [longitud, latitud],
           },

          region: limpiarValor(row.region),
          predio: limpiarValor(row.predio),

          causa: limpiarValor(row.causa),
          causaEspecifica: limpiarValor(row.causa_especifica),

          tipoIncendio: limpiarValor(row.tipo_incendio),
          tipoImpacto: limpiarValor(row.tipo_impacto),
          tipoVegetacion: limpiarValor(row.tipo_vegetacion),
          regimenFuego: limpiarValor(row.regimen_fuego),

          superficie: numero(row.superficie_total_ha),
          superficieCategoria: limpiarValor(row.superficie_categoria),

          arboladoAdulto: numero(row.arbolado_adulto),
          arbustivo: numero(row.arbustivo),
          herbaceo: numero(row.herbaceo),
          hojarasca: numero(row.hojarasca),
          renuevo: numero(row.renuevo),

          duracion: formatearHora(row.duracion),
          deteccion: formatearHora(row.deteccion),
          llegada: formatearHora(row.llegada),

          fuente: "CONAFOR",
          archivoOrigen: archivo,
          });
          totalProcesados++;
        })
        .on("end", resolve)
        .on("error", reject);
    });

    if (registros.length > 0) {
      const guardados = await incendioRepository.crearMuchos(registros);
      totalGuardados += guardados.length;
    }

    archivosProcesados.push({
      archivo,
      registrosLeidos: registros.length
    });
  }

  return {
    mensaje: "Incendios CONAFOR importados correctamente",
    archivosProcesados: csvFiles.length,
    detalleArchivos: archivosProcesados,
    totalProcesados,
    totalGuardados
  };
}
}