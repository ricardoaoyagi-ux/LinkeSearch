import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { APP_VERSION } from "@/lib/version";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "LinkeSearch",
  description: "Vagas do LinkedIn em uma lista única, ordenada e com status claro",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        {children}
        <span
          className="pointer-events-none fixed right-2 bottom-1 z-50 text-[11px] text-slate-400 select-none"
          title="Versão do LinkeSearch"
        >
          LinkeSearch {APP_VERSION}
        </span>
      </body>
    </html>
  );
}
