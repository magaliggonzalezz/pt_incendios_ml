import { Router } from "express";
import { ResultadosEstadoController } from "../controllers/resultadosEstado.controller.js";
import { ResultadosMunicipioController } from "../controllers/resultadosMunicipio.controller.js";

const router = Router();
const estadoController = new ResultadosEstadoController();
const municipioController = new ResultadosMunicipioController();

router.get("/estado/dia", estadoController.obtenerDia.bind(estadoController));
router.get("/estado/rango", estadoController.obtenerRango.bind(estadoController));
router.get("/estado/mes", estadoController.obtenerMes.bind(estadoController));
router.get("/estado/anio", estadoController.obtenerAnio.bind(estadoController));

router.get("/municipio/dia", municipioController.obtenerDia.bind(municipioController));
router.get("/municipio/rango", municipioController.obtenerRango.bind(municipioController));
router.get("/municipio/mes", municipioController.obtenerMes.bind(municipioController));
router.get("/municipio/anio", municipioController.obtenerAnio.bind(municipioController));

export default router;
