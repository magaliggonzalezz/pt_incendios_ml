import dotenv from "dotenv";

dotenv.config();

export const env = {
  port: process.env.PORT || 3000,
  mongoUri: process.env.MONGODB_URI,
  preprocesamientoUrl: process.env.PREPROCESAMIENTO_UR
};
