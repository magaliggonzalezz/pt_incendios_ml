import { NDVIModel } from "../models/NDVIModel.js";

export class MongoNDVIRepository {

  async obtenerTodos() {
    return await NDVIModel.find().sort({ fecha: -1 });
  }

  async obtenerPorId(id) {
    return await NDVIModel.findById(id);
  }

  async crear(data) {
    return await NDVIModel.create(data);
  }

  async buscarConFiltros(filtros) {
    const query = {};

    if (filtros.fechaDesde || filtros.fechaHasta) {
      query.fecha = {};
      if (filtros.fechaDesde) query.fecha.$gte = new Date(filtros.fechaDesde);
      if (filtros.fechaHasta) query.fecha.$lte = new Date(filtros.fechaHasta);
    }

    if (filtros.valorMin || filtros.valorMax) {
      query.valor = {};
      if (filtros.valorMin) query.valor.$gte = Number(filtros.valorMin);
      if (filtros.valorMax) query.valor.$lte = Number(filtros.valorMax);
    }

    if (filtros.estado) {
      query.estado = { $regex: filtros.estado, $options: "i" };
    }

    return await NDVIModel.find(query).sort({ fecha: -1 });
  }
}