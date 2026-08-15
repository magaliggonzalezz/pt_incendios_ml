import { MongoCatalogosRepository } from "../../data/repositories/MongoCatalogosRepository.js";

const repository = new MongoCatalogosRepository();

export class CatalogosService {
  async obtenerClusters() {
    return await repository.obtenerClusters();
  }

  async obtenerEstados() {
    return await repository.obtenerEstados();
  }

  async obtenerMunicipios(cveEnt) {
    return await repository.obtenerMunicipios(cveEnt);
  }
}
