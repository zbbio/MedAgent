import { useState } from 'react';
import type { Citation } from '../types';

interface CitationPanelProps {
  citations: Citation[];
  isOpen: boolean;
  onToggle: () => void;
}

const sanitizeContent = (text: string): string => {
  if (!text) return '';
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
};

const truncateText = (text: string, maxLength: number): string => {
  if (!text || text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};

export const CitationPanel: React.FC<CitationPanelProps> = ({
  citations,
  isOpen,
  onToggle,
}) => {
  const [selectedCitation, setSelectedCitation] = useState<(Citation & { number: number }) | null>(null);

  const handleCitationClick = (citation: Citation, index: number) => {
    setSelectedCitation({ ...citation, number: index + 1 });
  };

  const handleBack = () => {
    setSelectedCitation(null);
  };

  return (
    <aside className={`citation-panel ${isOpen ? 'open' : 'collapsed'}`}>
      <div className="panel-header">
        <h3>📚 参考来源列表</h3>
        <button className="close-btn" onClick={onToggle}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
      </div>
      <div className="panel-content">
        {selectedCitation ? (
          /* 引用详情 */
          <div className="citation-detail">
            <button className="back-btn" onClick={handleBack}>
              ← 返回列表
            </button>
            <div className="citation-detail-header">
              <span className="citation-marker large">{selectedCitation.number}</span>
              <span className="citation-title">{sanitizeContent(selectedCitation.title)}</span>
            </div>
            <div className="citation-source">{sanitizeContent(selectedCitation.source || '未知来源')}</div>
            <div className="citation-detail-content">
              {sanitizeContent(selectedCitation.content || '无内容')}
            </div>
          </div>
        ) : (
          /* 引用列表 */
          <>
            {citations.length > 0 && (
              <div className="citation-hint">
                <span className="hint-icon">💡</span>
                <span className="hint-text">正文中的 [1] [2] 等编号与此列表对应</span>
              </div>
            )}

            {citations.length === 0 ? (
              <div className="empty-state">
                <div className="empty-icon">📖</div>
                <p>暂无参考来源</p>
                <p className="empty-hint">发送医学问题后，相关文献将显示在这里</p>
              </div>
            ) : (
              citations.map((cite, index) => (
                <div
                  key={index}
                  className="citation-card"
                  onClick={() => handleCitationClick(cite, index)}
                >
                  <div className="citation-card-header">
                    <span className="citation-marker">{index + 1}</span>
                    <span className="citation-title" title={cite.title}>
                      {truncateText(cite.title, 30)}
                    </span>
                  </div>
                  <div className="citation-source">{sanitizeContent(cite.source || '未知来源')}</div>
                  <div className="citation-content">{truncateText(cite.content, 100)}</div>
                </div>
              ))
            )}
          </>
        )}
      </div>
    </aside>
  );
};
