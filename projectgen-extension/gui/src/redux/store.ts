import { configureStore } from '@reduxjs/toolkit';
import projectGenReducer from './slices/projectGenSlice';
import modelConfigReducer from './slices/modelConfigSlice';
import chatHistoryReducer from './slices/chatHistorySlice';

export const store = configureStore({
  reducer: {
    projectGen: projectGenReducer,
    modelConfig: modelConfigReducer,
    chatHistory: chatHistoryReducer,
  }
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
