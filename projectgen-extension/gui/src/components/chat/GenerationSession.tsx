import React, { useState } from 'react';
import styled, { keyframes } from 'styled-components';
import { GeneratedFile } from '../../redux/slices/projectGenSlice';

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

const spin = keyframes`
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
`;

const SessionContainer = styled.div`
  display: flex;
  gap: 10px;
  padding: 12px 16px;
  animation: ${fadeIn} 0.2s ease-out;
  
  &:hover {
    background: var(--vscode-list-hoverBackground, rgba(255,255,255,0.04));
  }
`;

const Avatar = styled.div`
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  flex-shrink: 0;
  color: white;
  margin-top: 2px;
`;

const ContentWrapper = styled.div`
  flex: 1;
  min-width: 0;
`;

const Header = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
`;

const SenderName = styled.span`
  font-weight: 600;
  font-size: 13px;
  color: var(--vscode-foreground);
`;

const ThinkingIndicator = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  font-size: 13px;
  color: var(--vscode-descriptionForeground);
`;

const Spinner = styled.div`
  width: 14px;
  height: 14px;
  border: 2px solid var(--vscode-descriptionForeground);
  border-top-color: transparent;
  border-radius: 50%;
  animation: ${spin} 0.8s linear infinite;
`;

const StageSection = styled.div`
  margin-bottom: 4px;
`;

const StageHeader = styled.div<{ isExpanded: boolean }>`
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 0;
  cursor: pointer;
  font-size: 12px;
  color: var(--vscode-descriptionForeground);
  
  &:hover {
    color: var(--vscode-foreground);
  }
`;

const ChevronIcon = styled.span<{ isExpanded: boolean }>`
  font-size: 10px;
  transition: transform 0.15s;
  transform: rotate(${props => props.isExpanded ? '90deg' : '0deg'});
  opacity: 0.7;
`;

const StageIcon = styled.span<{ status: 'pending' | 'active' | 'complete' }>`
  font-size: 12px;
`;

const StageName = styled.span`
  flex: 1;
`;

const FileCount = styled.span`
  font-size: 11px;
  opacity: 0.7;
`;

const ProgressContainer = styled.div`
  padding: 4px 0 8px 18px;
`;

const ProgressTrack = styled.div`
  background: var(--vscode-progressBar-background, rgba(255,255,255,0.1));
  height: 2px;
  border-radius: 1px;
  overflow: hidden;
  width: 200px;
`;

const ProgressFill = styled.div<{ progress: number }>`
  background: var(--vscode-progressBar-background, #0078d4);
  height: 100%;
  width: ${props => props.progress}%;
  transition: width 0.3s ease-out;
`;

const FileList = styled.div<{ isExpanded: boolean }>`
  max-height: ${props => props.isExpanded ? '1000px' : '0'};
  overflow: hidden;
  transition: max-height 0.2s ease-out;
  padding-left: 18px;
`;

const FileItem = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 0;
  font-size: 12px;
  cursor: pointer;
  
  &:hover {
    background: var(--vscode-list-hoverBackground, rgba(255,255,255,0.04));
  }
`;

const FileIcon = styled.span`
  font-size: 14px;
  opacity: 0.8;
`;

const FileName = styled.span<{ isTmp: boolean }>`
  color: ${props => props.isTmp ? 'var(--vscode-editorWarning-foreground, #cca700)' : 'var(--vscode-textLink-foreground)'};
  font-family: var(--vscode-editor-font-family, monospace);
  font-size: 12px;
  
  &:hover {
    text-decoration: underline;
  }
`;

const CompletionMessage = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  margin-top: 8px;
  background: var(--vscode-inputValidation-infoBackground, rgba(0, 120, 212, 0.1));
  border: 1px solid var(--vscode-inputValidation-infoBorder, rgba(0, 120, 212, 0.4));
  border-radius: 4px;
  font-size: 13px;
`;

const SuccessIcon = styled.span`
  color: var(--vscode-testing-iconPassed, #73c991);
  font-size: 16px;
`;

interface GenerationSessionProps {
  repo: string;
  currentStage: 'architecture' | 'skeleton' | 'code' | '';
  progress: number;
  files: GeneratedFile[];
  isComplete: boolean;
  onFileClick: (file: GeneratedFile) => void;
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
  onFileClick
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
  
  return (
    <SessionContainer>
      <Avatar>✦</Avatar>
      <ContentWrapper>
        <Header>
          <SenderName>ProjectGen</SenderName>
        </Header>
        
        {!isComplete && currentStage && (
          <ThinkingIndicator>
            <Spinner />
            Generating {repo}...
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
                onClick={() => hasFiles && toggleStage(stage.key)}
                style={{ cursor: hasFiles ? 'pointer' : 'default' }}
              >
                {hasFiles ? (
                  <ChevronIcon isExpanded={isExpanded}>▶</ChevronIcon>
                ) : (
                  <span style={{ width: '10px' }} />
                )}
                <StageIcon status={status}>{getStageIcon(status)}</StageIcon>
                <StageName>{stage.name}</StageName>
                {hasFiles ? (
                  <FileCount>({stageFiles.length})</FileCount>
                ) : isStageComplete ? (
                  <FileCount style={{ opacity: 0.5 }}>No files</FileCount>
                ) : null}
              </StageHeader>
              
              {isActive && (
                <ProgressContainer>
                  <ProgressTrack>
                    <ProgressFill progress={progress} />
                  </ProgressTrack>
                </ProgressContainer>
              )}
              
              <FileList isExpanded={isExpanded && hasFiles}>
                {stageFiles.map((file, index) => {
                  const isTmpFile = file.path.includes('tmp_files');
                  return (
                    <FileItem 
                      key={`${stage.key}-${index}`}
                      onClick={() => onFileClick(file)}
                    >
                      <FileIcon>{isTmpFile ? '📋' : '📄'}</FileIcon>
                      <FileName isTmp={isTmpFile}>{file.path}</FileName>
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
            Generated {files.length} files for <strong>{repo}</strong>
          </CompletionMessage>
        )}
      </ContentWrapper>
    </SessionContainer>
  );
};
