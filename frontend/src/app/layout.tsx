import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Chronos Memory | Temporal Knowledge Graph for Conversational AI",
  description: "Cost-Efficient Temporal Knowledge Graph Memory for Conversational AI Agents. B.Tech CSE (AI & ML) Major Project.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased selection:bg-cyan-500/20 selection:text-cyan-200">
        {children}
      </body>
    </html>
  );
}
