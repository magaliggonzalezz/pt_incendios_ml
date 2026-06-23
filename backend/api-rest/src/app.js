import express from "express";
import cors from "cors";
import dns from "node:dns";

import { env } from "./config/env.js";
import { connectMongo } from "./data/database/mongo.js";
import incendiosRoutes from "./presentation/routes/incendios.routes.js";
import areainteresRoutes from "./presentation/routes/areainteres.routes.js";
import hotspotRoutes from "./presentation/routes/hotspot.routes.js";
import condicionesmeteorologicasRoutes from "./presentation/routes/CondicionesMetereologicas.routes.js";
import sesionesAnalisisRoutes from "./presentation/routes/sesionesAnalisis.routes.js";
import ndviRoutes from "./presentation/routes/ndvi.routes.js";
import datasetsRoutes from "./presentation/routes/datasets.routes.js";
import microserviciosRoutes from "./presentation/routes/microservicios.routes.js";
import analisisMLRoutes from "./presentation/routes/analisisML.routes.js";
import importacionRoutes from "./presentation/routes/importacion.routes.js";

// Forzar DNS públicos para resolver correctamente MongoDB Atlas SRV
dns.setServers(["8.8.8.8", "1.1.1.1"]);

const app = express();

app.use(cors());
app.use(express.json());

app.get("/", (req, res) => {
  res.send("API REST funcionando");
});

app.use("/api/incendios", incendiosRoutes);
app.use("/api/areainteres", areainteresRoutes);
app.use("/api/hotspot", hotspotRoutes);
app.use("/api/condicionesmeteorologicas", condicionesmeteorologicasRoutes);
app.use("/api/sesiones-analisis", sesionesAnalisisRoutes);
app.use("/api/ndvi", ndviRoutes);
app.use("/api/datasets", datasetsRoutes);
app.use("/api/microservicios", microserviciosRoutes);
app.use("/api/analisis-ml", analisisMLRoutes);
app.use("/api/importacion", importacionRoutes);


async function startServer() {
  await connectMongo();

  app.listen(env.port, () => {
    console.log(`Servidor ejecutándose en http://localhost:${env.port}`);
    });
}


startServer();