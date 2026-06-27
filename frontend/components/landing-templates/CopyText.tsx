"use client";

import type { CopyJson } from "@/lib/types";
import { useCopyEdit } from "./CopyEditContext";
import { EditableCopy, type EditableCopyProps } from "./EditableCopy";
import type { CopyMutator } from "@/lib/copy-mutations";

type CopyTextProps = Omit<EditableCopyProps, "value" | "onChange" | "editable"> & {
  copy: CopyJson;
  value: string;
  mutate: CopyMutator;
  maxLength?: number;
};

export function CopyText({
  copy,
  value,
  mutate,
  maxLength,
  ...rest
}: CopyTextProps) {
  const ctx = useCopyEdit();
  const editable = ctx?.editable ?? false;
  const displayValue = value;

  return (
    <EditableCopy
      {...rest}
      value={displayValue}
      editable={editable}
      onChange={(next) => ctx?.onCopyChange(mutate(copy, next))}
    />
  );
}
