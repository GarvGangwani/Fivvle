import type { Metadata } from "next";
import { DM_Mono, Inter } from "next/font/google";
import { AppProviders } from "@/components/providers/AppProviders";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-inter",
  display: "swap",
});

const dmMono = DM_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-dm-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Fivvle — Validate Your Startup Idea",
  description: "Validate your startup idea with real signal.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`h-full antialiased ${inter.variable} ${dmMono.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem("fivvle-theme");var m=localStorage.getItem("fivvle-reduced-motion");if(m==="true")document.documentElement.setAttribute("data-reduced-motion","true");var r=t==="light"?"light":t==="dark"?"dark":t==="system"?(window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"):"dark";document.documentElement.setAttribute("data-theme",r);}catch(e){document.documentElement.setAttribute("data-theme","dark");}})();`,
          }}
        />
      </head>
      <body className="flex min-h-full flex-col">
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
