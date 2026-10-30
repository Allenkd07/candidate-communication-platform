import { z } from "zod";

// Mirrors the backend rules so most mistakes are caught before submitting; the backend
// stays authoritative (e.g. it checks the number is a real mobile number).
export const candidateSchema = z.object({
  full_name: z
    .string()
    .trim()
    .min(1, "Enter the candidate's name.")
    .min(2, "Enter at least 2 characters.")
    .max(100, "Keep the name under 100 characters.")
    .regex(/^\p{L}[\p{L}\p{M} .'-]*$/u, "Use letters, spaces and . ' - only."),
  phone: z
    .string()
    .trim()
    .min(1, "Enter a mobile number.")
    .refine((value) => /^\+?\d{7,15}$/.test(value.replace(/[\s()-]/g, "")), "Enter a valid mobile number."),
  email: z.string().trim().min(1, "Enter an email address.").pipe(z.email("Enter a valid email address.")),
});

export type CandidateFormValues = z.input<typeof candidateSchema>;
