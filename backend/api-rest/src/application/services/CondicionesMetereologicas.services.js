import { MongoCondicionMeteorologicaRepository } from "../../data/repositories/MongoCondicionMetereologica.js";

const repository = new MongoCondicionMeteorologicaRepository();

export class CondicionesMeteorologicasService {
  async obtenerCondicionesMeteorologicas() {
    return await repository.obtenerTodos();
  }

  async obtenerCondicionMeteorologicaPorId(id) {
    return await repository.obtenerPorId(id);
  }

  async crearCondicionMeteorologica(datos) {
    return await repository.crear(datos);
  }

  async buscarConFiltros(filtros) {
    return await repository.buscarConFiltros(filtros);
  }
}