import React, { useMemo, useState } from 'react';
import styled from 'styled-components';
import {
  PlusIcon,
  XMarkIcon,
  ChatBubbleLeftIcon,
  ClockIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';
import { useAppDispatch, useAppSelector } from '../../redux/hooks';
import {
  createSession,
  switchSession,
  deleteSession,
  selectAllSessions,
} from '../../redux/slices/chatHistorySlice';

const Wrapper = styled.div`
  position: relative;
  border-bottom: 1px solid var(--vscode-widget-border, rgba(255, 255, 255, 0.1));
`;

const TabBarContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: var(--vscode-editor-background);
`;

const TabsScroll = styled.div`
  display: flex;
  align-items: center;
  gap: 4px;
  overflow-x: auto;
  flex: 1;

  &::-webkit-scrollbar {
    height: 4px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.2);
    border-radius: 2px;
  }
`;

const Tab = styled.button<{ active: boolean }>`
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: ${(props) =>
    props.active
      ? 'var(--vscode-tab-activeBackground, rgba(255, 255, 255, 0.1))'
      : 'transparent'};
  border: 1px solid
    ${(props) =>
      props.active
        ? 'var(--vscode-tab-activeBorder, rgba(255, 255, 255, 0.2))'
        : 'transparent'};
  border-radius: 6px;
  color: ${(props) =>
    props.active
      ? 'var(--vscode-tab-activeForeground, #fff)'
      : 'var(--vscode-tab-inactiveForeground, #999)'};
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  max-width: 170px;
  transition: all 0.15s ease;

  &:hover {
    background: var(--vscode-list-hoverBackground, rgba(255, 255, 255, 0.08));
  }
`;

const TabTitle = styled.span`
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  text-align: left;
`;

const ActionButton = styled.button<{ active?: boolean }>`
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 28px;
  padding: 0 10px;
  border-radius: 6px;
  border: 1px solid
    ${(props) =>
      props.active
        ? 'var(--vscode-focusBorder, #007fd4)'
        : 'var(--vscode-widget-border, rgba(255, 255, 255, 0.2))'};
  background: ${(props) =>
    props.active
      ? 'var(--vscode-list-activeSelectionBackground, rgba(255, 255, 255, 0.08))'
      : 'transparent'};
  color: var(--vscode-foreground);
  cursor: pointer;
  font-size: 12px;

  &:hover {
    background: var(--vscode-list-hoverBackground, rgba(255, 255, 255, 0.08));
  }

  svg {
    width: 14px;
    height: 14px;
  }
`;

const DeleteButton = styled.button`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  padding: 0;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--vscode-descriptionForeground);
  cursor: pointer;
  opacity: 0.7;

  &:hover {
    opacity: 1;
    background: var(--vscode-list-hoverBackground, rgba(255, 255, 255, 0.08));
  }
`;

const HistoryPanel = styled.div`
  position: absolute;
  top: 100%;
  right: 10px;
  width: 380px;
  max-height: 420px;
  margin-top: 6px;
  background: var(--vscode-editor-background);
  border: 1px solid var(--vscode-widget-border, rgba(255, 255, 255, 0.12));
  border-radius: 8px;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.25);
  z-index: 20;
  display: flex;
  flex-direction: column;
`;

const SearchWrap = styled.div`
  padding: 10px;
  border-bottom: 1px solid var(--vscode-widget-border, rgba(255, 255, 255, 0.1));
`;

const SearchBox = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  background: var(--vscode-input-background);
  border: 1px solid var(--vscode-input-border);

  svg {
    width: 14px;
    height: 14px;
    color: var(--vscode-descriptionForeground);
  }

  input {
    flex: 1;
    border: none;
    outline: none;
    background: transparent;
    color: var(--vscode-foreground);
    font-size: 12px;
  }
`;

const HistoryList = styled.div`
  overflow-y: auto;
  padding: 6px 0;
`;

const GroupLabel = styled.div`
  position: sticky;
  top: 0;
  background: var(--vscode-editor-background);
  padding: 6px 12px;
  font-size: 11px;
  font-weight: 600;
  color: var(--vscode-descriptionForeground);
  text-transform: uppercase;
  letter-spacing: 0.04em;
`;

const SessionRow = styled.button<{ active: boolean }>`
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: none;
  text-align: left;
  background: ${(props) =>
    props.active
      ? 'var(--vscode-list-activeSelectionBackground, rgba(255, 255, 255, 0.08))'
      : 'transparent'};
  color: var(--vscode-foreground);
  cursor: pointer;

  &:hover {
    background: var(--vscode-list-hoverBackground, rgba(255, 255, 255, 0.06));
  }
`;

const SessionMeta = styled.div`
  flex: 1;
  min-width: 0;
`;

const SessionTitle = styled.div`
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`;

const SessionInfo = styled.div`
  margin-top: 2px;
  font-size: 10px;
  color: var(--vscode-descriptionForeground);
`;

const EmptyState = styled.div`
  padding: 18px 12px;
  text-align: center;
  color: var(--vscode-descriptionForeground);
  font-size: 12px;
`;

const Footer = styled.div`
  border-top: 1px solid var(--vscode-widget-border, rgba(255, 255, 255, 0.1));
  padding: 8px 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
`;

const FooterNote = styled.span`
  font-size: 10px;
  color: var(--vscode-descriptionForeground);
`;

function toDayLabel(timestamp: number) {
  const date = new Date(timestamp);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const day = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
  const diffDays = Math.floor((today - day) / (24 * 60 * 60 * 1000));

  if (diffDays === 0) {
    return 'Today';
  }
  if (diffDays === 1) {
    return 'Yesterday';
  }
  return date.toLocaleDateString();
}

function formatUpdatedAt(timestamp: number) {
  return new Date(timestamp).toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export const SessionTabs: React.FC = () => {
  const dispatch = useAppDispatch();
  const sessions = useAppSelector(selectAllSessions);
  const currentSessionId = useAppSelector((state) => state.chatHistory.currentSessionId);
  const [showHistory, setShowHistory] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const sortedSessions = useMemo(
    () => [...sessions].sort((a, b) => b.updatedAt - a.updatedAt),
    [sessions],
  );

  const filteredSessions = useMemo(() => {
    const normalized = searchTerm.trim().toLowerCase();
    if (!normalized) {
      return sortedSessions;
    }
    return sortedSessions.filter((session) =>
      session.title.toLowerCase().includes(normalized),
    );
  }, [searchTerm, sortedSessions]);

  const groupedSessions = useMemo(() => {
    const groups: Array<{ label: string; items: typeof filteredSessions }> = [];
    filteredSessions.forEach((session) => {
      const label = toDayLabel(session.updatedAt);
      const group = groups.find((g) => g.label === label);
      if (group) {
        group.items.push(session);
      } else {
        groups.push({ label, items: [session] });
      }
    });
    return groups;
  }, [filteredSessions]);

  const handleNewSession = () => {
    dispatch(createSession());
    setShowHistory(false);
  };

  const handleSwitchSession = (id: string) => {
    dispatch(switchSession(id));
    setShowHistory(false);
  };

  const handleDeleteSession = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    dispatch(deleteSession(id));
  };

  const visibleTabs = sortedSessions.slice(0, 5);

  return (
    <Wrapper>
      <TabBarContainer>
        <TabsScroll>
          {visibleTabs.map((session) => (
            <Tab
              key={session.id}
              active={session.id === currentSessionId}
              onClick={() => handleSwitchSession(session.id)}
            >
              <ChatBubbleLeftIcon style={{ width: 14, height: 14, flexShrink: 0 }} />
              <TabTitle>{session.title || 'New Chat'}</TabTitle>
              {sessions.length > 1 && (
                <DeleteButton onClick={(e) => handleDeleteSession(e, session.id)}>
                  <XMarkIcon style={{ width: 12, height: 12 }} />
                </DeleteButton>
              )}
            </Tab>
          ))}
        </TabsScroll>

        <ActionButton active={showHistory} onClick={() => setShowHistory((prev) => !prev)}>
          <ClockIcon />
          History
        </ActionButton>

        <ActionButton onClick={handleNewSession}>
          <PlusIcon />
          New
        </ActionButton>
      </TabBarContainer>

      {showHistory && (
        <HistoryPanel>
          <SearchWrap>
            <SearchBox>
              <MagnifyingGlassIcon />
              <input
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search chat history"
              />
            </SearchBox>
          </SearchWrap>

          <HistoryList>
            {groupedSessions.length === 0 ? (
              <EmptyState>No sessions found.</EmptyState>
            ) : (
              groupedSessions.map((group) => (
                <div key={group.label}>
                  <GroupLabel>{group.label}</GroupLabel>
                  {group.items.map((session) => (
                    <SessionRow
                      key={session.id}
                      active={session.id === currentSessionId}
                      onClick={() => handleSwitchSession(session.id)}
                    >
                      <ChatBubbleLeftIcon style={{ width: 14, height: 14, flexShrink: 0 }} />
                      <SessionMeta>
                        <SessionTitle>{session.title || 'New Chat'}</SessionTitle>
                        <SessionInfo>
                          {formatUpdatedAt(session.updatedAt)} · {session.messages.length} messages
                        </SessionInfo>
                      </SessionMeta>
                      {sessions.length > 1 && (
                        <DeleteButton onClick={(e) => handleDeleteSession(e, session.id)}>
                          <XMarkIcon style={{ width: 12, height: 12 }} />
                        </DeleteButton>
                      )}
                    </SessionRow>
                  ))}
                </div>
              ))
            )}
          </HistoryList>

          <Footer>
            <FooterNote>History is stored in local browser storage.</FooterNote>
            <ActionButton onClick={() => setShowHistory(false)}>Close</ActionButton>
          </Footer>
        </HistoryPanel>
      )}
    </Wrapper>
  );
};

export default SessionTabs;
