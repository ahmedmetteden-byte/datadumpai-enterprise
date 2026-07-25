import type { IsoDateTime } from './api';

export type ReasoningMode =
  | 'ask'
  | 'summarise'
  | 'compare'
  | 'analyse'
  | 'generate_report'
  | 'recommend';

export type IntelligenceSourceKind =
  | 'document'
  | 'meeting'
  | 'report'
  | 'knowledge'
  | 'web';

export interface IntelligenceSource {
  id: string;
  kind: IntelligenceSourceKind;
  title: string;
  location?: string;
  excerpt?: string;
  previewUrl?: string;
}

export interface StudioReadiness {
  ready: boolean;
  status: string;
  documentCount: number;
  reportCount: number;
  canAsk: boolean;
  webResearchAvailable: boolean;
}

export interface IntelligenceConversationSummary {
  id: string;
  workspaceId: string;
  title: string;
  pinned: boolean;
  updatedAt: IsoDateTime;
  preview: string;
}

export interface IntelligenceMessage {
  id: string;
  conversationId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  /** Structured assistant payload — present when role === 'assistant' and complete */
  answer?: string;
  evidence?: string;
  confidence?: number;
  followUps?: string[];
  sources?: IntelligenceSource[];
  notice?: string | null;
  status: 'pending' | 'streaming' | 'complete' | 'error';
  createdAt: IsoDateTime;
  mode?: ReasoningMode;
}

export interface IntelligenceConversation {
  id: string;
  workspaceId: string;
  title: string;
  pinned: boolean;
  updatedAt: IsoDateTime;
  messages: IntelligenceMessage[];
}

export interface SendMessageInput {
  content: string;
  mode: ReasoningMode;
}

export interface StartConversationInput {
  title?: string;
  initialMessage?: string;
  mode?: ReasoningMode;
}
