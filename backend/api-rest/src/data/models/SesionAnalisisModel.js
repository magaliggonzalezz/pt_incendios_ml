import mongoose from "mongoose";

const CapaSchema = new mongoose.Schema(
  {
    nombre: {
      type: String,
      required: true
    },
    tipo: {
      type: String,
      required: true
    }
  },
  { _id: false }
);

const VistaMapaSchema = new mongoose.Schema(
  {
    fechaReferencia: {
      type: Date,
      required: true
    },
    proyeccion: {
      type: String,
      required: true
    },
    titulo: {
      type: String,
      required: true
    },
    capas: {
      type: [CapaSchema],
      default: []
    }
  },
  { _id: false }
);

const FiltroConsultaSchema = new mongoose.Schema(
  {
    fechaDesde: {
      type: Date,
      required: true
    },
    fechaHasta: {
      type: Date,
      required: true
    }
  },
  { _id: false }
);

const ExportacionSchema = new mongoose.Schema(
  {
    formato: {
      type: String,
      required: true
    },
    estado: {
      type: String,
      required: true
    },
    fechaGeneracion: {
      type: Date,
      required: true
    }
  },
  { _id: false }
);

const SesionAnalisisSchema = new mongoose.Schema(
  {
    fechaCreacion: {
      type: Date,
      default: Date.now
    },
    descripcion: {
      type: String,
      required: true
    },
    vistaMapa: {
      type: VistaMapaSchema,
      required: true
    },
    filtros: {
      type: FiltroConsultaSchema,
      required: true
    },
    exportaciones: {
      type: [ExportacionSchema],
      default: []
    }
  },
  {
    versionKey: false,
    collection: "sesion_analisis"
  }
);

SesionAnalisisSchema.index({ fechaCreacion: -1 });
SesionAnalisisSchema.index({ descripcion: 1 });

export const SesionAnalisisModel = mongoose.model(
  "SesionAnalisis",
  SesionAnalisisSchema
);