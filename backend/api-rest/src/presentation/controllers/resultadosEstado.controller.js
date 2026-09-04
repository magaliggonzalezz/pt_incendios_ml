import { ResultadosEstadoService } from "../../application/services/resultadosEstado.service.js";

const service = new ResultadosEstadoService();

function parseEntero(value, field) {
  if (value === undefined) return { error: `${field} es obligatorio` };
  if (!/^\d+$/.test(String(value))) return { error: `${field} debe ser un entero` };
  return { value: Number(value) };
}

function validarFecha(value, field) {
  if (!value) return { error: `${field} es obligatoria` };
  const text = String(value).trim();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) return { error: `${field} debe usar el formato YYYY-MM-DD` };
  const date = new Date(`${text}T00:00:00Z`);
  if (Number.isNaN(date.getTime()) || date.toISOString().slice(0, 10) !== text) return { error: `${field} no es válida` };
  return { value: text };
}

export class ResultadosEstadoController {
  async obtenerDia(req, res) {
    try {
      const fecha = validarFecha(req.query.fecha, "fecha");
      if (fecha.error) return res.status(400).json({ error: fecha.error });
      const data = await service.obtenerDia(fecha.value);
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async obtenerRango(req, res) {
    try {
      const fechaInicio = validarFecha(req.query.fecha_inicio, "fecha_inicio");
      const fechaFin = validarFecha(req.query.fecha_fin, "fecha_fin");
      if (fechaInicio.error) return res.status(400).json({ error: fechaInicio.error });
      if (fechaFin.error) return res.status(400).json({ error: fechaFin.error });
      if (fechaInicio.value > fechaFin.value) return res.status(400).json({ error: "fecha_inicio no puede ser posterior a fecha_fin" });

      const cveEnt = req.query.cve_ent ? String(req.query.cve_ent).trim().padStart(2, "0") : null;
      if (cveEnt && !/^\d{2}$/.test(cveEnt)) return res.status(400).json({ error: "cve_ent debe tener 1 o 2 dígitos" });

      const data = await service.obtenerRango({ fechaInicio: fechaInicio.value, fechaFin: fechaFin.value, cveEnt });
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async obtenerMes(req, res) {
    try {
      const anioResult = parseEntero(req.query.anio, "anio");
      const mesResult = parseEntero(req.query.mes, "mes");
      if (anioResult.error) return res.status(400).json({ error: anioResult.error });
      if (mesResult.error) return res.status(400).json({ error: mesResult.error });
      if (mesResult.value < 1 || mesResult.value > 12) return res.status(400).json({ error: "mes debe estar entre 1 y 12" });
      const data = await service.obtenerMes(anioResult.value, mesResult.value);
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async obtenerAnio(req, res) {
    try {
      const anioResult = parseEntero(req.query.anio, "anio");
      if (anioResult.error) return res.status(400).json({ error: anioResult.error });
      const data = await service.obtenerAnio(anioResult.value);
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }
}
