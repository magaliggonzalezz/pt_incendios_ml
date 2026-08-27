import { MongoResultadosMunicipioRepository } from "../../data/repositories/MongoResultadosMunicipioRepository.js";

const repository = new MongoResultadosMunicipioRepository();

export class ResultadosMunicipioService {
  async obtenerDia(filtros) {
    return await repository.obtenerDia(filtros);
  }

  async obtenerMes(filtros) {
    return await repository.obtenerMes(filtros);
  }

  async obtenerAnio(filtros) {
    return await repository.obtenerAnio(filtros);
  }
}
