import { HeadObjectCommand, S3Client } from "@aws-sdk/client-s3";

import { env } from "../../config/env.js";

function normalizeEndpoint(value) {
  const endpoint = String(value || "").trim().replace(/\/+$/, "");
  const bucket = String(env.r2Bucket || "").trim();

  if (!endpoint || !bucket) {
    return endpoint;
  }

  const suffix = `/${bucket}`;
  return endpoint.endsWith(suffix) ? endpoint.slice(0, -suffix.length) : endpoint;
}

export function isR2Configured() {
  return Boolean(
    normalizeEndpoint(env.r2Endpoint) &&
      env.r2Bucket &&
      env.r2AccessKeyId &&
      env.r2SecretAccessKey,
  );
}

let client;

export function getR2Client() {
  if (!isR2Configured()) {
    const error = new Error("Cloudflare R2 no está configurado en las variables de entorno");
    error.statusCode = 503;
    throw error;
  }

  if (!client) {
    client = new S3Client({
      region: "auto",
      endpoint: normalizeEndpoint(env.r2Endpoint),
      credentials: {
        accessKeyId: env.r2AccessKeyId,
        secretAccessKey: env.r2SecretAccessKey,
      },
    });
  }

  return client;
}

export async function obtenerMetadataObjetoR2(key) {
  const s3 = getR2Client();
  const response = await s3.send(
    new HeadObjectCommand({
      Bucket: env.r2Bucket,
      Key: key,
    }),
  );

  return {
    key,
    bucket: env.r2Bucket,
    bytes: response.ContentLength ?? null,
    contentType: response.ContentType ?? null,
    etag: response.ETag?.replaceAll('"', "") ?? null,
    ultimaModificacion: response.LastModified?.toISOString() ?? null,
  };
}
