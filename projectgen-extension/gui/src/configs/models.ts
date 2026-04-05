export interface ModelPackage {
  title: string;
  icon?: string;
  description: string;
  params: {
    model: string;
    contextLength: number;
    [key: string]: any;
  };
  isOpenSource: boolean;
}

export const models: { [key: string]: ModelPackage } = {
  // OpenAI Models
  gpt4o: {
    title: "GPT-4o",
    description: "OpenAI's most capable model for complex tasks",
    params: {
      model: "gpt-4o",
      contextLength: 128000,
    },
    isOpenSource: false,
  },
  gpt4oMini: {
    title: "GPT-4o Mini",
    description: "Fast and affordable small model",
    params: {
      model: "gpt-4o-mini",
      contextLength: 128000,
    },
    isOpenSource: false,
  },
  gpt4Turbo: {
    title: "GPT-4 Turbo",
    description: "GPT-4 with vision and improved instruction following",
    params: {
      model: "gpt-4-turbo",
      contextLength: 128000,
    },
    isOpenSource: false,
  },
  gpt35Turbo: {
    title: "GPT-3.5 Turbo",
    description: "Fast and capable for most tasks",
    params: {
      model: "gpt-3.5-turbo",
      contextLength: 16385,
    },
    isOpenSource: false,
  },

  // Anthropic Models
  claude35Sonnet: {
    title: "Claude 3.5 Sonnet",
    description: "Anthropic's most intelligent model",
    params: {
      model: "claude-3-5-sonnet-20241022",
      contextLength: 200000,
    },
    isOpenSource: false,
  },
  claude3Haiku: {
    title: "Claude 3 Haiku",
    description: "Fast and cost-effective",
    params: {
      model: "claude-3-haiku-20240307",
      contextLength: 200000,
    },
    isOpenSource: false,
  },
  claude3Opus: {
    title: "Claude 3 Opus",
    description: "Most powerful Claude model for complex tasks",
    params: {
      model: "claude-3-opus-20240229",
      contextLength: 200000,
    },
    isOpenSource: false,
  },

  // DeepSeek Models
  deepseekChat: {
    title: "DeepSeek Chat",
    description: "DeepSeek's conversational model",
    params: {
      model: "deepseek-chat",
      contextLength: 64000,
    },
    isOpenSource: false,
  },
  deepseekCoder: {
    title: "DeepSeek Coder",
    description: "Optimized for coding tasks",
    params: {
      model: "deepseek-coder",
      contextLength: 64000,
    },
    isOpenSource: false,
  },

  // Ollama / Local Models
  llama31: {
    title: "Llama 3.1",
    description: "Meta's open-weight model",
    params: {
      model: "llama3.1",
      contextLength: 8192,
    },
    isOpenSource: true,
  },
  codellama: {
    title: "Code Llama",
    description: "Meta's code-specialized model",
    params: {
      model: "codellama",
      contextLength: 16384,
    },
    isOpenSource: true,
  },
  mistral: {
    title: "Mistral",
    description: "Mistral AI's efficient model",
    params: {
      model: "mistral",
      contextLength: 32768,
    },
    isOpenSource: true,
  },
  qwen25Coder: {
    title: "Qwen 2.5 Coder",
    description: "Alibaba's code-optimized model",
    params: {
      model: "qwen2.5-coder",
      contextLength: 32768,
    },
    isOpenSource: true,
  },
};
