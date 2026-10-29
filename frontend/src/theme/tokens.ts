/**
 * Design tokens from the Figma file.
 * Components read them through the MUI theme, never directly.
 */
export const tokens = {
  color: {
    primary: "#4081DD",
    pageBackground: "#F2F2F2",
    surface: "#FFFFFF",
    tableHeader: "#F6F6F6",
    rowSelected: "#E3F2FD",
  },
  // Status chip colours. Read, Failed and Sent come from Figma; Queued, Scheduled and
  // Delivered extend the same palette.
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
