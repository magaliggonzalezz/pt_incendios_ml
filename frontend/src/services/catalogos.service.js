import { GEO_CATALOG } from "../data/geoCatalog";
import { apiFetch } from "./api";

function buildEstadosLocal() {
  const estados = new Map();

  GEO_CATALOG.forEach((row) => {
    const cveEnt = String(row.CVE_ENT || "").padStart(2, "0");
    if (!cveEnt || estados.has(cveEnt)) return;
    estados.set(cveEnt, {
      cve_ent: cveEnt,
      nombre: row.NOM_ENT,
      abreviatura: row.NOM_ABR,
    });
  });

  return [...estados.values()].sort((a, b) => a.cve_ent.localeCompare(b.cve_ent));
}

function buildMunicipiosLocal(cveEnt) {
  const target = String(cveEnt || "").padStart(2, "0");
  if (!target) return [];

  return GEO_CATALOG
    .filter((row) => String(row.CVE_ENT || "").padStart(2, "0") === target)
    .map((row) => ({
      cve_ent: target,
      cve_mun: String(row.CVE_MUN || "").padStart(3, "0"),
      cvegeo: String(row.CVEGEO || "").padStart(5, "0"),
      nombre: row.NOM_MUN,
    }))
    .sort((a, b) => a.cvegeo.localeCompare(b.cvegeo));
}

export async function obtenerClusters() {
  try {
    return await apiFetch("/api/catalogos/clusters");
  } catch {
    return [];
  }
}

export async function obtenerEstados() {
  try {
    return await apiFetch("/api/catalogos/estados");
  } catch {
    return buildEstadosLocal();
  }
}

export async function obtenerMunicipios(cveEnt) {
  const query = cveEnt ? `?cve_ent=${encodeURIComponent(cveEnt)}` : "";

  try {
    return await apiFetch(`/api/catalogos/municipios${query}`);
  } catch {
    return buildMunicipiosLocal(cveEnt);
  }
}
