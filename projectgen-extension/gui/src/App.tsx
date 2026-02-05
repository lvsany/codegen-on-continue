import React, { useEffect, useContext, useCallback, useState } from 'react';
import styled, { keyframes } from 'styled-components';
import { useAppDispatch, useAppSelector } from './redux/hooks';
import { startGeneration, updateProgress, addFile, completeGeneration, stopGeneration, setError, setStatusMessage, resetGeneration } from './redux/slices/projectGenSlice';
import { VsCodeApiContext } from './context/VsCodeApi';
import { SimpleInput } from './components/mainInput/SimpleInput';
import { InputBoxDiv } from './components/mainInput/StyledComponents';
import { ChatMessage } from './components/chat/ChatMessage';
import { GenerationSession } from './components/chat/GenerationSession';

// 🎬 动画
const fadeIn = keyframes`
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
`;

const float = keyframes`
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
`;

// 🎨 主容器 - 玻璃态背景
const Container = styled.div`
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--vscode-editor-background);
  color: var(--vscode-foreground);
  position: relative;
  
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: 
      radial-gradient(ellipse at 20% 0%, rgba(99, 102, 241, 0.08) 0%, transparent 50%),
      radial-gradient(ellipse at 80% 100%, rgba(139, 92, 246, 0.06) 0%, transparent 50%);
    pointer-events: none;
    z-index: 0;
  }
`;

// 💬 聊天容器
const ChatContainer = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  position: relative;
  z-index: 1;
  scroll-behavior: smooth;
`;

// ⌨️ 输入区域
const InputContainer = styled.div`
  position: relative;
  z-index: 1;
  border-top: 1px solid var(--pg-glass-border, rgba(255, 255, 255, 0.08));
  padding: 16px 20px;
  background: var(--pg-glass-bg, rgba(255, 255, 255, 0.02));
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
`;

// 工具栏
const Toolbar = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 4px 0;
  font-size: 11px;
  color: var(--vscode-descriptionForeground);
`;

const ToolbarHint = styled.span`
  flex: 1;
  opacity: 0.6;
  display: flex;
  align-items: center;
  gap: 6px;
  
  kbd {
    padding: 2px 6px;
    border-radius: 4px;
    background: var(--pg-gray-100, rgba(255, 255, 255, 0.06));
    border: 1px solid var(--pg-gray-200, rgba(255, 255, 255, 0.09));
    font-family: var(--pg-font-mono, monospace);
    font-size: 10px;
  }
`;

const ToolbarButton = styled.button<{ variant?: 'danger' | 'default' }>`
  padding: 6px 12px;
  background: ${props => props.variant === 'danger' 
    ? 'rgba(239, 68, 68, 0.12)' 
    : 'var(--pg-gray-100, rgba(255, 255, 255, 0.06))'};
  color: ${props => props.variant === 'danger' 
    ? '#ef4444' 
    : 'var(--vscode-foreground)'};
  border: 1px solid ${props => props.variant === 'danger'
    ? 'rgba(239, 68, 68, 0.2)'
    : 'var(--pg-gray-200, rgba(255, 255, 255, 0.09))'};
  border-radius: 6px;
  cursor: pointer;
  font-size: 11px;
  font-weight: 500;
  transition: all 0.2s cubic-bezier(0.19, 1, 0.22, 1);
  display: flex;
  align-items: center;
  gap: 5px;
  
  &:hover:not(:disabled) {
    background: ${props => props.variant === 'danger'
      ? 'rgba(239, 68, 68, 0.2)'
      : 'var(--pg-gray-200, rgba(255, 255, 255, 0.1))'};
    transform: translateY(-1px);
  }
  
  &:active:not(:disabled) {
    transform: translateY(0);
  }
  
  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
`;

// 🎯 空状态 - 引导式设计
const EmptyState = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  color: var(--vscode-descriptionForeground);
  animation: ${fadeIn} 0.5s ease-out;
  padding: 20px;
`;

const EmptyIcon = styled.div`
  width: 80px;
  height: 80px;
  border-radius: 20px;
  background: linear-gradient(135deg, 
    rgba(99, 102, 241, 0.15) 0%, 
    rgba(139, 92, 246, 0.1) 100%
  );
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
  animation: ${float} 3s ease-in-out infinite;
  box-shadow: 
    0 8px 32px rgba(99, 102, 241, 0.15),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
  
  svg {
    width: 40px;
    height: 40px;
    stroke: #8b5cf6;
    stroke-width: 1.5;
    fill: none;
  }
`;

const EmptyTitle = styled.h2`
  margin: 0 0 8px 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--vscode-foreground);
  letter-spacing: -0.02em;
`;

const EmptyDescription = styled.p`
  margin: 0 0 32px 0;
  font-size: 13px;
  opacity: 0.7;
  max-width: 320px;
  line-height: 1.6;
`;

const SuggestionGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  width: 100%;
  max-width: 400px;
`;

const SuggestionButton = styled.button`
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  background: var(--pg-glass-bg, rgba(255, 255, 255, 0.04));
  border: 1px solid var(--pg-glass-border, rgba(255, 255, 255, 0.08));
  border-radius: 12px;
  cursor: pointer;
  font-size: 13px;
  color: var(--vscode-foreground);
  text-align: left;
  transition: all 0.25s cubic-bezier(0.19, 1, 0.22, 1);
  backdrop-filter: blur(8px);
  
  &:hover {
    background: var(--pg-gray-100, rgba(255, 255, 255, 0.08));
    border-color: rgba(99, 102, 241, 0.3);
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  }
  
  &:active {
    transform: translateY(0);
  }
`;

const SuggestionText = styled.div`
  display: flex;
  flex-direction: column;
  gap: 2px;
  
  strong {
    font-weight: 500;
    font-size: 13px;
  }
  
  span {
    font-size: 11px;
    opacity: 0.6;
  }
`;

interface Message {
  type: 'user' | 'assistant' | 'error' | 'info';
  content: string | React.ReactNode;
}

export const App: React.FC = () => {
  const dispatch = useAppDispatch();
  const vscode = useContext(VsCodeApiContext);
  const { isGenerating, currentStage, progress, files, currentRepo, statusMessage } = useAppSelector((state) => state.projectGen);
  const [messages, setMessages] = useState<Message[]>([]);
  const [showEmpty, setShowEmpty] = useState(true);
  const [isSessionComplete, setIsSessionComplete] = useState(false);
  
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const message = event.data;
      console.log('[App] Received message:', message.type, message);
      
      switch (message.type) {
        case 'progress':
          dispatch(updateProgress({
            stage: message.content.stage,
            progress: message.content.progress
          }));
          break;
        case 'newFile':
          dispatch(addFile(message.content));
          break;
        case 'files':
          dispatch(completeGeneration());
          setIsSessionComplete(true);
          break;
        case 'error':
          dispatch(setError(message.content));
          setMessages(prev => [...prev, { type: 'error', content: '❌ ' + message.content }]);
          break;
        case 'info':
          // Info 消息直接更新到 statusMessage，显示在 GenerationSession 中
          dispatch(setStatusMessage(message.content));
          break;
      }
    };
    
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [dispatch]);
  
  const handleFileClick = useCallback((file: any) => {
    vscode?.postMessage({
      type: 'openFile',
      filePath: file.path,
      content: file.content
    });
  }, [vscode]);
  
  const parseCommand = (message: string) => {
    // 支持多种格式:
    // 1. /projectgen repo=xxx 或 /projectgen repo=dataset:xxx 或 /projectgen repo=dataset/xxx
    // 2. 直接输入项目名: bplustree
    // 3. 指定数据集: CodeProjectEval:bplustree 或 CodeProjectEval/bplustree
    
    const projectgenMatch = message.match(/\/projectgen\s+repo=([\w:\/\-]+)/);
    if (projectgenMatch) {
      return {
        isCommand: true,
        type: 'projectgen',
        repo: projectgenMatch[1],
        originalMessage: message
      };
    }
    
    // 如果不是 /projectgen 命令，直接把输入当作 repo 名称
    const trimmedMessage = message.trim();
    if (trimmedMessage && !trimmedMessage.includes(' ')) {
      return {
        isCommand: true,
        type: 'projectgen',
        repo: trimmedMessage,
        originalMessage: message
      };
    }
    
    return { isCommand: false, originalMessage: message };
  };
    
  const handleSubmit = useCallback((message: string) => {
    setShowEmpty(false);
    setIsSessionComplete(false);
    setMessages(prev => [...prev, { type: 'user', content: message }]);
    
    const parsed = parseCommand(message);
    
    if (parsed.isCommand && parsed.repo) {
      dispatch(startGeneration(parsed.repo));
      vscode?.postMessage({
        type: 'generateFromRepo',
        repo: parsed.repo,
        commandType: parsed.type,
        message: parsed.originalMessage
      });
    } else {
      vscode?.postMessage({
        type: 'generate',
        message: message
      });
    }
  }, [dispatch, vscode]);
  
  const handleClear = useCallback(() => {
    setMessages([]);
    setShowEmpty(true);
    setIsSessionComplete(false);
    dispatch(resetGeneration());
  }, [dispatch]);
  
  const handleStop = useCallback(() => {
    dispatch(stopGeneration());
    vscode?.postMessage({
      type: 'stopGeneration'
    });
    setMessages(prev => [...prev, { type: 'info', content: '⏹️ Generation stopped' }]);
  }, [dispatch, vscode]);
  
  const setSuggestion = (text: string) => {
    handleSubmit(text);
  };
  
  return (
    <Container>
      <ChatContainer>
        {showEmpty && messages.length === 0 ? (
          <EmptyState>
            <EmptyIcon>
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2L2 7L12 12L22 7L12 2Z" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M2 17L12 22L22 17" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M2 12L12 17L22 12" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </EmptyIcon>
            <EmptyTitle>Welcome to ProjectGen</EmptyTitle>
            <EmptyDescription>
              Transform your ideas into production-ready code. Select a template below or describe your project.
            </EmptyDescription>
            <SuggestionGrid>
              <SuggestionButton onClick={() => setSuggestion('/projectgen repo=bplustree')}>
                <SuggestionText>
                  <strong>B+ Tree</strong>
                  <span>Data structure</span>
                </SuggestionText>
              </SuggestionButton>
              <SuggestionButton onClick={() => setSuggestion('/projectgen repo=flask')}>
                <SuggestionText>
                  <strong>Flask</strong>
                  <span>Web framework</span>
                </SuggestionText>
              </SuggestionButton>
              <SuggestionButton onClick={() => setSuggestion('/projectgen repo=tinydb')}>
                <SuggestionText>
                  <strong>TinyDB</strong>
                  <span>Document database</span>
                </SuggestionText>
              </SuggestionButton>
              <SuggestionButton onClick={() => setSuggestion('/projectgen repo=simpy')}>
                <SuggestionText>
                  <strong>SimPy</strong>
                  <span>Simulation library</span>
                </SuggestionText>
              </SuggestionButton>
            </SuggestionGrid>
          </EmptyState>
        ) : (
          <>
            {messages.map((msg, index) => (
              <ChatMessage key={index} type={msg.type} content={msg.content} />
            ))}
            {(isGenerating || files.length > 0) && (
              <GenerationSession
                repo={currentRepo}
                currentStage={currentStage}
                progress={progress}
                files={files}
                isComplete={isSessionComplete}
                onFileClick={handleFileClick}
                statusMessage={statusMessage}
              />
            )}
          </>
        )}
      </ChatContainer>
      
      <InputContainer>
        <InputBoxDiv className={isGenerating ? 'generating' : ''}>
          <SimpleInput
            onSubmit={handleSubmit}
            disabled={isGenerating}
            placeholder="Enter project name or describe what you want to build..."
          />
        </InputBoxDiv>
        <Toolbar>
          <ToolbarHint>
            <kbd>↵</kbd> to send · <kbd>⇧↵</kbd> for new line
          </ToolbarHint>
          <div style={{ display: 'flex', gap: '8px' }}>
            {isGenerating && (
              <ToolbarButton variant="danger" onClick={handleStop}>
                ■ Stop
              </ToolbarButton>
            )}
            <ToolbarButton onClick={handleClear} disabled={isGenerating}>
              ↻ Clear
            </ToolbarButton>
          </div>
        </Toolbar>
      </InputContainer>
    </Container>
  );
};
