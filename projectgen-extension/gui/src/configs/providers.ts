import { ModelProviderTags } from "../components/modelSelection/utils";
import type { ModelPackage } from "./models";
import { models } from "./models";

export interface InputDescriptor {
  inputType: string;
  key: string;
  label: string;
  placeholder?: string;
  defaultValue?: string | number;
  required?: boolean;
  description?: string;
}

export interface ProviderInfo {
  title: string;
  icon?: string;      // PNG 文件名，如 "openai.png"
  provider: string;
  description: string;
  tags?: ModelProviderTags[];
  packages: ModelPackage[];
  params?: any;
  collectInputFor?: InputDescriptor[];
  apiKeyUrl?: string;
  apiBase?: string;
}

export const providers: Record<string, ProviderInfo> = {
  openai: {
    title: "OpenAI",
    provider: "openai",
    icon: "openai.png",
    description: "Use GPT-4o, GPT-4, or other OpenAI models",
    tags: [ModelProviderTags.RequiresApiKey],
    packages: [
      models.gpt4o,
      models.gpt4oMini,
      models.gpt4Turbo,
      models.gpt35Turbo,
    ],
    collectInputFor: [
      {
        inputType: "password",
        key: "apiKey",
        label: "API Key",
        placeholder: "Enter your OpenAI API key",
        required: true,
      },
      {
        inputType: "text",
        key: "apiBase",
        label: "API Base URL (Optional)",
        placeholder: "https://api.openai.com/v1",
        required: false,
      },
    ],
    apiKeyUrl: "https://platform.openai.com/account/api-keys",
  },
  anthropic: {
    title: "Anthropic",
    provider: "anthropic",
    icon: "anthropic.png",
    description: "Claude models with large context and high recall",
    tags: [ModelProviderTags.RequiresApiKey],
    packages: [
      models.claude35Sonnet,
      models.claude3Haiku,
      models.claude3Opus,
    ],
    collectInputFor: [
      {
        inputType: "password",
        key: "apiKey",
        label: "API Key",
        placeholder: "Enter your Anthropic API key",
        required: true,
      },
      {
        inputType: "text",
        key: "apiBase",
        label: "API Base URL (Optional)",
        placeholder: "https://api.anthropic.com",
        required: false,
      },
    ],
    apiKeyUrl: "https://console.anthropic.com/account/keys",
  },
  deepseek: {
    title: "DeepSeek",
    provider: "deepseek",
    icon: "deepseek.png",
    description: "DeepSeek's efficient and capable models",
    tags: [ModelProviderTags.RequiresApiKey],
    packages: [
      models.deepseekChat,
      models.deepseekCoder,
    ],
    collectInputFor: [
      {
        inputType: "password",
        key: "apiKey",
        label: "API Key",
        placeholder: "Enter your DeepSeek API key",
        required: true,
      },
      {
        inputType: "text",
        key: "apiBase",
        label: "API Base URL (Optional)",
        placeholder: "https://api.deepseek.com",
        required: false,
      },
    ],
    apiKeyUrl: "https://platform.deepseek.com/api_keys",
  },
  ollama: {
    title: "Ollama",
    provider: "ollama",
    icon: "ollama.png",
    description: "Run open-source models locally with Ollama",
    tags: [ModelProviderTags.Local, ModelProviderTags.Free, ModelProviderTags.OpenSource],
    packages: [
      models.llama31,
      models.codellama,
      models.mistral,
      models.qwen25Coder,
    ],
    collectInputFor: [
      {
        inputType: "text",
        key: "apiBase",
        label: "Ollama URL",
        placeholder: "http://localhost:11434",
        defaultValue: "http://localhost:11434",
        required: false,
      },
    ],
  },
  openaiCompatible: {
    title: "OpenAI Compatible",
    provider: "openai-compatible",
    icon: "openai.png",  // 复用 OpenAI 图标
    description: "Any OpenAI-compatible API (vLLM, LM Studio, etc.)",
    tags: [ModelProviderTags.Local],
    packages: [],
    collectInputFor: [
      {
        inputType: "text",
        key: "apiBase",
        label: "API Base URL",
        placeholder: "http://localhost:8000/v1",
        required: true,
      },
      {
        inputType: "password",
        key: "apiKey",
        label: "API Key (Optional)",
        placeholder: "Enter API key if required",
        required: false,
      },
      {
        inputType: "text",
        key: "model",
        label: "Model Name",
        placeholder: "e.g. meta-llama/Llama-3.1-8B-Instruct",
        required: true,
      },
    ],
  },
};

// Helper to get popular providers
export const popularProviders = ["openai", "anthropic", "deepseek", "ollama"];

export const getPopularProviders = () => 
  popularProviders.map(key => providers[key]).filter(Boolean);

export const getOtherProviders = () => 
  Object.entries(providers)
    .filter(([key]) => !popularProviders.includes(key))
    .map(([, provider]) => provider);
