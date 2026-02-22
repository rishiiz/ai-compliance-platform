"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bell, AlertTriangle, CheckCircle, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { useNotifications } from "@/api/hooks";
import { markNotificationRead } from "@/api";
import { config } from "@/lib/env";

function formatNotificationTime(iso: string): string {
  if (!iso) return "";
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins} min ago`;
  if (diffHours < 24) return `${diffHours} hour ago`;
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  return date.toLocaleDateString();
}

export function NotificationDropdown() {
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef<HTMLDivElement>(null);
  const { data: notifications, refetch } = useNotifications();
  const list = config.apiUrl ? notifications : [];
  const unread = list.filter((n) => !n.read);
  const count = unread.length;

  // When user opens the dropdown, mark all visible unread as read
  React.useEffect(() => {
    if (!open || unread.length === 0 || !config.apiUrl) return;
    let cancelled = false;
    (async () => {
      for (const n of unread) {
        if (cancelled) break;
        try {
          await markNotificationRead(n.id);
        } catch {
          // ignore
        }
      }
      if (!cancelled) refetch();
    })();
    return () => {
      cancelled = true;
    };
  }, [open]);

  React.useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const iconMap = {
    critical: AlertTriangle,
    warning: AlertTriangle,
    success: CheckCircle,
    info: Info,
  };

  return (
    <div className="relative" ref={ref}>
      <Button
        variant="ghost"
        size="icon"
        className="relative"
        onClick={() => setOpen((o) => !o)}
        aria-label="Notifications"
        aria-expanded={open}
      >
        <Bell className="h-5 w-5" />
        {count > 0 && (
          <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-medium text-destructive-foreground">
            {count > 9 ? "9+" : count}
          </span>
        )}
      </Button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            className="absolute right-0 top-full z-[100] mt-2 w-80 overflow-hidden rounded-lg border border-border bg-card shadow-xl backdrop-blur-xl"
          >
            <div className="border-b border-border/50 px-4 py-3">
              <h3 className="font-semibold">Notifications</h3>
              <p className="text-xs text-muted-foreground">{count} unread</p>
            </div>
            <ScrollArea className="h-[280px]">
              <div className="p-2">
                {list.length === 0 ? (
                  <p className="px-3 py-6 text-center text-sm text-muted-foreground">
                    No notifications
                  </p>
                ) : (
                  list.map((n) => {
                    const Icon = iconMap[n.type] ?? Info;
                    // Build subtitle: policy_name takes priority over body
                    const subtitle = n.policy_name
                      ? `Policy: ${n.policy_name}`
                      : n.body
                        ? n.body.slice(0, 60) + (n.body.length > 60 ? "…" : "")
                        : null;
                    return (
                      <button
                        key={n.id}
                        type="button"
                        className={cn(
                          "flex w-full gap-3 rounded-lg px-3 py-2.5 text-left transition-colors hover:bg-accent/50",
                          !n.read && "bg-accent/30"
                        )}
                        onClick={async () => {
                          if (!n.read && config.apiUrl) {
                            try {
                              await markNotificationRead(n.id);
                              refetch();
                            } catch {
                              // ignore
                            }
                          }
                          setOpen(false);
                        }}
                      >
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted">
                          <Icon
                            className={cn(
                              "h-4 w-4",
                              n.type === "critical" && "text-destructive",
                              n.type === "warning" && "text-amber-500",
                              n.type === "success" && "text-emerald-500",
                              n.type === "info" && "text-primary"
                            )}
                          />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium">{n.title}</p>
                          {subtitle && (
                            <p className="truncate text-xs text-muted-foreground mt-0.5">{subtitle}</p>
                          )}
                          <p className="text-xs text-muted-foreground mt-0.5">
                            {formatNotificationTime(n.createdAt)}
                          </p>
                        </div>
                      </button>
                    );
                  })
                )}
              </div>
            </ScrollArea>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
