import styled, { keyframes } from 'styled-components';

// 渐变动画 - Continue 风格的彩虹边框
const gradient = keyframes`
  0% { background-position: 0px 0; }
  100% { background-position: 100em 0; }
`;

// 输入框外层容器 - Continue 风格
export const InputBoxContainer = styled.div`
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 0 8px;
`;

// 渐变边框 - Continue GradientBorder 风格
export const GradientBorder = styled.div<{
  loading?: boolean;
}>`
  border-radius: 8px;
  padding: 1px;
  background: ${props => props.loading 
    ? `repeating-linear-gradient(
        101.79deg,
        #1BBE84 0%,
        #331BBE 16%,
        #BE1B55 33%,
        #A6BE1B 55%,
        #BE1B55 67%,
        #331BBE 85%,
        #1BBE84 99%
      )`
    : 'var(--vscode-input-border, #3c3c3c)'
  };
  animation: ${props => props.loading ? gradient : 'none'} 6s linear infinite;
  background-size: 200% 200%;
  width: 100%;
  display: flex;
  flex-direction: column;
  transition: all 0.2s ease;
  
  &:focus-within {
    background: var(--vscode-focusBorder, #007fd4);
  }
`;

// 输入框内部 - Continue 风格
export const InputBoxInner = styled.div`
  background: var(--vscode-input-background, #3c3c3c);
  border-radius: 7px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
`;

// 编辑器区域
export const EditorArea = styled.div`
  min-height: 40px;
  max-height: 200px;
  overflow-y: auto;
  padding: 8px 12px;
  
  &::-webkit-scrollbar {
    width: 4px;
  }
  
  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.2);
    border-radius: 2px;
  }
`;

// 工具栏 - Continue InputToolbar 风格
export const InputToolbar = styled.div`
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
  padding: 6px 8px;
  background: var(--vscode-input-background, #3c3c3c);
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 11px;
  user-select: none;
`;

// 工具栏左侧
export const ToolbarLeft = styled.div`
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 6px;
`;

// 工具栏右侧
export const ToolbarRight = styled.div`
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
`;

// 悬停项目 - Continue HoverItem 风格
export const HoverItem = styled.button`
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px 6px;
  border-radius: 4px;
  background: transparent;
  border: none;
  color: var(--vscode-descriptionForeground, #999);
  cursor: pointer;
  transition: all 0.15s ease;
  font-size: inherit;
  
  &:hover {
    background: rgba(255, 255, 255, 0.08);
    color: var(--vscode-foreground, #fff);
  }
  
  &:active {
    background: rgba(255, 255, 255, 0.12);
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

// 提交按钮 - Continue 风格
export const SubmitButton = styled.button<{ variant?: 'primary' | 'secondary' }>`
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 4px;
  border: none;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  
  background: ${props => props.variant === 'primary' 
    ? 'var(--vscode-button-background, #0e639c)' 
    : 'rgba(255, 255, 255, 0.08)'};
  color: ${props => props.variant === 'primary'
    ? 'var(--vscode-button-foreground, #fff)'
    : 'var(--vscode-foreground, #fff)'};
  
  &:hover:not(:disabled) {
    filter: brightness(1.2);
  }
  
  &:active:not(:disabled) {
    transform: scale(0.98);
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

// 分隔符
export const ToolbarDivider = styled.div`
  width: 1px;
  height: 14px;
  background: rgba(255, 255, 255, 0.1);
  margin: 0 2px;
`;

// 快捷键提示
export const KeyHint = styled.span`
  color: var(--vscode-descriptionForeground, #999);
  font-size: 10px;
  opacity: 0.7;
  
  kbd {
    padding: 1px 4px;
    border-radius: 3px;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.1);
    font-family: inherit;
    font-size: 9px;
  }
`;
