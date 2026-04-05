import {
  ListboxButton as HLButton,
  ListboxOption as HLOption,
  ListboxOptions as HLOptions,
  Listbox,
} from "@headlessui/react";
import * as React from "react";
import { cn } from "../../util/cn";
import { defaultBorderRadius, vscCommandCenterInactiveBorder } from "../../styles/theme";

type ListboxButtonProps = React.ComponentProps<typeof HLButton>;

const ListboxButton = React.forwardRef<HTMLButtonElement, ListboxButtonProps>(
  (props, ref) => {
    return (
      <HLButton
        ref={ref}
        {...props}
        className={cn(
          "bg-input text-foreground border-border m-0 flex flex-1 cursor-pointer flex-row items-center gap-1 border border-solid px-1 py-0.5 text-left transition-colors duration-200 text-xs",
          props.className,
        )}
        style={{
          borderRadius: defaultBorderRadius,
          ...props.style,
        }}
      />
    );
  },
);

type ListboxOptionsProps = React.ComponentProps<typeof HLOptions>;

const ListboxOptions = React.forwardRef<HTMLUListElement, ListboxOptionsProps>(
  (props, ref) => {
    return (
      <HLOptions
        ref={ref}
        anchor={"bottom start"}
        {...props}
        className={cn(
          "bg-input flex w-max min-w-[160px] max-w-[400px] flex-col overflow-auto px-0 shadow-md text-xs",
          props.className,
        )}
        style={{
          border: `1px solid ${vscCommandCenterInactiveBorder}`,
          borderRadius: defaultBorderRadius,
          zIndex: 200000,
          ...props.style,
        }}
      />
    );
  },
);

type ListboxOptionProps = React.ComponentProps<typeof HLOption>;

const ListboxOption = React.forwardRef<HTMLLIElement, ListboxOptionProps>(
  (props, ref) => {
    return (
      <HLOption
        ref={ref}
        {...props}
        className={cn(
          "text-foreground flex select-none flex-row items-center justify-between px-2 py-1 text-xs",
          props.disabled
            ? "opacity-50"
            : "background-transparent hover:bg-list-active hover:text-list-active-foreground cursor-pointer opacity-100",
          props.className,
        )}
      />
    );
  },
);

export { Listbox, ListboxButton, ListboxOption, ListboxOptions };
