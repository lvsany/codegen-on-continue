import React, { useCallback, useEffect, useRef, useState } from 'react';
import styled from 'styled-components';
import { ChatBubbleOvalLeftIcon } from '@heroicons/react/24/outline';
import { ChatMessage } from '../../redux/slices/chatHistorySlice';
import { GenerationCard } from './GenerationCard';

interface GeneratedFile {
  path: string;
  content: string;
}

interface ChatHistoryProps {
  messages: ChatMessage[];
  isStreaming?: boolean;
  onFileClick?: (file: GeneratedFile) => void;
  onResubmitUserMessage?: (messageId: string, message: string) => void;
}

const HistoryContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 2px;
`;

const TimelineItem = styled.div`
  margin: 0 0 0 1px;
`;

const MessageContainer = styled.div<{ role: 'user' | 'assistant'; clickable?: boolean }>`
  background: ${(props) =>
    props.role === 'assistant'
      ? 'var(--vscode-editor-inactiveSelectionBackground)'
      : 'transparent'};
  padding: 8px 10px;
  border-radius: 6px;
  cursor: ${(props) => (props.clickable ? 'pointer' : 'default')};
  border: 1px solid transparent;

  ${(props) =>
    props.clickable
      ? `
    &:hover {
      border-color: var(--vscode-focusBorder);
    }
  `
      : ''}

  &:hover {
    background: ${(props) =>
      props.role === 'assistant'
        ? 'var(--vscode-list-hoverBackground)'
        : 'var(--vscode-list-inactiveSelectionBackground)'};
  }
`;

const MessageHeader = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
`;

const IconWrap = styled.span`
  display: inline-flex;
  align-items: center;
  justify-content: center;

  svg {
    width: 14px;
    height: 14px;
    color: var(--vscode-descriptionForeground);
  }
`;

const RoleLabel = styled.span`
  font-size: 12px;
  font-weight: 500;
  color: var(--vscode-descriptionForeground);
`;

const MessageBody = styled.div`
  margin-left: 20px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--vscode-foreground);
  white-space: pre-wrap;
  word-break: break-word;

  code {
    background: var(--vscode-textCodeBlock-background);
    padding: 2px 5px;
    border-radius: 4px;
    font-family: var(--vscode-editor-font-family);
    font-size: 12px;
  }

  pre {
    background: var(--vscode-textCodeBlock-background);
    padding: 10px 12px;
    border-radius: 6px;
    overflow-x: auto;
    margin: 8px 0;

    code {
      background: transparent;
      padding: 0;
    }
  }
`;

const ScrollAnchor = styled.div`
  height: 1px;
`;

const EditContainer = styled.div`
  background: var(--vscode-editor-inactiveSelectionBackground);
  border: 1px solid var(--vscode-focusBorder);
  border-radius: 8px;
  padding: 10px;
`;

const EditTextArea = styled.textarea`
  width: 100%;
  background: var(--vscode-input-background);
  color: var(--vscode-input-foreground);
  border: 1px solid var(--vscode-input-border, var(--vscode-editorWidget-border));
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 13px;
  line-height: 1.5;
  font-family: inherit;
  resize: vertical;
  min-height: 72px;
  outline: none;

  &:focus {
    border-color: var(--vscode-focusBorder);
  }
`;

const EditActions = styled.div`
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
`;

const EditButton = styled.button<{ primary?: boolean }>`
  border: 1px solid
    ${(props) => (props.primary ? 'var(--vscode-button-background)' : 'var(--vscode-input-border, transparent)')};
  background: ${(props) => (props.primary ? 'var(--vscode-button-background)' : 'transparent')};
  color: ${(props) => (props.primary ? 'var(--vscode-button-foreground)' : 'var(--vscode-foreground)')};
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 12px;
  cursor: pointer;

  &:hover {
    background: ${(props) =>
      props.primary
        ? 'var(--vscode-button-hoverBackground)'
        : 'var(--vscode-list-hoverBackground)'};
  }
`;

export const ChatHistory: React.FC<ChatHistoryProps> = ({
  messages,
  isStreaming,
  onFileClick,
  onResubmitUserMessage,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState('');

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  useEffect(() => {
    if (!editingMessageId) {
      return;
    }
    const exists = messages.some(
      (message) => message.id === editingMessageId && message.role === 'user',
    );
    if (!exists) {
      setEditingMessageId(null);
      setEditingValue('');
    }
  }, [messages, editingMessageId]);

  const handleStartEdit = useCallback(
    (message: ChatMessage) => {
      if (isStreaming || message.role !== 'user' || !onResubmitUserMessage) {
        return;
      }
      setEditingMessageId(message.id);
      setEditingValue(message.content);
    },
    [isStreaming, onResubmitUserMessage],
  );

  const handleCancelEdit = useCallback(() => {
    setEditingMessageId(null);
    setEditingValue('');
  }, []);

  const handleSubmitEdit = useCallback(() => {
    if (!editingMessageId || !onResubmitUserMessage) {
      return;
    }
    const nextMessage = editingValue.trim();
    if (!nextMessage) {
      return;
    }
    onResubmitUserMessage(editingMessageId, nextMessage);
    setEditingMessageId(null);
    setEditingValue('');
  }, [editingMessageId, editingValue, onResubmitUserMessage]);

  const visibleMessages = messages.filter((m) => m.role !== 'system');

  if (visibleMessages.length === 0) {
    return null;
  }

  return (
    <HistoryContainer>
      {visibleMessages.map((message) => (
        <TimelineItem key={message.id}>
          {message.role === 'generation' ? (
            <GenerationCard metadata={message.metadata ?? {}} onFileClick={onFileClick} />
          ) : message.role === 'user' && message.id === editingMessageId ? (
            <EditContainer>
              <EditTextArea
                value={editingValue}
                onChange={(event) => setEditingValue(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Escape') {
                    event.preventDefault();
                    handleCancelEdit();
                    return;
                  }
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault();
                    handleSubmitEdit();
                  }
                }}
                autoFocus
              />
              <EditActions>
                <EditButton onClick={handleCancelEdit}>取消</EditButton>
                <EditButton primary onClick={handleSubmitEdit}>
                  重新生成
                </EditButton>
              </EditActions>
            </EditContainer>
          ) : (
            <MessageContainer
              role={message.role as 'user' | 'assistant'}
              clickable={message.role === 'user' && !isStreaming && !!onResubmitUserMessage}
              onClick={() => handleStartEdit(message)}
              title={message.role === 'user' && !isStreaming ? '单击可编辑并重新生成' : undefined}
            >
              <MessageHeader>
                <IconWrap>
                  <ChatBubbleOvalLeftIcon />
                </IconWrap>
                <RoleLabel>{message.role === 'user' ? 'You' : 'ProjectGen'}</RoleLabel>
              </MessageHeader>
              <MessageBody>{message.content}</MessageBody>
            </MessageContainer>
          )}
        </TimelineItem>
      ))}
      <ScrollAnchor ref={scrollRef} />
    </HistoryContainer>
  );
};

export default ChatHistory;
