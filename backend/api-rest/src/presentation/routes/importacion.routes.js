import { Router } from "express";
import { ImportacionController } from "../controllers/importacion.controller.js";

const router = Router();
const controller = new ImportacionController();

router.post(
  "/analisis-ml",
  controller.importarResultadosML.bind(controller)
);

router.post(
  "/incendios-conafor",
  controller.importarIncendiosConafor.bind(controller)
);

router.post(
  "/hotspots-firms",
  controller.importarHotspotsFirms.bind(controller)
);
export default router;