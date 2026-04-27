import { MongoHotspotRepository } from "../../data/repositories/MongoHotspotRepository.js";

const HotspotRepository = new MongoHotspotRepository();

export class HotspotService {
  async obtenerHotspot() {
    return await HotspotRepository.obtenerTodos();
  }

 
  async obtenerHotspotPorId(id) {
    return await HotspotRepository.obtenerPorId(id);
  }

  async crearHotspot(datos) {
    return await HotspotRepository.crear(datos);
  }

  async actualizarHotspot(id, datos) {
    return await HotspotRepository.actualizar(datos);
  }

  async eliminarHotspot(id) {
    return await HotspotRepository.eliminar(id);
  }

  async buscarConFiltros(filtros) {
    return await HotspotRepository.buscarConFiltros(filtros);
  }
}