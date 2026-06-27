type WalletPatchFn = (patch: { credits_balance: number }) => void;

/** Apply server-reported balance immediately, then refresh from GET /wallet. */
export async function syncWalletAfterPaidAction(
  refresh: () => Promise<void>,
  applyWalletPatch: WalletPatchFn,
  creditsBalance: number | undefined,
): Promise<void> {
  if (creditsBalance !== undefined) {
    applyWalletPatch({ credits_balance: creditsBalance });
  }
  await refresh();
}
