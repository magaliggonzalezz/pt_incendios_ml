import { Router } from "express";
import { PreprocesamientoController } from "../controllers/preprocesamiento.controller.js";

const router = Router();
const controller = new PreprocesamientoController();

router.get("/fuentes", controller.listarFuentes.bind(controller));
router.get("/:fuente/reportes", controller.obtenerReportes.bind(controller));
router.get("/:fuente/scripts", controller.obtenerScripts.bind(controller));

export default router;