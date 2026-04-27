import { DatasetModel } from "../models/DatasetModel.js";

export class MongoDatasetRepository {
  async obtenerTodos() {
    return await DatasetModel.find().sort({ fechaCarga: -1 });
  }

  async obtenerPorId(id) {
    return await DatasetModel.findById(id);
  }

  async crear(datos) {
    return await DatasetModel.create(datos);
  }

  async actualizar(id, datos) {
    return await DatasetModel.findByIdAndUpdate(id, datos, { new: true });
  }

  async eliminar(id) {
    return await DatasetModel.findByIdAndDelete(id);
  }

  async buscarConFiltros(filtros) {
    const query = {};

    if (filtros.nombre) {
      query.nombre = { $regex: filtros.nombre, $options: "i" };
    }

    if (filtros.categoria) {
      query.categoria = { $regex: filtros.categoria, $options: "i" };
    }

    if (filtros.fuente) {
      query.fuente = { $regex: filtros.fuente, $options: "i" };
    }

    if (filtros.estado) {
      query.estado = { $regex: filtros.estado, $options: "i" };
    }

    if (filtros.fechaDesde || filtros.fechaHasta) {
      query.fechaCarga = {};
      if (filtros.fechaDesde) {
        query.fechaCarga.$gte = new Date(filtros.fechaDesde);
      }
      if (filtros.fechaHasta) {
        query.fechaCarga.$lte = new Date(filtros.fechaHasta);
      }
    }

    return await DatasetModel.find(query).sort({ fechaCarga: -1 });
  }
}