import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import analisisRoutes from "./routes/analisis.routes.js";

dotenv.config();

const app = express();

app.use(cors());
app.use(express.json());

app.get("/", (req, res) => {
  res.send("MS Análisis ML funcionando");
});

app.use("/api/analisis-ml", analisisRoutes);

const PORT = process.env.PORT || 3003;

app.listen(PORT, () => {
  console.log(`MS Análisis ML ejecutándose en http://localhost:${PORT}`);
});
