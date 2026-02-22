"use client";

import * as React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageCircle, X, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/auth-context";
import { fetchPolicyAsk } from "@/api";

export function AskQuestionFloating() {
    const { user } = useAuth();
    const [open, setOpen] = React.useState(false);
    const [query, setQuery] = React.useState("");
    const [answer, setAnswer] = React.useState<string | null>(null);
    const [error, setError] = React.useState<string | null>(null);
    const [loading, setLoading] = React.useState(false);

    // Only show for admin and compliance
    if (!user || user.role === "viewer") return null;

    const handleClose = () => {
        setOpen(false);
        setQuery("");
        setAnswer(null);
        setError(null);
    };

    const handleSubmit = async (e?: React.FormEvent) => {
        e?.preventDefault();
        const q = query.trim();
        if (!q || loading) return;
        setLoading(true);
        setError(null);
        setAnswer(null);
        try {
            const res = await fetchPolicyAsk(q);
            setAnswer(res.answer);
        } catch (err) {
            const e = err as { message?: string };
            setError(e?.message ?? "An error occurred. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            {/* Floating panel */}
            <AnimatePresence>
                {open && (
                    <motion.div
                        key="ask-panel"
                        initial={{ x: "120%", opacity: 0 }}
                        animate={{ x: 0, opacity: 1 }}
                        exit={{ x: "120%", opacity: 0 }}
                        transition={{ type: "spring", stiffness: 320, damping: 32 }}
                        className={cn(
                            "fixed bottom-24 right-6 z-[200]",
                            "w-[360px] max-h-[70vh] rounded-2xl border border-border shadow-2xl bg-card backdrop-blur-xl",
                            "flex flex-col overflow-hidden"
                        )}
                    >
                        {/* Header */}
                        <div className="flex items-center justify-between border-b border-border/50 px-4 py-3 shrink-0">
                            <div className="flex items-center gap-2">
                                <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/15">
                                    <MessageCircle className="h-4 w-4 text-primary" />
                                </div>
                                <h3 className="font-semibold text-sm">Ask question</h3>
                            </div>
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-7 w-7 rounded-full hover:bg-accent/50"
                                onClick={handleClose}
                                aria-label="Close"
                            >
                                <X className="h-4 w-4" />
                            </Button>
                        </div>

                        {/* Content */}
                        <div className="flex-1 overflow-y-auto p-4 space-y-4">
                            {/* Input row */}
                            <form onSubmit={handleSubmit} className="flex items-center gap-2">
                                <input
                                    type="text"
                                    value={query}
                                    onChange={(e) => setQuery(e.target.value.slice(0, 500))}
                                    placeholder="Type your compliance question..."
                                    maxLength={500}
                                    disabled={loading}
                                    className={cn(
                                        "flex-1 min-w-0 rounded-full border border-border bg-background/60 px-4 py-2 text-sm outline-none",
                                        "focus:border-primary/50 focus:ring-2 focus:ring-primary/20 transition-all duration-150",
                                        "placeholder:text-muted-foreground/60"
                                    )}
                                />
                                <Button
                                    type="submit"
                                    size="sm"
                                    disabled={!query.trim() || loading}
                                    className="rounded-full bg-blue-600 hover:bg-blue-700 text-white shrink-0 px-4"
                                >
                                    {loading ? (
                                        <span className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin block" />
                                    ) : (
                                        <Send className="h-4 w-4" />
                                    )}
                                    <span className="ml-1.5 hidden sm:inline">{loading ? "..." : "Send"}</span>
                                </Button>
                            </form>

                            {/* Rate limit note */}
                            <p className="text-[11px] text-muted-foreground/70">
                                Max 500 chars. Rate limit applies.
                            </p>

                            {/* Error */}
                            {error && (
                                <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                                    {error}
                                </div>
                            )}

                            {/* Answer */}
                            {answer && (
                                <div className="rounded-xl border border-border bg-muted/30 px-4 py-3">
                                    <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-2">Answer</p>
                                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{answer}</p>
                                </div>
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Trigger button */}
            <button
                type="button"
                onClick={() => setOpen((o) => !o)}
                aria-label="Ask a compliance question"
                className={cn(
                    "fixed bottom-6 right-6 z-[200]",
                    "h-14 w-14 rounded-full shadow-lg flex items-center justify-center",
                    "bg-primary text-white hover:bg-primary/90 transition-all duration-200",
                    "hover:scale-105 active:scale-95",
                    open && "bg-primary/80"
                )}
            >
                <AnimatePresence mode="wait" initial={false}>
                    {open ? (
                        <motion.span
                            key="x"
                            initial={{ rotate: -90, opacity: 0 }}
                            animate={{ rotate: 0, opacity: 1 }}
                            exit={{ rotate: 90, opacity: 0 }}
                            transition={{ duration: 0.15 }}
                        >
                            <X className="h-5 w-5" />
                        </motion.span>
                    ) : (
                        <motion.span
                            key="msg"
                            initial={{ rotate: 90, opacity: 0 }}
                            animate={{ rotate: 0, opacity: 1 }}
                            exit={{ rotate: -90, opacity: 0 }}
                            transition={{ duration: 0.15 }}
                        >
                            <MessageCircle className="h-5 w-5" />
                        </motion.span>
                    )}
                </AnimatePresence>
            </button>
        </>
    );
}
