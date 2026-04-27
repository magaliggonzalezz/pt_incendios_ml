import { Router } from "express";
import { NDVIController } from "../controllers/ndvi.controller.js";

const router = Router();
const controller = new NDVIController();

router.get("/", controller.obtenerTodos.bind(controller));
router.get("/filtros/busqueda", controller.buscarConFiltros.bind(controller));
router.get("/:id", controller.obtenerPorId.bind(controller));
router.post("/", controller.crear.bind(controller));

export default router;