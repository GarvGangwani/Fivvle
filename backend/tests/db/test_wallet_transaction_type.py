"""Tests for WalletTransactionType enum (monetization Phase 9)."""

from __future__ import annotations

from app.db.enums import WalletTransactionType


def test_all_wallet_transaction_types_defined() -> None:
    assert len(WalletTransactionType) == 6


def test_wallet_transaction_type_values() -> None:
    assert WalletTransactionType.TOPUP == "TOPUP"
    assert WalletTransactionType.SERVICE_USAGE == "SERVICE_USAGE"
    assert WalletTransactionType.REFUND == "REFUND"
