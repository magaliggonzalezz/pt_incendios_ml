import mongoose from "mongoose";

export class MongoResultadosEstadoRepository {
  get db() {
    return mongoose.connection.db;
  }

  async obtenerDia(fecha) {
    return await this.db
      .collection("resultados_estado_dia")
      .find({ fecha }, { projection: { _id: 0 } })
      .sort({ cve_ent: 1 })
      .toArray();
  }

  async obtenerMes(anio, mes) {
    return await this.db
      .collection("resultados_estado_mes")
      .find({ anio, mes }, { projection: { _id: 0 } })
      .sort({ cve_ent: 1 })
      .toArray();
  }

  async obtenerAnio(anio) {
    return await this.db
      .collection("resultados_estado_anio")
      .find({ anio }, { projection: { _id: 0 } })
      .sort({ cve_ent: 1 })
      .toArray();
  }
}
