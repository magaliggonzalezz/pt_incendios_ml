import { SesionAnalisisModel } from "../models/SesionAnalisisModel.js";

export class MongoSesionAnalisisRepository {
  async obtenerTodos() {
    return await SesionAnalisisModel.find().sort({ fechaCreacion: -1 });
  }

  async obtenerPorId(id) {
    return await SesionAnalisisModel.findById(id);
  }

  async crear(data) {
    return await SesionAnalisisModel.create(data);
  }

  async actualizar(id, data) {
    return await SesionAnalisisModel.findByIdAndUpdate(id, data, { new: true });
  }

  async eliminar(id) {
    return await SesionAnalisisModel.findByIdAndDelete(id);
  }

  async buscarConFiltros(filtros) {
    const query = {};

    if (filtros.descripcion) {
      query.descripcion = { $regex: filtros.descripcion, $options: "i" };
    }

    if (filtros.fechaDesde || filtros.fechaHasta) {
      query.fechaCreacion = {};
      if (filtros.fechaDesde) query.fechaCreacion.$gte = new Date(filtros.fechaDesde);
      if (filtros.fechaHasta) query.fechaCreacion.$lte = new Date(filtros.fechaHasta);
    }

    return await SesionAnalisisModel.find(query).sort({ fechaCreacion: -1 });
  }
}