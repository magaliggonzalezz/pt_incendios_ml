import express from "express";
import cors from "cors";
import dns from "node:dns";

import { env } from "./config/env.js";
import { connectMongo } from "./data/database/mongo.js";
import catalogosRoutes from "./presentation/routes/catalogos.routes.js";
import resultadosRoutes from "./presentation/routes/resultados.routes.js";
import geometriasRoutes from "./presentation/routes/geometrias.routes.js";
import puntosMapaRoutes from "./presentation/routes/puntos-mapa.routes.js";
import recursosRoutes from "./presentation/routes/recursos.routes.js";

// Forzar DNS públicos para resolver correctamente MongoDB Atlas SRV
dns.setServers(["8.8.8.8", "1.1.1.1"]);

const app = express();

app.use(cors());
app.use(express.json());

app.get("/", (req, res) => {
  res.send("API REST funcionando");
});

app.use("/api/catalogos", catalogosRoutes);
app.use("/api/resultados", resultadosRoutes);
app.use("/api/geometrias", geometriasRoutes);
app.use("/api/puntos-mapa", puntosMapaRoutes);
app.use("/api/recursos", recursosRoutes);

async function startServer() {
  await connectMongo();

  app.listen(env.port, () => {
    console.log(`Servidor ejecutándose en http://localhost:${env.port}`);
  });
}

startServer();
