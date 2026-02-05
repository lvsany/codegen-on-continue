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
  background: var(--pg-glass-bg, rgba(255, 255, 255, 0.02));
  margin: 8px 0;
  border: 1px solid var(--pg-glass-border, rgba(255, 255, 255, 0.06));
  
  &:hover {
    background: var(--pg-gray-50, rgba(255,255,255,0.04));
    border-color: rgba(99, 102, 241, 0.15);
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

const SenderName = styled.span`
  font-weight: 600;
  font-size: 13px;
  color: var(--vscode-foreground);
  letter-spacing: -0.01em;
`;

const RepoBadge = styled.span`
  padding: 3px 10px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(139, 92, 246, 0.1) 100%);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 20px;
  font-size: 11px;
  font-weight: 500;
  color: #a5b4fc;
  font-family: var(--pg-font-mono, monospace);
`;

const ThinkingIndicator = styled.div`
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  font-size: 13px;
  color: var(--vscode-descriptionForeground);
  background: var(--pg-gray-50, rgba(255, 255, 255, 0.03));
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
  color: ${props => props.isActive ? 'var(--vscode-foreground)' : 'var(--vscode-descriptionForeground)'};
  background: ${props => props.isActive 
    ? 'linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.05) 100%)' 
    : 'transparent'};
  border-radius: 8px;
  transition: all 0.2s cubic-bezier(0.19, 1, 0.22, 1);
  border: 1px solid ${props => props.isActive 
    ? 'rgba(99, 102, 241, 0.2)' 
    : 'transparent'};
  
  &:hover {
    background: var(--pg-gray-100, rgba(255, 255, 255, 0.06));
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

const StageIcon = styled.span<{ status: 'pending' | 'active' | 'complete' }>`
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
          background: rgba(16, 185, 129, 0.15);
          color: #10b981;
        `;
      case 'active':
        return css`
          background: rgba(99, 102, 241, 0.15);
          color: #818cf8;
          animation: ${pulse} 1.5s ease-in-out infinite;
        `;
      default:
        return css`
          background: var(--pg-gray-100, rgba(255, 255, 255, 0.06));
          color: var(--vscode-descriptionForeground);
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
  background: var(--pg-gray-100, rgba(255, 255, 255, 0.06));
  border-radius: 10px;
  opacity: 0.8;
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
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(6, 182, 212, 0.05) 100%);
  border: 1px solid rgba(16, 185, 129, 0.2);
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
  color: var(--vscode-foreground);
  
  strong {
    color: #10b981;
    font-weight: 600;
  }
`;

interface GenerationSessionProps {
  repo: string;
  currentStage: 'architecture' | 'skeleton' | 'code' | '';
  progress: number;
  files: GeneratedFile[];
  isComplete: boolean;
  onFileClick: (file: GeneratedFile) => void;
  statusMessage?: string;
}

const stages = [
  { key: 'architecture', name: 'Architecture Design' },
  { key: 'skeleton', name: 'Code Skeleton' },
  { key: 'code', name: 'Code Generation' }
] as const;

export const GenerationSession: React.FC<GenerationSessionProps> = ({
  repo,
  currentStage,
  progress,
  files,
  isComplete,
  onFileClick,
  statusMessage
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
  
  const getStageStatus = (stageKey: string): 'pending' | 'active' | 'complete' => {
    const stageOrder = ['architecture', 'skeleton', 'code'];
    const currentIndex = stageOrder.indexOf(currentStage);
    const stageIndex = stageOrder.indexOf(stageKey);
    
    if (isComplete) return 'complete';
    if (stageKey === currentStage) return 'active';
    if (stageIndex < currentIndex) return 'complete';
    return 'pending';
  };

  const getStageIcon = (status: 'pending' | 'active' | 'complete') => {
    if (status === 'complete') return '✓';
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
          <SenderName>ProjectGen</SenderName>
          <RepoBadge>{repo}</RepoBadge>
        </Header>
        
        {!isComplete && (statusMessage || currentStage) && (
          <ThinkingIndicator>
            <Spinner />
            <ThinkingText>
              {statusMessage || 'Generating project structure'}<ThinkingDots>...</ThinkingDots>
            </ThinkingText>
          </ThinkingIndicator>
        )}
        
        {stages.map(stage => {
          const stageFiles = filesByStage[stage.key];
          const status = getStageStatus(stage.key);
          const isActive = status === 'active';
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
              
              {isActive && (
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
      </ContentWrapper>
    </SessionContainer>
  );
};
