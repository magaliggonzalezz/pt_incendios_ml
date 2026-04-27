import { Router } from "express";
import { IntegracionDatasetController } from "../controllers/integracionDataset.controller.js";

const router = Router();
const controller = new IntegracionDatasetController();

router.post("/procesar", controller.procesar.bind(controller));

export default router;