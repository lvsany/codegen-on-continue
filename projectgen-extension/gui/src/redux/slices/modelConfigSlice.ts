import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { ModelConfig } from '../../forms/AddModelForm';

export interface ModelConfigState {
  // Current selected model config
  currentConfig: ModelConfig | null;
  // List of saved model configs
  savedConfigs: ModelConfig[];
  // UI state
  showConfigDialog: boolean;
}

const DEFAULT_CONFIG: ModelConfig = {
  provider: 'openai',
  model: 'gpt-4o',
  title: 'GPT-4o',
  contextLength: 128000,
};

// Try to load from localStorage
const loadSavedConfigs = (): ModelConfig[] => {
  try {
    const saved = localStorage.getItem('projectgen_model_configs');
    return saved ? JSON.parse(saved) : [];
  } catch {
    return [];
  }
};

const loadCurrentConfig = (): ModelConfig | null => {
  try {
    const saved = localStorage.getItem('projectgen_current_config');
    return saved ? JSON.parse(saved) : null;
  } catch {
    return null;
  }
};

const initialState: ModelConfigState = {
  currentConfig: loadCurrentConfig() || DEFAULT_CONFIG,
  savedConfigs: loadSavedConfigs(),
  showConfigDialog: false,
};

const modelConfigSlice = createSlice({
  name: 'modelConfig',
  initialState,
  reducers: {
    setCurrentConfig: (state, action: PayloadAction<ModelConfig>) => {
      state.currentConfig = action.payload;
      // Save to localStorage
      localStorage.setItem('projectgen_current_config', JSON.stringify(action.payload));
    },
    addSavedConfig: (state, action: PayloadAction<ModelConfig>) => {
      // Check if config with same title exists
      const existingIndex = state.savedConfigs.findIndex(
        c => c.title === action.payload.title && c.provider === action.payload.provider
      );
      if (existingIndex >= 0) {
        state.savedConfigs[existingIndex] = action.payload;
      } else {
        state.savedConfigs.push(action.payload);
      }
      // Save to localStorage
      localStorage.setItem('projectgen_model_configs', JSON.stringify(state.savedConfigs));
    },
    removeSavedConfig: (state, action: PayloadAction<{ provider: string; title: string }>) => {
      state.savedConfigs = state.savedConfigs.filter(
        c => !(c.provider === action.payload.provider && c.title === action.payload.title)
      );
      localStorage.setItem('projectgen_model_configs', JSON.stringify(state.savedConfigs));
    },
    setShowConfigDialog: (state, action: PayloadAction<boolean>) => {
      state.showConfigDialog = action.payload;
    },
    clearAllConfigs: (state) => {
      state.savedConfigs = [];
      state.currentConfig = DEFAULT_CONFIG;
      localStorage.removeItem('projectgen_model_configs');
      localStorage.removeItem('projectgen_current_config');
    },
  },
});

export const {
  setCurrentConfig,
  addSavedConfig,
  removeSavedConfig,
  setShowConfigDialog,
  clearAllConfigs,
} = modelConfigSlice.actions;

export default modelConfigSlice.reducer;
