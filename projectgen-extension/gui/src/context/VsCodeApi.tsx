import { createContext } from 'react';
import { VsCodeApi } from '../vscode';

export const VsCodeApiContext = createContext<VsCodeApi | undefined>(undefined);
