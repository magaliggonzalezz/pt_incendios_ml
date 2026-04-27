export class SesionAnalisis {
  constructor({
    descripcion,
    fechaCreacion = new Date(),
    vistaMapa,
    filtros,
    exportaciones = []
  }) {
    this.descripcion = descripcion;
    this.fechaCreacion = fechaCreacion;
    this.vistaMapa = vistaMapa;
    this.filtros = filtros;
    this.exportaciones = exportaciones;
  }
}