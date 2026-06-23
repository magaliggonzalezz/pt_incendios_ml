import { Router } from "express";
import { MicroserviciosController } from "../controllers/microservicios.controller.js";

const router = Router();
const controller = new MicroserviciosController();

router.get(
  "/preprocesamiento/fuentes",
  controller.fuentesPreprocesamiento.bind(controller)
);

router.get(
  "/preprocesamiento/:fuente/reportes",
  controller.reportesPreprocesamiento.bind(controller)
);

router.get(
  "/preprocesamiento/:fuente/scripts",
  controller.scriptsPreprocesamiento.bind(controller)
);

router.get(
  "/analisis-ml/resultados",
  controller.resultadosML.bind(controller)
);

router.get(
  "/analisis-ml/reportes",
  controller.reportesML.bind(controller)
);

router.get(
  "/exportacion/archivos",
  controller.archivosExportacion.bind(controller)
);

router.post(
  "/exportacion/csv",
  controller.exportarCSV.bind(controller)
);

router.post(
  "/exportacion/json",
  controller.exportarJSON.bind(controller)
);

router.get(
  "/recoleccion/fuentes",
  controller.fuentesRecoleccion.bind(controller)
);

router.get(
  "/recoleccion/:fuente/archivos",
  controller.archivosRecoleccion.bind(controller)
);

export default router;