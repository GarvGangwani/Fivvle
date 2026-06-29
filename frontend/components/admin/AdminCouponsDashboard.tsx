"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Loader2,
  Plus,
  RefreshCw,
  RotateCcw,
  Ticket,
  ToggleLeft,
  ToggleRight,
  Trash2,
  Archive,
} from "lucide-react";
import {
  ApiError,
  archiveAdminCoupon,
  createAdminCoupon,
  deleteAdminCoupon,
  getAdminCoupons,
  restoreAdminCoupon,
  updateAdminCoupon,
  type AdminCouponSummary,
} from "@/lib/api";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { PageHeader } from "@/components/ui/PageHeader";
import { LoadingState } from "@/components/ui/LoadingState";

function toDatetimeLocalValue(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function fromDatetimeLocalValue(value: string): string | null {
  if (!value.trim()) return null;
  return new Date(value).toISOString();
}

function formatWhen(iso: string | null): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(iso));
}

function formatAdminApiError(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    if (err.status === 0) {
      return "Network error — is the backend running?";
    }
    if (typeof err.body === "object" && err.body !== null && "detail" in err.body) {
      const detail = (err.body as { detail: unknown }).detail;
      if (typeof detail === "string" && detail.trim()) {
        return detail;
      }
    }
  }
  return fallback;
}

type CreateFormState = {
  code: string;
  credits: string;
  enabled: boolean;
  max_redemptions: string;
  starts_at: string;
  ends_at: string;
  limit_reached_message: string;
  not_yet_active_message: string;
  expired_message: string;
  disabled_message: string;
};

const EMPTY_CREATE_FORM: CreateFormState = {
  code: "",
  credits: "25",
  enabled: true,
  max_redemptions: "",
  starts_at: "",
  ends_at: "",
  limit_reached_message: "",
  not_yet_active_message: "",
  expired_message: "",
  disabled_message: "",
};

function CouponEditor({
  coupon,
  onSaved,
}: {
  coupon: AdminCouponSummary;
  onSaved: () => void;
}) {
  const isArchived = coupon.archived_at !== null;
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    credits: String(coupon.credits),
    enabled: coupon.enabled,
    max_redemptions:
      coupon.max_redemptions === null ? "" : String(coupon.max_redemptions),
    starts_at: toDatetimeLocalValue(coupon.starts_at),
    ends_at: toDatetimeLocalValue(coupon.ends_at),
    limit_reached_message: coupon.limit_reached_message ?? "",
    not_yet_active_message: coupon.not_yet_active_message ?? "",
    expired_message: coupon.expired_message ?? "",
    disabled_message: coupon.disabled_message ?? "",
  });

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await updateAdminCoupon(coupon.id, {
        credits: Number(form.credits),
        enabled: form.enabled,
        max_redemptions: form.max_redemptions
          ? Number(form.max_redemptions)
          : null,
        starts_at: fromDatetimeLocalValue(form.starts_at),
        ends_at: fromDatetimeLocalValue(form.ends_at),
        clear_starts_at: !form.starts_at,
        clear_ends_at: !form.ends_at,
        limit_reached_message: form.limit_reached_message || null,
        not_yet_active_message: form.not_yet_active_message || null,
        expired_message: form.expired_message || null,
        disabled_message: form.disabled_message || null,
        clear_limit_reached_message: !form.limit_reached_message,
        clear_not_yet_active_message: !form.not_yet_active_message,
        clear_expired_message: !form.expired_message,
        clear_disabled_message: !form.disabled_message,
      });
      onSaved();
      setOpen(false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError("You do not have admin access.");
      } else {
        setError(formatAdminApiError(err, "Could not save coupon changes."));
      }
    } finally {
      setSaving(false);
    }
  }

  async function handleToggleEnabled() {
    if (isArchived) return;
    setSaving(true);
    setError(null);
    try {
      await updateAdminCoupon(coupon.id, { enabled: !coupon.enabled });
      onSaved();
    } catch (err) {
      setError(formatAdminApiError(err, "Could not update coupon status."));
    } finally {
      setSaving(false);
    }
  }

  async function handleArchive() {
    if (
      !window.confirm(
        `Archive coupon ${coupon.code}? It will stop accepting redemptions but redemption history is kept.`,
      )
    ) {
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await archiveAdminCoupon(coupon.id);
      onSaved();
    } catch (err) {
      setError(formatAdminApiError(err, "Could not archive coupon."));
    } finally {
      setSaving(false);
    }
  }

  async function handleRestore() {
    setSaving(true);
    setError(null);
    try {
      await restoreAdminCoupon(coupon.id);
      onSaved();
    } catch {
      setError("Could not restore coupon.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (
      !window.confirm(
        `Permanently delete coupon ${coupon.code}? This cannot be undone.`,
      )
    ) {
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await deleteAdminCoupon(coupon.id);
      onSaved();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError(
          "This coupon has redemptions and cannot be deleted. Archive it instead.",
        );
      } else {
        setError(formatAdminApiError(err, "Could not delete coupon."));
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <article
      className={`fv-section-card ${isArchived ? "opacity-80" : ""}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-mono text-base font-semibold text-[var(--fv-text)]">
              {coupon.code}
            </p>
            <span
              className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                isArchived
                  ? "bg-[var(--fv-surface-2)] text-[var(--fv-text-dim)]"
                  : coupon.enabled
                    ? "bg-[color-mix(in_srgb,var(--fv-success)_14%,transparent)] text-[var(--fv-success)]"
                    : "bg-[var(--fv-surface-2)] text-[var(--fv-text-muted)]"
              }`}
            >
              {isArchived ? "Archived" : coupon.enabled ? "Enabled" : "Disabled"}
            </span>
          </div>
          <p className="mt-1 text-sm text-[var(--fv-text-muted)]">
            {coupon.credits.toLocaleString()} credits ·{" "}
            {coupon.redemption_count.toLocaleString()} redeemed
            {coupon.max_redemptions !== null
              ? ` · ${coupon.remaining_redemptions?.toLocaleString() ?? 0} left`
              : " · unlimited"}
          </p>
        </div>
        <div className="text-right">
          <p className="text-lg font-semibold tabular-nums text-[var(--fv-text)]">
            {coupon.total_usd_gifted}
          </p>
          <p className="text-[11px] text-[var(--fv-text-dim)]">USD gifted</p>
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <p className="text-[11px] uppercase tracking-wide text-[var(--fv-text-dim)]">
            Active from
          </p>
          <p className="mt-1 text-sm text-[var(--fv-text-soft)]">
            {formatWhen(coupon.starts_at)}
          </p>
        </div>
        <div>
          <p className="text-[11px] uppercase tracking-wide text-[var(--fv-text-dim)]">
            Active until
          </p>
          <p className="mt-1 text-sm text-[var(--fv-text-soft)]">
            {formatWhen(coupon.ends_at)}
          </p>
        </div>
        <div>
          <p className="text-[11px] uppercase tracking-wide text-[var(--fv-text-dim)]">
            Credits gifted
          </p>
          <p className="mt-1 text-sm tabular-nums text-[var(--fv-text-soft)]">
            {coupon.total_credits_gifted.toLocaleString()}
          </p>
        </div>
        <div>
          <p className="text-[11px] uppercase tracking-wide text-[var(--fv-text-dim)]">
            Hard limit
          </p>
          <p className="mt-1 text-sm tabular-nums text-[var(--fv-text-soft)]">
            {coupon.max_redemptions?.toLocaleString() ?? "Unlimited"}
          </p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {!isArchived ? (
          <>
            <button
              type="button"
              className="fv-btn-ghost inline-flex items-center gap-2 px-3 py-2 text-sm"
              onClick={() => void handleToggleEnabled()}
              disabled={saving}
            >
              {coupon.enabled ? (
                <ToggleRight className="h-4 w-4 text-[var(--fv-success)]" />
              ) : (
                <ToggleLeft className="h-4 w-4" />
              )}
              {coupon.enabled ? "Disable" : "Enable"}
            </button>
            <button
              type="button"
              className="fv-btn-ghost px-3 py-2 text-sm"
              onClick={() => setOpen((prev) => !prev)}
            >
              {open ? "Hide settings" : "Edit coupon"}
            </button>
            <button
              type="button"
              className="fv-btn-ghost inline-flex items-center gap-2 px-3 py-2 text-sm text-[var(--fv-text-muted)]"
              onClick={() => void handleArchive()}
              disabled={saving}
            >
              <Archive className="h-4 w-4" />
              Archive
            </button>
            {coupon.redemption_count === 0 ? (
              <button
                type="button"
                className="fv-btn-ghost inline-flex items-center gap-2 px-3 py-2 text-sm text-[var(--fv-danger)]"
                onClick={() => void handleDelete()}
                disabled={saving}
              >
                <Trash2 className="h-4 w-4" />
                Delete
              </button>
            ) : null}
          </>
        ) : (
          <>
            <button
              type="button"
              className="fv-btn-ghost inline-flex items-center gap-2 px-3 py-2 text-sm"
              onClick={() => void handleRestore()}
              disabled={saving}
            >
              <RotateCcw className="h-4 w-4" />
              Restore
            </button>
            {coupon.redemption_count === 0 ? (
              <button
                type="button"
                className="fv-btn-ghost inline-flex items-center gap-2 px-3 py-2 text-sm text-[var(--fv-danger)]"
                onClick={() => void handleDelete()}
                disabled={saving}
              >
                <Trash2 className="h-4 w-4" />
                Delete permanently
              </button>
            ) : (
              <p className="self-center text-xs text-[var(--fv-text-dim)]">
                Archived coupons with redemptions cannot be deleted.
              </p>
            )}
          </>
        )}
      </div>

      {error ? (
        <ErrorBanner message={error} onDismiss={() => setError(null)} className="mt-4" />
      ) : null}

      {open && !isArchived ? (
        <div className="mt-4 space-y-4 border-t border-[var(--fv-border)] pt-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="mb-1 block text-xs text-[var(--fv-text-muted)]">
                Credits per redemption
              </span>
              <input
                type="number"
                min={1}
                value={form.credits}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, credits: e.target.value }))
                }
                className="fv-input w-full"
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block text-xs text-[var(--fv-text-muted)]">
                Max redemptions (blank = unlimited)
              </span>
              <input
                type="number"
                min={1}
                value={form.max_redemptions}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    max_redemptions: e.target.value,
                  }))
                }
                className="fv-input w-full"
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block text-xs text-[var(--fv-text-muted)]">
                Active from
              </span>
              <input
                type="datetime-local"
                value={form.starts_at}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, starts_at: e.target.value }))
                }
                className="fv-input w-full"
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block text-xs text-[var(--fv-text-muted)]">
                Active until
              </span>
              <input
                type="datetime-local"
                value={form.ends_at}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, ends_at: e.target.value }))
                }
                className="fv-input w-full"
              />
            </label>
          </div>

          <div className="grid gap-3">
            {(
              [
                ["limit_reached_message", "Limit reached message"],
                ["not_yet_active_message", "Not yet active message"],
                ["expired_message", "Expired message"],
                ["disabled_message", "Disabled message"],
              ] as const
            ).map(([key, label]) => (
              <label key={key} className="block text-sm">
                <span className="mb-1 block text-xs text-[var(--fv-text-muted)]">
                  {label}
                </span>
                <textarea
                  value={form[key]}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, [key]: e.target.value }))
                  }
                  rows={2}
                  className="fv-input w-full resize-y"
                  placeholder="Leave blank for default message"
                />
              </label>
            ))}
          </div>

          <button
            type="button"
            className="fv-btn-primary px-4 py-2 text-sm disabled:opacity-50"
            onClick={() => void handleSave()}
            disabled={saving}
          >
            {saving ? "Saving…" : "Save changes"}
          </button>
        </div>
      ) : null}
    </article>
  );
}

export function AdminCouponsDashboard() {
  const [coupons, setCoupons] = useState<AdminCouponSummary[]>([]);
  const [totalUsdGifted, setTotalUsdGifted] = useState("$0");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [showArchived, setShowArchived] = useState(false);
  const [createForm, setCreateForm] = useState<CreateFormState>(EMPTY_CREATE_FORM);

  const loadCoupons = useCallback(async () => {
    setError(null);
    const data = await getAdminCoupons(showArchived);
    setCoupons(data.coupons);
    setTotalUsdGifted(data.total_usd_gifted_all_coupons);
  }, [showArchived]);

  useEffect(() => {
    void loadCoupons()
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403) {
          setError("You do not have admin access.");
        } else {
          setError("Could not load coupons.");
        }
      })
      .finally(() => setLoading(false));
  }, [loadCoupons]);

  async function handleCreate() {
    if (!createForm.code.trim()) {
      setError("Enter a coupon code.");
      return;
    }
    const credits = Number(createForm.credits);
    if (!Number.isFinite(credits) || credits <= 0) {
      setError("Credits must be a positive number.");
      return;
    }

    setCreating(true);
    setError(null);
    try {
      await createAdminCoupon({
        code: createForm.code.trim(),
        credits,
        enabled: createForm.enabled,
        max_redemptions: createForm.max_redemptions
          ? Number(createForm.max_redemptions)
          : null,
        starts_at: fromDatetimeLocalValue(createForm.starts_at),
        ends_at: fromDatetimeLocalValue(createForm.ends_at),
        limit_reached_message: createForm.limit_reached_message || null,
        not_yet_active_message: createForm.not_yet_active_message || null,
        expired_message: createForm.expired_message || null,
        disabled_message: createForm.disabled_message || null,
      });
      setCreateForm(EMPTY_CREATE_FORM);
      setShowCreate(false);
      await loadCoupons();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError("A coupon with this code already exists.");
      } else {
        setError("Could not create coupon.");
      }
    } finally {
      setCreating(false);
    }
  }

  if (loading) {
    return <LoadingState label="Loading coupons…" />;
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <PageHeader
        title="Coupon management"
        description="Create promo codes, set redemption limits, and track total credit value gifted to founders."
        actions={
          <button
            type="button"
            className="fv-icon-btn"
            aria-label="Refresh coupons"
            onClick={() => {
              setLoading(true);
              void loadCoupons().finally(() => setLoading(false));
            }}
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        }
      />

      {error ? (
        <ErrorBanner message={error} onDismiss={() => setError(null)} />
      ) : null}

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="fv-section-card">
          <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--fv-text-muted)]">
            Total USD gifted
          </p>
          <p className="mt-2 text-2xl font-semibold text-[var(--fv-accent)]">
            {totalUsdGifted}
          </p>
        </div>
        <div className="fv-section-card">
          <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--fv-text-muted)]">
            Active coupons
          </p>
          <p className="mt-2 text-2xl font-semibold text-[var(--fv-text)]">
            {coupons.filter((c) => c.enabled && c.archived_at === null).length}
          </p>
        </div>
        <div className="fv-section-card">
          <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--fv-text-muted)]">
            Total redemptions
          </p>
          <p className="mt-2 text-2xl font-semibold text-[var(--fv-text)]">
            {coupons
              .reduce((sum, coupon) => sum + coupon.redemption_count, 0)
              .toLocaleString()}
          </p>
        </div>
      </div>

      <section>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-4">
            <h2 className="fv-panel-label">Coupons</h2>
            <label className="flex items-center gap-2 text-sm text-[var(--fv-text-muted)]">
              <input
                type="checkbox"
                checked={showArchived}
                onChange={(e) => {
                  setShowArchived(e.target.checked);
                  setLoading(true);
                }}
              />
              Show archived
            </label>
          </div>
          <button
            type="button"
            className="fv-btn-primary inline-flex items-center gap-2 px-3 py-2 text-sm"
            onClick={() => setShowCreate((prev) => !prev)}
          >
            <Plus className="h-4 w-4" />
            {showCreate ? "Cancel" : "Add coupon"}
          </button>
        </div>

        {showCreate ? (
          <div className="fv-section-card mb-4 space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block text-sm">
                <span className="mb-1 block text-xs text-[var(--fv-text-muted)]">
                  Code
                </span>
                <input
                  type="text"
                  value={createForm.code}
                  onChange={(e) =>
                    setCreateForm((prev) => ({
                      ...prev,
                      code: e.target.value.toUpperCase(),
                    }))
                  }
                  className="fv-input w-full font-mono uppercase"
                  placeholder="LAUNCH50"
                />
              </label>
              <label className="block text-sm">
                <span className="mb-1 block text-xs text-[var(--fv-text-muted)]">
                  Credits
                </span>
                <input
                  type="number"
                  min={1}
                  value={createForm.credits}
                  onChange={(e) =>
                    setCreateForm((prev) => ({
                      ...prev,
                      credits: e.target.value,
                    }))
                  }
                  className="fv-input w-full"
                />
              </label>
              <label className="block text-sm">
                <span className="mb-1 block text-xs text-[var(--fv-text-muted)]">
                  Max redemptions
                </span>
                <input
                  type="number"
                  min={1}
                  value={createForm.max_redemptions}
                  onChange={(e) =>
                    setCreateForm((prev) => ({
                      ...prev,
                      max_redemptions: e.target.value,
                    }))
                  }
                  className="fv-input w-full"
                  placeholder="Unlimited if blank"
                />
              </label>
              <label className="flex items-center gap-2 pt-6 text-sm">
                <input
                  type="checkbox"
                  checked={createForm.enabled}
                  onChange={(e) =>
                    setCreateForm((prev) => ({
                      ...prev,
                      enabled: e.target.checked,
                    }))
                  }
                />
                Enabled on create
              </label>
              <label className="block text-sm">
                <span className="mb-1 block text-xs text-[var(--fv-text-muted)]">
                  Active from
                </span>
                <input
                  type="datetime-local"
                  value={createForm.starts_at}
                  onChange={(e) =>
                    setCreateForm((prev) => ({
                      ...prev,
                      starts_at: e.target.value,
                    }))
                  }
                  className="fv-input w-full"
                />
              </label>
              <label className="block text-sm">
                <span className="mb-1 block text-xs text-[var(--fv-text-muted)]">
                  Active until
                </span>
                <input
                  type="datetime-local"
                  value={createForm.ends_at}
                  onChange={(e) =>
                    setCreateForm((prev) => ({
                      ...prev,
                      ends_at: e.target.value,
                    }))
                  }
                  className="fv-input w-full"
                />
              </label>
            </div>
            <button
              type="button"
              className="fv-btn-primary inline-flex items-center gap-2 px-4 py-2 text-sm disabled:opacity-50"
              onClick={() => void handleCreate()}
              disabled={creating}
            >
              {creating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Ticket className="h-4 w-4" />
              )}
              Create coupon
            </button>
          </div>
        ) : null}

        {coupons.length === 0 ? (
          <div className="fv-section-card text-center text-sm text-[var(--fv-text-muted)]">
            No coupons yet. Add one to start tracking redemptions.
          </div>
        ) : (
          <div className="space-y-4">
            {coupons.map((coupon) => (
              <CouponEditor
                key={coupon.id}
                coupon={coupon}
                onSaved={() => void loadCoupons()}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
