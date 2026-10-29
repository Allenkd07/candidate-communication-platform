import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";

import { tokens } from "@/theme/tokens";

// Placeholder until Phase 3 builds the candidate table.
export default function HomePage() {
  return (
    <Box
      component="header"
      sx={{
        height: tokens.size.headerHeight,
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
