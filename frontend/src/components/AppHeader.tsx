"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

// Client component because `sx` callbacks that read the theme cannot be passed from Server Components.
export function AppHeader() {
  return (
    <Box
      component="header"
      sx={{
        height: (theme) => theme.size.headerHeight,
        px: 3,
        display: "flex",
        alignItems: "center",
        bgcolor: "background.paper",
      }}
    >
      <Typography variant="h1">Candidate communication</Typography>
    </Box>
  );
}
