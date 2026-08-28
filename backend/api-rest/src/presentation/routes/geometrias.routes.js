import { Router } from "express";
import { GeometriasController } from "../controllers/geometrias.controller.js";

const router = Router();
const controller = new GeometriasController();

router.get("/estados", controller.estados.bind(controller));
router.get("/municipios", controller.municipios.bind(controller));
router.get("/smn", controller.smn.bind(controller));
router.get("/tematicas/:capa/viewport", controller.tematicaViewport.bind(controller));
router.get("/tematicas/:capa", controller.tematica.bind(controller));

export default router;
