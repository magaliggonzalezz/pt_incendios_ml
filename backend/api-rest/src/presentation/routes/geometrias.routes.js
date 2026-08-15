import { Router } from "express";
import { GeometriasController } from "../controllers/geometrias.controller.js";

const router = Router();
const controller = new GeometriasController();

router.get("/estados", controller.estados.bind(controller));
router.get("/municipios", controller.municipios.bind(controller));

export default router;
