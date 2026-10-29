"use client";

import { createTheme } from "@mui/material/styles";

import { type MessageStatusToken, tokens } from "./tokens";

type StatusPalette = Record<MessageStatusToken, { bg: string; fg: string }>;

declare module "@mui/material/styles" {
  interface Palette {
    status: StatusPalette;
    table: { header: string; rowSelected: string };
  }
  interface PaletteOptions {
    status?: StatusPalette;
    table?: { header: string; rowSelected: string };
  }
}

export const theme = createTheme({
  palette: {
    primary: { main: tokens.color.primary },
    background: { default: tokens.color.pageBackground, paper: tokens.color.surface },
    status: tokens.status,
    table: { header: tokens.color.tableHeader, rowSelected: tokens.color.rowSelected },
  },
  shape: { borderRadius: tokens.radius },
  typography: {
    // The Lato font is loaded by next/font in the root layout and exposed as this variable.
    fontFamily: "var(--font-lato), Arial, sans-serif",
    h1: { fontSize: 24, fontWeight: 700 },
  },
  components: {
    MuiButton: {
      defaultProps: { disableElevation: true },
    },
    MuiTableRow: {
      styleOverrides: {
        root: ({ theme }) => ({
          height: tokens.size.tableRowHeight,
          "&.Mui-selected, &.Mui-selected:hover": { backgroundColor: theme.palette.table.rowSelected },
        }),
        head: ({ theme }) => ({ backgroundColor: theme.palette.table.header }),
      },
    },
  },
});
