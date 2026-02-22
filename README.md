# AI Compliance Intelligence Platform

An AI-powered compliance monitoring system for SaaS companies. Built with Next.js 14, TypeScript, TailwindCSS, shadcn/ui, Framer Motion, and Recharts.

## Features

- **Landing Page (/)** - Hero, features, how it works, enterprise trust, footer. Animated gradient background, smooth scroll, Framer Motion.
- **Login (/login)** - Glassmorphism login with email, password, role selector (Admin / Compliance Officer / Viewer), demo mode badge. Mock auth with redirect.
- **Auth System** - AuthContext with user (name, role, email, department), login(), logout(). Unauthenticated users redirect to /login.
- **Role Logic** - Admin: full access. Compliance Officer: no Settings, no user management. Viewer: Dashboard + Reports only, no action buttons.
- **Dashboard** - Compliance score, KPIs, 30-day trend chart, risk heatmap, recent violations
- **Upload Policy** - Drag-and-drop PDF upload with rule extraction preview
- **Rules** - Browse policy-derived rules with severity badges and expandable details
- **Violations** - Advanced table with filters, evidence panel, AI explanations, and suggested remediation steps
- **Review** - Approve/Reject workflow with reviewer comments, suggested remediation, and audit log
- **Policy Impact** - Compare two policy versions (rule diff) and estimated new violations if you adopt the new policy
- **Reports** - Download PDF, export CSV, trend analytics (export hidden for Viewer)
- **Logout** - Header dropdown; clears state, redirects to landing, shows toast
- **Page Transitions** - Route-based shrink/expand with Framer Motion AnimatePresence
- **Theme Toggle** - Dark/light in header, persisted in localStorage, Tailwind dark class
- **Notifications** - Clickable bell, dropdown with mock list, red badge count, close on outside click

## Tech Stack

- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript
- **Styling:** TailwindCSS (dark mode class)
- **Components:** shadcn/ui (Radix UI primitives)
- **Animation:** Framer Motion
- **Charts:** Recharts
- **Icons:** Lucide React

## How to Run

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

1. **Navigate to the project directory:**
   ```bash
   cd ai-compliance-platform
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Run the development server:**
   ```bash
   npm run dev
   ```

4. **Open in browser:** [http://localhost:3000](http://localhost:3000)

- **Landing:** `/` — hero, features, how it works, footer. Use "Access Demo" or "Sign in" to go to login.
- **Login:** `/login` — any email/password works (demo). Choose role: Admin, Compliance Officer, or Viewer. After login you are redirected to `/dashboard`.
- **App (protected):** `/dashboard`, `/upload`, `/rules`, `/policy-impact`, `/violations`, `/review`, `/reports` — require login. Sidebar and header show based on role. Use header theme toggle (sun/moon) and notification bell. Sign out from the user dropdown; you get a toast and redirect to `/`.

### Build for Production

Stop the dev server (Ctrl+C) before building.

```bash
npm run build
npm start
```

### Verify (No Errors)

```bash
npm run test    # Lint + TypeScript check
```

## Project Structure

```
src/
├── app/
│   ├── (app)/              # Protected app routes (auth required)
│   │   ├── layout.tsx      # Auth guard, AppLayout, page transitions
│   │   ├── dashboard/
│   │   ├── upload/
│   │   ├── rules/
│   │   ├── policy-impact/
│   │   ├── violations/
│   │   ├── review/
│   │   └── reports/
│   ├── login/              # Login page
│   ├── page.tsx            # Landing page
│   ├── layout.tsx          # Root layout (Providers only)
│   └── globals.css
├── components/
│   ├── dashboard/
│   ├── layout/
│   │   ├── header.tsx      # Search, theme toggle, notifications, user dropdown (logout)
│   │   ├── sidebar.tsx    # Role-based nav
│   │   ├── notification-dropdown.tsx
│   │   ├── page-transition.tsx
│   │   ├── providers.tsx  # Auth, Theme, Toast
│   │   └── ...
│   └── ui/
├── contexts/
│   ├── auth-context.tsx    # User, login(), logout(), role helpers
│   ├── theme-context.tsx   # Dark/light, localStorage
│   └── toast-context.tsx  # Toast on logout
├── data/
└── lib/
```

## Architecture (Performance & Layout)

- **Root layout (`app/layout.tsx`)** — Server Component (no `"use client"`). Wraps children in `<Providers>`. No AnimatePresence on the whole tree.
- **App layout (`(app)/layout.tsx`)** — Client component owns `collapsed` state and provides it via `SidebarContext`. On `pathname` change, `setCollapsed(true)` so sidebar auto-collapses on nav. Structure: `<Sidebar />` then `<div className="flex-1"><Header /><main>{children}</main></div>`. Sidebar does not re-mount on route change.
- **Sidebar** — Memoized. Width `w-64` / `w-16`, `transition-[width] duration-200 ease-in-out`. Role-based nav (admin: all + Settings; compliance: all except Settings; viewer: Dashboard, Profile, Reports). Links use `<Link prefetch>`; layout collapses on pathname change.
- **Header** — Memoized. Profile and Settings are `<Link href="/profile">` and `<Link href="/settings">` (Settings for admin only).
- **Page transitions** — Per-page only: `<PageTransition>` wraps content with `motion.div` (opacity + scale 0.98 → 1). No AnimatePresence wrapping the whole layout.
- **Loading** — Each route has `loading.tsx` with skeleton loaders.
- **Charts** — Recharts loaded via `dynamic(..., { ssr: false })` in `trend-chart-dynamic.tsx`.
- **Notifications** — Framer Motion fade, outside-click close, red badge count.
- **Roles** — `admin` | `compliance` | `viewer`. Login redirects with `router.replace("/dashboard")`.

## Design

- **Theme:** Dark by default; light/dark toggle in header, persisted in localStorage
- **Style:** Enterprise-grade, glassmorphism cards, blue-purple gradient accents
- **Auth:** Mock; any email/password + role. Replace with real API in production

## Connecting Backend & Database

### 1. Run the backend

From the project root:

```bash
cd backend
pip install -r requirements.txt
# Ensure .env exists (copy from .env.example) with DATABASE_URL and OPENAI_API_KEY
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be at **http://localhost:8000** (API docs: http://localhost:8000/docs).

### 2. Connect the frontend to the backend

In the **project root** (not inside `backend/`), create or edit `.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Then start the frontend (from project root):

```bash
npm run dev
```

Open **http://localhost:3000**. The dashboard will load real data from the backend (policies, violations, scan status). CORS is enabled on the backend for `http://localhost:3000` and `http://127.0.0.1:3000`.

### 3. Connect an external database (for compliance scans)

The backend needs to connect to **your** database (the one you want to run compliance rules against). Use the API or Swagger:

1. Open **http://localhost:8000/docs**.
2. Find **POST /database/connect**.
3. Send a JSON body with your DB credentials, for example:

```json
{
  "host": "localhost",
  "username": "your_db_user",
  "password": "your_db_password",
  "db_name": "your_database_name"
}
```

After a successful connect, you can upload policies (POST /policy/upload) and run scans (POST /scan/run). The scan runs the extracted rules against the connected external database and stores violations.

**Summary**

| Step | What | Where |
|------|------|--------|
| Backend | `uvicorn app.main:app --reload --port 8000` | `backend/` |
| Frontend env | `NEXT_PUBLIC_API_URL=http://localhost:8000` | `.env.local` in project root |
| Frontend | `npm run dev` | project root |
| External DB | POST /database/connect with host, username, password, db_name | API or Swagger UI |

## Mock Data

- `src/data/` — analytics, policies, rules, violations (JSON). Used when `NEXT_PUBLIC_API_URL` is not set.
