import React, { useEffect, useContext, useCallback, useState } from 'react';
import styled from 'styled-components';
import { useAppDispatch, useAppSelector } from './redux/hooks';
import { startGeneration, updateProgress, addFile, completeGeneration, stopGeneration, setError, resetGeneration } from './redux/slices/projectGenSlice';
import { VsCodeApiContext } from './context/VsCodeApi';
import { SimpleInput } from './components/mainInput/SimpleInput';
import { InputBoxDiv } from './components/mainInput/StyledComponents';
import { ChatMessage } from './components/chat/ChatMessage';
import { GenerationSession } from './components/chat/GenerationSession';

const Container = styled.div`
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--vscode-editor-background);
  color: var(--vscode-foreground);
`;

const Header = styled.div`
  padding: 16px;
  border-bottom: 1px solid var(--vscode-panel-border);
  background: var(--vscode-sideBar-background);
  
  h1 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
  }
`;

const ChatContainer = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 16px;
`;

const InputContainer = styled.div`
  border-top: 1px solid var(--vscode-panel-border);
  padding: 12px 16px;
  background: var(--vscode-editor-background);
`;

const Toolbar = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-top: 1px solid var(--vscode-input-border);
  font-size: 11px;
  color: var(--vscode-descriptionForeground);
`;

const ToolbarHint = styled.span`
  flex: 1;
  opacity: 0.6;
`;

const ToolbarButton = styled.button<{ variant?: 'danger' | 'default' }>`
  padding: 4px 8px;
  background: transparent;
  color: ${props => props.variant === 'danger' ? 'var(--vscode-errorForeground, #f14c4c)' : 'var(--vscode-textLink-foreground)'};
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  transition: background 0.2s;
  
  &:hover {
    background: ${props => props.variant === 'danger' ? 'rgba(241, 76, 76, 0.15)' : 'rgba(255, 255, 255, 0.1)'};
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const EmptyState = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  color: var(--vscode-descriptionForeground);
  
  svg {
    width: 64px;
    height: 64px;
    margin-bottom: 16px;
    opacity: 0.5;
  }
  
  h2 {
    margin: 0 0 8px 0;
    font-size: 20px;
    color: var(--vscode-foreground);
  }
  
  p {
    margin: 0 0 24px 0;
    opacity: 0.7;
  }
`;

const SuggestionButton = styled.button`
  padding: 12px 16px;
  margin: 4px;
  background: var(--vscode-button-secondaryBackground);
  color: var(--vscode-button-secondaryForeground);
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: background 0.2s;
  
  &:hover {
    background: var(--vscode-button-secondaryHoverBackground);
  }
`;

interface Message {
  type: 'user' | 'assistant' | 'error' | 'info';
  content: string | React.ReactNode;
}

export const App: React.FC = () => {
  const dispatch = useAppDispatch();
  const vscode = useContext(VsCodeApiContext);
  const { isGenerating, currentStage, progress, files, currentRepo } = useAppSelector((state) => state.projectGen);
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
          setMessages(prev => [...prev, { type: 'info', content: 'ℹ️ ' + message.content }]);
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
      <Header>
        <h1>🤖 ProjectGen 代码生成助手</h1>
      </Header>
      
      <ChatContainer>
        {showEmpty && messages.length === 0 ? (
          <EmptyState>
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
            </svg>
            <h2>欢迎使用 ProjectGen</h2>
            <p>我可以帮你生成完整的项目代码</p>
            <div>
              <SuggestionButton onClick={() => setSuggestion('/projectgen repo=bplustree')}>
                🌳 生成 B+树项目 (bplustree)
              </SuggestionButton>
              <SuggestionButton onClick={() => setSuggestion('/projectgen repo=flask')}>
                🌶️ 生成 Flask Web框架
              </SuggestionButton>
              <SuggestionButton onClick={() => setSuggestion('/projectgen repo=tinydb')}>
                🗄️ 生成 TinyDB 数据库
              </SuggestionButton>
              <SuggestionButton onClick={() => setSuggestion('/projectgen repo=simpy')}>
                ⚙️ 生成 SimPy 仿真库
              </SuggestionButton>
            </div>
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
            placeholder="输入项目名(如: bplustree 或 CodeProjectEval:bplustree)..."
          />
        </InputBoxDiv>
        <Toolbar>
          <ToolbarHint>💡 Enter to send, Shift+Enter for new line</ToolbarHint>
          <div style={{ display: 'flex', gap: '8px' }}>
            {isGenerating && (
              <ToolbarButton variant="danger" onClick={handleStop}>
                ⏹️ Stop
              </ToolbarButton>
            )}
            <ToolbarButton onClick={handleClear} disabled={isGenerating}>
              🗑️ Clear
            </ToolbarButton>
          </div>
        </Toolbar>
      </InputContainer>
    </Container>
  );
};
