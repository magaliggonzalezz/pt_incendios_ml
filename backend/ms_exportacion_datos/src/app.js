import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import exportacionRoutes from "./routes/exportacion.routes.js";

dotenv.config();

const app = express();

app.use(cors());
app.use(express.json());

app.get("/", (req, res) => {
  res.send("MS Exportación de datos funcionando");
});

app.use("/api/exportacion", exportacionRoutes);

const PORT = process.env.PORT || 3004;

app.listen(PORT, () => {
  console.log(`MS Exportación ejecutándose en http://localhost:${PORT}`);
});