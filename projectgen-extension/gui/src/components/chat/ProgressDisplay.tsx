import React from 'react';
import styled from 'styled-components';

const ProgressDiv = styled.div`
  padding: 12px 16px;
  margin: 8px 0;
  background: rgba(255, 255, 255, 0.05);
  border-left: 3px solid var(--vscode-button-background);
  border-radius: 8px;
  animation: pulse 2s ease-in-out infinite;
  
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.8; }
  }
`;

const ProgressBar = styled.div`
  background: rgba(255, 255, 255, 0.1);
  height: 6px;
  border-radius: 3px;
  overflow: hidden;
  margin-top: 8px;
`;

const ProgressFill = styled.div<{ progress: number }>`
  background: var(--vscode-button-background);
  height: 100%;
  width: ${props => props.progress}%;
  transition: width 0.3s;
`;

interface ProgressDisplayProps {
  stage: 'architecture' | 'skeleton' | 'code';
  progress: number;
}

const stageNames = {
  architecture: '🏗️ 架构设计',
  skeleton: '📐 代码框架',
  code: '💻 代码生成'
};

export const ProgressDisplay: React.FC<ProgressDisplayProps> = ({ stage, progress }) => {
  return (
    <ProgressDiv>
      <div style={{ marginBottom: '8px' }}>
        ⏳ {stageNames[stage]} ({progress}%)
      </div>
      <ProgressBar>
        <ProgressFill progress={progress} />
      </ProgressBar>
    </ProgressDiv>
  );
};
