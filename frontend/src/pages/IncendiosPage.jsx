import { useEffect, useState } from "react";
import { obtenerIncendios } from "../services/incendios.service.js";

export default function IncendiosPage() {
  const [incendios, setIncendios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const cargarIncendios = async () => {
      try {
        const data = await obtenerIncendios();
        setIncendios(data);
      } catch (err) {
        setError(err.message || "Error al cargar incendios");
      } finally {
        setLoading(false);
      }
    };

    cargarIncendios();
  }, []);

  if (loading) return <p>Cargando incendios...</p>;
  if (error) return <p>{error}</p>;

  return (
    <div>
      <h1>Incendios</h1>

      {incendios.length === 0 ? (
        <p>No hay registros disponibles.</p>
      ) : (
        <ul>
          {incendios.map((incendio) => (
            <li key={incendio._id}>
              <strong>{incendio.region}</strong> - {incendio.causa} -{" "}
              {new Date(incendio.fecha).toLocaleDateString()}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}