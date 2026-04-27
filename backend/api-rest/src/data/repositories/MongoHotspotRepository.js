import { HotspotModel } from "../models/HotspotModel.js";

export class MongoHotspotRepository {
  async obtenerTodos() {
    return await HotspotModel.find().sort({ fecha: -1 });
  }

  async obtenerPorId(id) {
    return await HotspotModel.findById(id);
  }

  async crear(datos) {
    return await HotspotModel.create(datos);
  }

  async actualizar(id, datos) {
    return await HotspotModel.findByIdAndUpdate(id, datos, { new: true });
  }

  async eliminar(id) {
    return await HotspotModel.findByIdAndDelete(id);
  }

  async buscarConFiltros(filtros) {
    const query = {};

    if (filtros.ubicacion) query.ubicacion = filtros.ubicacion;
    if (filtros.temperatura) query.temperatura = filtros.temperatura;
  

    if (filtros.fechaDesde || filtros.fechaHasta) {
      query.fecha = {};
      if (filtros.fechaDesde) query.fecha.$gte = new Date(filtros.fechaDesde);
      if (filtros.fechaHasta) query.fecha.$lte = new Date(filtros.fechaHasta);
    }

    return await HotspotModel.find(query).sort({ fecha: -1 });
  }
}