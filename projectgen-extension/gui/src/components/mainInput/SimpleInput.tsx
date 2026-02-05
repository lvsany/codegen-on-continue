import React, { useCallback, useRef, useState } from 'react';
import styled, { keyframes } from 'styled-components';

const scaleIn = keyframes`
  from { transform: scale(0.9); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
`;

const TextArea = styled.textarea`
  width: 100%;
  padding: 12px 52px 12px 14px;
  background: transparent;
  color: var(--vscode-input-foreground);
  border: none;
  font-size: 14px;
  line-height: 1.5;
  font-family: inherit;
  resize: none;
  max-height: 200px;
  min-height: 46px;
  outline: none;
  letter-spacing: -0.01em;
  
  &::placeholder {
    color: var(--vscode-input-placeholderForeground);
    opacity: 0.5;
  }
  
  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
`;

const SendButton = styled.button`
  position: absolute;
  right: 8px;
  bottom: 8px;
  width: 36px;
  height: 36px;
  padding: 0;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: white;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.25s cubic-bezier(0.19, 1, 0.22, 1);
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.35);
  
  &:hover:not(:disabled) {
    transform: translateY(-2px) scale(1.02);
    box-shadow: 0 4px 16px rgba(99, 102, 241, 0.45);
  }
  
  &:active:not(:disabled) {
    transform: translateY(0) scale(0.98);
  }
  
  &:disabled {
    opacity: 0.35;
    cursor: not-allowed;
    box-shadow: none;
    background: var(--pg-gray-300, rgba(255, 255, 255, 0.16));
  }
  
  svg {
    width: 18px;
    height: 18px;
    fill: currentColor;
    transition: transform 0.2s ease;
  }
  
  &:hover:not(:disabled) svg {
    transform: translateX(2px);
  }
`;

const InputWrapper = styled.div`
  position: relative;
  animation: ${scaleIn} 0.2s ease-out;
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
    <InputWrapper>
      <TextArea
        ref={textareaRef}
        value={value}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        placeholder={placeholder || 'Describe what you want to build...'}
        rows={1}
        disabled={disabled}
      />
      <SendButton 
        onClick={handleSubmit} 
        disabled={disabled || !value.trim()} 
        title="Send (Enter)"
        aria-label="Send message"
      >
        <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
        </svg>
      </SendButton>
    </InputWrapper>
  );
};
