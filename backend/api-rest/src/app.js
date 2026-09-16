import express from "express";
import cors from "cors";
import dns from "node:dns";
import mongoose from "mongoose";

import { env } from "./config/env.js";
import { connectMongo } from "./data/database/mongo.js";
import { isR2Configured } from "./data/storage/r2.js";
import catalogosRoutes from "./presentation/routes/catalogos.routes.js";
import resultadosRoutes from "./presentation/routes/resultados.routes.js";
import geometriasRoutes from "./presentation/routes/geometrias.routes.js";
import puntosMapaRoutes from "./presentation/routes/puntos-mapa.routes.js";
import recursosRoutes from "./presentation/routes/recursos.routes.js";

// Forzar DNS públicos para resolver correctamente MongoDB Atlas SRV
dns.setServers(["8.8.8.8", "1.1.1.1"]);

const app = express();

app.disable("x-powered-by");
app.set("trust proxy", 1);

app.use(
  cors({
    origin(origin, callback) {
      if (!origin || env.corsOrigins.includes(origin)) {
        return callback(null, true);
      }

      const error = new Error("Origen no permitido por CORS");
      error.statusCode = 403;
      return callback(error);
    },
  }),
);
app.use(express.json({ limit: "1mb" }));

app.get("/", (req, res) => {
  res.send("API REST funcionando");
});

app.get("/api/health", (req, res) => {
  const mongoConnected = mongoose.connection.readyState === 1;
  const r2Configured = isR2Configured();
  const healthy = mongoConnected && r2Configured;

  res.status(healthy ? 200 : 503).json({
    status: healthy ? "ok" : "degraded",
    environment: env.nodeEnv,
    dependencies: {
      mongodb: mongoConnected ? "connected" : "disconnected",
      r2: r2Configured ? "configured" : "not_configured",
    },
  });
});

app.use("/api/catalogos", catalogosRoutes);
app.use("/api/resultados", resultadosRoutes);
app.use("/api/geometrias", geometriasRoutes);
app.use("/api/puntos-mapa", puntosMapaRoutes);
app.use("/api/recursos", recursosRoutes);

async function startServer() {
  try {
    await connectMongo();
  } catch (error) {
    if (env.isProduction) {
      console.error("No se iniciará la API en producción sin conexión a MongoDB Atlas.");
      process.exit(1);
    }

    console.warn(
      "MongoDB Atlas no está disponible. La API continuará activa para rutas que no dependen de MongoDB.",
    );
  }

  app.listen(env.port, env.host, () => {
    console.log(
      `Servidor ejecutándose en ${env.host}:${env.port} (${env.nodeEnv})`,
    );
  });
}

startServer();
