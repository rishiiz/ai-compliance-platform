"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { Search, ChevronDown, Sun, Moon, LogOut, Menu, X, User, Settings } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import { useSidebar } from "./sidebar-context";
import { useAuth } from "@/contexts/auth-context";
import { useTheme } from "@/contexts/theme-context";
import { useToast } from "@/contexts/toast-context";
import { NotificationDropdown } from "./notification-dropdown";

function HeaderInner() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { collapsed, setCollapsed } = useSidebar();
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { toast } = useToast();
  const [searchFocused, setSearchFocused] = React.useState(false);
  const [dropdownOpen, setDropdownOpen] = React.useState(false);
  const [searchQuery, setSearchQuery] = React.useState("");

  const urlQ = pathname === "/search" ? searchParams.get("q") ?? "" : "";
  React.useEffect(() => {
    if (urlQ !== "" && urlQ !== searchQuery) setSearchQuery(urlQ);
  }, [urlQ]);

  const handleLogout = () => {
    setDropdownOpen(false);
    logout();
    toast("Signed out successfully");
  };

  const displayName = user?.name ?? "User";
  const initials = displayName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <header className="sticky top-0 z-30 flex h-16 shrink-0 items-center gap-4 border-b border-border/50 bg-background/80 px-6 backdrop-blur-xl">
      <Button
        variant="ghost"
        size="icon"
        className="shrink-0 hover:bg-accent/50 transition-colors duration-150"
        onClick={() => setCollapsed(!collapsed)}
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {collapsed ? <Menu className="h-5 w-5" /> : <X className="h-5 w-5" />}
      </Button>

      <div className="flex flex-1 items-center gap-4">
        <form
          className={cn(
            "relative flex-1 max-w-md transition-all duration-200 ease-out",
            searchFocused && "max-w-xl"
          )}
          onSubmit={(e) => {
            e.preventDefault();
            const q = searchQuery.trim();
            if (q) router.push(`/search?q=${encodeURIComponent(q)}`);
          }}
        >
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground transition-colors duration-150" />
          <Input
            type="search"
            placeholder="Search policies, rules, violations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 bg-background/50 focus:bg-background/80 transition-colors duration-150"
            onFocus={() => setSearchFocused(true)}
            onBlur={() => setSearchFocused(false)}
          />
        </form>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          className="hover:bg-accent/50 transition-all duration-150"
          aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          <div className="transition-opacity duration-200">
            {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </div>
        </Button>

        <NotificationDropdown />

        <DropdownMenu open={dropdownOpen} onOpenChange={setDropdownOpen}>
          <DropdownMenuTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              className="flex cursor-pointer items-center gap-2 px-2 hover:bg-accent/50 transition-colors duration-150"
            >
              <Avatar className="h-8 w-8 ring-2 ring-transparent hover:ring-primary/20 transition-all duration-150">
                <AvatarImage src="" alt={displayName} />
                <AvatarFallback className="text-xs bg-primary/20 text-primary">
                  {initials}
                </AvatarFallback>
              </Avatar>
              <span className="hidden text-sm font-medium sm:inline-block">
                {displayName}
              </span>
              <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition-transform duration-150", dropdownOpen && "rotate-180")} />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56 z-[100]" onCloseAutoFocus={(e) => e.preventDefault()}>
            <DropdownMenuItem asChild>
              <Link href="/dashboard" onClick={() => setDropdownOpen(false)}>Dashboard</Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href="/profile" onClick={() => setDropdownOpen(false)}>
                <User className="mr-2 h-4 w-4" />
                Profile
              </Link>
            </DropdownMenuItem>
            {user?.role === "admin" && (
              <DropdownMenuItem asChild>
                <Link href="/settings" onClick={() => setDropdownOpen(false)}>
                  <Settings className="mr-2 h-4 w-4" />
                  Settings
                </Link>
              </DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="cursor-pointer text-destructive focus:text-destructive"
              onClick={handleLogout}
            >
              <LogOut className="mr-2 h-4 w-4" />
              Logout
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}

export const Header = React.memo(HeaderInner);
