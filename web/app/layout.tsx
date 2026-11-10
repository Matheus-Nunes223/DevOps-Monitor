import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "DevOps Monitor",
    template: "%s · DevOps Monitor",
  },
  description: "Painel seguro de monitoramento de infraestrutura DevOps.",
  applicationName: "DevOps Monitor",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
