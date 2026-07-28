import { useEffect, useRef, useState } from 'react';
import { CitationPanel } from './components/CitationPanel';
import { InputArea } from './components/InputArea';
import { Message } from './components/Message';
import { HealthContent, Modal, StatsContent } from './components/Modal';
import { StatusBar } from './components/StatusBar';
import {
  ApiError,
  askQuestion,
  getAuthStatus,
  getHealth,
  getStats,
  login,
  logout,
} from './api/client';
import type { ChatMessage, Citation, SystemHealth, SystemStats } from './types';
import './styles/global.css';

type RichMessage = ChatMessage & { thinking?: string; citations?: Citation[] };

function App() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [loginPassword, setLoginPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);
  const [messages, setMessages] = useState<RichMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState<'ready' | 'processing' | 'error'>('ready');
  const [statusText, setStatusText] = useState('系统就绪');
  const [useRag, setUseRag] = useState(true);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [citationPanelOpen, setCitationPanelOpen] = useState(true);
  const [statsModalOpen, setStatsModalOpen] = useState(false);
  const [healthModalOpen, setHealthModalOpen] = useState(false);
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [healthError, setHealthError] = useState<string>();
  const [showWelcome, setShowWelcome] = useState(true);
  const chatHistory = useRef<ChatMessage[]>([]);

  useEffect(() => {
    void Promise.allSettled([checkHealth(), checkAuthentication()]);
  }, []);

  const checkAuthentication = async () => {
    try {
      const result = await getAuthStatus();
      setAuthenticated(result.authenticated);
      if (result.authenticated) {
        setStats(await getStats().catch(() => null));
      }
    } catch {
      setAuthenticated(false);
      setLoginError('无法连接到服务，请确认后端已经启动');
    }
  };

  const checkHealth = async () => {
    try {
      const data = await getHealth();
      setHealth(data);
      setHealthError(undefined);
      setStatus('ready');
      setStatusText('系统就绪');
    } catch {
      setHealthError('无法连接到服务器');
      setStatus('error');
      setStatusText('无法连接');
    }
  };

  const handleLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!loginPassword || loginLoading) return;
    setLoginLoading(true);
    setLoginError('');
    try {
      await login(loginPassword);
      setAuthenticated(true);
      setLoginPassword('');
      setStats(await getStats().catch(() => null));
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : '登录失败');
    } finally {
      setLoginLoading(false);
    }
  };

  const resetConversation = () => {
    chatHistory.current = [];
    setMessages([]);
    setCitations([]);
    setShowWelcome(true);
  };

  const handleLogout = async () => {
    await logout().catch(() => undefined);
    resetConversation();
    setAuthenticated(false);
  };

  const handleSend = async (question: string) => {
    if (!question.trim() || isLoading) return;
    setShowWelcome(false);
    const userMessage: ChatMessage = { role: 'user', content: question };
    setMessages((previous) => [...previous, userMessage]);
    setIsLoading(true);
    setStatus('processing');
    setStatusText('正在分析...');

    try {
      const response = await askQuestion({
        question,
        history: chatHistory.current.slice(-10),
        use_rag: useRag,
      });
      const assistantMessage: RichMessage = {
        role: 'assistant',
        content: response.answer,
        thinking: response.thinking,
        citations: response.citations,
      };
      setMessages((previous) => [...previous, assistantMessage]);
      setCitations(response.citations || []);
      const historyAssistant: ChatMessage = {
        role: 'assistant',
        content: response.answer,
      };
      chatHistory.current = [
        ...chatHistory.current,
        userMessage,
        historyAssistant,
      ].slice(-10);
      setStatus('ready');
      setStatusText('系统就绪');
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setAuthenticated(false);
      }
      const requestId = error instanceof ApiError && error.requestId
        ? `（请求号：${error.requestId}）`
        : '';
      setMessages((previous) => [...previous, {
        role: 'assistant',
        content: `${error instanceof Error ? error.message : '请求失败'}${requestId}`,
      }]);
      setStatus('error');
      setStatusText('请求失败');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStatsClick = async () => {
    setStatsModalOpen(true);
    setStats(null);
    try {
      setStats(await getStats());
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) setAuthenticated(false);
    }
  };

  const handleHealthClick = async () => {
    setHealthModalOpen(true);
    setHealth(null);
    setHealthError(undefined);
    await checkHealth();
  };

  if (authenticated === null) {
    return (
      <div className="auth-shell">
        <div className="auth-card auth-loading">
          <div className="loading-spinner" />
          <p>正在连接 MedAgent…</p>
        </div>
      </div>
    );
  }

  if (!authenticated) {
    return (
      <div className="auth-shell">
        <div className="auth-card">
          <div className="auth-pulse" aria-hidden="true">
            <span />
          </div>
          <div className="auth-mark">M+</div>
          <p className="auth-eyebrow">PRIVATE MEDICAL RAG</p>
          <h1>进入 MedAgent</h1>
          <p className="auth-copy">这是受控演示环境。输入访问密码后开始医学知识库问答。</p>
          <form onSubmit={handleLogin}>
            <label htmlFor="access-password">访问密码</label>
            <input
              id="access-password"
              type="password"
              value={loginPassword}
              onChange={(event) => setLoginPassword(event.target.value)}
              placeholder="请输入访问密码"
              autoComplete="current-password"
              autoFocus
            />
            {loginError && <p className="auth-error" role="alert">{loginError}</p>}
            <button type="submit" disabled={!loginPassword || loginLoading}>
              {loginLoading ? '正在验证…' : '进入助手'}
            </button>
          </form>
          <p className="auth-note">回答仅供参考，不能替代医生诊断。</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <StatusBar
        status={status}
        statusText={statusText}
        onStatsClick={handleStatsClick}
        onHealthClick={handleHealthClick}
        onLogout={handleLogout}
      />
      <div className="main-content">
        <div className="chat-panel">
          <div className="chat-area">
            {showWelcome ? (
              <div className="welcome-screen">
                <div className="welcome-icon">🩺</div>
                <h2>欢迎使用 MedAgent</h2>
                <p>基于 RAG 技术的智能医学助手</p>
                {stats?.knowledge_mode === 'pubmed_only' && (
                  <p className="welcome-mode-notice">
                    当前部署未安装本地知识库，将使用模型与 PubMed 实时检索。
                  </p>
                )}
                <div className="quick-actions">
                  <button className="quick-btn" onClick={() => handleSend('高血压的诊断标准是什么？')}>
                    <span className="quick-icon">📋</span><span>诊断标准</span>
                  </button>
                  <button className="quick-btn" onClick={() => handleSend('糖尿病酮症酸中毒如何治疗？')}>
                    <span className="quick-icon">💊</span><span>治疗方案</span>
                  </button>
                  <button className="quick-btn" onClick={() => handleSend('心电图ST段抬高意味着什么？')}>
                    <span className="quick-icon">🫀</span><span>检查解读</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="messages-container">
                {messages.map((message, index) => (
                  <Message
                    key={index}
                    role={message.role}
                    content={message.content}
                    thinking={message.thinking}
                    citations={message.citations}
                    question={message.role === 'assistant' ? messages[index - 1]?.content : undefined}
                  />
                ))}
              </div>
            )}
          </div>
          <InputArea
            onSend={handleSend}
            isLoading={isLoading}
            useRag={useRag}
            onRagChange={setUseRag}
          />
        </div>
        <CitationPanel
          citations={citations}
          isOpen={citationPanelOpen}
          onToggle={() => setCitationPanelOpen(!citationPanelOpen)}
        />
      </div>
      <Modal isOpen={statsModalOpen} onClose={() => setStatsModalOpen(false)} title="系统统计">
        <StatsContent stats={stats} />
      </Modal>
      <Modal isOpen={healthModalOpen} onClose={() => setHealthModalOpen(false)} title="系统状态">
        <HealthContent health={health} error={healthError} />
      </Modal>
    </div>
  );
}

export default App;
