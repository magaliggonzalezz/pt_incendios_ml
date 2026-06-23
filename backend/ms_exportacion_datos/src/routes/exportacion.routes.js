import { Router } from "express";
import { ExportacionController } from "../controllers/exportacion.controller.js";

const router = Router();
const controller = new ExportacionController();

router.post("/json", controller.exportarJSON.bind(controller));
router.post("/csv", controller.exportarCSV.bind(controller));
router.get("/archivos", controller.listarArchivos.bind(controller));
router.get("/descargar/:nombreArchivo", controller.descargarArchivo.bind(controller));

export default router;