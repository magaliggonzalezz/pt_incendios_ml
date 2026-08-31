import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, X } from "lucide-react";
import "./SearchableSelect.css";

export default function SearchableSelect({
  id,
  label,
  value = "",
  options = [],
  placeholder = "Selecciona una opción",
  searchPlaceholder = "Buscar...",
  disabled = false,
  maxVisible = 7,
  onChange,
}) {
  const rootRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  const availableOptions = useMemo(() => {
    if (options.some((option) => String(option.value) === "")) return options;
    return [{ value: "", label: placeholder }, ...options];
  }, [options, placeholder]);

  const selected = availableOptions.find((option) => String(option.value) === String(value));
  const normalizedQuery = query.trim().toLocaleLowerCase("es-MX");
  const filtered = useMemo(() => {
    if (!normalizedQuery) return availableOptions;
    return availableOptions.filter((option) =>
      `${option.label} ${option.meta || ""}`.toLocaleLowerCase("es-MX").includes(normalizedQuery)
    );
  }, [availableOptions, normalizedQuery]);

  useEffect(() => {
    const handleOutside = (event) => {
      if (!rootRef.current?.contains(event.target)) setOpen(false);
    };
    document.addEventListener("pointerdown", handleOutside);
    return () => document.removeEventListener("pointerdown", handleOutside);
  }, []);

  useEffect(() => {
    if (!open) setQuery("");
  }, [open]);

  const choose = (option) => {
    onChange?.(String(option.value));
    setOpen(false);
    setQuery("");
  };

  return (
    <div className="field searchableField" ref={rootRef}>
      {label ? <label htmlFor={id}>{label}</label> : null}
      <div className={`searchableSelect ${disabled ? "isDisabled" : ""}`}>
        <button
          id={id}
          className="searchableSelectTrigger"
          type="button"
          disabled={disabled}
          aria-haspopup="listbox"
          aria-expanded={open}
          onClick={() => setOpen((current) => !current)}
        >
          <span className={value ? "" : "placeholder"}>{selected?.label || placeholder}</span>
          <ChevronDown size={16} aria-hidden="true" />
        </button>

        {open ? (
          <div className="searchableSelectPopover">
            <div className="searchableSelectSearchWrap">
              <input
                className="searchableSelectSearch"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={searchPlaceholder}
                autoFocus
                aria-label={searchPlaceholder}
              />
              {query ? (
                <button type="button" className="searchableSelectClear" aria-label="Limpiar búsqueda" onClick={() => setQuery("")}>
                  <X size={14} />
                </button>
              ) : null}
            </div>
            <div className="searchableSelectList" role="listbox" style={{ "--visible-options": Math.max(3, Math.min(maxVisible, 9)) }}>
              {filtered.map((option) => (
                <button
                  type="button"
                  role="option"
                  aria-selected={String(option.value) === String(value)}
                  className={`searchableSelectOption ${String(option.value) === String(value) ? "isSelected" : ""}`}
                  key={`${id}-${option.value || "empty"}`}
                  onClick={() => choose(option)}
                >
                  <span>{option.label}</span>
                  {option.meta ? <small>{option.meta}</small> : null}
                </button>
              ))}
              {!filtered.length ? <div className="searchableSelectEmpty">Sin coincidencias</div> : null}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
