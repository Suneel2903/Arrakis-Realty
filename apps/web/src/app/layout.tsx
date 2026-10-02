import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Arrakis Realty",
  description: "Verified Bengaluru homes on a 3D city map",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col">{children}</body>
    </html>
  );
}
