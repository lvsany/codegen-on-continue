import React, { useState } from 'react';
import styled, { keyframes } from 'styled-components';
import { GenerationMetadata } from '../../redux/slices/chatHistorySlice';

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

const CardContainer = styled.div`
  display: flex;
  gap: 12px;
  padding: 16px;
  border-radius: 12px;
  animation: ${fadeIn} 0.35s cubic-bezier(0.19, 1, 0.22, 1);
  background: var(--vscode-editor-inactiveSelectionBackground);
  border: 1px solid var(--vscode-panel-border);
  margin: 4px 0;
  
  &:hover {
    border-color: var(--vscode-focusBorder);
    background: var(--vscode-list-hoverBackground);
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

const CardTitle = styled.span`
  font-weight: 600;
  font-size: 13px;
  color: var(--vscode-foreground);
  letter-spacing: -0.01em;
`;

const StatusIndicator = styled.div`
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  font-size: 12px;
  color: var(--vscode-descriptionForeground);
  background: var(--vscode-input-background);
  border-radius: 8px;
  margin-bottom: 12px;
  border: 1px solid var(--vscode-input-border);
`;

const Spinner = styled.div`
  width: 14px;
  height: 14px;
  border: 2px solid var(--vscode-progressBar-background);
  border-top-color: transparent;
  border-radius: 50%;
  animation: ${spin} 0.7s linear infinite;
`;

const StatusText = styled.span`
  flex: 1;
`;

const StatusDots = styled.span`
  animation: ${pulse} 1.4s ease-in-out infinite;
`;

const StageSection = styled.div`
  margin-bottom: 6px;
`;

const StageHeader = styled.div<{ isExpanded: boolean; isActive: boolean }>`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  background: ${props => props.isActive 
    ? 'var(--vscode-list-activeSelectionBackground)' 
    : 'var(--vscode-list-inactiveSelectionBackground)'};
  color: ${props => props.isActive
    ? 'var(--vscode-list-activeSelectionForeground)'
    : 'var(--vscode-foreground)'};
  font-size: 12px;
  font-weight: 500;
  transition: all 0.2s ease;
  user-select: none;
  
  &:hover {
    background: var(--vscode-list-hoverBackground);
  }
`;

const ChevronIcon = styled.span<{ isExpanded: boolean }>`
  display: inline-block;
  font-size: 10px;
  transition: transform 0.2s ease;
  transform: ${props => props.isExpanded ? 'rotate(90deg)' : 'rotate(0deg)'};
  color: var(--vscode-foreground);
  opacity: 0.6;
`;

const StageIcon = styled.span<{ status: 'pending' | 'active' | 'complete' | 'failed' }>`
  font-size: 14px;
  ${props => {
    switch (props.status) {
      case 'complete': return 'color: var(--vscode-testing-iconPassed);';
      case 'failed': return 'color: var(--vscode-testing-iconFailed);';
      case 'active': return 'color: var(--vscode-progressBar-background);';
      default: return 'opacity: 0.3;';
    }
  }}
`;

const StageName = styled.span`
  flex: 1;
`;

const FileCount = styled.span`
  font-size: 11px;
  opacity: 0.7;
`;

const ProgressContainer = styled.div`
  margin: 10px 0 10px 32px;
`;

const ProgressTrack = styled.div`
  height: 4px;
  background: var(--vscode-editorWidget-background);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 4px;
`;

const ProgressFill = styled.div<{ progress: number }>`
  height: 100%;
  width: ${props => props.progress}%;
  background: var(--vscode-progressBar-background);
  border-radius: 2px;
  transition: width 0.3s ease;
`;

const ProgressText = styled.div`
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--vscode-descriptionForeground);
`;

const FileList = styled.div<{ isExpanded: boolean }>`
  max-height: ${props => props.isExpanded ? '400px' : '0'};
  overflow: hidden;
  transition: max-height 0.3s ease;
  margin: 4px 0 4px 32px;
`;

const FileItem = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  margin: 2px 0;
  border-radius: 6px;
  font-size: 12px;
  background: var(--vscode-editor-background);
  border: 1px solid var(--vscode-panel-border);
  cursor: pointer;
  transition: all 0.15s ease;
  
  &:hover {
    background: var(--vscode-list-hoverBackground);
    border-color: var(--vscode-focusBorder);
    transform: translateX(2px);
  }
`;

const FileName = styled.span<{ isTmp?: boolean }>`
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--vscode-foreground);
  opacity: ${props => props.isTmp ? 0.6 : 1};
  font-family: var(--vscode-editor-font-family);
`;

const FileSize = styled.span`
  font-size: 10px;
  color: var(--vscode-descriptionForeground);
  margin-left: 12px;
`;

const CompletionMessage = styled.div`
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: var(--vscode-editorInfo-background);
  border-radius: 10px;
  color: var(--vscode-editorInfo-foreground);
  font-size: 13px;
  font-weight: 500;
  margin: 8px 0;
  border: 1px solid var(--vscode-editorInfo-border);
`;

const ErrorMessage = styled.div`
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 14px 16px;
  background: var(--vscode-inputValidation-errorBackground);
  border: 1px solid var(--vscode-inputValidation-errorBorder);
  border-radius: 10px;
  color: var(--vscode-inputValidation-errorForeground);
  font-size: 12px;
  margin: 8px 0;
`;

const ErrorText = styled.div`
  flex: 1;
  word-break: break-word;
  white-space: pre-wrap;
`;

interface GeneratedFile {
  path: string;
  content: string;
}

interface GenerationCardProps {
  metadata: GenerationMetadata;
  onFileClick?: (file: GeneratedFile) => void;
}

const stages = [
  { key: 'architecture', name: 'Architecture Design' },
  { key: 'skeleton', name: 'Code Skeleton' },
  { key: 'code', name: 'Code Generation' }
] as const;

type StageStatus = 'pending' | 'active' | 'complete' | 'failed';

export const GenerationCard: React.FC<GenerationCardProps> = ({ metadata, onFileClick }) => {
  const [expandedStages, setExpandedStages] = useState<Set<string>>(
    new Set(['architecture', 'skeleton', 'code'])
  );

  const {
    repo,
    currentStage = '',
    progress = 0,
    files = [],
    statusMessage,
    error,
    isComplete = false,
  } = metadata;

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
    if (path.includes('arch_step') || path.includes('architecture_') || path.includes('/architecture')) {
      filesByStage.architecture.push(file);
    } else if (path.includes('skeleton_step') || path.includes('skeleton_')) {
      filesByStage.skeleton.push(file);
    } else {
      filesByStage.code.push(file);
    }
  });

  const getStageStatus = (stageKey: string, fileCount: number): StageStatus => {
    if (error) return 'failed';
    if (isComplete && fileCount > 0) return 'complete';

    const stageIndex = stages.findIndex(s => s.key === stageKey);
    const currentIndex = stages.findIndex(s => s.key === currentStage);

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
    <CardContainer>
      <ContentWrapper>
        <Header>
          <CardTitle>ProjectGen [{repo || 'Unknown'}]</CardTitle>
        </Header>

        {/* Status indicator - shown when not complete */}
        {!isComplete && !error && (statusMessage || currentStage) && (
          <StatusIndicator>
            <Spinner />
            <StatusText>
              {statusMessage || 'Generating project structure'}
              <StatusDots>...</StatusDots>
            </StatusText>
          </StatusIndicator>
        )}

        {/* Stages */}
        {stages.map(stage => {
          const stageFiles = filesByStage[stage.key];
          const status = getStageStatus(stage.key, stageFiles.length);
          const isActive = status === 'active' || status === 'failed';
          const isStageComplete = status === 'complete';
          const isExpanded = expandedStages.has(stage.key);
          const hasFiles = stageFiles.length > 0;

          // Skip pending stages without files
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

              {/* Progress bar for active stage */}
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

              {/* File list */}
              <FileList isExpanded={isExpanded && hasFiles}>
                {stageFiles.map((file, index) => {
                  const isTmpFile = file.path.includes('tmp_files');
                  const fileName = file.path.split('/').pop() || file.path;
                  return (
                    <FileItem
                      key={`${stage.key}-${index}`}
                      onClick={() => onFileClick?.(file)}
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

        {/* Completion message */}
        {isComplete && !error && (
          <CompletionMessage>
            Generation complete. Created {files.length} files.
          </CompletionMessage>
        )}

        {/* Error message */}
        {error && (
          <ErrorMessage>
            <ErrorText>{error}</ErrorText>
          </ErrorMessage>
        )}
      </ContentWrapper>
    </CardContainer>
  );
};
