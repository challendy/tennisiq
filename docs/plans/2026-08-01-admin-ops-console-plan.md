# Admin Ops Console Implementation Plan

> **For agentic workers:** Execute task-by-task. Checkbox tracking optional in this session.

**Goal:** Ship `/admin` ops console gated by `User.IsAdmin` for plan/quota and job retry/cancel.

**Architecture:** Next.js `(admin)` routes + ASP.NET `/api/admin/*` with JWT `is_admin` claim and `AdminOnly` policy. Bootstrap email at startup.

**Tech Stack:** ASP.NET Core, EF/Npgsql, Next.js, existing JWT auth.

**Spec:** `docs/specs/2026-08-01-admin-ops-console-design.md`

---

### Task 1: Domain + schema + JWT + policy + bootstrap — done
### Task 2: AdminController + Auth me/login isAdmin — done
### Task 3: API tests — done
### Task 4: Web admin UI + nav + api client — done
### Task 5: README note + verify — done
