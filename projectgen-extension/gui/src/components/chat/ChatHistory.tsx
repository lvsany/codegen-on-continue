import React, { useEffect, useRef } from 'react';
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
}

const HistoryContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 2px;
`;

const TimelineItem = styled.div`
  margin: 0 0 0 1px;
`;

const MessageContainer = styled.div<{ role: 'user' | 'assistant' }>`
  background: ${(props) =>
    props.role === 'assistant'
      ? 'var(--vscode-editor-inactiveSelectionBackground)'
      : 'transparent'};
  padding: 8px 10px;
  border-radius: 6px;

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

export const ChatHistory: React.FC<ChatHistoryProps> = ({
  messages,
  isStreaming,
  onFileClick,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

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
          ) : (
            <MessageContainer role={message.role as 'user' | 'assistant'}>
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
