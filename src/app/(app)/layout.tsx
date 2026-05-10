"use client";

import { useState, useEffect, useMemo } from "react";
import { usePathname } from "next/navigation";
import { SidebarContext, useSidebar } from "@/components/layout/sidebar-context";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { AskQuestionFloating } from "@/components/layout/ask-question-floating";
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
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    setCollapsed(true);
  }, [pathname]);

  const sidebarValue = useMemo(
    () => ({ collapsed, setCollapsed }),
    [collapsed]
  );

  return (
    <SidebarContext.Provider value={sidebarValue}>
      <AppLayoutInner>{children}</AppLayoutInner>
    </SidebarContext.Provider>
  );
}
