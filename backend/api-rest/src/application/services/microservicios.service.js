import {
  obtenerFuentesRecoleccion,
  obtenerArchivosRecoleccion
} from "../../data/clients/recoleccion.client.js";

import {
  obtenerFuentesPreprocesamiento,
  obtenerReportesPreprocesamiento,
  obtenerScriptsPreprocesamiento
} from "../../data/clients/preprocesamiento.client.js";

import {
  obtenerResultadosML,
  obtenerReportesML
} from "../../data/clients/analisisMl.client.js";

import {
  listarArchivosExportacion,
  exportarCSV,
  exportarJSON
} from "../../data/clients/exportacion.client.js";

export class MicroserviciosService {
  async obtenerFuentesPreprocesamiento() {
    return await obtenerFuentesPreprocesamiento();
  }

  async obtenerReportesPreprocesamiento(fuente) {
    return await obtenerReportesPreprocesamiento(fuente);
  }

  async obtenerScriptsPreprocesamiento(fuente) {
    return await obtenerScriptsPreprocesamiento(fuente);
  }

  async obtenerResultadosML() {
    return await obtenerResultadosML();
  }

  async obtenerReportesML() {
    return await obtenerReportesML();
  }

  async listarArchivosExportacion() {
    return await listarArchivosExportacion();
  }

  async exportarCSV(payload) {
    return await exportarCSV(payload);
  }

  async exportarJSON(payload) {
    return await exportarJSON(payload);
  }

  async obtenerFuentesRecoleccion() {
  return await obtenerFuentesRecoleccion();
}

async obtenerArchivosRecoleccion(fuente) {
  return await obtenerArchivosRecoleccion(fuente);
}
}