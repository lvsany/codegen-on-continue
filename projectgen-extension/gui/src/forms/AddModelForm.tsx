import { ArrowTopRightOnSquareIcon } from "@heroicons/react/24/outline";
import { useEffect, useState } from "react";
import { useForm, FormProvider } from "react-hook-form";
import { Button, Input } from "../components/ui";
import ModelSelectionListbox, { DisplayInfo } from "../components/modelSelection/ModelSelectionListbox";
import {
  ProviderInfo,
  providers,
  getPopularProviders,
  getOtherProviders,
} from "../configs/providers";
import { ModelPackage } from "../configs/models";

interface AddModelFormProps {
  onDone: (config: ModelConfig) => void;
  onCancel?: () => void;
}

export interface ModelConfig {
  provider: string;
  model: string;
  title: string;
  apiKey?: string;
  apiBase?: string;
  contextLength: number;
}

export function AddModelForm({ onDone, onCancel }: AddModelFormProps) {
  const [selectedProvider, setSelectedProvider] = useState<ProviderInfo>(
    providers["openai"]!
  );
  const [selectedModel, setSelectedModel] = useState<ModelPackage>(
    selectedProvider.packages[0]
  );
  const formMethods = useForm();

  const popularProvidersList = getPopularProviders();
  const otherProvidersList = getOtherProviders();

  useEffect(() => {
    if (selectedProvider.packages.length > 0) {
      setSelectedModel(selectedProvider.packages[0]);
    }
  }, [selectedProvider]);

  function isDisabled() {
    // For providers that need API key
    if (selectedProvider.collectInputFor?.some(f => f.key === "apiKey" && f.required)) {
      const apiKey = formMethods.watch("apiKey");
      if (!apiKey || apiKey.trim() === "") {
        return true;
      }
    }

    // For OpenAI Compatible that needs model name
    if (selectedProvider.provider === "openai-compatible") {
      const model = formMethods.watch("model");
      const apiBase = formMethods.watch("apiBase");
      if (!model || !apiBase) {
        return true;
      }
    }

    return false;
  }

  function onSubmit() {
    const apiKey = formMethods.watch("apiKey");
    const apiBase = formMethods.watch("apiBase");
    const customModel = formMethods.watch("model");

    const config: ModelConfig = {
      provider: selectedProvider.provider,
      model: customModel || selectedModel?.params.model || "gpt-4o",
      title: selectedModel?.title || customModel || "Custom Model",
      apiKey: apiKey || undefined,
      apiBase: apiBase || undefined,
      contextLength: selectedModel?.params.contextLength || 8192,
    };

    onDone(config);
  }

  return (
    <FormProvider {...formMethods}>
      <form onSubmit={formMethods.handleSubmit(onSubmit)}>
        <div className="mx-auto max-w-md p-4">
          <h2 className="mb-4 text-center text-lg font-semibold text-foreground">
            Configure Model
          </h2>

          <div className="flex flex-col gap-4">
            {/* Provider Selection */}
            <div>
              <label className="block text-sm font-medium text-foreground mb-1">
                Provider
              </label>
              <ModelSelectionListbox
                selectedProvider={{ title: selectedProvider.title, icon: selectedProvider.icon }}
                setSelectedProvider={(val: DisplayInfo) => {
                  const match = [...popularProvidersList, ...otherProvidersList].find(
                    (provider) => provider.title === val.title
                  );
                  if (match) {
                    setSelectedProvider(match);
                  }
                }}
                topOptions={popularProvidersList.map(p => ({ title: p.title, icon: p.icon }))}
                otherOptions={otherProvidersList.map(p => ({ title: p.title, icon: p.icon }))}
              />
              <span className="text-description-muted text-xs">
                {selectedProvider.description}
              </span>
            </div>

            {/* Model Selection (if provider has packages) */}
            {selectedProvider.packages.length > 0 && (
              <div>
                <label className="block text-sm font-medium text-foreground mb-1">
                  Model
                </label>
                <ModelSelectionListbox
                  selectedProvider={{ title: selectedModel?.title || "Select model", icon: selectedModel?.icon }}
                  setSelectedProvider={(val: DisplayInfo) => {
                    const match = selectedProvider.packages.find(
                      (pkg) => pkg.title === val.title
                    );
                    if (match) {
                      setSelectedModel(match);
                    }
                  }}
                  topOptions={selectedProvider.packages.map(p => ({ title: p.title, icon: p.icon }))}
                />
                {selectedModel && (
                  <span className="text-description-muted text-xs">
                    {selectedModel.description}
                  </span>
                )}
              </div>
            )}

            {/* Dynamic Input Fields */}
            {selectedProvider.collectInputFor?.map((field) => (
              <div key={field.key}>
                <label className="block text-sm font-medium text-foreground mb-1">
                  {field.label}
                  {field.required && <span className="text-error ml-1">*</span>}
                </label>
                <Input
                  id={field.key}
                  type={field.inputType === "password" ? "password" : "text"}
                  placeholder={field.placeholder}
                  defaultValue={field.defaultValue as string}
                  {...formMethods.register(field.key)}
                />
                {field.description && (
                  <span className="text-description-muted text-xs">
                    {field.description}
                  </span>
                )}
              </div>
            ))}

            {/* API Key URL Link */}
            {selectedProvider.apiKeyUrl && (
              <a
                href={selectedProvider.apiKeyUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-xs text-description hover:text-foreground"
              >
                <ArrowTopRightOnSquareIcon className="h-3 w-3" />
                Get API key from {selectedProvider.title}
              </a>
            )}
          </div>

          {/* Buttons */}
          <div className="mt-6 flex gap-2">
            {onCancel && (
              <Button
                type="button"
                variant="secondary"
                className="flex-1"
                onClick={onCancel}
              >
                Cancel
              </Button>
            )}
            <Button
              type="submit"
              variant="primary"
              className="flex-1"
              disabled={isDisabled()}
            >
              Save Configuration
            </Button>
          </div>
        </div>
      </form>
    </FormProvider>
  );
}

export default AddModelForm;
