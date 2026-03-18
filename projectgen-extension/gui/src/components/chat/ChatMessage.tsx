import React from 'react';
import styled, { keyframes } from 'styled-components';

const fadeIn = keyframes`
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
`;

const MessageContainer = styled.div`
  display: flex;
  gap: 12px;
  padding: 16px;
  border-radius: 12px;
  animation: ${fadeIn} 0.35s cubic-bezier(0.19, 1, 0.22, 1);
  margin-bottom: 4px;
  transition: background 0.2s ease;
  
  &:hover {
    background: var(--pg-gray-50, rgba(255,255,255,0.03));
  }
`;

const MessageContent = styled.div`
  flex: 1;
  min-width: 0;
`;

const MessageHeader = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
`;

const SenderName = styled.span`
  font-weight: 600;
  font-size: 13px;
  color: var(--vscode-foreground);
  letter-spacing: -0.01em;
`;



const MessageBody = styled.div<{ type: 'user' | 'assistant' | 'error' | 'info' }>`
  font-size: 13px;
  line-height: 1.65;
  color: var(--vscode-foreground);
  word-wrap: break-word;
  white-space: pre-wrap;
  
  ${props => props.type === 'error' && `
    color: #f87171;
    padding: 10px 14px;
    background: rgba(239, 68, 68, 0.1);
    border-radius: 8px;
    border-left: 3px solid #ef4444;
  `}
  
  ${props => props.type === 'info' && `
    color: #22d3ee;
    padding: 10px 14px;
    background: rgba(6, 182, 212, 0.1);
    border-radius: 8px;
    border-left: 3px solid #06b6d4;
  `}
  
  code {
    background: var(--pg-gray-100, rgba(255, 255, 255, 0.08));
    padding: 2px 6px;
    border-radius: 4px;
    font-family: var(--pg-font-mono, 'SF Mono', Monaco, monospace);
    font-size: 12px;
    border: 1px solid var(--pg-gray-200, rgba(255, 255, 255, 0.1));
  }
  
  pre {
    background: var(--pg-gray-100, rgba(0, 0, 0, 0.25));
    padding: 14px 16px;
    border-radius: 10px;
    overflow-x: auto;
    margin: 10px 0;
    border: 1px solid var(--pg-gray-200, rgba(255, 255, 255, 0.08));
    
    code {
      background: none;
      padding: 0;
      border: none;
    }
  }
  
  p {
    margin: 0 0 8px 0;
    
    &:last-child {
      margin-bottom: 0;
    }
  }
  
  a {
    color: var(--pg-primary, #6366f1);
    text-decoration: none;
    border-bottom: 1px solid transparent;
    transition: border-color 0.2s ease;
    
    &:hover {
      border-bottom-color: var(--pg-primary, #6366f1);
    }
  }
`;

interface ChatMessageProps {
  type: 'user' | 'assistant' | 'error' | 'info';
  content: string | React.ReactNode;
}

const getSenderName = (type: string) => {
  switch (type) {
    case 'user': return 'You';
    case 'assistant': return 'ProjectGen';
    case 'error': return 'Error';
    case 'info': return 'Info';
    default: return '';
  }
};

export const ChatMessage: React.FC<ChatMessageProps> = ({ type, content }) => {
  return (
    <MessageContainer>
      <MessageContent>
        <MessageHeader>
          <SenderName>{getSenderName(type)}</SenderName>
        </MessageHeader>
        <MessageBody type={type}>
          {typeof content === 'string' ? (
            <span>{content}</span>
          ) : (
            content
          )}
        </MessageBody>
      </MessageContent>
    </MessageContainer>
  );
};
