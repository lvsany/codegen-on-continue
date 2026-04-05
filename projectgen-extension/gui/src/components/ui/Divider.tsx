import { cn } from "../../util/cn";

interface DividerProps {
  className?: string;
}

export function Divider({ className }: DividerProps) {
  return <div className={cn("bg-border my-2 h-px min-h-px", className)} />;
}
