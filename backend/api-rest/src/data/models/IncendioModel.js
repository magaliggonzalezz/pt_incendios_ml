import mongoose from "mongoose";

const IncendioSchema = new mongoose.Schema(
  {
    claveIncendio: String,
    anio: Number,

    fechaInicio: Date,
    fechaTermino: Date,

    estado: String,
    municipio: String,

    cveEnt: String,
    cveMun: String,
    cvegeo: String,

    latitud: Number,
    longitud: Number,

    ubicacion: {
      type: {
        type: String,
        enum: ["Point"],
        default: "Point"
      },
      coordinates: {
        type: [Number],
        required: true
      }
    },

    region: String,
    predio: String,
    causa: String,
    causaEspecifica: String,

    tipoIncendio: String,
    tipoImpacto: String,
    tipoVegetacion: String,
    regimenFuego: String,

    superficieCategoria: String,
    arboladoAdulto: Number,
    arbustivo: Number,
    herbaceo: Number,
    hojarasca: Number,
    renuevo: Number,

    duracion: String,
    deteccion: String,
    llegada: String,

    fuente: {
      type: String,
      default: "CONAFOR"
    },

    archivoOrigen: String
  },
  {
    versionKey: false,
    collection: "incendios"
  }
);

IncendioSchema.index({ ubicacion: "2dsphere" });
IncendioSchema.index({ anio: 1 });
IncendioSchema.index({ estado: 1 });
IncendioSchema.index({ municipio: 1 });
IncendioSchema.index({ fuente: 1 });

export const IncendioModel = mongoose.model("Incendio", IncendioSchema);