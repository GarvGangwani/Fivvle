# Project follow-ups

Lightweight backlog of non-urgent engineering notes. Not blocking; logged so they are not forgotten.

---

## Dashboard / billing

- **#3 — `MONTHLY_VALIDATION_TARGET`:** Wire the soft monthly validation target in `UsageSidebarCard` to the user's subscription tier (e.g. Founder = 20, Unicorn = unlimited) once subscription monetization is real.
- **Google `photoURL` referrer policy:** `ProfileAvatar` uses `referrerPolicy="no-referrer"` for Firebase Google auth photos. If avatars still fail for some users, investigate signed URLs or alternate auth flows after a fresh Google signup test.

---

## Synthesizer / ValidationReport

- Extend ValidationReport lockstep test to verify hydration threading, not just schema caps.
- When adding another top-level field to ValidationReport, this would catch the same bug type (`draft` → `_hydrate_draft` → final) before it ships — see voices hydration fix (2026-07-08).
