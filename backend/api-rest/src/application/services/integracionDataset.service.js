import { procesarDatasetEnMicroservicio } from "../../data/clients/preprocesamiento.client.js";
import { MongoDatasetRepository } from "../../data/repositories/MongoDatasetRepository.js";
import { MongoIncendioRepository } from "../../data/repositories/MongoIncendioRepository.js";
import { MongoHotspotRepository } from "../../data/repositories/MongoHotspotRepository.js";
import { MongoNDVIRepository } from "../../data/repositories/MongoNDVIRepository.js";
import { MongoCondicionMeteorologicaRepository } from "../../data/repositories/MongoCondicionMetereologica.js";

const datasetRepository = new MongoDatasetRepository();
const incendioRepository = new MongoIncendioRepository();
const hotspotRepository = new MongoHotspotRepository();
const ndviRepository = new MongoNDVIRepository();
const condicionMeteorologicaRepository = new MongoCondicionMeteorologicaRepository();

export class IntegracionDatasetService {
  async procesarDataset(payload) {
    const { dataset, registros } = payload;

    if (!dataset || !Array.isArray(registros)) {
      throw new Error("Se requiere un objeto dataset y un arreglo de registros");
    }

    // 1. Registrar metadatos del dataset
    const datasetGuardado = await datasetRepository.crear(dataset);

    // 2. Enviar registros al microservicio Python
    const resultadoPreprocesamiento = await procesarDatasetEnMicroservicio({
      datasetId: datasetGuardado._id.toString(),
      registros
    });

    // 3. Persistir registros procesados según su tipo
    let totalInsertados = 0;
    const resumen = {
      incendios: 0,
      hotspots: 0,
      ndvi: 0,
      condiciones_meteorologicas: 0,
      desconocidos: 0
    };

    for (const item of resultadoPreprocesamiento.registros) {
      const { tipo, procesado } = item;

      if (!procesado) {
        resumen.desconocidos += 1;
        continue;
      }

      const documentoConDataset = {
        ...procesado,
        datasetId: datasetGuardado._id
      };

      if (tipo === "incendio") {
        await incendioRepository.crear(documentoConDataset);
        resumen.incendios += 1;
        totalInsertados += 1;
      } else if (tipo === "hotspot") {
        await hotspotRepository.crear(documentoConDataset);
        resumen.hotspots += 1;
        totalInsertados += 1;
      } else if (tipo === "ndvi") {
        await ndviRepository.crear(documentoConDataset);
        resumen.ndvi += 1;
        totalInsertados += 1;
      } else if (tipo === "condicion_meteorologica") {
        await condicionMeteorologicaRepository.crear(documentoConDataset);
        resumen.condiciones_meteorologicas += 1;
        totalInsertados += 1;
      } else {
        resumen.desconocidos += 1;
      }
    }

    return {
      mensaje: "Dataset procesado correctamente",
      datasetId: datasetGuardado._id,
      totalRecibidos: registros.length,
      totalInsertados,
      resumen,
      resultadoPreprocesamiento
    };
  }
}