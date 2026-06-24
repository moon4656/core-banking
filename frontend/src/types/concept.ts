export type Concept = {
  concept_id: string;
  name: string;
  description: string | null;
  domain: string | null;
  is_active: boolean;
};

export type ConceptDetail = Concept & {
  aliases: string[];
};

export type AliasItem = {
  id: number;
  concept_id: string;
  alias: string;
  language: string;
};

export type RelationItem = {
  id: number;
  source_concept_id: string;
  target_concept_id: string;
  relation_type: string;
  weight: number;
};

export type AgentSummary = {
  agent_id: string;
  name: string;
  agent_type: string;
  description: string | null;
  capabilities: unknown[] | null;
  is_active: boolean;
};

export type ApiSummary = {
  api_id: string;
  name: string;
  endpoint: string;
  method: string;
  description: string | null;
  is_active: boolean;
};

export type AgentMappingItem = {
  id: number;
  agent_id: string;
  concept_id: string;
  priority: number;
};

export type ConceptApiMappingItem = {
  id: number;
  concept_id: string;
  api_id: string;
  priority: number;
};
