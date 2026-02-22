"use client";

import { useState, useEffect, useMemo } from "react";
import { usePathname, useRouter } from "next/navigation";
import { SidebarContext, useSidebar } from "@/components/layout/sidebar-context";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { AskQuestionFloating } from "@/components/layout/ask-question-floating";
import { useAuth } from "@/contexts/auth-context";
import { cn } from "@/lib/utils";

function AppLayoutInner({ children }: { children: React.ReactNode }) {
  const { collapsed } = useSidebar();

  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar />
      <div className={cn("flex-1 flex flex-col min-w-0 transition-[margin] duration-200 ease-in-out", collapsed ? "ml-16" : "ml-64")}>
        <Header />
        <main className="flex-1 p-6">
          {children}
        </main>
      </div>
      <AskQuestionFloating />
    </div>
  );
}

export default function AppGroupLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    setCollapsed(true);
  }, [pathname]);

  useEffect(() => {
    if (isLoading) return;
    if (!user) {
      router.replace("/login");
    }
  }, [user, isLoading, router]);

  const sidebarValue = useMemo(
    () => ({ collapsed, setCollapsed }),
    [collapsed]
  );

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" aria-hidden />
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <SidebarContext.Provider value={sidebarValue}>
      <AppLayoutInner>{children}</AppLayoutInner>
    </SidebarContext.Provider>
  );
}
