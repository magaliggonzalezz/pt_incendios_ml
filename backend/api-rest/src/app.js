import express from "express";
import cors from "cors";
import { env } from "./config/env.js";
import { connectMongo } from "./data/database/mongo.js";
import incendiosRoutes from "./presentation/routes/incendios.routes.js";
import areainteresRoutes from "./presentation/routes/areainteres.routes.js";
import hotspotRoutes from "./presentation/routes/hotspot.routes.js";
import condicionesmeteorologicasRoutes from "./presentation/routes/CondicionesMetereologicas.routes.js";
import sesionesAnalisisRoutes from "./presentation/routes/sesionesAnalisis.routes.js";
import ndviRoutes from "./presentation/routes/ndvi.routes.js";
import datasetsRoutes from "./presentation/routes/datasets.routes.js";
import integracionDatasetRoutes from "./presentation/routes/integracionDataset.routes.js";

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
app.use("/api/integracion-dataset", integracionDatasetRoutes);

async function startServer() {
  await connectMongo();

  app.listen(env.port, () => {
    console.log(`Servidor ejecutándose en http://localhost:${env.port}`);
  });
}

startServer();