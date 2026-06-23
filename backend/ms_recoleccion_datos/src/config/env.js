import dotenv from "dotenv";

dotenv.config();

export const env = {
  port: process.env.PORT || 3001,
  dataUnderstandingPath:
    process.env.DATA_UNDERSTANDING_PATH ||
    "../../ml-pipeline/02_data-understanding"
};