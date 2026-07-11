import type { Metadata } from "next";

export const metadata: Metadata = {
  title: {
    template: "%s | Atelier Marie",
    default: "Atelier Marie | Luxury Handcrafted Candles",
  },
  description:
    "Luxury handcrafted candles for your home. Artisan scents made with love.",
  icons: {
    icon: "/favicon.svg",
  },
};

// Root layout is a bare shell — locale-aware rendering lives in [locale]/layout.tsx
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}
