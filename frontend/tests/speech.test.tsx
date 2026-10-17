import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ListenButton } from "@/components/listen-button";
import { pickChineseVoice } from "@/lib/speech";

const toastError = vi.fn();
vi.mock("sonner", () => ({ toast: { error: (m: string) => toastError(m) } }));

type FakeVoice = { lang: string; localService: boolean; voiceURI: string; name: string };
const voice = (lang: string, localService: boolean, name = lang): FakeVoice => ({
  lang,
  localService,
  voiceURI: `${name}-${localService ? "local" : "net"}`,
  name,
});

describe("pickChineseVoice", () => {
  it("prefers a local zh-CN voice", () => {
    const voices = [
      voice("en-US", true),
      voice("zh-CN", false, "Google 普通话"),
      voice("zh-TW", true),
      voice("zh-CN", true, "Tingting"),
    ];
    expect(pickChineseVoice(voices)?.name).toBe("Tingting");
  });

  it("accepts underscore and cmn tags, and falls back to other Chinese variants", () => {
    expect(pickChineseVoice([voice("en-GB", true), voice("zh_CN", false)])?.lang).toBe("zh_CN");
    expect(pickChineseVoice([voice("cmn-Hans-CN", true)])?.lang).toBe("cmn-Hans-CN");
    expect(pickChineseVoice([voice("fr-FR", true), voice("zh-TW", true)])?.lang).toBe("zh-TW");
  });

  it("returns null without any Chinese voice", () => {
    expect(pickChineseVoice([voice("en-US", true), voice("fr-FR", true)])).toBeNull();
  });
});

class FakeUtterance {
  text: string;
  lang = "";
  rate = 1;
  voice: FakeVoice | null = null;
  onend: (() => void) | null = null;
  onerror: (() => void) | null = null;
  constructor(text: string) {
    this.text = text;
  }
}

function installSpeech(voices: FakeVoice[]) {
  const spoken: FakeUtterance[] = [];
  const synth = {
    getVoices: () => voices,
    speak: vi.fn((u: FakeUtterance) => spoken.push(u)),
    cancel: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  };
  Object.defineProperty(window, "speechSynthesis", { value: synth, configurable: true });
  Object.defineProperty(window, "SpeechSynthesisUtterance", { value: FakeUtterance, configurable: true });
  return { synth, spoken };
}

describe("ListenButton", () => {
  beforeEach(() => toastError.mockReset());
  afterEach(() => {
    // @ts-expect-error test cleanup of injected globals
    delete window.speechSynthesis;
    // @ts-expect-error test cleanup of injected globals
    delete window.SpeechSynthesisUtterance;
  });

  it("reads the word with the Chinese voice, slower than normal", () => {
    const { spoken } = installSpeech([voice("en-US", true), voice("zh-CN", true, "Tingting")]);
    render(<ListenButton text="电脑" label="Écouter" rate={0.8} />);

    fireEvent.click(screen.getByRole("button", { name: /écouter/i }));
    expect(spoken).toHaveLength(1);
    expect(spoken[0].text).toBe("电脑");
    expect(spoken[0].voice?.name).toBe("Tingting");
    expect(spoken[0].lang).toBe("zh-CN");
    expect(spoken[0].rate).toBe(0.8);
    expect(screen.getByRole("button", { name: /écouter/i })).toHaveAttribute("aria-pressed", "true");

    act(() => spoken[0].onend?.());
    expect(screen.getByRole("button", { name: /écouter/i })).toHaveAttribute("aria-pressed", "false");
    expect(toastError).not.toHaveBeenCalled();
  });

  it("a second click while playing stops the audio", () => {
    const { synth, spoken } = installSpeech([voice("zh-CN", true)]);
    render(<ListenButton text="你好" label="Écouter" />);
    const button = screen.getByRole("button", { name: /écouter/i });
    fireEvent.click(button);
    fireEvent.click(button);
    expect(spoken).toHaveLength(1);
    expect(synth.cancel).toHaveBeenCalledTimes(2); // once before speaking, once to stop
    expect(button).toHaveAttribute("aria-pressed", "false");
  });

  it("still tries zh-CN when the voice list is not loaded yet", () => {
    const { spoken } = installSpeech([]);
    render(<ListenButton text="谢谢" label="Écouter" />);
    fireEvent.click(screen.getByRole("button", { name: /écouter/i }));
    expect(spoken).toHaveLength(1);
    expect(spoken[0].lang).toBe("zh-CN");
    expect(spoken[0].voice).toBeNull();
  });

  it("explains when the device has no Chinese voice", () => {
    const { spoken } = installSpeech([voice("en-US", true), voice("fr-FR", true)]);
    render(<ListenButton text="谢谢" label="Écouter" />);
    fireEvent.click(screen.getByRole("button", { name: /écouter/i }));
    expect(spoken).toHaveLength(0);
    expect(toastError).toHaveBeenCalledWith(expect.stringMatching(/Aucune voix chinoise/));
  });

  it("explains when the browser has no speech synthesis at all", () => {
    render(<ListenButton text="谢谢" />);
    fireEvent.click(screen.getByRole("button", { name: "Écouter 谢谢" }));
    expect(toastError).toHaveBeenCalledWith(expect.stringMatching(/ne sait pas lire/));
  });
});
