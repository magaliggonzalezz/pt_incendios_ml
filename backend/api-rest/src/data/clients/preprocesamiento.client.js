export async function procesarDatasetEnMicroservicio(payload) {
  return {
    total: payload.registros.length,
    registros: payload.registros.map((registro) => {
      if (
        registro.superficie !== undefined &&
        registro.causa &&
        registro.region
      ) {
        return {
          tipo: "incendio",
          procesado: {
            fecha: new Date(registro.fecha),
            ubicacion: {
              type: "Point",
              coordinates: [Number(registro.longitud), Number(registro.latitud)]
            },
            superficie: Number(registro.superficie),
            causa: registro.causa,
            region: registro.region,
            estado: registro.estado,
            municipio: registro.municipio,
            fuente: registro.fuente
          }
        };
      }

      if (
        registro.intensidad !== undefined &&
        registro.latitud !== undefined &&
        registro.longitud !== undefined
      ) {
        return {
          tipo: "hotspot",
          procesado: {
            fecha: new Date(registro.fecha),
            ubicacion: {
              type: "Point",
              coordinates: [Number(registro.longitud), Number(registro.latitud)]
            },
            intensidad: Number(registro.intensidad),
            fuente: registro.fuente,
            region: registro.region,
            estado: registro.estado
          }
        };
      }

      if (
        registro.variable &&
        registro.valor !== undefined &&
        registro.unidad
      ) {
        return {
          tipo: "condicion_meteorologica",
          procesado: {
            fecha: new Date(registro.fecha),
            variable: registro.variable,
            valor: Number(registro.valor),
            unidad: registro.unidad,
            fuente: registro.fuente,
            region: registro.region,
            estado: registro.estado
          }
        };
      }

      return {
        tipo: "desconocido",
        procesado: null
      };
    })
  };
}