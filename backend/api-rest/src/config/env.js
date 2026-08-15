import dotenv from "dotenv";

dotenv.config();

export const env = {
  port: process.env.PORT || 3000,
  mongoUri: process.env.MONGODB_URI,
  mongoDbName: process.env.MONGODB_DB_NAME || "incendios_forestales_v2",
  assetsBaseUrl: process.env.ASSETS_BASE_URL,
  msRecoleccionUrl: process.env.MS_RECOLECCION_URL,
  msPreprocesamientoUrl: process.env.MS_PREPROCESAMIENTO_URL,
  msAnalisisMlUrl: process.env.MS_ANALISIS_ML_URL,
  msExportacionUrl: process.env.MS_EXPORTACION_URL
};
