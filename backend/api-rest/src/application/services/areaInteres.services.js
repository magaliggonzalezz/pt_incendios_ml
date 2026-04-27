import { MongoAreaInteresRepository } from "../../data/repositories/MongoAreaInteresRepository.js";

const AreaRepository = new MongoAreaInteresRepository();

export class AreaInteresService {
  async obtenerAreaInteres() {
    return await AreaRepository.obtenerTodos();
  }

  async obtenerPorNombre(nombre) {
  return await AreaRepository.obtenerPorNombre(nombre);
  }

  async obtenerAreaPorId(id) {
    return await AreaRepository.obtenerPorId(id);
  }

  async crearArea(datos) {
    return await AreaRepository.crear(datos);
  }

  async actualizarArea(id, datos) {
    return await AreaRepository.actualizar(datos);
  }

  async buscarConFiltros(filtros) {
    return await AreaRepository.buscarConFiltros(filtros);
  }

  async obtenerAreaMapa() {
    return await AreaRepository.obtenerParaMapa();
  }
}