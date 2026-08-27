import { consultarMunicipioDiaR2 } from "../../application/services/consulta-municipio-dia-r2.service.js";
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

function validarFecha(value) {
  if (value === undefined) return { error: "fecha es obligatoria" };
  const text = String(value).trim();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) {
    return { error: "fecha debe tener formato YYYY-MM-DD" };
  }
  const date = new Date(`${text}T00:00:00Z`);
  if (Number.isNaN(date.getTime()) || date.toISOString().slice(0, 10) !== text) {
    return { error: "fecha no es válida" };
  }
  return { value: text };
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
  async obtenerDia(req, res) {
    try {
      const cvegeo = normalizarCvegeo(req.query.cvegeo);
      const fecha = validarFecha(req.query.fecha);

      if (cvegeo?.error) return res.status(400).json({ error: cvegeo.error });
      if (!cvegeo) return res.status(400).json({ error: "cvegeo es obligatorio" });
      if (fecha.error) return res.status(400).json({ error: fecha.error });

      const data = await consultarMunicipioDiaR2({
        cvegeo,
        fecha: fecha.value,
      });

      res.status(200).json(data);
    } catch (error) {
      res.status(error.statusCode || 500).json({ error: error.message });
    }
  }

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
