"use client";

import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import SearchIcon from "@mui/icons-material/Search";
import SendIcon from "@mui/icons-material/Send";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import InputAdornment from "@mui/material/InputAdornment";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useEffect, useRef, useState } from "react";

const SEARCH_DEBOUNCE_MS = 300;

type AppHeaderProps = {
  selectedCount: number;
  search: string;
  onSearchChange: (search: string) => void;
  onAdd: () => void;
  onDelete: () => void;
  onSend: () => void;
};

export function AppHeader({ selectedCount, search, onSearchChange, onAdd, onDelete, onSend }: AppHeaderProps) {
  const nothingSelected = selectedCount === 0;

  return (
    <Box
      component="header"
      sx={{
        minHeight: (theme) => theme.size.headerHeight,
        px: 3,
        py: 1,
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        justifyContent: "space-between",
        rowGap: 1,
        bgcolor: "background.paper",
      }}
    >
      <Typography variant="h1">Candidate communication</Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 1 }}>
          <Button variant="outlined" startIcon={<AddIcon />} onClick={onAdd}>
          Add candidate
        </Button>
        <Button variant="contained" startIcon={<DeleteIcon />} disabled={nothingSelected} onClick={onDelete}>
          Delete candidate
        </Button>
        <Button variant="contained" startIcon={<SendIcon />} disabled={nothingSelected} onClick={onSend}>
          Send message
        </Button>
        <SearchField value={search} onChange={onSearchChange} />
      </Box>
    </Box>
  );
}

/** Updates the parent once typing pauses, so each keystroke doesn't trigger a request. */
function SearchField({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const [draft, setDraft] = useState(value);
  const [syncedValue, setSyncedValue] = useState(value);
  const onChangeRef = useRef(onChange);

  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  // The URL changed externally (back button, shared link).
  if (value !== syncedValue) {
    setSyncedValue(value);
    setDraft(value);
  }

  useEffect(() => {
    if (draft.trim() === value.trim()) return;
    const timer = setTimeout(() => onChangeRef.current(draft.trim()), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [draft, value]);

  return (
    <TextField
      size="small"
      placeholder="Search"
      value={draft}
      onChange={(event) => setDraft(event.target.value)}
      sx={(theme) => ({
        width: { xs: "100%", sm: theme.size.searchFieldWidth },
        "& .MuiOutlinedInput-root": { height: 40, pl: 1.5, pr: 2, fontSize: 14 },
      })}
      slotProps={{
        htmlInput: { "aria-label": "Search candidates", maxLength: 100 },
        input: {
          startAdornment: (
            <InputAdornment position="start" sx={{ minWidth: 24, mr: 0, color: "common.black" }}>
              <SearchIcon sx={{ fontSize: 16 }} />
            </InputAdornment>
          ),
        },
      }}
    />
  );
}
