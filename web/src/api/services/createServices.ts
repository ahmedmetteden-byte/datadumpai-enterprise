import { isMockApiEnabled } from '@/api/config';
import type { ServiceContainer } from '@/api/services/contracts';
import { HttpAIService, MockAIService } from '@/api/services/AIService';
import {
  HttpBillingService,
  MockBillingService,
} from '@/api/services/BillingService';
import {
  HttpBrandingService,
  MockBrandingService,
} from '@/api/services/BrandingService';
import { HttpHomeService, MockHomeService } from '@/api/services/HomeService';
import {
  HttpIntelligenceService,
  MockIntelligenceService,
} from '@/api/services/IntelligenceService';
import {
  HttpKnowledgeService,
  MockKnowledgeService,
} from '@/api/services/KnowledgeService';
import {
  HttpPublishService,
  MockPublishService,
} from '@/api/services/PublishService';
import {
  HttpReportService,
  MockReportService,
} from '@/api/services/ReportService';
import {
  HttpWorkspaceService,
  MockWorkspaceService,
} from '@/api/services/WorkspaceService';
import { createProfileService } from '@/api/services/ProfileService';

/**
 * Builds the application service container.
 * Uses HTTP services by default. Set VITE_USE_MOCK_API=true only for offline demos.
 */
export function createServices(): ServiceContainer {
  const profile = createProfileService();

  if (isMockApiEnabled()) {
    const workspace = new MockWorkspaceService();
    const knowledge = new MockKnowledgeService();
    const report = new MockReportService();
    const publish = new MockPublishService();
    const ai = new MockAIService();
    const intelligence = new MockIntelligenceService();

    return {
      workspace,
      knowledge,
      report,
      publish,
      ai,
      intelligence,
      home: new MockHomeService(workspace, knowledge, report, ai),
      profile,
      billing: new MockBillingService(),
      branding: new MockBrandingService(),
    };
  }

  return {
    home: new HttpHomeService(),
    workspace: new HttpWorkspaceService(),
    knowledge: new HttpKnowledgeService(),
    report: new HttpReportService(),
    publish: new HttpPublishService(),
    ai: new HttpAIService(),
    intelligence: new HttpIntelligenceService(),
    profile,
    billing: new HttpBillingService(),
    branding: new HttpBrandingService(),
  };
}

/** App-wide singleton — import this from hooks/UI, not individual implementations. */
export const services = createServices();
