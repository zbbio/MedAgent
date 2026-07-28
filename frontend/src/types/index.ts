// API 请求和响应类型

export interface AskRequest {
  question: string;
  history: ChatMessage[];
  use_rag: boolean;
}

export interface AskResponse {
  answer: string;
  thinking: string;
  citations: Citation[];
  route: string;
  timings: Record<string, number>;
  request_id: string;
}

export interface Citation {
  marker: string;
  title: string;
  content: string;
  source: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface SystemHealth {
  status: string;
  version: string;
}

export interface SystemStats {
  total_documents: number;
  bm25_chunks: number;
  textbook_sources: number;
  vector_documents: number;
  knowledge_mode: 'local_and_pubmed' | 'pubmed_only';
  provider: string;
  model: string;
  retrievers: Record<string, string>;
  generation: {
    active: number;
    pending: number;
    max_active: number;
    max_pending: number;
  };
  metrics: Record<string, number>;
}

export interface AuthStatus {
  authenticated: boolean;
}

// 组件 Props 类型

export interface MessageProps {
  message: ChatMessage;
  citations?: Citation[];
  thinking?: string;
  question?: string;
}

export interface CitationPanelProps {
  citations: Citation[];
  isOpen: boolean;
  onToggle: () => void;
}

export interface StatusBarProps {
  status: 'ready' | 'processing' | 'error';
  statusText: string;
}
