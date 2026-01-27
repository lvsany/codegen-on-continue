import { configureStore } from '@reduxjs/toolkit';
import projectGenReducer from './slices/projectGenSlice';

export const store = configureStore({
  reducer: {
    projectGen: projectGenReducer
  }
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
