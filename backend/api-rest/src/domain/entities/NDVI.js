export class NDVI {
  constructor({
    fecha,
    valor,
    geometria,
    fuente,
    region,
    estado
  }) {
    this.fecha = fecha;
    this.valor = valor;
    this.geometria = geometria;
    this.fuente = fuente;
    this.region = region;
    this.estado = estado;
  }
}