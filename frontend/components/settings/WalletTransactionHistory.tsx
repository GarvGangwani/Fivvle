"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowDownLeft,
  ArrowUpRight,
  Coins,
  Gift,
  Loader2,
  Receipt,
  RefreshCw,
  RotateCcw,
  ShoppingBag,
  Sparkles,
} from "lucide-react";
import {
  ApiError,
  getWalletTransactions,
  type WalletTransaction,
  type WalletTransactionType,
} from "@/lib/api";
import {
  formatTransactionCredits,
  formatTransactionDate,
  isCreditTransaction,
  transactionTypeLabel,
} from "@/lib/wallet-transactions";

const PAGE_SIZE = 15;

const TYPE_ICONS: Record<
  WalletTransactionType,
  typeof Coins
> = {
  TOPUP: ShoppingBag,
  BONUS: Sparkles,
  COUPON: Gift,
  SERVICE_USAGE: Receipt,
  REFUND: RotateCcw,
  ADMIN_ADJUSTMENT: Coins,
};

function TransactionRow({ tx }: { tx: WalletTransaction }) {
  const Icon = TYPE_ICONS[tx.type] ?? Coins;
  const credit = isCreditTransaction(tx.credits);

  return (
    <li className="fv-wallet-tx-row">
      <div
        className={`fv-wallet-tx-icon ${
          credit ? "fv-wallet-tx-icon-credit" : "fv-wallet-tx-icon-debit"
        }`}
      >
        <Icon className="h-4 w-4" aria-hidden />
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-[var(--fv-text)]">
              {tx.title}
            </p>
            {tx.detail ? (
              <p className="mt-0.5 truncate text-xs text-[var(--fv-text-muted)]">
                {tx.detail}
              </p>
            ) : null}
          </div>
          <p
            className={`shrink-0 text-sm font-semibold tabular-nums ${
              credit ? "text-[var(--fv-success)]" : "text-[var(--fv-text)]"
            }`}
          >
            {formatTransactionCredits(tx.credits)}
          </p>
        </div>

        <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-[var(--fv-text-dim)]">
          <span>{formatTransactionDate(tx.created_at)}</span>
          <span aria-hidden>·</span>
          <span className="rounded-full border border-[var(--fv-border)] px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-[var(--fv-text-muted)]">
            {transactionTypeLabel(tx.type)}
          </span>
          {tx.reference ? (
            <>
              <span aria-hidden>·</span>
              <span className="font-mono">{tx.reference}</span>
            </>
          ) : null}
          <span aria-hidden>·</span>
          <span>
            Balance {tx.balance_after.toLocaleString()}
          </span>
        </div>
      </div>

      <span className="sr-only">
        {credit ? "Credits added" : "Credits spent"}
      </span>
      {credit ? (
        <ArrowDownLeft className="sr-only" aria-hidden />
      ) : (
        <ArrowUpRight className="sr-only" aria-hidden />
      )}
    </li>
  );
}

export function WalletTransactionHistory() {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [transactions, setTransactions] = useState<WalletTransaction[]>([]);
  const [summary, setSummary] = useState({
    credits_balance: 0,
    total_credits_purchased: 0,
    total_credits_consumed: 0,
    total: 0,
  });
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);

  const loadPage = useCallback(async (offset: number, append: boolean) => {
    const result = await getWalletTransactions({
      limit: PAGE_SIZE,
      offset,
    });
    setSummary({
      credits_balance: result.credits_balance,
      total_credits_purchased: result.total_credits_purchased,
      total_credits_consumed: result.total_credits_consumed,
      total: result.total,
    });
    setHasMore(result.has_more);
    setTransactions((prev) =>
      append ? [...prev, ...result.transactions] : result.transactions,
    );
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    void loadPage(0, false)
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 401) {
          setError(null);
          return;
        }
        setError("Could not load billing history.");
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [loadPage]);

  async function handleLoadMore() {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    setError(null);
    try {
      await loadPage(transactions.length, true);
    } catch {
      setError("Could not load more transactions.");
    } finally {
      setLoadingMore(false);
    }
  }

  function handleScroll() {
    const el = scrollRef.current;
    if (!el || loadingMore || !hasMore) return;
    const distanceFromBottom =
      el.scrollHeight - el.scrollTop - el.clientHeight;
    if (distanceFromBottom < 48) {
      void handleLoadMore();
    }
  }

  async function handleRefresh() {
    setLoading(true);
    setError(null);
    try {
      await loadPage(0, false);
    } catch {
      setError("Could not refresh billing history.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mb-8">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 className="fv-panel-label">Billing history</h3>
        <button
          type="button"
          onClick={() => void handleRefresh()}
          disabled={loading}
          className="fv-icon-btn"
          aria-label="Refresh billing history"
        >
          <RefreshCw
            className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}
          />
        </button>
      </div>

      <div className="mb-3 grid grid-cols-3 gap-2">
        <div className="fv-wallet-tx-stat">
          <p className="fv-wallet-tx-stat-label">Balance</p>
          <p className="fv-wallet-tx-stat-value">
            {summary.credits_balance.toLocaleString()}
          </p>
        </div>
        <div className="fv-wallet-tx-stat">
          <p className="fv-wallet-tx-stat-label">Added</p>
          <p className="fv-wallet-tx-stat-value text-[var(--fv-success)]">
            +{summary.total_credits_purchased.toLocaleString()}
          </p>
        </div>
        <div className="fv-wallet-tx-stat">
          <p className="fv-wallet-tx-stat-label">Used</p>
          <p className="fv-wallet-tx-stat-value">
            {summary.total_credits_consumed.toLocaleString()}
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-[var(--fv-border)] bg-[var(--fv-surface-2)]">
        {loading && transactions.length === 0 ? (
          <div className="flex items-center justify-center gap-2 px-4 py-10 text-sm text-[var(--fv-text-muted)]">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
            Loading transactions…
          </div>
        ) : error ? (
          <div className="px-4 py-8 text-center text-sm text-[var(--fv-danger-light)]">
            {error}
          </div>
        ) : transactions.length === 0 ? (
          <div className="px-4 py-8 text-center">
            <Receipt
              className="mx-auto mb-3 h-8 w-8 text-[var(--fv-text-dim)]"
              aria-hidden
            />
            <p className="text-sm font-medium text-[var(--fv-text)]">
              No transactions yet
            </p>
            <p className="mt-1 text-xs leading-relaxed text-[var(--fv-text-muted)]">
              Purchases, coupon redemptions, and service charges will appear
              here.
            </p>
          </div>
        ) : (
          <>
            <div
              ref={scrollRef}
              className="fv-wallet-tx-scroll"
              onScroll={handleScroll}
            >
              <ul className="divide-y divide-[var(--fv-border)]">
                {transactions.map((tx) => (
                  <TransactionRow key={tx.id} tx={tx} />
                ))}
              </ul>
              {loadingMore ? (
                <div className="flex items-center justify-center gap-2 border-t border-[var(--fv-border)] px-4 py-3 text-xs text-[var(--fv-text-muted)]">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
                  Loading more…
                </div>
              ) : null}
            </div>
            {summary.total > 4 ? (
              <p className="border-t border-[var(--fv-border)] px-4 py-2 text-center text-[11px] text-[var(--fv-text-dim)]">
                {transactions.length} of {summary.total} — scroll for more
              </p>
            ) : summary.total > 0 ? (
              <p className="border-t border-[var(--fv-border)] px-4 py-2 text-center text-[11px] text-[var(--fv-text-dim)]">
                {summary.total} transaction{summary.total === 1 ? "" : "s"}
              </p>
            ) : null}
          </>
        )}
      </div>
    </section>
  );
}
