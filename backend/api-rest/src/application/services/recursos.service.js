const YEAR_MIN = 2001;
const YEAR_MAX = 2025;

export function obtenerConfiguracionRecursos() {
  return {
    periodo: { desde: YEAR_MIN, hasta: YEAR_MAX },
    almacenamiento: "Cloudflare R2 privado",
    formatosExportacion: ["csv", "json"],
    estrategiaExportacion:
      "La exportación corresponde a los resultados de la consulta activa, no a archivos anuales completos.",
  };
}
