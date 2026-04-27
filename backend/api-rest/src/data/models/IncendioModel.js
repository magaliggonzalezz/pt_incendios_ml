import mongoose from "mongoose";

const IncendioSchema = new mongoose.Schema(
  {
    fecha: {
      type: Date,
      required: true
    },
    ubicacion: {
      type: {
        type: String,
        enum: ["Point"],
        required: true
      },
      coordinates: {
        type: [Number],
        required: true
      }
    },
    superficie: {
      type: Number,
      required: true
    },
    causa: {
      type: String,
      required: true
    },
    region: {
      type: String,
      required: true
    },
    estado: {
      type: String,
      required: true
    },
    municipio: {
      type: String,
      required: true
    },
    fuente: {
      type: String,
      required: true
    }
  },
  {
    versionKey: false,
    collection: "incendios"
  }
);

IncendioSchema.index({ ubicacion: "2dsphere" });
IncendioSchema.index({ fecha: 1 });
IncendioSchema.index({ region: 1 });

export const IncendioModel = mongoose.model("Incendio", IncendioSchema);