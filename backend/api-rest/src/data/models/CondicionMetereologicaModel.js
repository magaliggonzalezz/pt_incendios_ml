import mongoose from "mongoose";

const CondicionMeteorologicaSchema = new mongoose.Schema(
  {
    fecha: {
      type: Date,
      required: true
    },
    variable: {
      type: String,
      required: true
    },
    valor: {
      type: Number,
      required: true
    },
    unidad: {
      type: String,
      required: true
    },
    fuente: {
      type: String,
      required: true
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
    collection: "condiciones_meteorologicas"
  }
);

CondicionMeteorologicaSchema.index({ fecha: 1 });
CondicionMeteorologicaSchema.index({ variable: 1 });
CondicionMeteorologicaSchema.index({ estado: 1 });

export const CondicionMeteorologicaModel = mongoose.model(
  "CondicionMeteorologica",
  CondicionMeteorologicaSchema
);