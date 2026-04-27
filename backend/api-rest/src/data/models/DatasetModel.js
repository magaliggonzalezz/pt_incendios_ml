import mongoose from "mongoose";

const DatasetSchema = new mongoose.Schema(
  {
    nombre: {
      type: String,
      required: true,
      trim: true
    },
    categoria: {
      type: String,
      required: true,
      trim: true
    },
    fechaInicio: {
      type: Date,
      required: true
    },
    fechaFin: {
      type: Date,
      required: true
    },
    fuente: {
      type: String,
      required: true,
      trim: true
    },
    descripcion: {
      type: String,
      trim: true
    },
    fechaCarga: {
      type: Date,
      default: Date.now
    },
    estado: {
      type: String,
      required: true,
      trim: true
    }
  },
  {
    versionKey: false,
    collection: "datasets"
  } 
);

DatasetSchema.index({ nombre: 1 });
DatasetSchema.index({ categoria: 1 });
DatasetSchema.index({ fuente: 1 });
DatasetSchema.index({ fechaInicio: 1, fechaFin: 1 });

export const DatasetModel = mongoose.model("Dataset", DatasetSchema);