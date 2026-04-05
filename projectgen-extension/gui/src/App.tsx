import React, { useEffect, useContext, useCallback, useState, useRef } from 'react';
import styled, { keyframes } from 'styled-components';
import { useAppDispatch, useAppSelector } from './redux/hooks';
import { startGeneration, updateProgress, addFile, completeGeneration, stopGeneration, setError, setStatusMessage, resetGeneration } from './redux/slices/projectGenSlice';
import { addUserMessage, addAssistantMessage, selectCurrentMessages, createSession, addGenerationMessage, updateGenerationMessage, clearCurrentSession } from './redux/slices/chatHistorySlice';
import { VsCodeApiContext } from './context/VsCodeApi';
import { SimpleInput, SimpleInputRef } from './components/mainInput/SimpleInput';
import { ChatHistory } from './components/chat/ChatHistory';
import { SessionTabs } from './components/chat/SessionTabs';
import { ModelSelector } from './components/ModelSelector';
import type { ModelConfig } from './forms/AddModelForm';
import {
  GradientBorder,
  InputBoxInner,
  InputToolbar,
  ToolbarLeft,
  ToolbarRight,
  HoverItem,
  SubmitButton,
} from './components/mainInput/ContinueStyleInput';

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
  padding: 12px 16px;
`;

// 编辑区域样式
const EditorArea = styled.div`
  min-height: 40px;
  max-height: 200px;
  overflow-y: auto;
  
  &::-webkit-scrollbar {
    width: 4px;
  }
  
  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.2);
    border-radius: 2px;
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

export const App: React.FC = () => {
  const dispatch = useAppDispatch();
  const vscode = useContext(VsCodeApiContext);
  const { isGenerating, files } = useAppSelector((state) => state.projectGen);
  const { currentConfig } = useAppSelector((state) => state.modelConfig);
  const chatMessages = useAppSelector(selectCurrentMessages);
  const currentSessionId = useAppSelector((state) => state.chatHistory.currentSessionId);
  const [showEmpty, setShowEmpty] = useState(true);
  const inputRef = useRef<SimpleInputRef>(null);

  // 初始化：如果没有会话，创建一个
  useEffect(() => {
    if (!currentSessionId) {
      dispatch(createSession('Welcome'));
    }
  }, [currentSessionId, dispatch]);

  // Notify VS Code when model config changes
  const handleModelChange = useCallback((config: ModelConfig) => {
    vscode?.postMessage({
      type: 'modelConfigChanged',
      config,
    });
  }, [vscode]);
  
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
          // 更新生成消息的进度
          dispatch(updateGenerationMessage({
            currentStage: message.content.stage,
            progress: message.content.progress,
          }));
          break;
        case 'newFile':
          dispatch(addFile(message.content));
          // 更新生成消息的文件列表
          dispatch(updateGenerationMessage({
            files: [...files, message.content],
          }));
          break;
        case 'files':
          dispatch(completeGeneration());
          {
            const completedFiles = Array.isArray(message.content?.files)
              ? message.content.files
              : files;
            const completedRepo = typeof message.content?.repo === 'string'
              ? message.content.repo
              : undefined;

            // 更新生成消息为完成状态
            dispatch(updateGenerationMessage({
              isComplete: true,
              files: completedFiles,
              ...(completedRepo ? { repo: completedRepo } : {}),
            }));
          }
          break;
        case 'error':
          dispatch(setError(message.content));
          // 更新生成消息为错误状态
          dispatch(updateGenerationMessage({
            error: message.content,
          }));
          break;
        case 'info':
          // Info 消息更新到生成消息的状态
          dispatch(setStatusMessage(message.content));
          dispatch(updateGenerationMessage({
            statusMessage: message.content,
          }));
          break;
      }
    };
    
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, [dispatch, files]);
  
  const handleFileClick = useCallback((file: any) => {
    vscode?.postMessage({
      type: 'openFile',
      filePath: file.path,
      content: file.content
    });
  }, [vscode]);
  
  const parseCommand = (message: string) => {
    const trimmed = message.trim();
    const isProjectGenCommand = /^\/projectgen\b/i.test(trimmed);

    // 支持路径格式: /projectgen repo=<绝对或相对路径>
    const projectgenMatch = message.match(/\/projectgen\s+repo=(.+)$/i);
    if (projectgenMatch) {
      let repoPath = projectgenMatch[1].trim();

      // 允许使用引号包裹路径，便于传入带空格路径。
      if (
        (repoPath.startsWith('"') && repoPath.endsWith('"')) ||
        (repoPath.startsWith("'") && repoPath.endsWith("'"))
      ) {
        repoPath = repoPath.slice(1, -1).trim();
      }

      if (!repoPath) {
        return { isCommand: false, originalMessage: message };
      }

      return {
        isCommand: true,
        type: 'projectgen',
        repo: repoPath,
        originalMessage: message,
        valid: true
      };
    }

    if (isProjectGenCommand) {
      return {
        isCommand: true,
        type: 'projectgen',
        repo: '',
        originalMessage: message,
        valid: false
      };
    }

    return { isCommand: false, originalMessage: message };
  };
    
  const handleSubmit = useCallback((message: string) => {
    setShowEmpty(false);
    
    // 添加用户消息到聊天历史
    dispatch(addUserMessage(message));

    const parsed = parseCommand(message);
    
    if (parsed.isCommand) {
      dispatch(startGeneration(parsed.repo || '未指定路径'));
      
      // 添加生成消息（不再添加助手消息）
      dispatch(addGenerationMessage({
        repo: parsed.repo || 'repository',
        content: `Starting project generation for: ${parsed.repo || 'repository'}...`
      }));

      if (parsed.repo) {
        vscode?.postMessage({
          type: 'generateFromRepo',
          repo: parsed.repo,
          commandType: parsed.type,
          message: parsed.originalMessage,
          modelConfig: currentConfig,
        });
        return;
      }

      vscode?.postMessage({
        type: 'generate',
        message: message,
        modelConfig: currentConfig,
      });
      return;
    }

    // 普通消息：添加简单助手响应
    dispatch(addAssistantMessage(`I received your message: "${message.slice(0, 100)}${message.length > 100 ? '...' : ''}"\n\nTo generate a project, use: /projectgen repo=<path>`));
    
    // 不发送到后端（目前只支持 /projectgen 命令）
  }, [dispatch, vscode, currentConfig]);
  
  const handleClear = useCallback(() => {
    setShowEmpty(true);
    inputRef.current?.clear();
    dispatch(clearCurrentSession());
    dispatch(resetGeneration());
  }, [dispatch]);
  
  const handleStop = useCallback(() => {
    dispatch(stopGeneration());
    vscode?.postMessage({
      type: 'stopGeneration'
    });
  }, [dispatch, vscode]);
  
  const setSuggestion = (text: string) => {
    handleSubmit(text);
  };

  // 检查是否有对话历史
  const hasHistory = chatMessages.length > 0;
  
  return (
    <Container>
      {/* Session Tabs - Continue 风格 */}
      <SessionTabs />
      
      <ChatContainer>
        {showEmpty && !hasHistory ? (
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
              Use a repository path to generate code. Example: /projectgen repo=./datasets/CodeProjectEval/bplustree
            </EmptyDescription>
            <SuggestionGrid>
              <SuggestionButton onClick={() => setSuggestion('/projectgen repo=./datasets/CodeProjectEval/bplustree')}>
                <SuggestionText>
                  <strong>B+ Tree</strong>
                  <span>CodeProjectEval path</span>
                </SuggestionText>
              </SuggestionButton>
              <SuggestionButton onClick={() => setSuggestion('/projectgen repo=./datasets/CodeProjectEval/flask')}>
                <SuggestionText>
                  <strong>Flask</strong>
                  <span>CodeProjectEval path</span>
                </SuggestionText>
              </SuggestionButton>
              <SuggestionButton onClick={() => setSuggestion('/projectgen repo=/absolute/path/to/repo')}>
                <SuggestionText>
                  <strong>Absolute Path</strong>
                  <span>Custom repository</span>
                </SuggestionText>
              </SuggestionButton>
              <SuggestionButton onClick={() => setSuggestion('/projectgen repo="./datasets/CodeProjectEval/csvs-to-sqlite"')}>
                <SuggestionText>
                  <strong>Quoted Path</strong>
                  <span>CodeProjectEval path</span>
                </SuggestionText>
              </SuggestionButton>
            </SuggestionGrid>
          </EmptyState>
        ) : (
          <>
            {/* 统一时间线：聊天历史 + 生成进度 */}
            <ChatHistory 
              messages={chatMessages} 
              isStreaming={isGenerating}
              onFileClick={handleFileClick}
            />
          </>
        )}
      </ChatContainer>
      
      <InputContainer>
        {/* Continue 风格的渐变边框输入框 */}
        <GradientBorder loading={isGenerating}>
          <InputBoxInner>
            {/* 编辑器区域 */}
            <EditorArea>
              <SimpleInput
                ref={inputRef}
                onSubmit={handleSubmit}
                disabled={isGenerating}
                placeholder="Use /projectgen repo=<path>"
              />
            </EditorArea>
            
            {/* 工具栏 - Continue InputToolbar 风格 */}
            <InputToolbar>
              <ToolbarLeft>
                {/* 模型选择器 - 紧凑模式 */}
                <ModelSelector onModelChange={handleModelChange} compact />
              </ToolbarLeft>
              
              <ToolbarRight>
                {/* 快捷键提示 */}
                <span style={{ color: 'var(--vscode-descriptionForeground)', opacity: 0.6, fontSize: '10px' }}>
                  ⏎ Enter to send
                </span>
                
                {/* 停止按钮 */}
                {isGenerating && (
                  <HoverItem onClick={handleStop} style={{ color: '#ef4444' }}>
                    ■ Stop
                  </HoverItem>
                )}
                
                {/* 清除按钮 */}
                <HoverItem onClick={handleClear} disabled={isGenerating}>
                  ↻ Clear
                </HoverItem>
                
                {/* 发送按钮 */}
                <SubmitButton 
                  variant="primary" 
                  disabled={isGenerating}
                  onClick={() => inputRef.current?.submit()}
                >
                  ⏎ Send
                </SubmitButton>
              </ToolbarRight>
            </InputToolbar>
          </InputBoxInner>
        </GradientBorder>
      </InputContainer>
    </Container>
  );
};
