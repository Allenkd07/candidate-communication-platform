"use client";

import Box from "@mui/material/Box";
import Drawer from "@mui/material/Drawer";
import type { ReactNode } from "react";
import { useId } from "react";

import { panelBackdrop, panelFields, PanelActions, PanelTitle } from "./PanelParts";

type DrawerShellProps = {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  /** Pinned to the bottom of the drawer. */
  footer?: ReactNode;
};

/** The design's right-hand drawer: title with a close button, scrolling body, pinned bottom bar. */
export function DrawerShell({ open, title, onClose, children, footer }: DrawerShellProps) {
  const titleId = useId();

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      slotProps={{
        backdrop: { sx: panelBackdrop },
        paper: {
          "aria-labelledby": titleId,
          sx: (theme) => ({
            width: { xs: "100%", sm: theme.size.drawerWidth },
            display: "flex",
            boxShadow: theme.palette.dialog.shadow,
          }),
        },
      }}
    >
      <Box sx={{ px: 5, pt: 5, pb: 6 }}>
        <PanelTitle id={titleId} title={title} onClose={onClose} />
      </Box>
      <Box sx={[panelFields, { flex: 1, overflowY: "auto", px: 5, pb: 3 }]}>{children}</Box>
      {footer && <PanelActions>{footer}</PanelActions>}
    </Drawer>
  );
}
