"use client";

/** Lightweight wrapper for consistent layout. Animations removed for faster perceived load. */
export function PageTransition({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={className}>{children}</div>;
}
