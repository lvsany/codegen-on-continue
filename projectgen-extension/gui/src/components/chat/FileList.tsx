import React, { useContext } from 'react';
import styled from 'styled-components';
import { GeneratedFile } from '../../redux/slices/projectGenSlice';
import { VsCodeApiContext } from '../../context/VsCodeApi';

const FileListDiv = styled.div`
  padding: 12px 16px;
  margin: 8px 0;
  background: rgba(255, 255, 255, 0.05);
  border-left: 3px solid #4ec9b0;
  border-radius: 8px;
  max-height: 500px;
  overflow-y: auto;
`;

const StageHeader = styled.div`
  font-weight: 600;
  color: #3b82f6;
  margin: 12px 0 8px 0;
  padding: 4px 0;
  border-bottom: 1px solid rgba(59, 130, 246, 0.3);
`;

const FileItem = styled.div`
  padding: 6px 12px;
  margin: 2px 0;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  animation: slideIn 0.3s ease-out;
  
  &:hover {
    background: rgba(255, 255, 255, 0.12);
  }
  
  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
`;

const FileLink = styled.a`
  color: inherit;
  text-decoration: none;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  
  &:hover {
    text-decoration: underline;
  }
`;

interface FileListProps {
  files: GeneratedFile[];
}

export const FileList: React.FC<FileListProps> = ({ files }) => {
  const vscode = useContext(VsCodeApiContext);
  
  const handleFileClick = (file: GeneratedFile) => {
    vscode?.postMessage({
      type: 'openFile',
      filePath: file.path,
      content: file.content
    });
  };
  
  const tmpFiles = files.filter(f => f.path.includes('tmp_files'));
  const regularFiles = files.filter(f => !f.path.includes('tmp_files'));
  
  return (
    <FileListDiv>
      {tmpFiles.length > 0 && (
        <>
          <StageHeader>📋 临时文件</StageHeader>
          {tmpFiles.map((file, index) => (
            <FileItem key={`tmp-${index}`} onClick={() => handleFileClick(file)}>
              <span style={{ color: 'var(--vscode-descriptionForeground)', fontSize: '11px', marginRight: '8px', opacity: 0.6 }}>
                {index + 1}.
              </span>
              <span style={{ color: '#4EC9B0', fontSize: '12px' }}>created</span>
              {' '}
              <FileLink href="#" style={{ color: '#FFA500' }} onClick={(e) => e.preventDefault()}>
                📋 {file.path}
              </FileLink>
            </FileItem>
          ))}
        </>
      )}
      
      {regularFiles.length > 0 && (
        <>
          <StageHeader>📄 项目文件</StageHeader>
          {regularFiles.map((file, index) => (
            <FileItem key={`regular-${index}`} onClick={() => handleFileClick(file)}>
              <span style={{ color: 'var(--vscode-descriptionForeground)', fontSize: '11px', marginRight: '8px', opacity: 0.6 }}>
                {tmpFiles.length + index + 1}.
              </span>
              <span style={{ color: '#4EC9B0', fontSize: '12px' }}>created</span>
              {' '}
              <FileLink href="#" style={{ color: 'var(--vscode-textLink-foreground)' }} onClick={(e) => e.preventDefault()}>
                📄 {file.path}
              </FileLink>
            </FileItem>
          ))}
        </>
      )}
    </FileListDiv>
  );
};
