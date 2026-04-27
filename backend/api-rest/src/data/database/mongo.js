import mongoose from "mongoose";
import { env } from "../../config/env.js";

export async function connectMongo() {
  try {
    await mongoose.connect(env.mongoUri);
    console.log("MongoDB Atlas conectado correctamente");
  } catch (error) {
    console.error("Error al conectar con MongoDB Atlas:", error.message);
    process.exit(1);
  }
}
