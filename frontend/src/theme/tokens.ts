/**
 * Design tokens from the Figma file.
 * Components read them through the MUI theme, never directly.
 */
export const tokens = {
  color: {
    primary: "#4081DD",
    // Outlined buttons, dialog buttons and checkboxes.
    accent: "#2196F3",
    dialogBorder: "#BDBDBD",
    dialogIcon: "#747474",
    fieldLabel: "#616161",
    chip: "#ECEFF1",
    overlay: "rgba(0, 0, 0, 0.12)",
    panelShadow: "-2px 0 12px rgba(0, 0, 0, 0.16)",
    pageBackground: "#F2F2F2",
    surface: "#FFFFFF",
    title: "#000000",
    text: "#212121",
    placeholder: "#717171",
    muted: "#9D9D9D",
    icon: "#757575",
    fieldBorder: "#CCCCCC",
    tableHeader: "#F6F6F6",
    tableHeaderBorder: "#CCCCCC",
    tableRowBorder: "#EEEEEE",
    rowSelected: "#E3F2FD",
  },
  // Status chip colours. Read, Failed and Sent come from Figma; Queued, Scheduled and
  // Delivered extend the same palette.
  status: {
    queued: { bg: "#F5F5F5", fg: "#424242" },
    scheduled: { bg: "#F3E5F5", fg: "#6A1B9A" },
    sent: { bg: "#E3F2FD", fg: "#1565C0" },
    delivered: { bg: "#E0F2F1", fg: "#00695C" },
    read: { bg: "#E8F5E9", fg: "#2E7D32" },
    failed: { bg: "#FEEBEE", fg: "#C62828" },
  },
  size: {
    headerHeight: 72,
    tableHeaderHeight: 48,
    tableRowHeight: 42,
    checkboxColumnWidth: 48,
    stickyNameColumnWidth: 288,
    dataColumnWidth: 282,
    searchFieldWidth: 240,
    dialogWidth: 600,
    drawerWidth: 660,
  },
  radius: 4,
} as const;

export type MessageStatusToken = keyof typeof tokens.status;
