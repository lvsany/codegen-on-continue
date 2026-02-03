import React, { useCallback, useRef, useState } from 'react';
import styled from 'styled-components';

const TextArea = styled.textarea`
  width: 100%;
  padding: 8px 50px 8px 8px;
  background: transparent;
  color: var(--vscode-input-foreground);
  border: none;
  font-size: 14px;
  line-height: 1.5;
  font-family: inherit;
  resize: none;
  max-height: 200px;
  min-height: 42px;
  outline: none;
  
  &::placeholder {
    color: var(--vscode-input-placeholderForeground);
    opacity: 0.6;
  }
`;

const SendButton = styled.button`
  position: absolute;
  right: 8px;
  bottom: 8px;
  width: 32px;
  height: 32px;
  padding: 0;
  background: var(--vscode-button-background);
  color: var(--vscode-button-foreground);
  border: none;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  
  &:hover:not(:disabled) {
    background: var(--vscode-button-hoverBackground);
    transform: scale(1.05);
  }
  
  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
  
  svg {
    width: 16px;
    height: 16px;
    fill: currentColor;
  }
`;

interface SimpleInputProps {
  onSubmit: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export const SimpleInput: React.FC<SimpleInputProps> = ({ onSubmit, disabled, placeholder }) => {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  
  const handleSubmit = useCallback(() => {
    if (!value.trim() || disabled) return;
    onSubmit(value.trim());
    setValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [value, disabled, onSubmit]);
  
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };
  
  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px';
  };
  
  return (
    <div style={{ position: 'relative' }}>
      <TextArea
        ref={textareaRef}
        value={value}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        placeholder={placeholder || '使用 /projectgen repo=reponame 或 repo=dataset:reponame...'}
        rows={1}
        disabled={disabled}
      />
      <SendButton onClick={handleSubmit} disabled={disabled || !value.trim()} title="发送 (Enter)">
        <svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
          <path d="M15 8L1 1v6l10 1-10 1v6z"/>
        </svg>
      </SendButton>
    </div>
  );
};
