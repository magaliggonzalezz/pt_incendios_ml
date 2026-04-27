import { AreaInteresModel } from "../models/AreaInteresModel.js";

export class MongoAreaInteresRepository {
  async obtenerTodos() {
    return await AreaInteresModel.find().sort({ nombre: -1 });
  }

  async obtenerPorNombre(nombre) {
  return await AreaInteresModel.find({
    nombre: { $regex: nombre, $options: "i" }
  });
  }

  async obtenerPorId(id) {
    return await AreaInteresModel.findById(id);
  }

  async crear(datos) {
    return await AreaInteresModel.create(datos);
  }

  async actualizar(id, datos) {
    return await AreaInteresModel.findByIdAndUpdate(id, datos, { new: true });
  }

  async buscarConFiltros(filtros) {
    const query = {};

    if (filtros.nombre) query.nombre = filtros.nombre;
    if (filtros.geometria) query.geometria = filtros.geometria;
    if (filtros.coordinates) query.coordinates = filtros.coordinates;

    return await AreaInteresModel.find(query).sort({ nombre: -1 });
  }

   async obtenerParaMapa() {
    return await AreaInteresModel.find(
      {},
      {
        nombre: 1,
        geometria: 1, 
        coordinates: 1
        
      }
    ).sort({ nombre: -1 });
  }
}