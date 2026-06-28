import { HotspotModel } from "../models/HotspotModel.js";

export class MongoHotspotRepository {
  async crearMuchos(registros) {
    return await HotspotModel.insertMany(registros, {
      ordered: false,
    });
  }

  async eliminarPorFuente(fuente) {
    return await HotspotModel.deleteMany({ fuente });
  }

  async obtenerParaMapa(filtros = {}) {
    const query = {};

    if (filtros.estado) {
      query.estado = { $regex: filtros.estado, $options: "i" };
    }

    if (filtros.municipio) {
      query.municipio = { $regex: filtros.municipio, $options: "i" };
    }

    if (filtros.anio) {
      query.anio = Number(filtros.anio);
    }

    if (filtros.confidence) {
      query.confidence = { $regex: filtros.confidence, $options: "i" };
    }

    return await HotspotModel.find(query)
      .select(
        "anio estado municipio confidence totalHotspots frpPromedio brightnessPromedio latitudPromedio longitudPromedio ubicacion fuente"
      )
      .limit(5000);
  }
}