import { Router } from "express";
import { RecursosController } from "../controllers/recursos.controller.js";

const router = Router();
const controller = new RecursosController();

router.get("/configuracion", controller.configuracion.bind(controller));
router.get("/diagnostico-r2", controller.diagnosticoR2.bind(controller));
router.get("/inspeccion-parquet-r2", controller.inspeccionParquetR2.bind(controller));

export default router;
