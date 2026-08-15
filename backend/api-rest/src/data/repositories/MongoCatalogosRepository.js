import mongoose from "mongoose";

export class MongoCatalogosRepository {
  get db() {
    return mongoose.connection.db;
  }

  async obtenerClusters() {
    return await this.db
      .collection("clusters")
      .find({}, { projection: { _id: 0 } })
      .sort({ cluster: 1 })
      .toArray();
  }

  async obtenerEstados() {
    return await this.db
      .collection("estados")
      .find({}, { projection: { _id: 0 } })
      .sort({ cve_ent: 1 })
      .toArray();
  }

  async obtenerMunicipios(cveEnt) {
    const query = cveEnt ? { cve_ent: cveEnt } : {};

    return await this.db
      .collection("municipios")
      .find(query, { projection: { _id: 0 } })
      .sort({ cve_ent: 1, cvegeo: 1 })
      .toArray();
  }
}
