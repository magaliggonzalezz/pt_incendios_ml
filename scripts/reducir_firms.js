import fs from "fs";
import path from "path";
import readline from "readline";

const entrada = path.resolve("data-import/firms_original");
const salida = path.resolve("data-import/firms_reducido");

const columnasConservar = [
  "latitude",
  "longitude",
  "fecha",
  "acq_time",
  "satellite",
  "instrument",
  "confidence",
  "brightness",
  "frp",
  "daynight",
  "anio",
  "estado",
  "municipio",
  "cvegeo"
];

if (!fs.existsSync(salida)) {
  fs.mkdirSync(salida, { recursive: true });
}

function parseCSVLine(linea) {
  const resultado = [];
  let actual = "";
  let dentroComillas = false;

  for (let i = 0; i < linea.length; i++) {
    const char = linea[i];

    if (char === '"') {
      dentroComillas = !dentroComillas;
    } else if (char === "," && !dentroComillas) {
      resultado.push(actual);
      actual = "";
    } else {
      actual += char;
    }
  }

  resultado.push(actual);
  return resultado;
}

async function reducirArchivo(nombreArchivo) {
  const rutaEntrada = path.join(entrada, nombreArchivo);
  const rutaSalida = path.join(salida, nombreArchivo);

  const lector = readline.createInterface({
    input: fs.createReadStream(rutaEntrada),
    crlfDelay: Infinity
  });

  const escritor = fs.createWriteStream(rutaSalida, { encoding: "utf-8" });

  let indices = [];
  let esPrimeraLinea = true;
  let filas = 0;

  for await (const linea of lector) {
    if (!linea.trim()) continue;

    const valores = parseCSVLine(linea);

    if (esPrimeraLinea) {
      const headers = valores.map((h) => h.trim());
      indices = columnasConservar.map((col) => headers.indexOf(col));

      escritor.write(columnasConservar.join(",") + "\n");
      esPrimeraLinea = false;
      continue;
    }

    const filaReducida = indices.map((idx) => {
      const valor = idx >= 0 ? valores[idx] ?? "" : "";
      return valor.includes(",") ? `"${valor}"` : valor;
    });

    const confidenceIndex = columnasConservar.indexOf("confidence");
    const confidenceValue = filaReducida[confidenceIndex]?.toLowerCase();

    if (confidenceValue === "low") {
    continue;
    }

    escritor.write(filaReducida.join(",") + "\n");
    filas++;
  }

  escritor.end();

  console.log(`Listo: ${nombreArchivo} | filas: ${filas}`);
}

async function main() {
  console.log("Carpeta entrada:", entrada);
  console.log("Carpeta salida:", salida);
  const archivos = fs
    .readdirSync(entrada)
    .filter((archivo) => archivo.endsWith(".csv"));

  for (const archivo of archivos) {
    await reducirArchivo(archivo);
  }

  console.log("Proceso terminado.");
}

main();