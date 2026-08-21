import dotenv from "dotenv";

dotenv.config();

export const env = {
  port: process.env.PORT || 3000,
  mongoUri: process.env.MONGODB_URI,
  mongoDbName: process.env.MONGODB_DB_NAME || "incendios_forestales_v2",
  assetsBaseUrl: process.env.ASSETS_BASE_URL,
  r2Endpoint: process.env.R2_ENDPOINT,
  r2Bucket: process.env.R2_BUCKET,
  r2AccessKeyId: process.env.R2_ACCESS_KEY_ID,
  r2SecretAccessKey: process.env.R2_SECRET_ACCESS_KEY,
  msRecoleccionUrl: process.env.MS_RECOLECCION_URL,
  msPreprocesamientoUrl: process.env.MS_PREPROCESAMIENTO_URL,
  msAnalisisMlUrl: process.env.MS_ANALISIS_ML_URL,
  msExportacionUrl: process.env.MS_EXPORTACION_URL
};
