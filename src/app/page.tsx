"use client";

import Link from "next/link";
import { Shield, FileSearch, BarChart3, Zap, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function LandingPage() {
  return (
    <div className="relative min-h-screen overflow-x-hidden bg-background">
      {/* Subtle radial background highlights (indigo/slate, no neon teal) */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(163,126,59,0.18),transparent)] dark:bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(197,160,89,0.25),transparent)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_40%_at_80%_60%,rgba(163,126,59,0.12),transparent)] dark:bg-[radial-gradient(ellipse_60%_40%_at_80%_60%,rgba(197,160,89,0.1),transparent)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_50%_30%_at_20%_80%,rgba(15,17,21,0.1),transparent)]" />
      </div>

      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
              <Shield className="h-5 w-5 text-white" />
            </div>
            <span className="font-semibold">AI Compliance</span>
          </Link>
          <nav className="flex items-center gap-4">
            <a href="#features" className="text-sm text-muted-foreground transition-colors hover:text-foreground">
              Features
            </a>
            <a href="#how-it-works" className="text-sm text-muted-foreground transition-colors hover:text-foreground">
              How It Works
            </a>
            <Link href="/dashboard">
              <Button variant="ghost">Dashboard</Button>
            </Link>
            <Link href="/dashboard">
              <Button>Get Started</Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="relative px-6 pb-24 pt-20 md:pb-32 md:pt-28">
        <div className="mx-auto max-w-4xl text-center">
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl animate-fade-in">
            AI-Powered Continuous{" "}
            <span className="gradient-text">
              Compliance Monitoring
            </span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground animate-fade-in">
            Automate policy analysis and rule extraction with AI. Monitor compliance in real time, reduce risk, and keep your organization audit-ready.
          </p>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-4 animate-fade-in">
            <Link href="/dashboard">
              <Button size="lg" variant="gradient" className="gap-2">
                Go to Dashboard
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <a href="#features">
              <Button size="lg" variant="outline">View Features</Button>
            </a>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="scroll-mt-20 border-t border-border/50 bg-muted/30 px-6 py-20">
        <div className="mx-auto max-w-6xl">
          <h2 className="text-center text-3xl font-bold tracking-tight">
            Enterprise-Grade Compliance, Simplified
          </h2>
          <p className="mx-auto mt-3 max-w-2xl text-center text-muted-foreground">
            From policy upload to violation tracking, one platform for continuous compliance.
          </p>
          <div className="mt-16 grid gap-8 md:grid-cols-3">
            {[
              {
                icon: FileSearch,
                title: "AI Rule Extraction",
                description: "Upload policies and let AI identify compliance rules, severity, and requirements automatically.",
              },
              {
                icon: BarChart3,
                title: "Real-Time Monitoring",
                description: "Track compliance scores, violations, and trends across departments with live dashboards.",
              },
              {
                icon: Zap,
                title: "Review & Remediation",
                description: "Approve or reject findings, add comments, and maintain a full audit trail for regulators.",
              },
            ].map((item) => (
              <div
                key={item.title}
                className="rounded-xl border border-border/50 bg-card/80 p-6 backdrop-blur-sm transition-transform hover:-translate-y-0.5"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                  <item.icon className="h-6 w-6 text-primary" />
                </div>
                <h3 className="mt-4 font-semibold">{item.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="scroll-mt-20 px-6 py-20">
        <div className="mx-auto max-w-4xl">
          <h2 className="text-center text-3xl font-bold tracking-tight">
            How It Works
          </h2>
          <div className="mt-16 space-y-12">
            {[
              { step: 1, title: "Upload policies", text: "Drag and drop PDF policy documents into the platform." },
              { step: 2, title: "AI extracts rules", text: "Our AI identifies compliance rules, clauses, and severity levels." },
              { step: 3, title: "Monitor & detect", text: "Track violations, compliance scores, and risk by department." },
              { step: 4, title: "Review & report", text: "Approve findings, add comments, and export audit-ready reports." },
            ].map((item) => (
              <div key={item.step} className="flex gap-6">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-bold text-primary-foreground">
                  {item.step}
                </div>
                <div>
                  <h3 className="font-semibold">{item.title}</h3>
                  <p className="mt-1 text-muted-foreground">{item.text}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Enterprise trust */}
      <section className="border-t border-border/50 bg-muted/30 px-6 py-16">
        <div className="mx-auto max-w-6xl">
          <p className="text-center text-sm font-medium text-muted-foreground">
            Trusted by compliance teams at leading enterprises
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-12 opacity-70">
            {["Acme Corp", "GlobalTech", "SecureBank", "DataFirst", "CloudScale"].map((name) => (
              <span key={name} className="text-lg font-semibold text-muted-foreground">
                {name}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/50 px-6 py-12">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-6 sm:flex-row">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            <span className="font-medium">AI Compliance Intelligence Platform</span>
          </div>
          <div className="flex gap-6 text-sm text-muted-foreground">
            <a href="#features" className="hover:text-foreground">Features</a>
            <a href="#how-it-works" className="hover:text-foreground">How It Works</a>
            <Link href="/dashboard" className="hover:text-foreground">Dashboard</Link>
          </div>
        </div>
        <p className="mx-auto mt-8 max-w-6xl text-center text-xs text-muted-foreground">
          © {new Date().getFullYear()} AI Compliance Intelligence Platform. Enterprise compliance monitoring.
        </p>
      </footer>
    </div>
  );
}
