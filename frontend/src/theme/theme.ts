"use client";

import { createTheme, type PaletteColor, type PaletteColorOptions } from "@mui/material/styles";

import { type MessageStatusToken, tokens } from "./tokens";

type StatusPalette = Record<MessageStatusToken, { bg: string; fg: string }>;
type Sizes = typeof tokens.size;
type TablePalette = { header: string; headerBorder: string; rowBorder: string; rowSelected: string };
type DialogPalette = {
  border: string;
  icon: string;
  fieldLabel: string;
  overlay: string;
  shadow: string;
  chip: string;
};

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
    table: TablePalette;
    accent: PaletteColor;
    dialog: DialogPalette;
    muted: string;
    icon: string;
    fieldBorder: string;
  }
  interface PaletteOptions {
    status?: StatusPalette;
    table?: TablePalette;
    accent?: PaletteColorOptions;
    dialog?: DialogPalette;
    muted?: string;
    icon?: string;
    fieldBorder?: string;
  }
}

declare module "@mui/material/Button" {
  interface ButtonPropsColorOverrides {
    accent: true;
  }
}

declare module "@mui/material/IconButton" {
  interface IconButtonPropsColorOverrides {
    accent: true;
  }
}

const { color } = tokens;
const { palette: base } = createTheme();

export const theme = createTheme({
  palette: {
    primary: { main: color.primary },
    background: { default: color.pageBackground, paper: color.surface },
    text: { primary: color.text },
    status: tokens.status,
    table: {
      header: color.tableHeader,
      headerBorder: color.tableHeaderBorder,
      rowBorder: color.tableRowBorder,
      rowSelected: color.rowSelected,
    },
    accent: base.augmentColor({ color: { main: color.accent }, name: "accent" }),
    dialog: {
      border: color.dialogBorder,
      icon: color.dialogIcon,
      fieldLabel: color.fieldLabel,
      overlay: color.overlay,
      shadow: color.panelShadow,
      chip: color.chip,
    },
    muted: color.muted,
    icon: color.icon,
    fieldBorder: color.fieldBorder,
  },
  shape: { borderRadius: tokens.radius },
  size: tokens.size,
  typography: {
    // Lato is loaded by next/font in the root layout and exposed as this CSS variable.
    fontFamily: "var(--font-lato), Arial, sans-serif",
    h1: { fontSize: 24, lineHeight: 1.2, fontWeight: 700, color: color.title },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          padding: "6px 16px",
          lineHeight: "24px",
          letterSpacing: 0.4,
          // The 1px outline is part of the padding, so both variants are the same size.
          "&.MuiButton-outlined": { padding: "5px 15px" },
          "&.MuiButton-outlinedPrimary:not(.Mui-disabled)": {
            color: color.accent,
            borderColor: `color-mix(in srgb, ${color.accent} 50%, transparent)`,
          },
        },
      },
    },
    MuiCheckbox: {
      styleOverrides: {
        root: {
          color: color.muted,
          "& .MuiSvgIcon-root": { fontSize: 20 },
          "&.Mui-checked, &.MuiCheckbox-indeterminate": { color: color.accent },
          "&.Mui-checked .MuiSvgIcon-root, &.MuiCheckbox-indeterminate .MuiSvgIcon-root": { fontSize: 24 },
        },
      },
    },
    MuiInputBase: {
      styleOverrides: {
        input: { "&::placeholder": { color: color.placeholder, opacity: 1 } },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        notchedOutline: { borderColor: color.fieldBorder },
      },
    },
    MuiTableRow: {
      styleOverrides: {
        root: ({ theme }) => ({
          height: tokens.size.tableRowHeight,
          "&.Mui-selected, &.Mui-selected:hover": { backgroundColor: theme.palette.table.rowSelected },
        }),
        head: ({ theme }) => ({ height: tokens.size.tableHeaderHeight, backgroundColor: theme.palette.table.header }),
      },
    },
    MuiTableCell: {
      styleOverrides: {
        // The 1px bottom border counts towards the 42px row height.
        root: {
          padding: "8px 12px 7px",
          fontSize: 14,
          lineHeight: "26px",
          borderBottom: `1px solid ${color.tableRowBorder}`,
        },
        head: {
          fontWeight: 700,
          backgroundColor: color.tableHeader,
          borderBottom: `1px solid ${color.tableHeaderBorder}`,
        },
      },
    },
  },
});
