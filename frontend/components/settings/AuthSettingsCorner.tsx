import { SettingsButton } from "@/components/settings/SettingsButton";

export function AuthSettingsCorner() {
  return (
    <div className="absolute right-4 top-4 z-10 sm:right-6 sm:top-6">
      <SettingsButton />
    </div>
  );
}
