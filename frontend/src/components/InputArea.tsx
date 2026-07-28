import React, { useState, useRef, useEffect } from 'react';

interface InputAreaProps {
  onSend: (question: string) => void;
  isLoading: boolean;
  useRag: boolean;
  onRagChange: (checked: boolean) => void;
}

const MAX_QUESTION_CHARS = 2000;

export const InputArea: React.FC<InputAreaProps> = ({
  onSend,
  isLoading,
  useRag,
  onRagChange,
}) => {
  const [question, setQuestion] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + 'px';
    }
  }, [question]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    const trimmed = question.trim();
    if (trimmed && !isLoading) {
      onSend(trimmed);
      setQuestion('');
    }
  };

  return (
    <div className="input-area">
      <div className="input-controls">
        <label className="rag-toggle">
          <input
            type="checkbox"
            checked={useRag}
            onChange={(e) => onRagChange(e.target.checked)}
          />
          <span className="toggle-slider" />
          <span className="toggle-label">知识库检索</span>
        </label>
      </div>
      <div className="input-wrapper">
        <textarea
          ref={textareaRef}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="请输入您的医学问题..."
          maxLength={MAX_QUESTION_CHARS}
          rows={1}
          disabled={isLoading}
        />
        <button
          className={`send-btn ${isLoading ? 'loading' : ''}`}
          onClick={handleSend}
          disabled={isLoading || !question.trim()}
        >
          <svg className="send-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
          </svg>
          <span className="send-text">发送</span>
        </button>
      </div>
      <div className="input-hint">
        <span>按 Enter 发送，Shift + Enter 换行</span>
        <span className={question.length > 1800 ? 'char-count near-limit' : 'char-count'}>
          {question.length}/{MAX_QUESTION_CHARS}
        </span>
      </div>
    </div>
  );
};
