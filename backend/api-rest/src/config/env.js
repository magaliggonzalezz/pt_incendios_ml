import dotenv from "dotenv";

dotenv.config();

const nodeEnv = process.env.NODE_ENV || "development";
const isProduction = nodeEnv === "production";

function parseList(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function requireEnv(name) {
  const value = process.env[name]?.trim();
  if (!value) {
    throw new Error(`Variable de entorno obligatoria no definida: ${name}`);
  }
  return value;
}

if (isProduction) {
  [
    "MONGODB_URI",
    "MONGODB_DB_NAME",
    "CORS_ORIGINS",
    "R2_ENDPOINT",
    "R2_BUCKET",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
  ].forEach(requireEnv);
}

export const env = {
  nodeEnv,
  isProduction,
  host: process.env.HOST || (isProduction ? "127.0.0.1" : "0.0.0.0"),
  port: Number(process.env.PORT || 3000),
  mongoUri: process.env.MONGODB_URI,
  mongoDbName: process.env.MONGODB_DB_NAME || "incendios_forestales_v2",
  assetsBaseUrl: process.env.ASSETS_BASE_URL,
  corsOrigins: parseList(
    process.env.CORS_ORIGINS || (isProduction ? "" : "http://localhost:5173"),
  ),
  r2Endpoint: process.env.R2_ENDPOINT,
  r2Bucket: process.env.R2_BUCKET,
  r2AccessKeyId: process.env.R2_ACCESS_KEY_ID,
  r2SecretAccessKey: process.env.R2_SECRET_ACCESS_KEY,
};

if (!Number.isInteger(env.port) || env.port < 1 || env.port > 65535) {
  throw new Error(`PORT inválido: ${process.env.PORT}`);
}
