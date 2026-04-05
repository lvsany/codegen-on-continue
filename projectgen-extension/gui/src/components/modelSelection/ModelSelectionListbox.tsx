import {
  CheckIcon,
  ChevronUpDownIcon,
  CubeIcon,
} from "@heroicons/react/24/outline";
import { Fragment } from "react";
import {
  Listbox,
  ListboxButton,
  ListboxOption,
  ListboxOptions,
  Transition,
} from "../ui";

export interface DisplayInfo {
  title: string;
  icon?: string;
}

// Provider Logo 组件
const ProviderIcon: React.FC<{ icon?: string; className?: string }> = ({ icon, className = "h-4 w-4" }) => {
  if (!icon) {
    return <CubeIcon className={className} />;
  }
  
  // 如果是 .png 文件，使用图片
  if (icon.endsWith('.png')) {
    return (
      <img 
        src={`logos/${icon}`} 
        alt="" 
        className={`${className} object-contain`}
        onError={(e) => {
          (e.target as HTMLImageElement).style.display = 'none';
        }}
      />
    );
  }
  
  // 否则作为 emoji 显示
  return <span className={className}>{icon}</span>;
};

interface ModelSelectionListboxProps {
  selectedProvider: DisplayInfo;
  setSelectedProvider: (val: DisplayInfo) => void;
  topOptions?: DisplayInfo[];
  otherOptions?: DisplayInfo[];
}

function ModelSelectionListbox({
  selectedProvider,
  setSelectedProvider,
  topOptions = [],
  otherOptions = [],
}: ModelSelectionListboxProps) {
  return (
    <Listbox value={selectedProvider} onChange={setSelectedProvider}>
      <div className="relative mb-2 mt-1">
        <ListboxButton className="bg-background border-border text-foreground hover:bg-input relative m-0 grid h-full w-full cursor-pointer grid-cols-[1fr_auto] items-center rounded-lg border border-solid py-2 pl-3 pr-10 text-left focus:outline-none">
          <span className="flex items-center">
            <ProviderIcon icon={selectedProvider.icon} className="mr-3 h-5 w-5" />
            <span className="text-xs">{selectedProvider.title}</span>
          </span>
          <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
            <ChevronUpDownIcon
              className="text-description-muted h-5 w-5"
              aria-hidden="true"
            />
          </span>
        </ListboxButton>

        <Transition
          as={Fragment}
          leave="transition ease-in duration-100"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <ListboxOptions className="bg-input rounded-default absolute left-0 top-full z-10 mt-1 h-fit w-full overflow-y-auto p-0 focus:outline-none [&]:!max-h-[30vh]">
            {topOptions.length > 0 && (
              <div className="py-1">
                <div className="text-description-muted px-3 py-1 text-xs font-medium uppercase tracking-wider">
                  Popular
                </div>
                {topOptions.map((option, index) => (
                  <ListboxOption
                    key={index}
                    className="hover:bg-list-active hover:text-list-active-foreground relative flex cursor-pointer select-none items-center justify-between gap-2 p-1.5 px-3 py-2 pr-4"
                    value={option}
                  >
                    <div className="flex items-center">
                      <ProviderIcon icon={option.icon} className="mr-2 h-4 w-4" />
                      <span className="text-xs">{option.title}</span>
                    </div>
                    {selectedProvider.title === option.title && (
                      <CheckIcon className="h-3 w-3" aria-hidden="true" />
                    )}
                  </ListboxOption>
                ))}
              </div>
            )}
            {topOptions.length > 0 && otherOptions.length > 0 && (
              <div className="bg-border my-1 h-px min-h-px" />
            )}
            {otherOptions.length > 0 && (
              <div className="py-1">
                <div className="text-description-muted px-3 py-1 text-xs font-medium uppercase tracking-wider">
                  Additional providers
                </div>
                {otherOptions.map((option, index) => (
                  <ListboxOption
                    key={index}
                    className="hover:bg-list-active hover:text-list-active-foreground relative flex cursor-pointer select-none items-center justify-between gap-2 p-1.5 px-3 py-2 pr-4"
                    value={option}
                  >
                    <div className="flex items-center">
                      <ProviderIcon icon={option.icon} className="mr-2 h-4 w-4" />
                      <span className="text-xs">{option.title}</span>
                    </div>
                    {selectedProvider.title === option.title && (
                      <CheckIcon className="h-3 w-3" aria-hidden="true" />
                    )}
                  </ListboxOption>
                ))}
              </div>
            )}
          </ListboxOptions>
        </Transition>
      </div>
    </Listbox>
  );
}

export default ModelSelectionListbox;
