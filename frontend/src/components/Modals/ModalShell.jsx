import { useEffect } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import "./ModalShell.css";

export default function ModalShell({
    open,
    title,
    children,
    onClose,
    footer = null,
    width = 720,
    allowOverlayClose = true,
}) {
    useEffect(() => {
        if (!open) return;

        const onKeyDown = (e) => {
            if (e.key === "Escape") onClose?.();
        };
        window.addEventListener("keydown", onKeyDown);

        const prev = document.body.style.overflow;
        document.body.style.overflow = "hidden";

        return () => {
            window.removeEventListener("keydown", onKeyDown);
            document.body.style.overflow = prev;
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
            <div className="ms-dialog" style={{ width }}>
                <div className="ms-header">
                    <h2 className="ms-title">{title}</h2>
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