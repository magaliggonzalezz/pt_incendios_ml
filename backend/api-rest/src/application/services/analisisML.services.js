import { MongoAnalisisMLRepository } from "../../data/repositories/MongoAnalisisMLRepository.js";

const repository = new MongoAnalisisMLRepository();

export class AnalisisMLService {
  async obtenerTodos() {
    return await repository.obtenerTodos();
  }

  async obtenerPorId(id) {
    return await repository.obtenerPorId(id);
  }

  async crear(data) {
    return await repository.crear(data);
  }

  async eliminar(id) {
    return await repository.eliminar(id);
  }

  async buscarConFiltros(filtros) {
    return await repository.buscarConFiltros(filtros);
  }
}