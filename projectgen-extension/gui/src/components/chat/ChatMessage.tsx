import React from 'react';
import styled, { keyframes } from 'styled-components';

const fadeIn = keyframes`
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
`;

const MessageContainer = styled.div`
  display: flex;
  gap: 10px;
  padding: 12px 16px;
  animation: ${fadeIn} 0.2s ease-out;
  
  &:hover {
    background: var(--vscode-list-hoverBackground, rgba(255,255,255,0.04));
  }
`;

const Avatar = styled.div<{ type: 'user' | 'assistant' | 'error' | 'info' }>`
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  flex-shrink: 0;
  margin-top: 2px;
  
  ${props => {
    switch (props.type) {
      case 'user':
        return `
          background: var(--vscode-button-background);
          color: var(--vscode-button-foreground);
        `;
      case 'assistant':
        return `
          background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
          color: white;
        `;
      case 'error':
        return `
          background: var(--vscode-errorForeground, #f14c4c);
          color: white;
        `;
      case 'info':
        return `
          background: var(--vscode-textLink-foreground, #3794ff);
          color: white;
        `;
      default:
        return `
          background: var(--vscode-button-background);
          color: var(--vscode-button-foreground);
        `;
    }
  }}
`;

const MessageContent = styled.div`
  flex: 1;
  min-width: 0;
`;

const MessageHeader = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
`;

const SenderName = styled.span`
  font-weight: 600;
  font-size: 13px;
  color: var(--vscode-foreground);
`;

const MessageBody = styled.div<{ type: 'user' | 'assistant' | 'error' | 'info' }>`
  font-size: 13px;
  line-height: 1.6;
  color: var(--vscode-foreground);
  word-wrap: break-word;
  
  ${props => props.type === 'error' && `
    color: var(--vscode-errorForeground, #f14c4c);
  `}
  
  ${props => props.type === 'info' && `
    color: var(--vscode-textLink-foreground, #3794ff);
  `}
  
  code {
    background: var(--vscode-textCodeBlock-background, rgba(0, 0, 0, 0.3));
    padding: 2px 5px;
    border-radius: 3px;
    font-family: var(--vscode-editor-font-family, 'SF Mono', Monaco, monospace);
    font-size: 12px;
  }
  
  pre {
    background: var(--vscode-textCodeBlock-background, rgba(0, 0, 0, 0.3));
    padding: 12px;
    border-radius: 6px;
    overflow-x: auto;
    margin: 8px 0;
    
    code {
      background: none;
      padding: 0;
    }
  }
  
  p {
    margin: 0 0 8px 0;
    
    &:last-child {
      margin-bottom: 0;
    }
  }
`;

interface ChatMessageProps {
  type: 'user' | 'assistant' | 'error' | 'info';
  content: string | React.ReactNode;
}

const getAvatarIcon = (type: string) => {
  switch (type) {
    case 'user': return '👤';
    case 'assistant': return '✦';
    case 'error': return '!';
    case 'info': return 'i';
    default: return '•';
  }
};

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
      <Avatar type={type}>
        {getAvatarIcon(type)}
      </Avatar>
      <MessageContent>
        <MessageHeader>
          <SenderName>{getSenderName(type)}</SenderName>
        </MessageHeader>
        <MessageBody type={type}>
          {typeof content === 'string' ? (
            <div dangerouslySetInnerHTML={{ __html: content }} />
          ) : (
            content
          )}
        </MessageBody>
      </MessageContent>
    </MessageContainer>
  );
};
