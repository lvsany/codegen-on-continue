import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface GeneratedFile {
  path: string;
  content?: string;
}

export interface ProjectGenState {
  isGenerating: boolean;
  currentStage: 'architecture' | 'skeleton' | 'code' | '';
  progress: number;
  files: GeneratedFile[];
  currentRepo: string;
  error: string | null;
}

const initialState: ProjectGenState = {
  isGenerating: false,
  currentStage: '',
  progress: 0,
  files: [],
  currentRepo: '',
  error: null
};

const projectGenSlice = createSlice({
  name: 'projectGen',
  initialState,
  reducers: {
    startGeneration: (state, action: PayloadAction<string>) => {
      state.isGenerating = true;
      state.currentRepo = action.payload;
      state.files = [];
      state.progress = 0;
      state.currentStage = '';
      state.error = null;
    },
    updateProgress: (state, action: PayloadAction<{ stage: 'architecture' | 'skeleton' | 'code'; progress: number }>) => {
      state.currentStage = action.payload.stage;
      state.progress = action.payload.progress;
    },
    addFile: (state, action: PayloadAction<GeneratedFile>) => {
      state.files.push(action.payload);
    },
    completeGeneration: (state) => {
      state.isGenerating = false;
      state.progress = 100;
    },
    stopGeneration: (state) => {
      state.isGenerating = false;
      state.error = 'Generation stopped by user';
    },
    setError: (state, action: PayloadAction<string>) => {
      state.error = action.payload;
      // 保持 isGenerating 为 true，让用户可以点击停止按钮
      // state.isGenerating = false;
    },
    resetGeneration: (state) => {
      state.isGenerating = false;
      state.currentStage = '';
      state.progress = 0;
      state.files = [];
      state.currentRepo = '';
      state.error = null;
    },
    reset: () => initialState
  }
});

export const {
  startGeneration,
  updateProgress,
  addFile,
  completeGeneration,
  stopGeneration,
  setError,
  resetGeneration,
  reset
} = projectGenSlice.actions;

export default projectGenSlice.reducer;
