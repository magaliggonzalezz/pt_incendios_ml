import { Router } from "express";
import { CatalogosController } from "../controllers/catalogos.controller.js";

const router = Router();
const controller = new CatalogosController();

router.get("/clusters", controller.obtenerClusters.bind(controller));
router.get("/estados", controller.obtenerEstados.bind(controller));
router.get("/municipios", controller.obtenerMunicipios.bind(controller));

export default router;
