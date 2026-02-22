"use client";

import { SidebarProvider } from "./sidebar-context";
import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { useSidebar } from "./sidebar-context";
import { cn } from "@/lib/utils";

export function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <AppLayoutContent>{children}</AppLayoutContent>
    </SidebarProvider>
  );
}

function AppLayoutContent({ children }: { children: React.ReactNode }) {
  const { collapsed } = useSidebar();

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <Header />
      <main
        className={cn(
          "min-h-[calc(100vh-4rem)] transition-all duration-300",
          collapsed ? "ml-[72px]" : "ml-64"
        )}
      >
        <div className="p-6">{children}</div>
      </main>
    </div>
  );
}
