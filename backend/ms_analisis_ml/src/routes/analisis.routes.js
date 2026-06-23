import { Router } from "express";
import { AnalisisController } from "../controller/analisis.controller.js";

const router = Router();
const controller = new AnalisisController();

router.get("/resultados", controller.obtenerResultados.bind(controller));
router.get("/reportes", controller.obtenerReportes.bind(controller));

export default router;