import React from 'react';

interface StatusBarProps {
  status: 'ready' | 'processing' | 'error';
  statusText: string;
  onStatsClick: () => void;
  onHealthClick: () => void;
  onLogout: () => void;
}

export const StatusBar: React.FC<StatusBarProps> = ({
  status,
  statusText,
  onStatsClick,
  onHealthClick,
  onLogout,
}) => {
  const getStatusColor = () => {
    switch (status) {
      case 'ready':
        return 'var(--success)';
      case 'processing':
        return 'var(--warning)';
      case 'error':
        return 'var(--error)';
      default:
        return 'var(--gray-400)';
    }
  };

  return (
    <header className="status-bar">
      <div className="status-left">
        <span className="logo">🏥</span>
        <span className="app-name">MedAgent</span>
        <span className="version">v1.1</span>
      </div>
      <div className="status-center">
        <span className="status-indicator">
          <span className="status-dot" style={{ background: getStatusColor() }} />
          <span className="status-text">{statusText}</span>
        </span>
      </div>
      <div className="status-right">
        <button className="icon-btn" onClick={onStatsClick} title="系统统计">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 20V10M12 20V4M6 20v-6" />
          </svg>
        </button>
        <button className="icon-btn" onClick={onHealthClick} title="系统状态">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
          </svg>
        </button>
        <button className="icon-btn" onClick={onLogout} title="退出登录" aria-label="退出登录">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M10 17l5-5-5-5M15 12H3M14 3h5a2 2 0 012 2v14a2 2 0 01-2 2h-5" />
          </svg>
        </button>
      </div>
    </header>
  );
};
