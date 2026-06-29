import { ApiError } from "@/lib/api";

type CouponErrorDetail = {
  error?: string;
  message?: string;
};

function readCouponErrorDetail(err: ApiError): CouponErrorDetail | null {
  const body = err.body;
  if (
    !body ||
    typeof body !== "object" ||
    !("detail" in body) ||
    !body.detail ||
    typeof body.detail !== "object"
  ) {
    return null;
  }
  return body.detail as CouponErrorDetail;
}

export function readCouponRedeemError(err: unknown): string {
  if (!(err instanceof ApiError)) {
    return "Could not redeem coupon. Please try again.";
  }

  const detail = readCouponErrorDetail(err);
  if (detail?.message) {
    return detail.message;
  }

  if (err.status === 409) {
    return "You have already redeemed this coupon.";
  }
  if (err.status === 400) {
    return "This coupon code is not valid.";
  }
  if (err.status === 403) {
    return "This coupon cannot be redeemed right now.";
  }

  return "Could not redeem coupon. Please try again.";
}
