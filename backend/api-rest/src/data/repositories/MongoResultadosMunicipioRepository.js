import mongoose from "mongoose";

export class MongoResultadosMunicipioRepository {
  get db() {
    return mongoose.connection.db;
  }

  async obtenerMes({ anio, mes, cveEnt, cvegeo }) {
    const query = { anio, mes };

    if (cveEnt) query.cve_ent = cveEnt;
    if (cvegeo) query.cvegeo = cvegeo;

    return await this.db
      .collection("resultados_municipio_mes")
      .find(query, { projection: { _id: 0 } })
      .sort({ cvegeo: 1 })
      .toArray();
  }

  async obtenerAnio({ anio, cveEnt, cvegeo }) {
    const query = { anio };

    if (cveEnt) query.cve_ent = cveEnt;
    if (cvegeo) query.cvegeo = cvegeo;

    return await this.db
      .collection("resultados_municipio_anio")
      .find(query, { projection: { _id: 0 } })
      .sort({ cvegeo: 1 })
      .toArray();
  }
}
