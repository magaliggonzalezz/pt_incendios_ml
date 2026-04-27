import mongoose from "mongoose";

const NDVISchema = new mongoose.Schema(
  {
    fecha: {
      type: Date,
      required: true
    },
    valor: {
      type: Number,
      required: true
    },
    geometria: {
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
    fuente: {
      type: String
    },
    region: {
      type: String
    },
    estado: {
      type: String
    }
  },
  {
    versionKey: false,
    collection: "NDVI"
  }
);

NDVISchema.index({ geometria: "2dsphere" });

export const NDVIModel = mongoose.model("NDVI", NDVISchema);