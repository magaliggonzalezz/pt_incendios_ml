import mongoose from "mongoose";

const HotspotSchema = new mongoose.Schema(
  {
    anio: Number,
    estado: String,
    municipio: String,

    totalHotspots: Number,
    confidencePromedio: Number,
    confidenceCategoriaDominante: String,

    frpPromedio: Number,
    frpMaximo: Number,

    brightnessPromedio: Number,
    brightnessMaximo: Number,

    latitudPromedio: Number,
    longitudPromedio: Number,

    ubicacion: {
      type: {
        type: String,
        enum: ["Point"],
        default: "Point",
      },
      coordinates: {
        type: [Number],
        required: true,
      },
    },

    fuente: {
      type: String,
      default: "FIRMS",
    },
  },
  {
    versionKey: false,
    collection: "hotspots",
  }
);

HotspotSchema.index({ ubicacion: "2dsphere" });
HotspotSchema.index({ anio: 1 });
HotspotSchema.index({ estado: 1 });
HotspotSchema.index({ municipio: 1 });

export const HotspotModel = mongoose.model("Hotspot", HotspotSchema);