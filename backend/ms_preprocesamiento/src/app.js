import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import preprocesamientoRoutes from "./routes/preprocesamiento.routes.js";

dotenv.config();

const app = express();

app.use(cors());
app.use(express.json());

app.get("/", (req, res) => {
  res.send("MS Preprocesamiento funcionando");
});

app.use("/api/preprocesamiento", preprocesamientoRoutes);

const PORT = process.env.PORT || 3002;

app.listen(PORT, () => {
  console.log(`MS Preprocesamiento ejecutándose en http://localhost:${PORT}`);
  console.log(process.env.PREPROCESSING_PATH);
});