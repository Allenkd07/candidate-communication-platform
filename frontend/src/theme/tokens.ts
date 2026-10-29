/**
 * Design tokens taken from the Figma file (see docs/PLAN.md §0).
 * Components never use these directly; they read them through the MUI theme.
 */
export const tokens = {
  color: {
    primary: "#4081DD",
    pageBackground: "#F2F2F2",
    surface: "#FFFFFF",
    tableHeader: "#F6F6F6",
    rowSelected: "#E3F2FD",
  },
  // Status chip backgrounds. Read, Failed and Sent are from Figma; the rest are
  // not in Figma and were picked to sit in the same palette.
  status: {
    queued: { bg: "#F5F5F5", fg: "#424242" },
    scheduled: { bg: "#F3E5F5", fg: "#6A1B9A" },
    sent: { bg: "#E3F2FD", fg: "#0D47A1" },
    delivered: { bg: "#E0F2F1", fg: "#00695C" },
    read: { bg: "#E8F5E9", fg: "#1B5E20" },
    failed: { bg: "#FEEBEE", fg: "#B71C1C" },
  },
  size: {
    headerHeight: 72,
    tableRowHeight: 42,
    stickyNameColumnWidth: 288,
    searchFieldWidth: 240,
    dialogWidth: 600,
    drawerWidth: 660,
  },
  radius: 4,
} as const;

export type MessageStatusToken = keyof typeof tokens.status;
