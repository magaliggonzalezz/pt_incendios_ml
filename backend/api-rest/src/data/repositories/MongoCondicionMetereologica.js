import { CondicionMeteorologicaModel } from "../models/CondicionMetereologicaModel.js";

export class MongoCondicionMeteorologicaRepository {
  async obtenerTodos() {
    return await CondicionMeteorologicaModel.find().sort({ fecha: -1 });
  }

  async obtenerPorId(id) {
    return await CondicionMeteorologicaModel.findById(id);
  }

  async crear(datos) {
    return await CondicionMeteorologicaModel.create(datos);
  }

  async buscarConFiltros(filtros) {
    const query = {};

    if (filtros.variable) {
      query.variable = { $regex: filtros.variable, $options: "i" };
    }

    if (filtros.unidad) {
      query.unidad = filtros.unidad;
    }

    if (filtros.fuente) {
      query.fuente = { $regex: filtros.fuente, $options: "i" };
    }

    if (filtros.region) {
      query.region = { $regex: filtros.region, $options: "i" };
    }

    if (filtros.estado) {
      query.estado = { $regex: filtros.estado, $options: "i" };
    }

    if (filtros.valorMin || filtros.valorMax) {
      query.valor = {};
      if (filtros.valorMin) query.valor.$gte = Number(filtros.valorMin);
      if (filtros.valorMax) query.valor.$lte = Number(filtros.valorMax);
    }

    if (filtros.fechaDesde || filtros.fechaHasta) {
      query.fecha = {};
      if (filtros.fechaDesde) query.fecha.$gte = new Date(filtros.fechaDesde);
      if (filtros.fechaHasta) query.fecha.$lte = new Date(filtros.fechaHasta);
    }

    return await CondicionMeteorologicaModel.find(query).sort({ fecha: -1 });
  }
}