import { IncendioModel } from "../models/IncendioModel.js";

export class MongoIncendioRepository {
  async obtenerTodos() {
    return await IncendioModel.find().limit(1000);
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

  if (filtros.fechaInicio) {
    query.fechaInicio = {
      $gte: new Date(filtros.fechaInicio)
    };
  }

  return await IncendioModel.find(query)
    .select(
      "claveIncendio anio estado municipio latitud longitud ubicacion causa superficie fechaInicio fuente"
    )
    .limit(5000);
}
  
 async crearMuchos(registros) {
    return await IncendioModel.insertMany(registros, {
      ordered: false
    });
  }

  async eliminarPorFuente(fuente) {
    return await IncendioModel.deleteMany({ fuente });
  }

}