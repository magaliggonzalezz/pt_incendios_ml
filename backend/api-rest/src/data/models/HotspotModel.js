import mongoose from "mongoose";

const HotspotSchema = new mongoose.Schema(
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
    temperatura: {
      type: Number,
      required: true
    },
    fuente: {
      type: String,
      required:true
    }
  },
  {
    versionKey: false,
    collection: "hotspots"
  }
);

HotspotSchema.index({ ubicacion: "2dsphere" });
HotspotSchema.index({ fecha: 1 });
HotspotSchema.index({ temperatura: 1 });
HotspotSchema.index({ fuente: 1 });


export const HotspotModel = mongoose.model("Hotspot", HotspotSchema);