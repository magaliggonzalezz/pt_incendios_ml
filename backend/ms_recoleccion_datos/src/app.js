import express from "express";
import cors from "cors";
import { env } from "./config/env.js";
import recoleccionRoutes from "./presentation/routes/recoleccion.routes.js";

const app = express();

app.use(cors());
app.use(express.json());

app.get("/", (req, res) => {
  res.send("MS Recolección de Datos funcionando");
});

app.use("/api/recoleccion", recoleccionRoutes);

app.listen(env.port, () => {
  console.log(`MS Recolección ejecutándose en http://localhost:${env.port}`);
});