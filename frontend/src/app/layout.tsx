import { AppRouterCacheProvider } from "@mui/material-nextjs/v16-appRouter";
import type { Metadata } from "next";
import localFont from "next/font/local";

import { Providers } from "./providers";

// Lato 2.0 (SIL OFL, see fonts/OFL.txt). Google Fonts serves only Lato 1, which lacks the
// 500 and 600 weights the design uses.
const lato = localFont({
  src: [
    { path: "./fonts/lato-normal.woff2", weight: "400", style: "normal" },
    { path: "./fonts/lato-medium.woff2", weight: "500", style: "normal" },
    { path: "./fonts/lato-semibold.woff2", weight: "600", style: "normal" },
    { path: "./fonts/lato-bold.woff2", weight: "700", style: "normal" },
  ],
  display: "swap",
  variable: "--font-lato",
});

export const metadata: Metadata = {
  title: "Candidate communication",
  description: "Manage candidates and track the messages you send them.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={lato.variable}>
      {/* Extensions add attributes to <body> before hydration; ignored on this element only. */}
      <body suppressHydrationWarning>
        <AppRouterCacheProvider>
          <Providers>{children}</Providers>
        </AppRouterCacheProvider>
      </body>
    </html>
  );
}
