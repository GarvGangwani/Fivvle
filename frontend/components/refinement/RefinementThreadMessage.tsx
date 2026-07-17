"use client";

import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  Lightbulb,
  MessageCircleQuestion,
  Pencil,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import type { ChatRole, ChatTurnKind } from "@/lib/types";
import { useOptionalAuth } from "@/lib/auth-context";
import { getChatUserLabel } from "@/lib/user-avatar";
import { UserAvatar } from "@/components/auth/UserAvatar";
import { FivvleLogo } from "@/components/layout/FivvleLogo";
import {
  excerptIdea,
  parseClarifyingAnswerContent,
  parseResearchingHypothesis,
} from "@/lib/refinement-thread";
import { ChatMarkdown } from "@/components/chat/ChatMarkdown";
import "./refinement-ascent.css";
import "./refinement-thread.css";

export type RefinementThreadVariant = "ascent" | "peak";

interface RefinementThreadMessageProps {
  id: string;
  role: ChatRole;
  content: string;
  turnKind?: ChatTurnKind | null;
  isSparkIdea?: boolean;
  originalIdea?: string;
  clarityRound?: number;
  /** Label when rendered outside AuthProvider (e.g. refinement demos). */
  demoUserLabel?: string;
  showRefining?: boolean;
  canEdit?: boolean;
  onEdit?: (messageId: string, newContent: string) => Promise<void>;
  /** Ascent is live in Refine; peak kept for /refinement-demos comparison. */
  variant?: RefinementThreadVariant;
}

function EditActions({
  saving,
  canSave,
  onSave,
  onCancel,
}: {
  saving: boolean;
  canSave: boolean;
  onSave: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="mt-3 flex items-center gap-2">
      <button
        type="button"
        onClick={onSave}
        disabled={saving || !canSave}
        className="fv-btn-primary px-4 py-2 text-sm disabled:cursor-not-allowed disabled:opacity-50"
      >
        {saving ? "Saving…" : "Save"}
      </button>
      <button
        type="button"
        onClick={onCancel}
        disabled={saving}
        className="fv-btn-ghost px-4 py-2 text-sm disabled:opacity-50"
      >
        Cancel
      </button>
    </div>
  );
}

export function RefinementThreadMessage({
  id,
  role,
  content,
  turnKind,
  isSparkIdea = false,
  originalIdea,
  clarityRound = 1,
  demoUserLabel,
  showRefining = false,
  canEdit = false,
  onEdit,
  variant = "ascent",
}: RefinementThreadMessageProps) {
  const auth = useOptionalAuth();
  const user = auth?.user ?? null;
  const userLabel = user
    ? getChatUserLabel(user)
    : (demoUserLabel?.trim() || "You");
  const isUser = role === "user";
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(content);
  const [saving, setSaving] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const clarityBlocks = isUser ? parseClarifyingAnswerContent(content) : null;
  const refinedHypothesis =
    !isUser && turnKind === "refinement_finalize"
      ? parseResearchingHypothesis(content)
      : null;

  useEffect(() => {
    if (!isEditing) setDraft(content);
  }, [content, isEditing]);

  useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.focus();
      textareaRef.current.setSelectionRange(
        textareaRef.current.value.length,
        textareaRef.current.value.length,
      );
    }
  }, [isEditing]);

  async function handleSave() {
    const trimmed = draft.trim();
    if (!trimmed || !onEdit || trimmed === content) {
      setDraft(content);
      setIsEditing(false);
      return;
    }
    setSaving(true);
    try {
      await onEdit(id, trimmed);
      setIsEditing(false);
    } finally {
      setSaving(false);
    }
  }

  const editButton =
    isUser && canEdit && !isEditing ? (
      <button
        type="button"
        onClick={() => setIsEditing(true)}
        aria-label="Edit message"
        className="rounded-md p-1.5 text-[var(--fv-text-muted)] transition-colors hover:bg-[var(--fv-hover-overlay)] hover:text-[var(--fv-text-soft)]"
      >
        <Pencil className="h-3.5 w-3.5" />
      </button>
    ) : null;

  const isAscent = variant === "ascent";

  if (isSparkIdea && isUser) {
    if (isAscent) {
      return (
        <div className="fv-msg-enter">
          <header className="ra-hero">
            <div className="ra-hero-head">
              <div>
                <div className="ra-hero-icon" aria-hidden>
                  <Lightbulb />
                </div>
                <p className="ra-kicker">Chapter 1 · The spark</p>
                <h3 className="ra-hero-title">
                  Every great company starts as a sentence.
                </h3>
              </div>
              {editButton}
            </div>
            {isEditing ? (
              <>
                <textarea
                  ref={textareaRef}
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  disabled={saving}
                  rows={5}
                  className="fv-input mt-2 w-full resize-y px-3 py-2 text-[15px] leading-[1.65]"
                />
                <EditActions
                  saving={saving}
                  canSave={Boolean(draft.trim())}
                  onSave={() => void handleSave()}
                  onCancel={() => {
                    setDraft(content);
                    setIsEditing(false);
                  }}
                />
              </>
            ) : (
              <>
                <blockquote className="ra-hero-quote">{content}</blockquote>
                <div className="ra-hero-byline">
                  <UserAvatar
                    displayName={user?.displayName ?? demoUserLabel}
                    email={user?.email}
                    photoUrl={user?.photoURL}
                    size="sm"
                    className="!h-5 !w-5 !text-[10px]"
                  />
                  {userLabel}
                </div>
              </>
            )}
          </header>
        </div>
      );
    }

    return (
      <div className="fv-msg-enter">
        <div className="relative mx-auto w-full max-w-full lg:max-w-[720px]">
          <article className="rt-step">
            <div className="rt-step-marker" aria-hidden>
              <Lightbulb />
            </div>
            <div className="rt-card rt-card-spark">
              <div className="rt-card-head">
                <p className="rt-eyebrow rt-eyebrow-accent">Your starting point</p>
                <span className="rt-badge">
                  <Sparkles className="h-3 w-3" aria-hidden />
                  Raw idea
                </span>
              </div>
              <div className="rt-card-body">
                {isEditing ? (
                  <>
                    <textarea
                      ref={textareaRef}
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      disabled={saving}
                      rows={5}
                      className="fv-input w-full resize-y px-3 py-2 text-[15px] leading-[1.65]"
                    />
                    <EditActions
                      saving={saving}
                      canSave={Boolean(draft.trim())}
                      onSave={() => void handleSave()}
                      onCancel={() => {
                        setDraft(content);
                        setIsEditing(false);
                      }}
                    />
                  </>
                ) : (
                  <>
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <UserAvatar
                          displayName={user?.displayName ?? demoUserLabel}
                          email={user?.email}
                          photoUrl={user?.photoURL}
                          size="sm"
                          className="!h-6 !w-6 !text-[11px]"
                        />
                        <span className="text-[13px] font-medium text-[var(--fv-text-soft)]">
                          {userLabel}
                        </span>
                      </div>
                      {editButton}
                    </div>
                    <p className="rt-spark-text">{content}</p>
                  </>
                )}
              </div>
            </div>
          </article>
        </div>
      </div>
    );
  }

  if (clarityBlocks && isUser) {
    if (isAscent) {
      return null;
    }

    return (
      <div className="fv-msg-enter">
        <div className="relative mx-auto w-full max-w-full lg:max-w-[720px]">
          <article className="rt-step">
            <div className="rt-step-marker" aria-hidden>
              <MessageCircleQuestion />
            </div>
            <div className="rt-card">
              <div className="rt-card-head">
                <p className="rt-eyebrow rt-eyebrow-accent">
                  Clarity round {clarityRound}
                </p>
                {editButton}
              </div>
              <div className="rt-card-body">
                {isEditing ? (
                  <>
                    <textarea
                      ref={textareaRef}
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      disabled={saving}
                      rows={8}
                      className="fv-input w-full resize-y px-3 py-2 font-mono text-[13px] leading-[1.55]"
                    />
                    <EditActions
                      saving={saving}
                      canSave={Boolean(draft.trim())}
                      onSave={() => void handleSave()}
                      onCancel={() => {
                        setDraft(content);
                        setIsEditing(false);
                      }}
                    />
                  </>
                ) : (
                  <div className="rt-clarity-stack">
                    {clarityBlocks.map((block) => (
                      <div key={block.question} className="rt-clarity-item">
                        <p className="rt-clarity-q">{block.question}</p>
                        <div className="rt-clarity-answers">
                          {block.answers.map((answer) => (
                            <span key={answer} className="rt-clarity-chip">
                              {answer}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </article>
        </div>
      </div>
    );
  }

  if (refinedHypothesis) {
    const before = originalIdea ? excerptIdea(originalIdea) : null;

    if (isAscent) {
      return (
        <div className="fv-msg-enter">
          <section className="ra-finale">
            <div className="ra-finale-badge">
              <Sparkles className="h-3.5 w-3.5" aria-hidden />
              Refined &amp; research-ready
            </div>
            <p className="ra-kicker ra-kicker-light">Chapter 3 · The upgrade</p>
            <div className="ra-finale-grid">
              {before ? (
                <div className="ra-finale-before">
                  <p className="ra-finale-label">Before</p>
                  <p>{before}</p>
                </div>
              ) : null}
              {before ? (
                <ArrowRight className="ra-finale-arrow" aria-hidden />
              ) : null}
              <div className="ra-finale-after">
                <p className="ra-finale-label">Researching</p>
                <p className="ra-finale-hypothesis">{refinedHypothesis}</p>
              </div>
            </div>
          </section>
        </div>
      );
    }

    return (
      <div className="fv-msg-enter">
        <div className="relative mx-auto w-full max-w-full lg:max-w-[720px]">
          <article className="rt-step">
            <div className="rt-step-marker rt-step-marker-success" aria-hidden>
              <TrendingUp />
            </div>
            <div className="rt-card rt-card-refined">
              <div className="rt-card-head">
                <div className="flex items-center gap-2">
                  <FivvleLogo size={22} />
                  <p className="rt-eyebrow rt-eyebrow-success mb-0">
                    Refined hypothesis
                  </p>
                </div>
                <span className="rt-badge rt-badge-success">Upgrade ready</span>
              </div>
              <div className="rt-card-body">
                <div className="rt-upgrade-grid">
                  {before ? (
                    <div className="rt-upgrade-before">
                      <p className="rt-upgrade-label">Where you started</p>
                      <p className="rt-upgrade-text">{before}</p>
                    </div>
                  ) : null}
                  {before ? (
                    <div className="rt-upgrade-arrow" aria-hidden>
                      <ArrowUpRight />
                    </div>
                  ) : null}
                  <div className="rt-upgrade-after">
                    <p className="rt-upgrade-label">What we&apos;re researching</p>
                    <p className="rt-upgrade-text rt-upgrade-text-strong">
                      {refinedHypothesis}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </article>
        </div>
      </div>
    );
  }

  return (
    <div className="fv-msg-enter">
      <div
        className={`relative mx-auto w-full max-w-full lg:max-w-[720px] ${
          isAscent ? "ra-default-row" : "rt-default-row"
        }`}
      >
        <div className="flex items-start gap-3">
          {isUser ? (
            <UserAvatar
              displayName={user?.displayName ?? demoUserLabel}
              email={user?.email}
              photoUrl={user?.photoURL}
              size="sm"
              className="!h-6 !w-6 !text-[11px]"
            />
          ) : (
            <FivvleLogo size={24} />
          )}
          <div className="min-w-0 flex-1">
            <span className="mb-1 block text-[13px] font-medium text-[var(--fv-text-soft)]">
              {isUser ? userLabel : "Fivvle"}
              {!isUser && showRefining && (
                <span className="fv-refining-badge ml-2">Refining</span>
              )}
            </span>
            {isUser ? (
              <div className="fv-msg-user whitespace-pre-wrap break-words">
                {content}
              </div>
            ) : (
              <ChatMarkdown content={content} className="fv-msg-ai break-words" />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
