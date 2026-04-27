import { MongoIncendioRepository } from "../../data/repositories/MongoIncendioRepository.js";

const incendioRepository = new MongoIncendioRepository();

export class IncendiosService {
  async obtenerIncendios() {
    return await incendioRepository.obtenerTodos();
  }

  async obtenerIncendioPorId(id) {
    return await incendioRepository.obtenerPorId(id);
  }

  async crearIncendio(datos) {
    return await incendioRepository.crear(datos);
  }

  async actualizarIncendio(id, datos) {
    return await incendioRepository.actualizar(id, datos);
  }

  async eliminarIncendio(id) {
    return await incendioRepository.eliminar(id);
  }

  async buscarConFiltros(filtros) {
    return await incendioRepository.buscarConFiltros(filtros);
  }

  async obtenerIncendiosParaMapa() {
    return await incendioRepository.obtenerParaMapa();
  }
}