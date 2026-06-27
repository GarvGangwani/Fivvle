"use client";

import {
  useEffect,
  useRef,
  type CSSProperties,
  type ElementType,
  type KeyboardEvent,
  type MouseEvent,
} from "react";
import styles from "./editable-copy.module.css";

export interface EditableCopyProps {
  value: string;
  onChange: (value: string) => void;
  editable?: boolean;
  as?: ElementType;
  className?: string;
  multiline?: boolean;
  inline?: boolean;
  placeholder?: string;
  style?: CSSProperties;
}

export function EditableCopy({
  value,
  onChange,
  editable = false,
  as: Tag = "span",
  className,
  multiline = false,
  inline = false,
  placeholder,
  style,
}: EditableCopyProps) {
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || document.activeElement === el) return;
    el.textContent = value;
  }, [value]);

  if (!editable) {
    return (
      <Tag className={className} style={style}>
        {value}
      </Tag>
    );
  }

  const commit = () => {
    const next = (ref.current?.innerText ?? "").replace(/\u00a0/g, " ").trim();
    if (next !== value.trim()) {
      onChange(next);
    } else if (ref.current) {
      ref.current.textContent = value;
    }
  };

  const stopNav = (event: MouseEvent) => {
    event.stopPropagation();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      if (ref.current) {
        ref.current.textContent = value;
      }
      ref.current?.blur();
      return;
    }
    if (!multiline && event.key === "Enter") {
      event.preventDefault();
      ref.current?.blur();
    }
  };

  const classes = [
    styles.editable,
    inline ? styles.inline : "",
    multiline ? styles.multiline : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <Tag
      ref={ref as never}
      contentEditable
      suppressContentEditableWarning
      className={classes}
      style={style}
      onBlur={commit}
      onKeyDown={handleKeyDown}
      onClick={stopNav}
      onMouseDown={stopNav}
      data-placeholder={placeholder}
      role="textbox"
      aria-label="Edit text"
      spellCheck
    />
  );
}
