"use client";

import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import type { FormEventHandler, ReactNode } from "react";
import { useId } from "react";

import { panelBackdrop, panelFields, PanelActions, PanelTitle } from "./PanelParts";

// Dialogs sit this far from the top instead of being centred.
const TOP_OFFSET = 150;

type DialogShellProps = {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  actions: ReactNode;
  /** Height from the design; content taller than this grows the dialog. */
  minHeight?: number;
  /** Wraps the dialog in a form, so Enter submits it. */
  onSubmit?: FormEventHandler<HTMLFormElement>;
  /** Called after the open transition. Focus fields here: the focus trap undoes autoFocus. */
  onEntered?: () => void;
  /** Called after the close transition. */
  onExited?: () => void;
  /** Keeps the dialog open on backdrop clicks. */
  ignoreBackdropClick?: boolean;
};

/** The design's dialog: title with a close button, content, and a bottom bar of right-aligned actions. */
export function DialogShell({
  open,
  title,
  onClose,
  children,
  actions,
  minHeight,
  onSubmit,
  onEntered,
  onExited,
  ignoreBackdropClick = false,
}: DialogShellProps) {
  const titleId = useId();

  const body = (
    <>
      <Box sx={{ px: 5, pt: 5, pb: 2, display: "flex", flexDirection: "column", gap: 6 }}>
        <PanelTitle id={titleId} title={title} onClose={onClose} />
        <Box sx={panelFields}>{children}</Box>
      </Box>
      <PanelActions>{actions}</PanelActions>
    </>
  );

  return (
    <Dialog
      open={open}
      onClose={(_, reason) => {
        if (reason === "backdropClick" && ignoreBackdropClick) return;
        onClose();
      }}
      fullWidth
      aria-labelledby={titleId}
      sx={{ "& .MuiDialog-container": { alignItems: { md: "flex-start" } } }}
      slotProps={{
        backdrop: { sx: panelBackdrop },
        paper: {
          sx: (theme) => ({
            maxWidth: theme.size.dialogWidth,
            minHeight,
            mt: { md: `${TOP_OFFSET}px` },
            borderRadius: 0,
            // An outline instead of a border takes no space from the content.
            outline: `1px solid ${theme.palette.dialog.border}`,
            outlineOffset: -1,
            boxShadow: theme.palette.dialog.shadow,
            display: "flex",
            flexDirection: "column",
          }),
        },
        transition: { onEntered, onExited },
      }}
    >
      {onSubmit ? (
        <Box component="form" onSubmit={onSubmit} noValidate sx={{ display: "contents" }}>
          {body}
        </Box>
      ) : (
        body
      )}
    </Dialog>
  );
}
