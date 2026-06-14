export interface AgentConfig {
  agent_id: string;
  name: string;
  model: string;
  temperature: number;
  max_tokens: number;
  system_prompt: string;
}

export interface Agent {
  id: string;
  name: string;
  config: AgentConfig;
  status: 'idle' | 'running' | 'paused' | 'error';
  is_active: boolean;
  created_at: string;
  last_activity: string;
  memory_size: number;
  metadata: Record<string, string>;
}

export interface ChatMessage {
  id: string;
  agent_id: string;
  role: 'user' | 'ai' | 'system';
  content: string;
  timestamp: string;
}

export interface TokenStat {
  agent_id: string;
  agent_name: string;
  tokens_used: number;
  failure_rate: number;
}

export const AVAILABLE_MODELS = [
  'llama-3.3-70b-versatile',
  'llama-3.3-70b-specdec',
  'llama-3.1-70b-versatile',
  'gemma2-9b-it',
  'gpt-4o',
  'gpt-4o-mini',
  'claude-3-5-sonnet',
  'claude-3-haiku',
] as const;
