// ── C4: FAQ Resolver ──────────────────────────────────────────────────────────
// Single Responsibility: FAQ key normalization and fuzzy lookup only.
// FAQ data is fetched from backend — no client-side hardcoding.

import VoiceService from '../services/VoiceService';

let _cache: Record<string, string> | null = null;

export const loadFaqMap = async (): Promise<Record<string, string>> => {
  if (!_cache) _cache = await VoiceService.fetchFaq();
  return _cache;
};

export const normalizeFaqKey = (text: string): string =>
  text.toLowerCase().replace(/[^a-z0-9 ]/g, '').trim();

export const findFaqHit = (key: string, map: Record<string, string>): string | undefined => {
  const hit = map[key] ?? Object.entries(map).find(
    ([k]) => key.includes(k) || k.includes(key)
  )?.[1];
  return hit === '__BYPASS_FAQ__' ? undefined : hit;
};
