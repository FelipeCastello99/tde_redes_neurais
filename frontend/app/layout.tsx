import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TDE Redes Neurais",
  description: "Dashboard de Treinamento e Simulação PRF 2024",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
