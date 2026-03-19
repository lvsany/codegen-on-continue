import React, { useState } from 'react';
import styled, { keyframes, css } from 'styled-components';
import { GeneratedFile } from '../../redux/slices/projectGenSlice';

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

const spin = keyframes`
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
`;

const pulse = keyframes`
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
`;

const shimmer = keyframes`
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
`;

const SessionContainer = styled.div`
  display: flex;
  gap: 12px;
  padding: 16px;
  border-radius: 12px;
  animation: ${fadeIn} 0.35s cubic-bezier(0.19, 1, 0.22, 1);
  background: var(--pg-session-bg, rgba(255, 255, 255, 0.86));
  margin: 8px 0;
  border: 1px solid var(--pg-session-border, rgba(15, 23, 42, 0.16));
  box-shadow: var(--pg-session-shadow, 0 4px 14px rgba(15, 23, 42, 0.06));
  
  &:hover {
    background: var(--pg-session-hover-bg, rgba(248, 250, 252, 0.96));
    border-color: var(--pg-session-hover-border, rgba(79, 70, 229, 0.25));
  }
`;

const ContentWrapper = styled.div`
  flex: 1;
  min-width: 0;
`;

const Header = styled.div`
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
`;

const SessionTitle = styled.span`
  font-weight: 600;
  font-size: 13px;
  color: var(--vscode-foreground);
  letter-spacing: -0.01em;
`;

const ThinkingIndicator = styled.div`
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  font-size: 13px;
  color: var(--pg-status-text, #334155);
  background: var(--pg-status-bg, rgba(15, 23, 42, 0.05));
  border-radius: 10px;
  margin-bottom: 12px;
`;

const Spinner = styled.div`
  width: 16px;
  height: 16px;
  border: 2px solid rgba(99, 102, 241, 0.2);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: ${spin} 0.7s linear infinite;
`;

const ThinkingText = styled.span`
  flex: 1;
`;

const ThinkingDots = styled.span`
  animation: ${pulse} 1.4s ease-in-out infinite;
`;

const StageSection = styled.div`
  margin-bottom: 6px;
`;

const StageHeader = styled.div<{ isExpanded: boolean; isActive: boolean }>`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  cursor: pointer;
  font-size: 12px;
  color: ${props => props.isActive ? 'var(--pg-stage-active-text, var(--vscode-foreground))' : 'var(--pg-stage-pending-text, var(--vscode-descriptionForeground))'};
  background: ${props => props.isActive 
    ? 'var(--pg-stage-active-bg, rgba(79, 70, 229, 0.12))' 
    : 'transparent'};
  border-radius: 8px;
  transition: all 0.2s cubic-bezier(0.19, 1, 0.22, 1);
  border: 1px solid ${props => props.isActive 
    ? 'var(--pg-stage-active-border, rgba(79, 70, 229, 0.32))' 
    : 'transparent'};
  
  &:hover {
    background: var(--pg-stage-hover-bg, rgba(15, 23, 42, 0.06));
    color: var(--vscode-foreground);
  }
`;

const ChevronIcon = styled.span<{ isExpanded: boolean }>`
  font-size: 10px;
  transition: transform 0.2s cubic-bezier(0.19, 1, 0.22, 1);
  transform: rotate(${props => props.isExpanded ? '90deg' : '0deg'});
  opacity: 0.6;
  width: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
`;

const StageIcon = styled.span<{ status: 'pending' | 'active' | 'complete' | 'failed' }>`
  font-size: 14px;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s ease;
  
  ${props => {
    switch (props.status) {
      case 'complete':
        return css`
          background: var(--pg-stage-complete-bg, rgba(5, 150, 105, 0.16));
          color: var(--pg-stage-complete-text, #047857);
        `;
      case 'active':
        return css`
          background: var(--pg-stage-active-bg, rgba(79, 70, 229, 0.12));
          color: var(--pg-stage-active-text, #1e1b4b);
          animation: ${pulse} 1.5s ease-in-out infinite;
        `;
      case 'failed':
        return css`
          background: var(--pg-stage-failed-bg, rgba(220, 38, 38, 0.16));
          color: var(--pg-stage-failed-text, #b91c1c);
        `;
      default:
        return css`
          background: var(--pg-stage-pending-bg, rgba(15, 23, 42, 0.07));
          color: var(--pg-stage-pending-text, #64748b);
          opacity: 0.5;
        `;
    }
  }}
`;

const StageName = styled.span`
  flex: 1;
  font-weight: 500;
`;

const FileCount = styled.span`
  font-size: 11px;
  padding: 2px 8px;
  background: var(--pg-pill-bg, rgba(15, 23, 42, 0.08));
  color: var(--pg-pill-text, #475569);
  border-radius: 10px;
  opacity: 0.92;
`;

const ProgressContainer = styled.div`
  padding: 8px 12px 12px 40px;
`;

const ProgressTrack = styled.div`
  background: var(--pg-gray-100, rgba(255, 255, 255, 0.08));
  height: 4px;
  border-radius: 2px;
  overflow: hidden;
  position: relative;
`;

const ProgressFill = styled.div<{ progress: number }>`
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  width: ${props => props.progress}%;
  background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 50%, #06b6d4 100%);
  background-size: 200% 100%;
  animation: ${shimmer} 2s ease-in-out infinite;
  border-radius: 2px;
  transition: width 0.4s cubic-bezier(0.19, 1, 0.22, 1);
`;

const ProgressText = styled.div`
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  font-size: 11px;
  color: var(--vscode-descriptionForeground);
  opacity: 0.7;
`;

const FileList = styled.div<{ isExpanded: boolean }>`
  max-height: ${props => props.isExpanded ? '500px' : '0'};
  overflow: hidden;
  transition: max-height 0.3s cubic-bezier(0.19, 1, 0.22, 1);
  padding-left: 40px;
`;

const FileItem = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  margin: 2px 0;
  font-size: 12px;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.15s ease;
  
  &:hover {
    background: var(--pg-gray-100, rgba(255, 255, 255, 0.06));
    transform: translateX(4px);
  }
`;

const FileName = styled.span<{ isTmp: boolean }>`
  color: ${props => props.isTmp 
    ? '#fbbf24' 
    : 'var(--pg-primary, #818cf8)'};
  font-family: var(--pg-font-mono, monospace);
  font-size: 12px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  
  &:hover {
    text-decoration: underline;
  }
`;

const FileSize = styled.span`
  font-size: 10px;
  color: var(--vscode-descriptionForeground);
  opacity: 0.6;
`;

const CompletionMessage = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  margin-top: 12px;
  background: var(--pg-success-panel-bg, rgba(5, 150, 105, 0.14));
  border: 1px solid var(--pg-success-panel-border, rgba(5, 150, 105, 0.34));
  border-radius: 10px;
  font-size: 13px;
  animation: ${fadeIn} 0.4s cubic-bezier(0.19, 1, 0.22, 1);
`;

const SuccessIcon = styled.span`
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
`;

const CompletionText = styled.span`
  color: var(--pg-success-panel-text, var(--vscode-foreground));
  
  strong {
    color: #10b981;
    font-weight: 600;
  }
`;

const ErrorState = styled.div`
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid var(--pg-error-panel-border, #f3b4b4);
  background: var(--pg-error-panel-bg, #fde8e8);
  color: var(--pg-error-panel-text, #7f1d1d);
  font-size: 12px;
  font-weight: 500;
  line-height: 1.5;
  white-space: pre-wrap;
  box-shadow: inset 0 0 0 1px rgba(185, 28, 28, 0.16);
`;

interface GenerationSessionProps {
  repo: string;
  currentStage: 'architecture' | 'skeleton' | 'code' | '';
  progress: number;
  files: GeneratedFile[];
  isComplete: boolean;
  onFileClick: (file: GeneratedFile) => void;
  statusMessage?: string;
  error?: string;
}

const stages = [
  { key: 'architecture', name: 'Architecture Design' },
  { key: 'skeleton', name: 'Code Skeleton' },
  { key: 'code', name: 'Code Generation' }
] as const;

type StageStatus = 'pending' | 'active' | 'complete' | 'failed';

export const GenerationSession: React.FC<GenerationSessionProps> = ({
  repo,
  currentStage,
  progress,
  files,
  isComplete,
  onFileClick,
  statusMessage,
  error
}) => {
  const [expandedStages, setExpandedStages] = useState<Set<string>>(new Set(['architecture', 'skeleton', 'code']));
  
  const toggleStage = (stage: string) => {
    setExpandedStages(prev => {
      const next = new Set(prev);
      if (next.has(stage)) {
        next.delete(stage);
      } else {
        next.add(stage);
      }
      return next;
    });
  };
  
  // Group files by stage
  const filesByStage: { [key: string]: GeneratedFile[] } = {
    architecture: [],
    skeleton: [],
    code: []
  };
  
  files.forEach(file => {
    const path = file.path.toLowerCase();
    // 支持 arch_step_ 和 architecture_ 两种命名
    if (path.includes('arch_step') || path.includes('architecture_') || path.includes('/architecture')) {
      filesByStage.architecture.push(file);
    // 支持 skeleton_step_ 和 skeleton_ 两种命名 (排除已匹配的 architecture)
    } else if (path.includes('skeleton_step') || path.includes('skeleton_')) {
      filesByStage.skeleton.push(file);
    } else {
      filesByStage.code.push(file);
    }
  });
  
  // Debug log
  console.log('[GenerationSession] Files by stage:', {
    total: files.length,
    architecture: filesByStage.architecture.length,
    skeleton: filesByStage.skeleton.length,
    code: filesByStage.code.length,
    files: files.map(f => f.path)
  });
  
  const getStageStatus = (stageKey: string, stageFilesCount: number): StageStatus => {
    const stageOrder = ['architecture', 'skeleton', 'code'];
    const currentIndex = stageOrder.indexOf(currentStage);
    const stageIndex = stageOrder.indexOf(stageKey);
    const hasError = Boolean(error);
    
    if (isComplete) return 'complete';
    if (hasError) {
      if (stageKey === currentStage) {
        return 'failed';
      }
      // 失败场景下，只有有实际产出文件的阶段才标记为完成，避免假阳性“已通过”
      return stageFilesCount > 0 ? 'complete' : 'pending';
    }

    if (stageKey === currentStage) return 'active';
    if (stageIndex < currentIndex) return 'complete';
    return 'pending';
  };

  const getStageIcon = (status: StageStatus) => {
    if (status === 'complete') return '✓';
    if (status === 'failed') return '✕';
    if (status === 'active') return '◐';
    return '○';
  };
  
  const formatFileSize = (content: string) => {
    const bytes = new Blob([content]).size;
    if (bytes < 1024) return `${bytes} B`;
    return `${(bytes / 1024).toFixed(1)} KB`;
  };
  
  return (
    <SessionContainer>
      <ContentWrapper>
        <Header>
          <SessionTitle>ProjectGen [{repo || '未指定路径'}]</SessionTitle>
        </Header>
        
        {!isComplete && !error && (statusMessage || currentStage) && (
          <ThinkingIndicator>
            <Spinner />
            <ThinkingText>
              {statusMessage || 'Generating project structure'}<ThinkingDots>...</ThinkingDots>
            </ThinkingText>
          </ThinkingIndicator>
        )}
        
        {stages.map(stage => {
          const stageFiles = filesByStage[stage.key];
          const status = getStageStatus(stage.key, stageFiles.length);
          const isActive = status === 'active' || status === 'failed';
          const isStageComplete = status === 'complete';
          const isExpanded = expandedStages.has(stage.key);
          const hasFiles = stageFiles.length > 0;
          
          // 只跳过还没开始的阶段
          if (status === 'pending' && !hasFiles) return null;
          
          return (
            <StageSection key={stage.key}>
              <StageHeader 
                isExpanded={isExpanded}
                isActive={isActive}
                onClick={() => hasFiles && toggleStage(stage.key)}
                style={{ cursor: hasFiles ? 'pointer' : 'default' }}
              >
                {hasFiles ? (
                  <ChevronIcon isExpanded={isExpanded}>▶</ChevronIcon>
                ) : (
                  <span style={{ width: '12px' }} />
                )}
                <StageIcon status={status}>{getStageIcon(status)}</StageIcon>
                <StageName>{stage.name}</StageName>
                {hasFiles ? (
                  <FileCount>{stageFiles.length} files</FileCount>
                ) : isStageComplete ? (
                  <FileCount style={{ opacity: 0.4 }}>—</FileCount>
                ) : null}
              </StageHeader>
              
              {isActive && !error && (
                <ProgressContainer>
                  <ProgressTrack>
                    <ProgressFill progress={progress} />
                  </ProgressTrack>
                  <ProgressText>
                    <span>Processing...</span>
                    <span>{progress}%</span>
                  </ProgressText>
                </ProgressContainer>
              )}
              
              <FileList isExpanded={isExpanded && hasFiles}>
                {stageFiles.map((file, index) => {
                  const isTmpFile = file.path.includes('tmp_files');
                  const fileName = file.path.split('/').pop() || file.path;
                  return (
                    <FileItem 
                      key={`${stage.key}-${index}`}
                      onClick={() => onFileClick(file)}
                    >
                      <FileName isTmp={isTmpFile} title={file.path}>
                        {fileName}
                      </FileName>
                      <FileSize>
                        {file.content ? formatFileSize(file.content) : '—'}
                      </FileSize>
                    </FileItem>
                  );
                })}
              </FileList>
            </StageSection>
          );
        })}
        
        {isComplete && (
          <CompletionMessage>
            <SuccessIcon>✓</SuccessIcon>
            <CompletionText>
              Successfully generated <strong>{files.length} files</strong> for {repo}
            </CompletionText>
          </CompletionMessage>
        )}

        {error && (
          <ErrorState>
            {error}
          </ErrorState>
        )}
      </ContentWrapper>
    </SessionContainer>
  );
};
