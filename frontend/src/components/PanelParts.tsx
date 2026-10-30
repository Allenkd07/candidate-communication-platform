"use client";

import CloseIcon from "@mui/icons-material/Close";
import Box from "@mui/material/Box";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import type { ReactNode } from "react";

/** Title row shared by dialogs and drawers: bold title, close cross at the far right. */
export function PanelTitle({ id, title, onClose }: { id: string; title: string; onClose: () => void }) {
  return (
    <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <Typography id={id} component="h2" sx={{ fontSize: 20, lineHeight: "24px", fontWeight: 700 }}>
        {title}
      </Typography>
      <IconButton aria-label="Close" onClick={onClose} sx={{ p: 0, width: 24, height: 24, color: "dialog.icon" }}>
        {/* MUI's cross fills 14/24 of its box; this makes it 16px wide. */}
        <CloseIcon sx={{ fontSize: 16 * (24 / 14) }} />
      </IconButton>
    </Box>
  );
}

/** Bottom bar shared by dialogs and drawers: a divider above right-aligned actions. */
export function PanelActions({ children }: { children: ReactNode }) {
  return (
    <Box
      sx={{
        mt: "auto",
        height: 96,
        flexShrink: 0,
        px: 5,
        display: "flex",
        alignItems: "center",
        justifyContent: "flex-end",
        gap: 1.5,
        boxShadow: (theme) => `inset 0 1px 0 ${theme.palette.table.rowBorder}`,
      }}
    >
      {children}
    </Box>
  );
}

/** Outlined text fields as drawn in the design's dialogs and drawers. */
export const panelFields = {
  "& .MuiOutlinedInput-notchedOutline": {
    borderColor: "dialog.border",
    px: 1.5,
    // Unlabelled fields have an empty legend, which must not open a gap in the border.
    "& legend > span:not(.notranslate)": { px: 0.5 },
  },
  "& .MuiInputBase-input": { fontSize: 16, lineHeight: "24px", letterSpacing: 0.15 },
  "& .MuiInputBase-input:not(textarea)": { px: 1.5, py: 2, height: 24 },
  "& .MuiInputBase-multiline": { px: 1.5, py: 2 },
  "& .MuiInputLabel-root": {
    color: "dialog.fieldLabel",
    letterSpacing: 0.15,
    transform: "translate(12px, 16px) scale(1)",
  },
  "& .MuiInputLabel-shrink": { transform: "translate(16px, -9px) scale(0.75)" },
  "& .MuiFormLabel-asterisk": { color: "error.main" },
} as const;

/** The dimmed, blurred page behind dialogs and drawers. */
export const panelBackdrop = { bgcolor: "dialog.overlay", backdropFilter: "blur(1.5px)" } as const;
