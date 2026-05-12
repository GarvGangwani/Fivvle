"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { syncUser, ApiError, type UserSyncResponse } from "@/lib/api";

type SyncState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; data: UserSyncResponse }
  | { status: "error"; message: string; requestId: string | null };

export default function DashboardPage() {
  const { user, logOut } = useAuth();
  const [syncState, setSyncState] = useState<SyncState>({ status: "idle" });
  const [loggingOut, setLoggingOut] = useState(false);

  async function handleSync() {
    setSyncState({ status: "loading" });
    try {
      const data = await syncUser();
      setSyncState({ status: "success", data });
    } catch (err) {
      if (err instanceof ApiError) {
        setSyncState({
          status: "error",
          message: `API ${err.status}: ${JSON.stringify(err.body)}`,
          requestId: err.requestId,
        });
      } else {
        setSyncState({
          status: "error",
          message: "Unexpected error. Please try again.",
          requestId: null,
        });
      }
    }
  }

  async function handleLogOut() {
    setLoggingOut(true);
    try {
      await logOut();
    } finally {
      setLoggingOut(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white px-4 py-4">
        <div className="mx-auto flex max-w-2xl items-center justify-between">
          <span className="text-lg font-semibold text-gray-900">Fivvle</span>
          <span className="text-sm text-gray-500">{user?.email}</span>
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-4 py-10">
        <h1 className="mb-8 text-2xl font-bold text-gray-900">Dashboard</h1>

        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-1 text-base font-semibold text-gray-900">
            Backend connection
          </h2>
          <p className="mb-4 text-sm text-gray-500">
            Verify the auth + API plumbing works end-to-end.
          </p>

          <button
            onClick={handleSync}
            disabled={syncState.status === "loading"}
            className="rounded-lg bg-gray-900 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-gray-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {syncState.status === "loading" ? "Syncing…" : "Sync user"}
          </button>

          {syncState.status === "success" && (
            <div className="mt-4 rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700">
              <p className="font-medium">Synced ✓</p>
              <p className="mt-1 font-mono text-xs text-green-600">
                id: {syncState.data.id}
              </p>
              <p className="font-mono text-xs text-green-600">
                email: {syncState.data.email}
              </p>
            </div>
          )}

          {syncState.status === "error" && (
            <div className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
              <p className="font-medium">Sync failed</p>
              <p className="mt-1 text-xs">{syncState.message}</p>
              {syncState.requestId && (
                <p className="mt-1 font-mono text-xs text-red-500">
                  request_id: {syncState.requestId}
                </p>
              )}
            </div>
          )}
        </div>

        <div className="mt-4 flex justify-end">
          <button
            onClick={handleLogOut}
            disabled={loggingOut}
            className="text-sm text-gray-500 underline-offset-2 hover:text-gray-900 hover:underline disabled:opacity-50"
          >
            {loggingOut ? "Logging out…" : "Log out"}
          </button>
        </div>
      </main>
    </div>
  );
}
