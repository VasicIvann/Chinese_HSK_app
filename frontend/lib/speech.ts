"use client";

/**
 * Mandarin pronunciation with the browser's own text-to-speech (Web Speech API).
 *
 * No backend, no API key: the device's Chinese voice reads the text. Quality and
 * availability depend on the device (iOS/Android ship a Chinese voice; desktop
 * Windows may need the Chinese language pack). Local voices are preferred because
 * they work offline and do not depend on Google servers (blocked in mainland China).
 */

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";

type VoiceLike = Pick<SpeechSynthesisVoice, "lang" | "localService" | "voiceURI" | "name">;

const normalizeLang = (lang: string) => lang.replace("_", "-").toLowerCase();

/** Best Mandarin voice: zh-CN first, then other zh/cmn variants; local before network. */
export function pickChineseVoice<T extends VoiceLike>(voices: readonly T[]): T | null {
  const score = (v: T): number => {
    const lang = normalizeLang(v.lang);
    let s: number;
    if (lang === "zh-cn" || lang === "cmn-cn" || lang === "cmn-hans-cn" || lang === "zh-hans-cn") s = 30;
    else if (lang === "zh" || lang === "cmn" || lang.startsWith("zh-hans")) s = 20;
    else if (lang === "zh-tw" || lang.startsWith("zh-hant") || lang.startsWith("cmn-")) s = 10;
    else if (lang.startsWith("zh-")) s = 5; // e.g. zh-HK (Cantonese): last resort
    else return -1;
    return s + (v.localService ? 2 : 0);
  };
  let best: T | null = null;
  let bestScore = -1;
  for (const v of voices) {
    const s = score(v);
    if (s > bestScore) {
      best = v;
      bestScore = s;
    }
  }
  return best;
}

const isSupported = () =>
  typeof window !== "undefined" &&
  "speechSynthesis" in window &&
  typeof window.SpeechSynthesisUtterance === "function";

/** Voice snapshot: "" = voices not loaded yet, "none" = loaded but no Chinese voice. */
function voiceSnapshot(): string {
  if (!isSupported()) return "none";
  const voices = window.speechSynthesis.getVoices();
  if (voices.length === 0) return "";
  return pickChineseVoice(voices)?.voiceURI ?? "none";
}

function subscribeVoices(onChange: () => void) {
  if (!isSupported()) return () => {};
  const synth = window.speechSynthesis;
  synth.addEventListener?.("voiceschanged", onChange);
  return () => synth.removeEventListener?.("voiceschanged", onChange);
}

export type SpeakOptions = {
  /** Identifies what is being read, so a button can show its own "playing" state. */
  key?: string;
  /** 1 = normal speed. Single words read a bit slower to hear the tones. */
  rate?: number;
};

export function useChineseSpeech() {
  const supported = useSyncExternalStore(
    () => () => {},
    isSupported,
    () => false
  );
  const voiceUri = useSyncExternalStore(subscribeVoices, voiceSnapshot, () => "");
  const [speakingKey, setSpeakingKey] = useState<string | null>(null);
  const current = useRef<SpeechSynthesisUtterance | null>(null);

  // Stop any audio when the component using the hook goes away (e.g. next card).
  useEffect(
    () => () => {
      if (isSupported() && current.current) window.speechSynthesis.cancel();
    },
    []
  );

  /** Read `text` aloud. Returns an error message to show, or null when playback started. */
  const speak = useCallback(
    (text: string, { key = text, rate = 0.85 }: SpeakOptions = {}): string | null => {
      if (!isSupported()) {
        return "Ton navigateur ne sait pas lire l'audio. Essaie Chrome, Safari ou Edge.";
      }
      if (voiceUri === "none") {
        return "Aucune voix chinoise sur cet appareil. Ajoute la langue chinoise dans les réglages du système.";
      }
      const synth = window.speechSynthesis;
      synth.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "zh-CN";
      utterance.rate = rate;
      const voice = voiceUri ? synth.getVoices().find((v) => v.voiceURI === voiceUri) : undefined;
      if (voice) {
        utterance.voice = voice;
        utterance.lang = voice.lang;
      }
      const done = () => {
        if (current.current === utterance) {
          current.current = null;
          setSpeakingKey(null);
        }
      };
      utterance.onend = done;
      utterance.onerror = done;
      current.current = utterance;
      setSpeakingKey(key);
      synth.speak(utterance);
      return null;
    },
    [voiceUri]
  );

  const stop = useCallback(() => {
    if (isSupported()) window.speechSynthesis.cancel();
    current.current = null;
    setSpeakingKey(null);
  }, []);

  return { supported, speak, stop, speakingKey };
}

// --------------------------------------------------------------------------- scripts (exercises)

export type ScriptLine = { s: "m" | "f" | "n"; t: string };

/** Pitch per speaker when the device has a single Chinese voice. */
const PITCH = { m: 0.75, f: 1.2, n: 1 } as const;

/** Two different Chinese voices (for 男 / 女) when the device has several. */
export function pickDialogueVoices<T extends VoiceLike>(voices: readonly T[]): { m: T | null; f: T | null } {
  const main = pickChineseVoice(voices);
  if (!main) return { m: null, f: null };
  const zh = voices.filter((v) => normalizeLang(v.lang) === normalizeLang(main.lang));
  const male = zh.find((v) => /male|man|男|yunxi|yunyang|kangkang|li-mu|liang/i.test(v.name) && !/female/i.test(v.name));
  const female = zh.find((v) => /female|woman|女|xiaoxiao|huihui|yaoyao|ting|mei|xiaoyi/i.test(v.name));
  const other = zh.find((v) => v.voiceURI !== main.voiceURI);
  if (male && female) return { m: male, f: female };
  if (male) return { m: male, f: main.voiceURI === male.voiceURI ? other ?? main : main };
  if (female) return { m: main.voiceURI === female.voiceURI ? other ?? main : main, f: female };
  return { m: main, f: other ?? main };
}

/**
 * Plays an exercise recording: each turn with its speaker's voice, the whole
 * script `times` times (the HSK papers play everything twice), short pauses
 * between turns and a longer one between repetitions.
 */
export function useScriptPlayer() {
  const { supported } = useChineseSpeech();
  const [playing, setPlaying] = useState(false);
  const run = useRef(0);

  useEffect(
    () => () => {
      run.current += 1;
      if (isSupported()) window.speechSynthesis.cancel();
    },
    []
  );

  const stop = useCallback(() => {
    run.current += 1;
    if (isSupported()) window.speechSynthesis.cancel();
    setPlaying(false);
  }, []);

  const play = useCallback(
    (lines: ScriptLine[], { times = 2, rate = 0.85, onEnd }: { times?: number; rate?: number; onEnd?: () => void } = {}): string | null => {
      if (!isSupported()) return "Ton navigateur ne sait pas lire l'audio. Essaie Chrome, Safari ou Edge.";
      const synth = window.speechSynthesis;
      const voices = synth.getVoices();
      const main = pickChineseVoice(voices);
      if (voices.length > 0 && !main) {
        return "Aucune voix chinoise sur cet appareil. Ajoute la langue chinoise dans les réglages du système.";
      }
      const pair = pickDialogueVoices(voices);
      const distinct = pair.m && pair.f && pair.m.voiceURI !== pair.f.voiceURI;
      const queue: { line: ScriptLine; pause: number }[] = [];
      for (let r = 0; r < times; r++) {
        lines.forEach((line, i) => queue.push({ line, pause: i === lines.length - 1 ? 1800 : 450 }));
      }
      synth.cancel();
      const token = ++run.current;
      setPlaying(true);
      const step = (i: number) => {
        if (token !== run.current) return;
        if (i >= queue.length) {
          setPlaying(false);
          onEnd?.();
          return;
        }
        const { line, pause } = queue[i];
        const u = new SpeechSynthesisUtterance(line.t);
        const voice = line.s === "n" ? main : pair[line.s];
        u.lang = voice?.lang ?? "zh-CN";
        if (voice) u.voice = voice;
        u.rate = rate;
        u.pitch = distinct && line.s !== "n" ? 1 : PITCH[line.s];
        const next = () => window.setTimeout(() => step(i + 1), pause);
        u.onend = next;
        u.onerror = next;
        synth.speak(u);
      };
      step(0);
      return null;
    },
    []
  );

  return { supported, play, stop, playing };
}
