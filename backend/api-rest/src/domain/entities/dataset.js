export class Dataset {
  constructor({
    nombre,
    categoria,
    fechaInicio,
    fechaFin,
    fuente,
    descripcion,
    fechaCarga = new Date(),
    estado
  }) {
    this.nombre = nombre;
    this.categoria = categoria;
    this.fechaInicio = fechaInicio;
    this.fechaFin = fechaFin;
    this.fuente = fuente;
    this.descripcion = descripcion;
    this.fechaCarga = fechaCarga;
    this.estado = estado;
  }
}