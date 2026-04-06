import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface GeneratedFile {
  path: string;
  content: string;
}

export interface GenerationMetadata {
  repo?: string;
  currentStage?: 'architecture' | 'skeleton' | 'code' | '';
  progress?: number;
  files?: GeneratedFile[];
  statusMessage?: string;
  error?: string;
  isComplete?: boolean;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'generation';
  content: string;
  timestamp: number;
  metadata?: GenerationMetadata;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
}

interface ChatHistoryState {
  currentSessionId: string | null;
  sessions: ChatSession[];
  isStreaming: boolean;
}

// 从 localStorage 加载历史
const loadFromStorage = (): ChatHistoryState => {
  try {
    const stored = localStorage.getItem('projectgen_chat_history');
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (e) {
    console.error('Failed to load chat history:', e);
  }
  return {
    currentSessionId: null,
    sessions: [],
    isStreaming: false,
  };
};

// 保存到 localStorage
const saveToStorage = (state: ChatHistoryState) => {
  try {
    localStorage.setItem('projectgen_chat_history', JSON.stringify({
      currentSessionId: state.currentSessionId,
      sessions: state.sessions,
      isStreaming: false,
    }));
  } catch (e) {
    console.error('Failed to save chat history:', e);
  }
};

const generateId = () => `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

const initialState: ChatHistoryState = loadFromStorage();

const chatHistorySlice = createSlice({
  name: 'chatHistory',
  initialState,
  reducers: {
    // 创建新会话
    createSession: (state, action: PayloadAction<string | undefined>) => {
      const session: ChatSession = {
        id: generateId(),
        title: action.payload || 'New Chat',
        messages: [],
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };
      state.sessions.unshift(session);
      state.currentSessionId = session.id;
      saveToStorage(state);
    },
    
    // 切换会话
    switchSession: (state, action: PayloadAction<string>) => {
      if (state.sessions.find(s => s.id === action.payload)) {
        state.currentSessionId = action.payload;
        saveToStorage(state);
      }
    },
    
    // 添加用户消息
    addUserMessage: (state, action: PayloadAction<string>) => {
      if (!state.currentSessionId) {
        // 自动创建新会话
        const session: ChatSession = {
          id: generateId(),
          title: action.payload.slice(0, 50),
          messages: [],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        };
        state.sessions.unshift(session);
        state.currentSessionId = session.id;
      }
      
      const session = state.sessions.find(s => s.id === state.currentSessionId);
      if (session) {
        session.messages.push({
          id: generateId(),
          role: 'user',
          content: action.payload,
          timestamp: Date.now(),
        });
        session.updatedAt = Date.now();
        
        // 更新标题为第一条用户消息
        if (session.messages.filter(m => m.role === 'user').length === 1) {
          session.title = action.payload.slice(0, 50);
        }
      }
      saveToStorage(state);
    },
    
    // 添加助手消息
    addAssistantMessage: (state, action: PayloadAction<string>) => {
      const session = state.sessions.find(s => s.id === state.currentSessionId);
      if (session) {
        session.messages.push({
          id: generateId(),
          role: 'assistant',
          content: action.payload,
          timestamp: Date.now(),
        });
        session.updatedAt = Date.now();
      }
      saveToStorage(state);
    },
    
    // 流式更新助手消息（更新最后一条助手消息）
    updateLastAssistantMessage: (state, action: PayloadAction<string>) => {
      const session = state.sessions.find(s => s.id === state.currentSessionId);
      if (session) {
        const lastAssistant = [...session.messages].reverse().find(m => m.role === 'assistant');
        if (lastAssistant) {
          lastAssistant.content = action.payload;
          session.updatedAt = Date.now();
        }
      }
      // 流式更新不保存到 localStorage，避免频繁写入
    },
    
    // 设置流式状态
    setStreaming: (state, action: PayloadAction<boolean>) => {
      state.isStreaming = action.payload;
      if (!action.payload) {
        saveToStorage(state);
      }
    },
    
    // 删除会话
    deleteSession: (state, action: PayloadAction<string>) => {
      state.sessions = state.sessions.filter(s => s.id !== action.payload);
      if (state.currentSessionId === action.payload) {
        state.currentSessionId = state.sessions[0]?.id || null;
      }
      saveToStorage(state);
    },
    
    // 清除当前会话消息
    clearCurrentSession: (state) => {
      const session = state.sessions.find(s => s.id === state.currentSessionId);
      if (session) {
        session.messages = [];
        session.updatedAt = Date.now();
      }
      saveToStorage(state);
    },
    
    // 重命名会话
    renameSession: (state, action: PayloadAction<{ id: string; title: string }>) => {
      const session = state.sessions.find(s => s.id === action.payload.id);
      if (session) {
        session.title = action.payload.title;
        session.updatedAt = Date.now();
      }
      saveToStorage(state);
    },
    
    // 添加生成消息
    addGenerationMessage: (state, action: PayloadAction<{ repo: string; content?: string }>) => {
      if (!state.currentSessionId) {
        // 自动创建新会话
        const session: ChatSession = {
          id: generateId(),
          title: `ProjectGen [${action.payload.repo}]`,
          messages: [],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        };
        state.sessions.unshift(session);
        state.currentSessionId = session.id;
      }
      
      const session = state.sessions.find(s => s.id === state.currentSessionId);
      if (session) {
        session.messages.push({
          id: generateId(),
          role: 'generation',
          content: action.payload.content || 'Generating project...',
          timestamp: Date.now(),
          metadata: {
            repo: action.payload.repo,
            currentStage: '',
            progress: 0,
            files: [],
            isComplete: false,
          },
        });
        session.updatedAt = Date.now();
      }
      saveToStorage(state);
    },
    
    // 更新生成消息
    updateGenerationMessage: (state, action: PayloadAction<Partial<GenerationMetadata>>) => {
      const session = state.sessions.find(s => s.id === state.currentSessionId);
      if (session) {
        // 找到最后一条生成消息
        const lastGeneration = [...session.messages].reverse().find(m => m.role === 'generation');
        if (lastGeneration && lastGeneration.metadata) {
          // 合并更新 metadata
          lastGeneration.metadata = {
            ...lastGeneration.metadata,
            ...action.payload,
          };
          
          // 如果是完成状态，更新内容
          if (action.payload.isComplete) {
            const fileCount = lastGeneration.metadata.files?.length || 0;
            lastGeneration.content = `Generation complete. Created ${fileCount} files.`;
          } else if (action.payload.error) {
            lastGeneration.content = `Generation failed: ${action.payload.error}`;
          } else if (action.payload.statusMessage) {
            lastGeneration.content = action.payload.statusMessage;
          }
          
          session.updatedAt = Date.now();
        }
      }
      // 生成过程中的频繁更新不保存到 localStorage
      if (action.payload.isComplete || action.payload.error) {
        saveToStorage(state);
      }
    },

    // 编辑指定用户消息，并截断其后的历史以便重新生成
    editUserMessageAndTruncate: (state, action: PayloadAction<{ messageId: string; content: string }>) => {
      const session = state.sessions.find(s => s.id === state.currentSessionId);
      if (!session) {
        return;
      }

      const messageIndex = session.messages.findIndex(
        (message) => message.id === action.payload.messageId && message.role === 'user'
      );
      if (messageIndex === -1) {
        return;
      }

      const nextContent = action.payload.content.trim();
      if (!nextContent) {
        return;
      }

      session.messages[messageIndex].content = nextContent;
      session.messages[messageIndex].timestamp = Date.now();
      session.messages = session.messages.slice(0, messageIndex + 1);
      session.updatedAt = Date.now();

      const firstUserMessage = session.messages.find((message) => message.role === 'user');
      session.title = firstUserMessage ? firstUserMessage.content.slice(0, 50) : 'New Chat';

      saveToStorage(state);
    },
  },
});

export const {
  createSession,
  switchSession,
  addUserMessage,
  addAssistantMessage,
  updateLastAssistantMessage,
  setStreaming,
  deleteSession,
  clearCurrentSession,
  renameSession,
  addGenerationMessage,
  updateGenerationMessage,
  editUserMessageAndTruncate,
} = chatHistorySlice.actions;

// Selectors
export const selectCurrentSession = (state: { chatHistory: ChatHistoryState }) => 
  state.chatHistory.sessions.find(s => s.id === state.chatHistory.currentSessionId);

export const selectCurrentMessages = (state: { chatHistory: ChatHistoryState }) => 
  selectCurrentSession(state)?.messages || [];

export const selectAllSessions = (state: { chatHistory: ChatHistoryState }) => 
  state.chatHistory.sessions;

export const selectIsStreaming = (state: { chatHistory: ChatHistoryState }) => 
  state.chatHistory.isStreaming;

export default chatHistorySlice.reducer;
