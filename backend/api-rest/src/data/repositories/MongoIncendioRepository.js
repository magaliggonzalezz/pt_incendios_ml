import { IncendioModel } from "../models/IncendioModel.js";

export class MongoIncendioRepository {
  async obtenerTodos() {
    return await IncendioModel.find().sort({ fecha: -1 });
  }

  async obtenerPorId(id) {
    return await IncendioModel.findById(id);
  }

  async crear(datos) {
    return await IncendioModel.create(datos);
  }

  async actualizar(id, datos) {
    return await IncendioModel.findByIdAndUpdate(id, datos, { new: true });
  }

  async eliminar(id) {
    return await IncendioModel.findByIdAndDelete(id);
  }

  async buscarConFiltros(filtros) {
    const query = {};

    if (filtros.region) query.region = filtros.region;
    if (filtros.causa) query.causa = filtros.causa;
    if (filtros.estado) query.estado = filtros.estado;
    if (filtros.municipio) query.municipio = filtros.municipio;

    if (filtros.fechaDesde || filtros.fechaHasta) {
      query.fecha = {};
      if (filtros.fechaDesde) query.fecha.$gte = new Date(filtros.fechaDesde);
      if (filtros.fechaHasta) query.fecha.$lte = new Date(filtros.fechaHasta);
    }

    return await IncendioModel.find(query).sort({ fecha: -1 });
  }

   async obtenerParaMapa() {
    return await IncendioModel.find(
      {},
      {
        fecha: 1,
        ubicacion: 1,
        superficie: 1,
        causa: 1,
        region: 1,
        estado: 1,
        municipio: 1,
        fuente: 1
      }
    ).sort({ fecha: -1 });
  }
}