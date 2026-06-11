// ── C4: FAQ Resolver ──────────────────────────────────────────────────────────
// Single Responsibility: FAQ key normalization and fuzzy lookup only.
// Open/Closed: extend FAQ_MAP in VoiceService without touching this logic.

import { FAQ_MAP } from '../services/VoiceService';

export const normalizeFaqKey = (text: string): string =>
  text.toLowerCase().replace(/[^a-z0-9 ]/g, '').trim();

export const findFaqHit = (key: string): string | undefined => {
  const hit = FAQ_MAP[key] ?? Object.entries(FAQ_MAP).find(
    ([k]) => key.includes(k) || k.includes(key)
  )?.[1];
  return hit === '__BYPASS_FAQ__' ? undefined : hit;
};
