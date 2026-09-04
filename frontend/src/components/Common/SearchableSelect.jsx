import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ChevronDown } from "lucide-react";
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
  const triggerRef = useRef(null);
  const popoverRef = useRef(null);
  const searchRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [popoverStyle, setPopoverStyle] = useState(null);

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

  const closeAndReturnFocus = () => {
    setOpen(false);
    setQuery("");
    window.requestAnimationFrame(() => triggerRef.current?.focus());
  };

  const focusOption = (direction = 1) => {
    const optionsButtons = Array.from(popoverRef.current?.querySelectorAll(".searchableSelectOption") || []);
    if (!optionsButtons.length) return;
    const currentIndex = optionsButtons.indexOf(document.activeElement);
    const nextIndex = currentIndex < 0
      ? (direction > 0 ? 0 : optionsButtons.length - 1)
      : Math.max(0, Math.min(optionsButtons.length - 1, currentIndex + direction));
    optionsButtons[nextIndex]?.focus();
  };

  useEffect(() => {
    const handleOutside = (event) => {
      if (rootRef.current?.contains(event.target) || popoverRef.current?.contains(event.target)) return;
      setOpen(false);
    };
    document.addEventListener("pointerdown", handleOutside);
    return () => document.removeEventListener("pointerdown", handleOutside);
  }, []);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setPopoverStyle(null);
      return undefined;
    }

    const position = () => {
      const rect = rootRef.current?.getBoundingClientRect();
      if (!rect) return;

      const gap = 6;
      const viewportPadding = 12;
      const optionRows = Math.max(3, Math.min(maxVisible, 7));
      const desiredHeight = 54 + optionRows * 38;
      const availableBelow = window.innerHeight - rect.bottom - gap - viewportPadding;
      const availableAbove = rect.top - gap - viewportPadding;
      const openUpward = availableBelow < Math.min(desiredHeight, 170) && availableAbove > availableBelow;
      const availableHeight = openUpward ? availableAbove : availableBelow;
      const maxHeight = Math.max(118, Math.min(desiredHeight, availableHeight));
      const width = Math.min(rect.width, window.innerWidth - viewportPadding * 2);
      const left = Math.min(
        Math.max(viewportPadding, rect.left),
        Math.max(viewportPadding, window.innerWidth - width - viewportPadding),
      );
      const top = openUpward
        ? Math.max(viewportPadding, rect.top - gap - maxHeight)
        : rect.bottom + gap;

      setPopoverStyle({
        left,
        top,
        width,
        maxHeight,
        "--visible-options": optionRows,
      });
    };

    const rafId = window.requestAnimationFrame(position);
    window.addEventListener("resize", position);
    window.addEventListener("scroll", position, true);
    return () => {
      window.cancelAnimationFrame(rafId);
      window.removeEventListener("resize", position);
      window.removeEventListener("scroll", position, true);
    };
  }, [open, maxVisible]);

  const choose = (option) => {
    onChange?.(String(option.value));
    closeAndReturnFocus();
  };

  const handlePopoverKeyDown = (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      closeAndReturnFocus();
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      focusOption(1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      focusOption(-1);
    }
  };

  return (
    <div className="field searchableField" ref={rootRef}>
      {label ? <label htmlFor={id}>{label}</label> : null}
      <div className={`searchableSelect ${disabled ? "isDisabled" : ""}`}>
        <button
          ref={triggerRef}
          id={id}
          className="searchableSelectTrigger"
          type="button"
          disabled={disabled}
          aria-haspopup="listbox"
          aria-expanded={open}
          onClick={() => setOpen((current) => !current)}
          onKeyDown={(event) => {
            if (event.key === "ArrowDown" || event.key === "ArrowUp") {
              event.preventDefault();
              setOpen(true);
              window.requestAnimationFrame(() => searchRef.current?.focus());
            }
          }}
        >
          <span className={value ? "" : "placeholder"}>{selected?.label || placeholder}</span>
          <ChevronDown size={16} aria-hidden="true" />
        </button>

        {open && popoverStyle ? createPortal(
          <div ref={popoverRef} className="searchableSelectPopover searchableSelectPortal" style={popoverStyle} onKeyDown={handlePopoverKeyDown}>
            <div className="searchableSelectSearchWrap">
              <input
                ref={searchRef}
                className="searchableSelectSearch"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={searchPlaceholder}
                autoFocus
                aria-label={searchPlaceholder}
              />
            </div>
            <div className="searchableSelectList" role="listbox">
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
          </div>,
          document.body
        ) : null}
      </div>
    </div>
  );
}
