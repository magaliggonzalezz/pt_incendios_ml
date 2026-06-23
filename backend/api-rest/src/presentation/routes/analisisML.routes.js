import { Router } from "express";
import { AnalisisMLController } from "../controllers/analisisML.controller.js";

const router = Router();
const controller = new AnalisisMLController();

router.get("/", controller.obtenerTodos.bind(controller));
router.get("/filtros/busqueda", controller.buscarConFiltros.bind(controller));
router.get("/:id", controller.obtenerPorId.bind(controller));
router.post("/", controller.crear.bind(controller));
router.delete("/:id", controller.eliminar.bind(controller));

export default router;