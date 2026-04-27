import { MongoNDVIRepository } from "../../data/repositories/MongoNDVIRepository.js";

const repository = new MongoNDVIRepository();

export class NDVIService {

  async obtenerNDVI() {
    return await repository.obtenerTodos();
  }

  async obtenerNDVIPorId(id) {
    return await repository.obtenerPorId(id);
  }

  async crearNDVI(data) {
    return await repository.crear(data);
  }

  async buscarConFiltros(filtros) {
    return await repository.buscarConFiltros(filtros);
  }
}