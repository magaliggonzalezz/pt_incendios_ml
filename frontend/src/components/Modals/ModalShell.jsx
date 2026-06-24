import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import "./ModalShell.css";

const titleToId = (title = "modal") =>
    `modal-${String(title).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}-title`;

export default function ModalShell({
    open,
    title,
    children,
    onClose,
    footer = null,
    width = 720,
    allowOverlayClose = true,
}) {
    const titleId = titleToId(title);
    const dialogRef = useRef(null);
    const previousFocusRef = useRef(null);

    useEffect(() => {
        if (!open) return;

        const onKeyDown = (e) => {
            if (e.key === "Escape") {
                onClose?.();
                return;
            }

            if (e.key !== "Tab") return;

            const focusable = dialogRef.current?.querySelectorAll(
                [
                    "a[href]",
                    "button:not([disabled])",
                    "textarea:not([disabled])",
                    "input:not([disabled])",
                    "select:not([disabled])",
                    "[tabindex]:not([tabindex='-1'])",
                ].join(",")
            );
            const items = Array.from(focusable ?? []).filter((item) => item.offsetParent !== null);
            if (!items.length) return;

            const first = items[0];
            const last = items[items.length - 1];

            if (e.shiftKey && document.activeElement === first) {
                e.preventDefault();
                last.focus();
            } else if (!e.shiftKey && document.activeElement === last) {
                e.preventDefault();
                first.focus();
            }
        };

        previousFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;

        window.setTimeout(() => {
            const firstFocusable = dialogRef.current?.querySelector(
                "button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])"
            );
            if (firstFocusable instanceof HTMLElement) {
                firstFocusable.focus();
            } else {
                dialogRef.current?.focus();
            }
        }, 0);

        window.addEventListener("keydown", onKeyDown);

        const prev = document.body.style.overflow;
        document.body.style.overflow = "hidden";

        return () => {
            window.removeEventListener("keydown", onKeyDown);
            document.body.style.overflow = prev;
            previousFocusRef.current?.focus?.();
        };
    }, [open, onClose]);

    if (!open) return null;

    return createPortal(
        <div
        className="ms-overlay"
        onMouseDown={(e) => {
            if (!allowOverlayClose) return;
            if (e.target === e.currentTarget) onClose?.();
        }}
        >
            <div
            ref={dialogRef}
            className="ms-dialog"
            style={{ width }}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
            tabIndex={-1}
            >
                <div className="ms-header">
                    <h2 className="ms-title" id={titleId}>{title}</h2>
                    <button className="ms-close" onClick={onClose} aria-label="Cerrar modal">
                        <X size={18} />
                    </button>
                </div>
                <div className="ms-body">{children}</div>
                {footer ? <div className="ms-footer">{footer}</div> : null}
            </div>
        </div>,
        document.body
    );
}
