import mongoose from "mongoose";
import { env } from "../../config/env.js";

export async function connectMongo() {
  try {
    await mongoose.connect(env.mongoUri, {
      dbName: env.mongoDbName,
    });
    console.log(`MongoDB Atlas conectado correctamente (${env.mongoDbName})`);
  } catch (error) {
    console.error("Error al conectar con MongoDB Atlas:", error.message);
    process.exit(1);
  }
}
