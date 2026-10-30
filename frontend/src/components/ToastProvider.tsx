"use client";

import Alert, { type AlertColor } from "@mui/material/Alert";
import Snackbar from "@mui/material/Snackbar";
import { createContext, type ReactNode, useCallback, useContext, useMemo, useState } from "react";

const AUTO_HIDE_MS = 4000;

type Toast = { key: number; message: string; severity: AlertColor };
type ShowToast = (message: string, severity?: AlertColor) => void;

const ToastContext = createContext<ShowToast | null>(null);

/** One toast at a time, bottom-right, as in the design. A new toast replaces the current one. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<Toast | null>(null);
  const [open, setOpen] = useState(false);

  const show = useCallback<ShowToast>((message, severity = "success") => {
    setToast({ key: Date.now(), message, severity });
    setOpen(true);
  }, []);

  const value = useMemo(() => show, [show]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <Snackbar
        key={toast?.key}
        open={open}
        autoHideDuration={AUTO_HIDE_MS}
        onClose={(_, reason) => {
          if (reason !== "clickaway") setOpen(false);
        }}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        sx={{ "@media (min-width: 600px)": { right: 18, bottom: 20 } }}
      >
        <Alert
          severity={toast?.severity ?? "success"}
          variant="standard"
          sx={{ "& .MuiAlert-message": { fontSize: 16, lineHeight: "24px", fontWeight: 500, letterSpacing: 0.15 } }}
        >
          {toast?.message}
        </Alert>
      </Snackbar>
    </ToastContext.Provider>
  );
}

export function useToast(): ShowToast {
  const show = useContext(ToastContext);
  if (!show) {
    throw new Error("useToast must be used inside ToastProvider.");
  }
  return show;
}
