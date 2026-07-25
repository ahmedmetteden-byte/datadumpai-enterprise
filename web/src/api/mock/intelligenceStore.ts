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
  "Summarise this month's meetings",
  'Compare Q2 and Q3 reports',
  'Generate board recommendations',
  'Identify unresolved actions',
  'What decisions were made last month?',
] as const;

const MOCK_SOURCES: IntelligenceSource[] = [
  {
    id: 'src_doc_1',
    kind: 'document',
    title: 'Q2 Operating Pack.pdf',
    location: '/documents/q2-operating-pack.pdf',
    excerpt: 'Gross margin in EMEA declined 1.8pts versus prior quarter.',
    previewUrl: '/documents/q2-operating-pack.pdf',
  },
  {
    id: 'src_mtg_1',
    kind: 'meeting',
    title: 'Executive Sync — 12 Jul',
    location: '/meetings/exec-sync-2026-07-12',
    excerpt: 'Action: assign owner for supplier concentration risk by Friday.',
    previewUrl: '/meetings/exec-sync-2026-07-12',
  },
  {
    id: 'src_rpt_1',
    kind: 'report',
    title: 'Q2 Operating Review',
    location: '/reports/q2-operating-review',
    excerpt: 'Board narrative recommends refreshing KPI pack before distribution.',
    previewUrl: '/reports/q2-operating-review',
  },
  {
    id: 'src_rpt_2',
    kind: 'report',
    title: 'Customer Retention Brief',
    location: '/reports/retention-brief',
    excerpt: 'Enterprise cohort retention improved 3pts QoQ.',
    previewUrl: '/reports/retention-brief',
  },
];

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

EMEA gross margin pressure remains the clearest signal (−1.8pts QoQ), while enterprise retention improved. Two reports still await executive review, and one supplier action from the 12 Jul sync lacks an owner.`,
    evidence:
      'Operating pack margin tables, executive sync actions, and the Q2 Operating Review narrative align on margin pressure and open ownership gaps. Retention brief corroborates cohort improvement.',
    confidence: 0.86,
    followUps: [
      'Which suppliers drive concentration risk?',
      'Draft talking points for the board pack',
      'List unresolved actions with owners',
    ],
    sources: MOCK_SOURCES,
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

  const convId = `conv_seed_${workspaceId}`;
  const seeded: IntelligenceConversation = {
    id: convId,
    workspaceId,
    title: 'EMEA margin pressure',
    pinned: true,
    updatedAt: '2026-07-24T16:40:00Z',
    messages: [
      {
        id: 'msg_seed_u',
        conversationId: convId,
        role: 'user',
        content: 'What is driving EMEA margin pressure this quarter?',
        status: 'complete',
        createdAt: '2026-07-24T16:38:00Z',
        mode: 'ask',
      },
      {
        id: 'msg_seed_a',
        conversationId: convId,
        role: 'assistant',
        content: '',
        answer:
          'EMEA gross margin declined 1.8pts versus the prior quarter, concentrated in product mix shifts and a higher share of discount-led deals. Retention improved in enterprise cohorts, so the pressure is not broad demand destruction.',
        evidence:
          'Q2 Operating Pack margin bridges and the Operating Review both cite mix and discounting. The July executive sync logged a follow-up on supplier concentration that remains unowned.',
        confidence: 0.88,
        followUps: [
          'Break down margin by product line',
          'Show discount trends by segment',
          'Who owns the supplier action?',
        ],
        sources: MOCK_SOURCES.slice(0, 3),
        notice: null,
        status: 'complete',
        createdAt: '2026-07-24T16:39:00Z',
        mode: 'ask',
      },
    ],
  };

  const second: IntelligenceConversation = {
    id: `conv_seed2_${workspaceId}`,
    workspaceId,
    title: 'Board recommendations',
    pinned: false,
    updatedAt: '2026-07-23T11:20:00Z',
    messages: [
      {
        id: 'msg_seed2_u',
        conversationId: `conv_seed2_${workspaceId}`,
        role: 'user',
        content: 'Generate board recommendations from this workspace.',
        status: 'complete',
        createdAt: '2026-07-23T11:18:00Z',
        mode: 'recommend',
      },
      buildAssistantReply(
        `conv_seed2_${workspaceId}`,
        'Generate board recommendations from this workspace.',
        'recommend',
      ),
    ],
  };

  const list = [seeded, second];
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
    status: 'AI ready — 128 documents indexed',
    documentCount: 128,
    reportCount: 14,
    canAsk: true,
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
