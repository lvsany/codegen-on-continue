import styled, { keyframes } from 'styled-components';

const glowPulse = keyframes`
  0%, 100% { box-shadow: 0 0 0 1px var(--pg-primary, #6366f1), 0 0 20px rgba(99, 102, 241, 0.15); }
  50% { box-shadow: 0 0 0 1px var(--pg-primary, #6366f1), 0 0 30px rgba(99, 102, 241, 0.25); }
`;

const shimmer = keyframes`
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
`;

export const InputBoxDiv = styled.div`
  position: relative;
  background: var(--pg-glass-bg, rgba(255, 255, 255, 0.04));
  border: 1px solid var(--pg-glass-border, rgba(255, 255, 255, 0.1));
  border-radius: 12px;
  padding: 4px;
  transition: all 0.3s cubic-bezier(0.19, 1, 0.22, 1);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  
  &::before {
    content: '';
    position: absolute;
    inset: -1px;
    border-radius: 13px;
    padding: 1px;
    background: linear-gradient(135deg, 
      transparent 0%, 
      rgba(99, 102, 241, 0) 40%,
      rgba(99, 102, 241, 0.1) 50%,
      rgba(99, 102, 241, 0) 60%,
      transparent 100%
    );
    -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
    -webkit-mask-composite: xor;
    mask-composite: exclude;
    opacity: 0;
    transition: opacity 0.3s ease;
    pointer-events: none;
  }
  
  &:hover {
    border-color: rgba(99, 102, 241, 0.3);
    background: rgba(255, 255, 255, 0.06);
    
    &::before {
      opacity: 1;
    }
  }
  
  &:focus-within {
    border-color: var(--pg-primary, #6366f1);
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15), 0 4px 12px rgba(0, 0, 0, 0.1);
    background: rgba(255, 255, 255, 0.05);
    
    &::before {
      opacity: 0;
    }
  }
  
  &.generating {
    border-color: var(--pg-primary, #6366f1);
    animation: ${glowPulse} 2s ease-in-out infinite;
    
    &::after {
      content: '';
      position: absolute;
      bottom: 0;
      left: 0;
      right: 0;
      height: 2px;
      background: linear-gradient(90deg, 
        transparent,
        var(--pg-primary, #6366f1),
        var(--pg-secondary, #8b5cf6),
        var(--pg-primary, #6366f1),
        transparent
      );
      background-size: 200% 100%;
      animation: ${shimmer} 1.5s ease-in-out infinite;
      border-radius: 0 0 11px 11px;
    }
  }
`;
