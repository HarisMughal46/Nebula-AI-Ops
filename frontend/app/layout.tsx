import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Nebula AI Ops",
  description: "Realtime AI-assisted system observability",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased font-sans">{children}</body>
    </html>
  );
}
