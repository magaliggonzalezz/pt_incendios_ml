import { MongoDatasetRepository } from "../../data/repositories/MongoDatasetRepository.js";

const repository = new MongoDatasetRepository();

export class DatasetsService {
  async obtenerDatasets() {
    return await repository.obtenerTodos();
  }

  async obtenerDatasetPorId(id) {
    return await repository.obtenerPorId(id);
  }

  async crearDataset(datos) {
    return await repository.crear(datos);
  }

  async actualizarDataset(id, datos) {
    return await repository.actualizar(id, datos);
  }

  async eliminarDataset(id) {
    return await repository.eliminar(id);
  }

  async buscarConFiltros(filtros) {
    return await repository.buscarConFiltros(filtros);
  }
}