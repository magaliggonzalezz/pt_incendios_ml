import { Router } from "express";
import { PuntosMapaController } from "../controllers/puntos-mapa.controller.js";

const router = Router();
const controller = new PuntosMapaController();

router.get("/firms", controller.firms.bind(controller));
router.get("/conafor", controller.conafor.bind(controller));

export default router;
