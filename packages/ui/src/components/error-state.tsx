import { AlertTriangle } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "../lib/cn";
import { Button } from "./button";

export interface ErrorStateProps {
  title?: string;
  description?: string;
  error?: unknown;
  onRetry?: () => void;
  action?: ReactNode;
  className?: string;
}

function messageFromError(error: unknown): string | undefined {
  if (!error) return undefined;
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  return undefined;
}

export function ErrorState({
  title = "Something went wrong",
  description,
  error,
  onRetry,
  action,
  className,
}: ErrorStateProps) {
  const detail = description ?? messageFromError(error);
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-lg border border-danger/30 bg-danger/5 px-6 py-12 text-center",
        className
      )}
    >
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-danger/15 text-danger">
        <AlertTriangle className="h-5 w-5" />
      </div>
      <div className="space-y-1">
        <p className="text-sm font-medium text-foreground">{title}</p>
        {detail ? <p className="max-w-sm text-sm text-muted-foreground">{detail}</p> : null}
      </div>
      {action}
      {onRetry ? (
        <Button variant="outline" size="sm" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}
