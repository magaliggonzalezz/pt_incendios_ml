import mongoose from "mongoose";

const AreaInteresSchema = new mongoose.Schema(
  {
    nombre: {
      type: String,
      required: true
    },
    geometria: {
      type: {
        type: String,
        enum: ["Polygon", "MultiPolygon"],
        required: true
      },
      coordinates: {
        type: Array,
        required: true
      }
    }
  },
  {
    versionKey: false,
    collection: "areas_interes"
  }
);

AreaInteresSchema.index({ nombre: 1 });
AreaInteresSchema.index({ geometria: "2dsphere" });

export const AreaInteresModel = mongoose.model("AreaInteres", AreaInteresSchema);