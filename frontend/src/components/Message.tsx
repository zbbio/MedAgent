import { useState } from 'react';
import type { Citation } from '../types';

interface MessageProps {
  role: 'user' | 'assistant';
  content: string;
  thinking?: string;
  citations?: Citation[];
  question?: string;
  isError?: boolean;
}

// 急症关键词
const emergencyKeywords = [
  '胸痛', '呼吸困难', '昏迷', '抽搐', '大出血', '严重', '急性', '突然',
  'DKA', '糖尿病酮症酸中毒', '酮症酸中毒',
  'ST段抬高', 'ST segment elevation', 'STEMI',
  '心梗', '心肌梗死', '急性心肌梗死',
  '休克', '心脏骤停', '猝死',
  '脑出血', '脑梗', '中风', '卒中',
  '窒息', '过敏性休克', '严重过敏',
];

const isEmergency = (question: string): boolean => {
  return emergencyKeywords.some(kw =>
    question.toLowerCase().includes(kw.toLowerCase())
  );
};

const sanitizeContent = (text: string): string => {
  if (!text) return '';
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');
};

const truncateText = (text: string, maxLength: number): string => {
  if (!text || text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};

export const Message: React.FC<MessageProps> = ({
  role,
  content,
  thinking,
  citations,
  question,
  isError = false,
}) => {
  const [thinkingExpanded, setThinkingExpanded] = useState(false);

  return (
    <div className={`message ${role}`}>
      <div className="message-avatar">
        {role === 'user' ? '👤' : '🩺'}
      </div>
      <div className="message-body">
        <div
          className="message-content"
          style={isError ? {
            background: '#fef2f2',
            borderColor: '#fecaca',
            color: '#991b1b',
          } : undefined}
          dangerouslySetInnerHTML={{ __html: sanitizeContent(content) }}
        />

        {/* 医学安全提示 */}
        {role === 'assistant' && question && !isError && (
          <div className={`medical-alert ${isEmergency(question) ? 'emergency' : 'info'}`}>
            <span className="alert-icon">
              {isEmergency(question) ? '🚨' : 'ℹ️'}
            </span>
            <span className="alert-text">
              {isEmergency(question) ? (
                <><strong>紧急提醒：</strong>如遇紧急情况，请立即拨打120或前往急诊科就诊。本回答仅供参考，不能替代专业医疗诊断。</>
              ) : (
                '本回答基于医学文献生成，仅供参考。如有疑问，请咨询专业医生。'
              )}
            </span>
          </div>
        )}

        {/* 检索依据摘要 */}
        {thinking && role === 'assistant' && (
          <div className="thinking-collapsed">
            <div
              className={`thinking-header ${thinkingExpanded ? 'expanded' : ''}`}
              onClick={() => setThinkingExpanded(!thinkingExpanded)}
            >
              <span className="thinking-icon">📋</span>
              <span className="thinking-title">检索依据摘要</span>
              <span className="thinking-toggle">▼</span>
            </div>
            <div
              className="thinking-content"
              style={{ display: thinkingExpanded ? 'block' : 'none' }}
              dangerouslySetInnerHTML={{ __html: sanitizeContent(truncateText(thinking, 300)) }}
            />
          </div>
        )}

        {/* 引用标签 */}
        {citations && citations.length > 0 && role === 'assistant' && (
          <div className="message-citations">
            {citations.slice(0, 5).map((cite, index) => (
              <span key={index} className="citation-tag">
                [{index + 1}] {truncateText(cite.title, 20)}
              </span>
            ))}
            {citations.length > 5 && (
              <span className="citation-tag more">
                还有 {citations.length - 5} 条
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
