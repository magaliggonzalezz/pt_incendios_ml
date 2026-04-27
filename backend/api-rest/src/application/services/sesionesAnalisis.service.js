import { MongoSesionAnalisisRepository } from "../../data/repositories/MongoSesiondeAnalisisRepository.js";

const repository = new MongoSesionAnalisisRepository();

export class SesionesAnalisisService {
  async obtenerSesiones() {
    return await repository.obtenerTodos();
  }

  async obtenerSesionPorId(id) {
    return await repository.obtenerPorId(id);
  }

  async crearSesion(data) {
    return await repository.crear(data);
  }

  async actualizarSesion(id, data) {
    return await repository.actualizar(id, data);
  }

  async eliminarSesion(id) {
    return await repository.eliminar(id);
  }

  async buscarConFiltros(filtros) {
    return await repository.buscarConFiltros(filtros);
  }
}