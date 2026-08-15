import { Router } from "express";
import { ResultadosEstadoController } from "../controllers/resultadosEstado.controller.js";

const router = Router();
const controller = new ResultadosEstadoController();

router.get("/estado/dia", controller.obtenerDia.bind(controller));
router.get("/estado/mes", controller.obtenerMes.bind(controller));
router.get("/estado/anio", controller.obtenerAnio.bind(controller));

export default router;
