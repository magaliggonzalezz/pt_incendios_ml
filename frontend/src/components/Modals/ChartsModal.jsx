import { useEffect, useMemo, useRef, useState } from "react";
import ModalShell from "./ModalShell";
import "./ChartsModal.css";
import { BarChart3, LineChart, AreaChart, CalendarDays, Download } from "lucide-react";

import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    BarElement,
    Filler,
    Tooltip,
    Legend,
    Title,
} from "chart.js";

import { Bar, Line } from "react-chartjs-2";

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    BarElement,
    Filler,
    Tooltip,
    Legend,
    Title
);

const TABS = [
    { key: "bar", label: "Barras", icon: BarChart3 },
    { key: "line", label: "Líneas", icon: LineChart },
    { key: "time", label: "Serie temporal", icon: CalendarDays },
    { key: "area", label: "Área", icon: AreaChart },
];

export default function ChartsModal({ open, onClose }) {
    const [tab, setTab] = useState("bar");
    const chartRef = useRef(null);

    const [timeStart, setTimeStart] = useState(0);
    const [timeEnd, setTimeEnd] = useState(8); // ajustar cuando sepamos length real

    // -------- Datos simulados --------
    const states = ["Hidalgo", "Colima", "Baja California Sur", "Nuevo León", "Querétaro", "Quintana Roo", "Chiapas", "Aguascalientes", "México", "Morelos"];

    const barData = useMemo(() => {
    const incendios = [15, 18, 16, 15, 14, 16, 15, 15, 14, 15];
    const hectareas = [28, 31, 37, 42.36, 33, 35, 45.16, 29, 32, 30];
    return {
        labels: states,
        datasets: [
            {
                label: "Hectáreas (ha)",
                data: hectareas,
                borderColor: "#F59E0B",
                backgroundColor: "#F59E0B",
            },
            {
                label: "Incendios",
                data: incendios,
                borderColor: "#0F766E",
                backgroundColor: "#0F766E",
            },
        ],
    };
    }, []);

    const lineData = useMemo(() => {
    const incendios = [16, 15, 15, 14, 15, 15, 14, 15, 14, 13];
    const hectareas = [26, 30, 38, 42, 31, 33, 45, 36, 34, 32];
    return {
        labels: states,
        datasets: [
            {
                label: "Hectáreas (ha)",
                data: hectareas,
                tension: 0.25,
                borderColor: "#F59E0B",
                backgroundColor: "#F59E0B",
                pointRadius: 3.5,
            },
            {
                label: "Incendios",
                data: incendios,
                tension: 0.25,
                borderColor: "#0F766E",
                backgroundColor: "#0F766E",
                pointRadius: 3.5,
            },
        ],
    };
    }, []);

    const timeDataFull = useMemo(() => {
        const months = ["2024-01", "2024-02", "2024-03", "2024-04", "2024-05", "2024-06", "2024-07", "2024-08", "2024-09"];
        const incendios = [1, 2, 3, 4, 3, 2, 4, 1, 3];

        return {
        labels: months,
        datasets: [
            {
                label: "Incendios detectados",
                data: incendios,
                tension: 0.25,
                borderColor: "#DC2626",
                backgroundColor: "#DC2626",
                pointRadius: 2.5,
                fill: false,
            },
        ],
        };
    }, []);

    // Ajusta automáticamente el rango máximo al tamaño real
    const timeMaxIdx = timeDataFull.labels.length - 1;

    useEffect(() => {
        if (tab !== "time") return;

        setTimeStart((s) => Math.max(0, Math.min(s, timeMaxIdx)));
        setTimeEnd((e) => Math.max(0, Math.min(e, timeMaxIdx)));
    }, [tab, timeMaxIdx]);

    const filteredTimeData = useMemo(() => {
        const start = Math.max(0, Math.min(timeStart, timeMaxIdx));
        const end = Math.max(start, Math.min(timeEnd, timeMaxIdx));

        return {
            labels: timeDataFull.labels.slice(start, end + 1),
            datasets: timeDataFull.datasets.map((ds) => ({
                ...ds,
                data: ds.data.slice(start, end + 1),
            })),
        };
    }, [timeDataFull, timeStart, timeEnd, timeMaxIdx]);

    const areaData = useMemo(() => {
    const dates = ["2024-01-20", "2024-01-25", "2024-02-02", "2024-02-10", "2024-02-18", "2024-02-22"];
    const acumulados = [1, 3, 5, 7, 10, 12];
    return {
        labels: dates,
        datasets: [
            {
                label: "Incendios acumulados",
                data: acumulados,
                fill: true,
                tension: 0.25,
                borderColor: "#14B8A6",
                backgroundColor: "rgba(20, 184, 166, 0.35)",
                pointRadius: 3.5,
            },
        ],
    };
    }, []);

    // -------- Opciones comunes (tooltips ON) --------
    const commonOptions = useMemo(
    () => ({
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: true },
            tooltip: {
                enabled: true,
                intersect: false,
                mode: "index",
            },
        },
        scales: {
            x: { ticks: { maxRotation: 45, minRotation: 0 } },
            y: { beginAtZero: true },
        },
    }),
    []
    );

    const timeMiniOptions = useMemo(
        () => ({
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false },
            },
            elements: { point: { radius: 0 } },
            scales: {
                x: { display: false },
                y: { display: false },
            },
        }),
        []
    );

    // -------- Export PNG --------
    const exportPng = () => {
        const chart = chartRef.current;
        if (!chart) return;

        const url = chart.toBase64Image("image/png", 1);
        const a = document.createElement("a");
        a.href = url;
        a.download = `grafica_${tab}.png`;
        a.click();
    };

    const footer = (
        <button className="cmExportBtn" onClick={exportPng} type="button">
            <Download size={16} />
            Exportar
        </button>
    );

    return (
        <ModalShell
            open={open}
            onClose={onClose}
            title="Visualización de datos"
            width={512}
            footer={footer}
            allowOverlayClose={true}
        >
            <div className="cmSub">
                Gráficas y análisis de incendios forestales en México
            </div>

            <div className="cmTabs" role="tablist" aria-label="Tipos de gráfica">
            {TABS.map(({ key, label, icon: Icon }) => (
                <button
                key={key}
                type="button"
                className={`cmTab ${tab === key ? "isActive" : ""}`}
                onClick={() => setTab(key)}
                role="tab"
                aria-selected={tab === key}
                >
                    <Icon size={16} />
                    {label}
                </button>
            ))}
            </div>

            <div className="cmChartTitle">
                {tab === "bar" && "Tendencia de incendios y hectáreas por estado"}
                {tab === "line" && "Tendencia de incendios y hectáreas por estado"}
                {tab === "time" && "Serie temporal de incendios por mes"}
                {tab === "area" && "Área afectada acumulada"}
            </div>

            <div className="cmChartWrap">
                {tab === "bar" && (
                    <Bar ref={chartRef} data={barData} options={commonOptions} />
                )}
                {tab === "line" && (
                    <Line ref={chartRef} data={lineData} options={commonOptions} />
                )}
                {tab === "time" && (
                    <div className="cmTimeLayout">
                        <div className="cmTimeMain">
                        {/* gráfica principal filtrada por el intervalo */}
                            <Line ref={chartRef} data={filteredTimeData} options={commonOptions} />
                        </div>

                        {/*  selector de intervalo */}
                        <div className="cmTimeRange" aria-label="Selector de intervalo">
                            <div className="cmMini">
                                <Line data={timeDataFull} options={timeMiniOptions} />
                            </div>

                            <div className="cmRangeUi">
                                <div className="cmRangeLabels">
                                    <span>{timeDataFull.labels[timeStart]}</span>
                                    <span>{timeDataFull.labels[timeEnd]}</span>
                                </div>

                                <div className="cmDoubleRange">
                                    <input
                                        className="cmRange"
                                        type="range"
                                        min={0}
                                        max={timeMaxIdx}
                                        value={timeStart}
                                        onChange={(e) => {
                                            const v = Number(e.target.value);
                                            setTimeStart(Math.min(v, timeEnd));
                                        }}
                                    />

                                    <input
                                        className="cmRange cmRangeEnd"
                                        type="range"
                                        min={0}
                                        max={timeMaxIdx}
                                        value={timeEnd}
                                        onChange={(e) => {
                                            const v = Number(e.target.value);
                                            setTimeEnd(Math.max(v, timeStart));
                                        }}
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                )}
                {tab === "area" && (
                    <Line
                    ref={chartRef}
                    data={areaData}
                    options={commonOptions}
                    />
                )}
            </div>
        </ModalShell>
    );
}