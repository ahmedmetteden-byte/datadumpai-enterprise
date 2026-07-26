/**
 * In-memory conversation store for MockIntelligenceService.
 */

import type {
  IntelligenceConversation,
  IntelligenceConversationSummary,
  IntelligenceMessage,
  IntelligenceSource,
  ReasoningMode,
  SendMessageInput,
  StartConversationInput,
  StudioReadiness,
} from '@/types/intelligence';
import { ApiError } from '@/api/client';

const SUGGESTED = [
  'What are the key risks in this workspace?',
  'Summarise the latest uploaded documents',
  'Which actions are still unresolved?',
  'Compare themes across the indexed sources',
  'Recommend next steps for leadership',
] as const;

const MOCK_SOURCES: IntelligenceSource[] = [];

function nowIso() {
  return new Date().toISOString();
}

function id(prefix: string) {
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;
}

function buildAssistantReply(
  conversationId: string,
  question: string,
  mode: ReasoningMode,
): IntelligenceMessage {
  const modeLead: Record<ReasoningMode, string> = {
    ask: 'Based on the active workspace corpus',
    summarise: 'Here is a concise summary grounded in workspace sources',
    compare: 'Comparing the most relevant workspace artefacts',
    analyse: 'Analysis of the available workspace evidence',
    generate_report: 'A report outline grounded in current workspace knowledge',
    recommend: 'Recommended next steps from workspace evidence',
  };

  return {
    id: id('msg'),
    conversationId,
    role: 'assistant',
    content: '',
    answer: `${modeLead[mode]}: ${question.trim() || 'your question'}.

Connect the live API and index documents to retrieve grounded evidence, citations, and linked sources.`,
    evidence:
      'No indexed evidence is available in mock mode. Use the live API for RAG answers.',
    confidence: 0.2,
    followUps: [
      'Upload documents to the Library',
      'Re-index existing documents',
      'Ask again after indexing shows Done',
    ],
    sources: MOCK_SOURCES,
    citations: [],
    linkedDocuments: [],
    notice: null,
    status: 'complete',
    createdAt: nowIso(),
    mode,
  };
}

/** workspaceId → conversations */
const store = new Map<string, IntelligenceConversation[]>();

function seedWorkspace(workspaceId: string): IntelligenceConversation[] {
  if (store.has(workspaceId)) {
    return store.get(workspaceId)!;
  }
  const list: IntelligenceConversation[] = [];
  store.set(workspaceId, list);
  return list;
}

function requireConversation(
  workspaceId: string,
  conversationId: string,
): IntelligenceConversation {
  const list = seedWorkspace(workspaceId);
  const match = list.find((item) => item.id === conversationId);
  if (!match) {
    throw new ApiError('Conversation not found', 404, {
      detail: 'Conversation not found',
      code: 'conversation_not_found',
    });
  }
  return match;
}

export function mockCheckReadiness(_workspaceId: string): StudioReadiness {
  void _workspaceId;
  return {
    ready: true,
    status: 'Upload and index documents to enable asking.',
    documentCount: 0,
    reportCount: 0,
    canAsk: false,
    webResearchAvailable: false,
  };
}

export function mockListConversations(
  workspaceId: string,
): IntelligenceConversationSummary[] {
  return seedWorkspace(workspaceId)
    .slice()
    .sort((a, b) => {
      if (a.pinned !== b.pinned) return a.pinned ? -1 : 1;
      return b.updatedAt.localeCompare(a.updatedAt);
    })
    .map((item) => ({
      id: item.id,
      workspaceId: item.workspaceId,
      title: item.title,
      pinned: item.pinned,
      updatedAt: item.updatedAt,
      preview:
        item.messages.filter((m) => m.role === 'user').at(-1)?.content ??
        item.title,
    }));
}

export function mockGetConversation(
  workspaceId: string,
  conversationId: string,
): IntelligenceConversation {
  const conv = requireConversation(workspaceId, conversationId);
  return {
    ...conv,
    messages: conv.messages.map((message) => ({
      ...message,
      sources: message.sources?.map((source) => ({ ...source })),
      followUps: message.followUps ? [...message.followUps] : undefined,
    })),
  };
}

export function mockStartConversation(
  workspaceId: string,
  input: StartConversationInput = {},
): IntelligenceConversation {
  const list = seedWorkspace(workspaceId);
  const conversationId = id('conv');
  const title =
    input.title?.trim() ||
    input.initialMessage?.trim().slice(0, 48) ||
    'New conversation';

  const conversation: IntelligenceConversation = {
    id: conversationId,
    workspaceId,
    title,
    pinned: false,
    updatedAt: nowIso(),
    messages: [],
  };

  if (input.initialMessage?.trim()) {
    const mode = input.mode ?? 'ask';
    conversation.messages.push({
      id: id('msg'),
      conversationId,
      role: 'user',
      content: input.initialMessage.trim(),
      status: 'complete',
      createdAt: nowIso(),
      mode,
    });
    conversation.messages.push(
      buildAssistantReply(conversationId, input.initialMessage, mode),
    );
  }

  list.unshift(conversation);
  store.set(workspaceId, list);
  return mockGetConversation(workspaceId, conversationId);
}

export function mockSendMessage(
  workspaceId: string,
  conversationId: string,
  input: SendMessageInput,
): IntelligenceConversation {
  const conversation = requireConversation(workspaceId, conversationId);
  const userMessage: IntelligenceMessage = {
    id: id('msg'),
    conversationId,
    role: 'user',
    content: input.content.trim(),
    status: 'complete',
    createdAt: nowIso(),
    mode: input.mode,
  };
  conversation.messages.push(userMessage);
  conversation.messages.push(
    buildAssistantReply(conversationId, input.content, input.mode),
  );
  if (conversation.title === 'New conversation') {
    conversation.title = input.content.trim().slice(0, 48) || conversation.title;
  }
  conversation.updatedAt = nowIso();
  return mockGetConversation(workspaceId, conversationId);
}

export function mockRenameConversation(
  workspaceId: string,
  conversationId: string,
  title: string,
): IntelligenceConversationSummary {
  const conversation = requireConversation(workspaceId, conversationId);
  conversation.title = title.trim() || conversation.title;
  conversation.updatedAt = nowIso();
  return mockListConversations(workspaceId).find((item) => item.id === conversationId)!;
}

export function mockDeleteConversation(
  workspaceId: string,
  conversationId: string,
): void {
  const list = seedWorkspace(workspaceId);
  store.set(
    workspaceId,
    list.filter((item) => item.id !== conversationId),
  );
}

export function mockTogglePin(
  workspaceId: string,
  conversationId: string,
): IntelligenceConversationSummary {
  const conversation = requireConversation(workspaceId, conversationId);
  conversation.pinned = !conversation.pinned;
  conversation.updatedAt = nowIso();
  return mockListConversations(workspaceId).find((item) => item.id === conversationId)!;
}

export function mockSuggestedPrompts(): string[] {
  return [...SUGGESTED];
}

export function clearIntelligenceStore(): void {
  store.clear();
}
