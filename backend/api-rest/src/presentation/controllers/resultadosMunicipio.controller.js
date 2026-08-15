import { ResultadosMunicipioService } from "../../application/services/resultadosMunicipio.service.js";

const service = new ResultadosMunicipioService();

function parseEntero(value, field) {
  if (value === undefined) {
    return { error: `${field} es obligatorio` };
  }

  if (!/^\d+$/.test(String(value))) {
    return { error: `${field} debe ser un entero` };
  }

  return { value: Number(value) };
}

function normalizarCveEnt(value) {
  if (value === undefined) return null;
  const text = String(value).trim();
  if (!/^\d{1,2}$/.test(text)) return { error: "cve_ent debe tener 1 o 2 dígitos" };
  return text.padStart(2, "0");
}

function normalizarCvegeo(value) {
  if (value === undefined) return null;
  const text = String(value).trim();
  if (!/^\d{5}$/.test(text)) return { error: "cvegeo debe tener 5 dígitos" };
  return text;
}

function validarFiltroTerritorial(query) {
  const cveEnt = normalizarCveEnt(query.cve_ent);
  const cvegeo = normalizarCvegeo(query.cvegeo);

  if (cveEnt?.error) return { error: cveEnt.error };
  if (cvegeo?.error) return { error: cvegeo.error };

  if (!cveEnt && !cvegeo) {
    return { error: "cve_ent o cvegeo es obligatorio" };
  }

  if (cveEnt && cvegeo && !cvegeo.startsWith(cveEnt)) {
    return { error: "cvegeo no pertenece a cve_ent" };
  }

  return { cveEnt, cvegeo };
}

export class ResultadosMunicipioController {
  async obtenerMes(req, res) {
    try {
      const anioResult = parseEntero(req.query.anio, "anio");
      const mesResult = parseEntero(req.query.mes, "mes");
      const territorio = validarFiltroTerritorial(req.query);

      if (anioResult.error) return res.status(400).json({ error: anioResult.error });
      if (mesResult.error) return res.status(400).json({ error: mesResult.error });
      if (mesResult.value < 1 || mesResult.value > 12) {
        return res.status(400).json({ error: "mes debe estar entre 1 y 12" });
      }
      if (territorio.error) return res.status(400).json({ error: territorio.error });

      const data = await service.obtenerMes({
        anio: anioResult.value,
        mes: mesResult.value,
        cveEnt: territorio.cveEnt,
        cvegeo: territorio.cvegeo,
      });

      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async obtenerAnio(req, res) {
    try {
      const anioResult = parseEntero(req.query.anio, "anio");
      const territorio = validarFiltroTerritorial(req.query);

      if (anioResult.error) return res.status(400).json({ error: anioResult.error });
      if (territorio.error) return res.status(400).json({ error: territorio.error });

      const data = await service.obtenerAnio({
        anio: anioResult.value,
        cveEnt: territorio.cveEnt,
        cvegeo: territorio.cvegeo,
      });

      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }
}
