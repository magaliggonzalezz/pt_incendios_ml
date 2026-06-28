import fs from "fs";
import path from "path";
import readline from "readline";

const entrada = path.resolve("data-import/firms_original/firms_detecciones.csv");
const salida = path.resolve("data-import/firms_reducido/firms_agregado.csv");

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

function limpiar(valor) {
  return String(valor ?? "").trim().replaceAll('"', "");
}

function numero(valor) {
  const n = Number(String(valor ?? "").replace(",", "."));
  return Number.isNaN(n) ? 0 : n;
}

function categoriaDominante(contador) {
  let dominante = "";
  let max = -1;

  for (const [categoria, total] of Object.entries(contador)) {
    if (total > max) {
      dominante = categoria;
      max = total;
    }
  }

  return dominante || null;
}

async function main() {
  console.log("Archivo entrada:", entrada);
  console.log("Archivo salida:", salida);

  const grupos = new Map();

  const lector = readline.createInterface({
    input: fs.createReadStream(entrada),
    crlfDelay: Infinity,
  });

  let headers = [];
  let primeraLinea = true;
  let filasLeidas = 0;

  for await (const linea of lector) {
    if (!linea.trim()) continue;

    const valores = parseCSVLine(linea);

    if (primeraLinea) {
      headers = valores.map((h) => limpiar(h));
      primeraLinea = false;
      continue;
    }

    const row = {};
    headers.forEach((h, i) => {
      row[h] = valores[i] ?? "";
    });

    const anio = limpiar(row.anio);
    const estado = limpiar(row.estado);
    const municipio = limpiar(row.municipio);

    const latitude = numero(row.latitude);
    const longitude = numero(row.longitude);
    const confidence = numero(row.confidence);
    const confidenceCategory = limpiar(row.confidence_category);

    const frp = numero(row.frp);
    const brightness = numero(row.brightness);

    if (!anio || !estado || !municipio) continue;
    if (!latitude || !longitude) continue;

    const clave = `${anio}|${estado}|${municipio}`;

    if (!grupos.has(clave)) {
      grupos.set(clave, {
        anio,
        estado,
        municipio,
        totalHotspots: 0,

        confidenceTotal: 0,
        confidenceCategorias: {},

        frpTotal: 0,
        frpMaximo: 0,

        brightnessTotal: 0,
        brightnessMaximo: 0,

        latTotal: 0,
        lonTotal: 0,
      });
    }

    const grupo = grupos.get(clave);

    grupo.totalHotspots += 1;

    grupo.confidenceTotal += confidence;

    if (confidenceCategory) {
      grupo.confidenceCategorias[confidenceCategory] =
        (grupo.confidenceCategorias[confidenceCategory] || 0) + 1;
    }

    grupo.frpTotal += frp;
    grupo.frpMaximo = Math.max(grupo.frpMaximo, frp);

    grupo.brightnessTotal += brightness;
    grupo.brightnessMaximo = Math.max(grupo.brightnessMaximo, brightness);

    grupo.latTotal += latitude;
    grupo.lonTotal += longitude;

    filasLeidas++;
  }

  const escritor = fs.createWriteStream(salida, { encoding: "utf-8" });

  escritor.write(
    "anio,estado,municipio,totalHotspots,confidencePromedio,confidenceCategoriaDominante,frpPromedio,frpMaximo,brightnessPromedio,brightnessMaximo,latitudPromedio,longitudPromedio\n"
  );

  for (const grupo of grupos.values()) {
    const total = grupo.totalHotspots;

    const confidencePromedio = grupo.confidenceTotal / total;
    const confidenceCategoriaDominante = categoriaDominante(
      grupo.confidenceCategorias
    );

    const frpPromedio = grupo.frpTotal / total;
    const brightnessPromedio = grupo.brightnessTotal / total;

    const latitudPromedio = grupo.latTotal / total;
    const longitudPromedio = grupo.lonTotal / total;

    escritor.write(
      [
        grupo.anio,
        grupo.estado,
        grupo.municipio,
        total,
        confidencePromedio.toFixed(2),
        confidenceCategoriaDominante,
        frpPromedio.toFixed(2),
        grupo.frpMaximo.toFixed(2),
        brightnessPromedio.toFixed(2),
        grupo.brightnessMaximo.toFixed(2),
        latitudPromedio.toFixed(6),
        longitudPromedio.toFixed(6),
      ].join(",") + "\n"
    );
  }

  escritor.end();

  console.log("Archivo FIRMS agregado generado correctamente.");
  console.log("Filas leídas:", filasLeidas);
  console.log("Total de grupos:", grupos.size);
}

main();