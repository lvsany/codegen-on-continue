import styled from 'styled-components';
import { defaultBorderRadius, vscInputBackground, vscInputBorder } from '../index';

export const InputBoxDiv = styled.div`
  background-color: ${vscInputBackground};
  border: 1px solid ${vscInputBorder};
  border-radius: ${defaultBorderRadius};
  padding: 8px 12px;
  transition: all 0.2s ease;
  
  &:focus-within {
    border-color: var(--vscode-focusBorder);
    box-shadow: 0 0 0 1px var(--vscode-focusBorder);
  }
  
  &.generating {
    border-color: var(--vscode-button-background);
    box-shadow: 0 0 0 1px var(--vscode-button-background);
  }
`;
