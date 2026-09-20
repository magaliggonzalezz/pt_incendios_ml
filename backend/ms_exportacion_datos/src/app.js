import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import exportacionRoutes from "./routes/exportacion.routes.js";

dotenv.config();

const app = express();
const corsOrigins = (process.env.CORS_ORIGINS || "http://localhost:5173")
  .split(",")
  .map((value) => value.trim())
  .filter(Boolean);

app.use(
  cors({
    origin(origin, callback) {
      if (!origin || corsOrigins.includes(origin)) return callback(null, true);
      return callback(new Error("Origen no permitido por CORS"));
    },
  }),
);
app.use(express.json({ limit: "10mb" }));

app.get("/", (req, res) => {
  res.send("MS Exportación de datos funcionando");
});

app.use("/api/exportacion", exportacionRoutes);

const PORT = process.env.PORT || 3004;

app.listen(PORT, () => {
  console.log(`MS Exportación ejecutándose en http://localhost:${PORT}`);
});
