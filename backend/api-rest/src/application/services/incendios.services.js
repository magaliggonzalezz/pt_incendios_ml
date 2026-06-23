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

  async eliminarIncendio(id) {
    return await incendioRepository.eliminar(id);
  }

  async buscarConFiltros(filtros) {
    return await incendioRepository.buscarConFiltros(filtros);
  }

  async obtenerParaMapa(filtros) {
  const incendios = await incendioRepository.obtenerParaMapa(filtros);

  return {
    type: "FeatureCollection",
    features: incendios.map((incendio) => ({
      type: "Feature",
      geometry: incendio.ubicacion,
      properties: {
        id: incendio._id,
        claveIncendio: incendio.claveIncendio,
        anio: incendio.anio,
        estado: incendio.estado,
        municipio: incendio.municipio,
        causa: incendio.causa,
        superficie: incendio.superficie,
        fechaInicio: incendio.fechaInicio,
        fuente: incendio.fuente
      }
    }))
  };
}
}