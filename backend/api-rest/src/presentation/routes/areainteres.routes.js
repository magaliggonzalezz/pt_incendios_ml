import { Router } from "express";
import { AreaController } from "../controllers/AreaInteres.controller.js";

const router = Router();
const controller = new AreaController();

router.get("/", controller.obtenerTodos.bind(controller));
router.get("/nombre/:nombre", controller.obtenerPorNombre.bind(controller));
router.get("/filtros/busqueda", controller.buscarConFiltros.bind(controller));
router.get("/visualizacion/mapa", controller.obtenerParaMapa.bind(controller));
router.get("/:id", controller.obtenerPorId.bind(controller));
router.post("/", controller.crear.bind(controller));
router.put("/:id", controller.actualizar.bind(controller));

export default router;