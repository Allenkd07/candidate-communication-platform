"use client";

import { createTheme } from "@mui/material/styles";

import { type MessageStatusToken, tokens } from "./tokens";

type StatusPalette = Record<MessageStatusToken, { bg: string; fg: string }>;
type Sizes = typeof tokens.size;

declare module "@mui/material/styles" {
  // Fixed layout sizes from Figma, read in `sx` as `(theme) => theme.size.<name>`.
  interface Theme {
    size: Sizes;
  }
  interface ThemeOptions {
    size?: Sizes;
  }
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
  size: tokens.size,
  typography: {
    // Lato is loaded by next/font in the root layout and exposed as this CSS variable.
    fontFamily: "var(--font-lato), Arial, sans-serif",
    // Lato ships no 500 weight; MUI uses fontWeightMedium for buttons, tabs and table headers.
    fontWeightMedium: 700,
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
