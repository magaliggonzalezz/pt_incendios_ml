import { ResultadosEstadoService } from "../../application/services/resultadosEstado.service.js";

const service = new ResultadosEstadoService();

function parseEntero(value, field) {
  if (value === undefined) {
    return { error: `${field} es obligatorio` };
  }

  if (!/^\d+$/.test(String(value))) {
    return { error: `${field} debe ser un entero` };
  }

  return { value: Number(value) };
}

export class ResultadosEstadoController {
  async obtenerDia(req, res) {
    try {
      const { fecha } = req.query;

      if (!fecha) {
        return res.status(400).json({ error: "fecha es obligatoria" });
      }

      if (!/^\d{4}-\d{2}-\d{2}$/.test(fecha)) {
        return res.status(400).json({
          error: "fecha debe usar el formato YYYY-MM-DD",
        });
      }

      const data = await service.obtenerDia(fecha);
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async obtenerMes(req, res) {
    try {
      const anioResult = parseEntero(req.query.anio, "anio");
      const mesResult = parseEntero(req.query.mes, "mes");

      if (anioResult.error) {
        return res.status(400).json({ error: anioResult.error });
      }
      if (mesResult.error) {
        return res.status(400).json({ error: mesResult.error });
      }
      if (mesResult.value < 1 || mesResult.value > 12) {
        return res.status(400).json({ error: "mes debe estar entre 1 y 12" });
      }

      const data = await service.obtenerMes(anioResult.value, mesResult.value);
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }

  async obtenerAnio(req, res) {
    try {
      const anioResult = parseEntero(req.query.anio, "anio");

      if (anioResult.error) {
        return res.status(400).json({ error: anioResult.error });
      }

      const data = await service.obtenerAnio(anioResult.value);
      res.status(200).json(data);
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  }
}
