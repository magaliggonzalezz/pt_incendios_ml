import { Router } from "express";
import { RecoleccionController } from "../controllers/recoleccion.controller.js";

const router = Router();
const controller = new RecoleccionController();

router.get("/fuentes", controller.listarFuentes.bind(controller));
router.get("/:fuente/archivos", controller.obtenerArchivosFuente.bind(controller));
router.get("/:fuente/archivos/:nombreArchivo", controller.obtenerArchivo.bind(controller));

export default router;