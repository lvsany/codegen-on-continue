import * as React from "react";
import { cn } from "../../util/cn";

type InputProps = React.ComponentProps<"input">;

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={cn(
          "w-full px-3 py-2 rounded bg-input text-foreground border border-solid border-border",
          "focus:outline-none focus:border-border-focus",
          "placeholder:text-description-muted",
          "text-sm",
          className
        )}
        {...props}
      />
    );
  }
);

Input.displayName = "Input";

export { Input };
