import React from 'react';
import type { SystemStats } from '../types';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
}) => {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{title}</h3>
          <button className="close-btn" onClick={onClose}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="modal-body">
          {children}
        </div>
      </div>
    </div>
  );
};

// 统计内容组件
export const StatsContent: React.FC<{ stats: SystemStats | null }> = ({ stats }) => {
  if (!stats) {
    return (
      <div>
        <div className="loading-spinner" />
        <p>加载中...</p>
      </div>
    );
  }

  return (
    <>
      {stats.knowledge_mode === 'pubmed_only' && (
        <div className="knowledge-mode-notice">
          当前未安装本地知识库，系统将使用模型与 PubMed 实时检索，不会显示教材引用。
        </div>
      )}
      <div className="stats-grid">
        <div className="stat-item">
          <div className="stat-value">{stats.bm25_chunks.toLocaleString()}</div>
          <div className="stat-label">教材切片</div>
        </div>
        <div className="stat-item">
          <div className="stat-value">{stats.textbook_sources}</div>
          <div className="stat-label">教材来源</div>
        </div>
        <div className="stat-item">
          <div className="stat-value">{stats.vector_documents.toLocaleString()}</div>
          <div className="stat-label">向量文档</div>
        </div>
        <div className="stat-item">
          <div className="stat-value">{stats.provider}</div>
          <div className="stat-label">模型接口</div>
        </div>
        <div className="stat-item">
          <div className="stat-value">{stats.model || '未知'}</div>
          <div className="stat-label">当前模型</div>
        </div>
        <div className="stat-item">
          <div className="stat-value">{stats.generation.active}/{stats.generation.max_active}</div>
          <div className="stat-label">正在生成</div>
        </div>
        <div className="stat-item">
          <div className="stat-value">{stats.generation.pending}/{stats.generation.max_pending}</div>
          <div className="stat-label">排队请求</div>
        </div>
      </div>
    </>
  );
};

// 健康状态内容组件
export const HealthContent: React.FC<{ health: { status: string; version: string } | null; error?: string }> = ({ health, error }) => {
  if (error) {
    return (
      <div className="health-status error">
        <span className="status-icon">✗</span>
        <div>
          <div className="status-title">系统连接失败</div>
          <div className="status-detail">无法连接到服务器</div>
        </div>
      </div>
    );
  }

  if (!health) {
    return (
      <div>
        <div className="loading-spinner" />
        <p>加载中...</p>
      </div>
    );
  }

  return (
    <div className="health-status success">
      <span className="status-icon">✓</span>
      <div>
        <div className="status-title">系统状态正常</div>
        <div className="status-detail">状态: {health.status || 'healthy'}</div>
        <div className="status-detail">版本: {health.version || '1.0.0'}</div>
      </div>
    </div>
  );
};
