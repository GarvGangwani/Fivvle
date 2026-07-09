import type { Metadata } from "next";
import { HomePageContent } from "@/components/home/HomePageContent";

export const metadata: Metadata = {
  title: "Fivvle — Validate Your Startup Idea",
  description:
    "Turn your startup idea into a defensible proceed or kill decision with cited market research and real behavioral signal.",
};

export default function HomePage() {
  return <HomePageContent />;
}
