import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "PharmacyFinder – AI-ranked pharmacies near you",
  description:
    "Find your nearest open pharmacy ranked by AI. A Greater London prototype built for SOFISTICA AI Hackathon 2026. Not for clinical use.",
};

// ---------------------------------------------------------------------------
// Root layout – every page renders through this template.
// SafetyBanner is rendered inside page.tsx so it gets the app context,
// but this layout ensures the baseline HTML structure is always present.
// ---------------------------------------------------------------------------

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>{children}</body>
    </html>
  );
}
