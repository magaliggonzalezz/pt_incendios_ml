import { MongoResultadosEstadoRepository } from "../../data/repositories/MongoResultadosEstadoRepository.js";

const repository = new MongoResultadosEstadoRepository();

export class ResultadosEstadoService {
  async obtenerDia(fecha) {
    return await repository.obtenerDia(fecha);
  }

  async obtenerRango(filtros) {
    return await repository.obtenerRango(filtros);
  }

  async obtenerMes(anio, mes) {
    return await repository.obtenerMes(anio, mes);
  }

  async obtenerAnio(anio) {
    return await repository.obtenerAnio(anio);
  }
}
