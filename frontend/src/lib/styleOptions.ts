export interface StyleChoices {
  video_format: string;
  visual_style: string;
  color_theme: string;
  accent_color?: string;
  caption_style: string;
  voice_id?: string;
  voice_gender?: 'male' | 'female';
  pace: string;
  music_mood: string;
  people_focus: boolean;
}

export const FORMATS = [
  { value: 'auto', label: 'Auto format', emoji: '✨', desc: 'AI picks the best angle for the topic' },
  { value: 'ugc', label: 'UGC / Selfie', emoji: '🤳', desc: 'First-person creator review or reaction' },
  { value: 'storytelling', label: 'Story', emoji: '📖', desc: 'Narrative arc with a hook and twist' },
  { value: 'explainer', label: 'Explainer', emoji: '💡', desc: 'Problem, mechanism, insight' },
  { value: 'listicle', label: 'Listicle', emoji: '🔢', desc: 'Top 3-5 punchy countdown items' },
  { value: 'cinematic', label: 'Cinematic', emoji: '🎬', desc: 'Aesthetic wide shots and slower lines' },
  { value: 'news', label: 'News Recap', emoji: '📰', desc: 'What happened, why it matters' },
  { value: 'motivational', label: 'Motivation', emoji: '🔥', desc: 'Rising intensity and inspiration' },
  { value: 'pov', label: 'POV / Relatable', emoji: '👀', desc: 'Everyday moments viewers relate to' },
];

export const VISUAL_STYLES = [
  { value: 'real', label: 'Realistic footage', desc: 'Real vertical video clips and photos' },
  { value: 'animated', label: 'Animated / 2D', desc: 'Procedural diagrams and vector visuals' },
  { value: 'mixed', label: 'Mixed media', desc: 'Blend of real footage and graphics' },
];

export const THEMES = [
  { value: 'vibrant', label: 'Vibrant pop', from: '#18203a', to: '#583c8c', highlight: '#ffe500' },
  { value: 'warm', label: 'Warm sunset', from: '#3c1810', to: '#aa5028', highlight: '#ff9f1c' },
  { value: 'cool', label: 'Cool tech', from: '#081830', to: '#145a82', highlight: '#3dd9ff' },
  { value: 'neon', label: 'Neon night', from: '#140628', to: '#5a1478', highlight: '#ff3cac' },
  { value: 'luxury', label: 'Luxury gold', from: '#12100e', to: '#3c301e', highlight: '#d4af37' },
  { value: 'minimal', label: 'Clean minimal', from: '#1e1e22', to: '#46464e', highlight: '#ffffff' },
  { value: 'mono', label: 'Black & white', from: '#0a0a0a', to: '#3c3c3c', highlight: '#ffffff' },
];

export const CAPTION_STYLES = [
  { value: 'bold', label: 'Bold pop', desc: 'Uppercase kinetic word highlight' },
  { value: 'clean', label: 'Clean subtitle', desc: 'Sentence case understated look' },
  { value: 'boxed', label: 'News box', desc: 'Dark solid pill behind words' },
];

export const PACES = [
  { value: 'fast', label: 'Fast (1.7s shots — TikTok / Reels pace)' },
  { value: 'normal', label: 'Normal (2.3s shots — balanced flow)' },
  { value: 'calm', label: 'Calm (3.0s shots — explainer pace)' },
];

export const MUSIC_MOODS = [
  { value: 'cinematic', label: 'Cinematic' },
  { value: 'upbeat', label: 'Upbeat' },
  { value: 'chill', label: 'Chill' },
  { value: 'inspiring', label: 'Inspiring' },
  { value: 'dramatic', label: 'Dramatic' },
  { value: 'lofi', label: 'Lo-Fi' },
  { value: 'corporate', label: 'Corporate' },
  { value: 'emotional', label: 'Emotional' },
  { value: 'none', label: 'No background music' },
];

export const DEFAULT_STYLE: StyleChoices = {
  video_format: 'auto',
  visual_style: 'real',
  color_theme: 'vibrant',
  caption_style: 'bold',
  pace: 'fast',
  music_mood: 'cinematic',
  people_focus: true,
};

const STORAGE_KEY = 'qreate_style_choices';

export function loadStyle(): StyleChoices {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      return { ...DEFAULT_STYLE, ...jsonParseSafe(raw) };
    }
  } catch {
    // ignore
  }
  return { ...DEFAULT_STYLE };
}

export function saveStyle(style: StyleChoices): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(style));
  } catch {
    // ignore
  }
}

function jsonParseSafe(raw: string): any {
  try {
    return JSON.parse(raw);
  } catch {
    return {};
  }
}
