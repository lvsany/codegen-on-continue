import React, { useCallback, useRef, useState, useImperativeHandle, forwardRef } from 'react';
import styled from 'styled-components';

const TextArea = styled.textarea`
  width: 100%;
  padding: 8px 12px;
  background: transparent;
  color: var(--vscode-input-foreground);
  border: none;
  font-size: 13px;
  line-height: 1.5;
  font-family: inherit;
  resize: none;
  max-height: 200px;
  min-height: 36px;
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

const InputWrapper = styled.div`
  position: relative;
`;

export interface SimpleInputRef {
  getValue: () => string;
  setValue: (val: string) => void;
  clear: () => void;
  submit: () => void;
}

interface SimpleInputProps {
  onSubmit: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export const SimpleInput = forwardRef<SimpleInputRef, SimpleInputProps>(
  ({ onSubmit, disabled, placeholder }, ref) => {
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

    // Expose methods via ref
    useImperativeHandle(ref, () => ({
      getValue: () => value,
      setValue: (val: string) => setValue(val),
      clear: () => {
        setValue('');
        if (textareaRef.current) {
          textareaRef.current.style.height = 'auto';
        }
      },
      submit: handleSubmit,
    }), [value, handleSubmit]);
    
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
      </InputWrapper>
    );
  }
);
