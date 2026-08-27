import { GetObjectCommand, HeadObjectCommand, S3Client } from "@aws-sdk/client-s3";

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

export async function obtenerObjetoR2Stream(key) {
  const s3 = getR2Client();
  const response = await s3.send(
    new GetObjectCommand({
      Bucket: env.r2Bucket,
      Key: key,
    }),
  );

  if (!response.Body) {
    const error = new Error(`R2 devolvió el objeto sin contenido: ${key}`);
    error.statusCode = 502;
    throw error;
  }

  return {
    body: response.Body,
    bytes: response.ContentLength ?? null,
    contentType: response.ContentType ?? "application/octet-stream",
    etag: response.ETag?.replaceAll('"', "") ?? null,
    ultimaModificacion: response.LastModified?.toISOString() ?? null,
  };
}

export async function descargarObjetoR2(key) {
  const { body } = await obtenerObjetoR2Stream(key);
  const bytes = await body.transformToByteArray();
  return Buffer.from(bytes);
}

export async function crearAsyncBufferR2(key) {
  const metadata = await obtenerMetadataObjetoR2(key);
  const byteLength = Number(metadata.bytes);

  if (!Number.isFinite(byteLength) || byteLength < 0) {
    throw new Error(`No se pudo determinar el tamaño del objeto R2: ${key}`);
  }

  const estadisticas = {
    solicitudesRange: 0,
    bytesTransferidos: 0,
  };

  const file = {
    byteLength,
    async slice(start, end = byteLength) {
      const inicio = Math.max(0, Number(start));
      const finExclusivo = Math.min(byteLength, Number(end));

      if (finExclusivo <= inicio) {
        return new ArrayBuffer(0);
      }

      const s3 = getR2Client();
      const response = await s3.send(
        new GetObjectCommand({
          Bucket: env.r2Bucket,
          Key: key,
          Range: `bytes=${inicio}-${finExclusivo - 1}`,
        }),
      );

      if (!response.Body) {
        throw new Error(`R2 devolvió un rango sin contenido: ${key}`);
      }

      const bytes = await response.Body.transformToByteArray();
      const buffer = Buffer.from(bytes);
      estadisticas.solicitudesRange += 1;
      estadisticas.bytesTransferidos += buffer.byteLength;

      return buffer.buffer.slice(
        buffer.byteOffset,
        buffer.byteOffset + buffer.byteLength,
      );
    },
  };

  return {
    file,
    metadata,
    obtenerEstadisticas: () => ({ ...estadisticas }),
  };
}
