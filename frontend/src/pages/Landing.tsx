import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Video,
  Zap,
  Sparkles,
  ArrowRight,
  Play,
  CheckCircle2,
  Layers,
  Subtitles,
  Cpu,
  Cloud,
  ShieldCheck,
  Clock,
  Volume2,
  Eye,
  Sliders,
} from 'lucide-react';
import ThemeToggle from '../components/common/ThemeToggle';
import { useAuth } from '../context/AuthContext';

// Sample Cloudinary video generated in this project
const SHOWCASE_VIDEO_URL =
  'https://res.cloudinary.com/dpvjcr8ea/video/upload/v1772412854/b3086eb0-7c2a-43cf-be6b-5606d64993ad_processed.mp4';

interface DemoTopic {
  title: string;
  tag: string;
  hook: string;
  words: string[];
  scenes: { scene: number; duration: string; visual: string; narration: string }[];
}

const DEMO_TOPICS: DemoTopic[] = [
  {
    title: 'Quantum Computing Explained',
    tag: 'Science & Tech',
    hook: 'Imagine a supercomputer solving a million-year puzzle in under two seconds.',
    words: ['Imagine', 'a', 'supercomputer', 'solving', 'a', 'million-year', 'puzzle', 'in', 'under', 'two', 'seconds.'],
    scenes: [
      {
        scene: 1,
        duration: '3.5s',
        visual: 'Holographic glowing qubit sphere suspended in absolute zero vacuum chamber.',
        narration: 'Classical computers think in ones and zeros. Quantum computers think in everything at once.',
      },
      {
        scene: 2,
        duration: '4.0s',
        visual: 'Quantum superposition visualization with laser interference grid.',
        narration: 'This state called superposition lets qubits test millions of solutions simultaneously.',
      },
      {
        scene: 3,
        duration: '3.5s',
        visual: 'Futuristic quantum processor motherboard illuminated with blue photons.',
        narration: 'From cracking unbreakable ciphers to discovering cures, the quantum leap has begun.',
      },
    ],
  },
  {
    title: 'The Secrets of Deep Sleep',
    tag: 'Health & Wellness',
    hook: 'Your brain cleans itself every night while you sleep, but only if you enter Stage 3.',
    words: ['Your', 'brain', 'cleans', 'itself', 'every', 'night', 'while', 'you', 'sleep.'],
    scenes: [
      {
        scene: 1,
        duration: '3.0s',
        visual: 'Cinematic 3D render of human brain glowing softly with cerebrospinal fluid flow.',
        narration: 'Every night during deep delta sleep, the glymphatic system washes away metabolic toxins.',
      },
      {
        scene: 2,
        duration: '3.8s',
        visual: 'Microscopic view of neural synapses pruning and consolidating memories.',
        narration: 'Adenosine resets, cellular repairs fire up, and today’s memories lock into permanent storage.',
      },
      {
        scene: 3,
        duration: '3.2s',
        visual: 'Morning sunbeams illuminating a refreshed person waking up energized.',
        narration: 'Prioritizing sleep isn’t rest — it’s your brain’s ultimate daily upgrade.',
      },
    ],
  },
  {
    title: 'AI in 2030: What Changes?',
    tag: 'Future Trends',
    hook: 'In less than five years, autonomous AI agents will manage entire digital companies.',
    words: ['Autonomous', 'AI', 'agents', 'will', 'manage', 'entire', 'digital', 'companies.'],
    scenes: [
      {
        scene: 1,
        duration: '3.5s',
        visual: 'Hyper-futuristic glass interface showing autonomous code agents collaborating.',
        narration: 'Single prompts now deploy full software platforms and automated media production.',
      },
      {
        scene: 2,
        duration: '3.8s',
        visual: 'Robot arm collaborating with industrial designer in modern laboratory.',
        narration: 'Physical robotics combined with multimodal models bridge the gap between bits and atoms.',
      },
      {
        scene: 3,
        duration: '3.5s',
        visual: 'Global skyline connected by light beams representing real-time decentralized intelligence.',
        narration: 'The creators of tomorrow won’t be programmers; they will be vision directors.',
      },
    ],
  },
];

export default function LandingPage() {
  const navigate = useNavigate();
  const { isAuthenticated, openAuthModal } = useAuth();
  
  const [selectedTopicIdx, setSelectedTopicIdx] = useState(0);
  const [activeWordIdx, setActiveWordIdx] = useState(0);
  const [isPlayingDemo, setIsPlayingDemo] = useState(true);

  const currentTopic = DEMO_TOPICS[selectedTopicIdx];

  // Animate the word-by-word subtitles karaoke simulation
  useEffect(() => {
    if (!isPlayingDemo) return;
    const interval = setInterval(() => {
      setActiveWordIdx((prev) => (prev + 1) % currentTopic.words.length);
    }, 420);
    return () => clearInterval(interval);
  }, [isPlayingDemo, currentTopic]);

  const handleCtaClick = () => {
    if (isAuthenticated) {
      navigate('/dashboard');
    } else {
      openAuthModal('register');
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col selection:bg-primary/20 selection:text-primary">
      {/* ── Fixed Navigation Bar ────────────────────────────────────────── */}
      <header className="fixed top-0 inset-x-0 z-50 h-16 border-b border-border/80 bg-background/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto h-full flex items-center justify-between px-6">
          {/* Logo */}
          <div
            onClick={() => navigate('/')}
            className="flex items-center gap-2.5 cursor-pointer group"
          >
            <div className="w-8 h-8 rounded-xl qreate-gradient flex items-center justify-center shadow-xs group-hover:scale-105 transition-transform">
              <Video className="w-4 h-4 text-white" />
            </div>
            <span className="text-xl font-extrabold tracking-tight">
              Q<span className="qreate-gradient-text">reate</span>
            </span>
            <span className="hidden sm:inline-block ml-1 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
              v2.0
            </span>
          </div>

          {/* Center Links (Desktop) */}
          <nav className="hidden md:flex items-center gap-7 text-sm font-medium text-muted-foreground">
            <a href="#simulator" className="hover:text-foreground transition-colors">
              Interactive Demo
            </a>
            <a href="#features" className="hover:text-foreground transition-colors">
              Features
            </a>
            <a href="#workflow" className="hover:text-foreground transition-colors">
              Workflow
            </a>
            <a href="#showcase" className="hover:text-foreground transition-colors">
              Showcase
            </a>
            <a href="#comparison" className="hover:text-foreground transition-colors">
              Comparison
            </a>
          </nav>

          {/* Right Action Buttons */}
          <div className="flex items-center gap-3">
            <ThemeToggle />

            {isAuthenticated ? (
              <button
                onClick={() => navigate('/dashboard')}
                className="px-4 py-2 rounded-xl text-xs font-semibold qreate-gradient text-white shadow-xs hover:shadow-md transition-all flex items-center gap-1.5"
              >
                Go to Dashboard
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            ) : (
              <>
                <button
                  onClick={() => openAuthModal('login')}
                  className="hidden sm:inline-flex px-3.5 py-1.5 text-xs font-semibold rounded-lg text-foreground hover:bg-accent transition-colors"
                >
                  Sign In
                </button>
                <button
                  onClick={() => openAuthModal('register')}
                  className="px-4 py-2 text-xs font-semibold rounded-xl qreate-gradient text-white shadow-xs hover:shadow-md hover:opacity-95 transition-all flex items-center gap-1.5"
                >
                  Get Started Free
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* ── Hero Section ────────────────────────────────────────────────── */}
      <section className="relative pt-32 pb-20 px-6 overflow-hidden">
        {/* Subtle background ambient gradients */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[400px] bg-primary/10 rounded-full blur-3xl pointer-events-none -z-10" />
        <div className="absolute top-1/3 left-1/4 w-[350px] h-[350px] bg-purple-500/10 rounded-full blur-3xl pointer-events-none -z-10" />

        <div className="max-w-5xl mx-auto text-center space-y-6">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-primary/30 bg-primary/5 text-primary text-xs font-medium shadow-xs animate-fade-in">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Next-Gen Multi-Scene Synthesis & Word-by-Word Captions</span>
          </div>

          {/* Main Headline */}
          <h1 className="text-4xl sm:text-6xl md:text-7xl font-extrabold tracking-tight leading-[1.1] text-foreground">
            Turn Any Idea into a{' '}
            <span className="qreate-gradient-text">Cinematic AI Video</span>
            <br />
            with Synced Subtitles
          </h1>

          {/* Subtitle */}
          <p className="text-base sm:text-xl text-muted-foreground max-w-2xl mx-auto font-normal leading-relaxed">
            Write a prompt. Get high-retention structured scripts, scene-by-scene visual synthesis,
            and animated karaoke captions — rendered directly in your cloud browser.
          </p>

          {/* CTA Buttons */}
          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              onClick={handleCtaClick}
              className="w-full sm:w-auto px-7 py-3.5 rounded-2xl qreate-gradient text-white text-sm font-semibold shadow-lg hover:shadow-xl hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center justify-center gap-2 group"
            >
              <span>{isAuthenticated ? 'Open Studio Dashboard' : 'Start Creating for Free'}</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>

            <a
              href="#simulator"
              className="w-full sm:w-auto px-6 py-3.5 rounded-2xl border border-border bg-card hover:bg-accent text-foreground text-sm font-medium transition-colors flex items-center justify-center gap-2"
            >
              <Play className="w-4 h-4 text-primary" />
              <span>Try Live Simulator</span>
            </a>
          </div>

          {/* Trust Metrics */}
          <div className="pt-8 flex flex-wrap items-center justify-center gap-6 sm:gap-12 text-xs text-muted-foreground border-t border-border/60 max-w-3xl mx-auto">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              <span>No GPU Required</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              <span>Word-by-Word Subtitles</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              <span>Dual Engine Video AI</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              <span>100% Free to Try</span>
            </div>
          </div>
        </div>
      </section>

      {/* ── Interactive Prompt & Scene Tester (Simulator) ────────────────── */}
      <section id="simulator" className="py-16 px-6 bg-muted/30 border-y border-border/70">
        <div className="max-w-6xl mx-auto space-y-10">
          <div className="text-center space-y-3">
            <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
              <Cpu className="w-4 h-4" />
              Live Interactive Simulator
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">
              Experience the Qreate Engine in Action
            </h2>
            <p className="text-sm sm:text-base text-muted-foreground max-w-xl mx-auto">
              Select a sample prompt below to inspect the AI script breakdown, scene prompts, and
              word-by-word synchronized karaoke captions.
            </p>
          </div>

          {/* Topic Selector Tabs */}
          <div className="flex flex-wrap items-center justify-center gap-2.5">
            {DEMO_TOPICS.map((topic, i) => (
              <button
                key={i}
                onClick={() => {
                  setSelectedTopicIdx(i);
                  setActiveWordIdx(0);
                }}
                className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-medium transition-all ${
                  selectedTopicIdx === i
                    ? 'bg-primary text-primary-foreground shadow-sm shadow-primary/20 scale-[1.02]'
                    : 'bg-card border border-border text-muted-foreground hover:text-foreground hover:bg-accent'
                }`}
              >
                <span className="opacity-70 mr-1.5">#{topic.tag}</span>
                {topic.title}
              </button>
            ))}
          </div>

          {/* Interactive Studio Preview Card */}
          <div className="grid lg:grid-cols-12 gap-6 bg-card border border-border rounded-3xl p-6 sm:p-8 shadow-xl">
            {/* Left Column: Script & Scene Breakdown */}
            <div className="lg:col-span-7 space-y-6">
              <div className="flex items-center justify-between pb-4 border-b border-border">
                <div>
                  <h3 className="text-lg font-bold text-foreground">{currentTopic.title}</h3>
                  <p className="text-xs text-muted-foreground">3 Scenes · 11.0s Total Duration · 9:16 Shorts Ready</p>
                </div>
                <span className="text-xs px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-semibold border border-emerald-500/20">
                  Ready to Render
                </span>
              </div>

              {/* Hook Banner */}
              <div className="p-4 rounded-2xl bg-primary/5 border border-primary/20 space-y-1.5">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-primary">
                  <Zap className="w-3.5 h-3.5" />
                  Hook (First 3 Seconds)
                </div>
                <p className="text-sm font-medium text-foreground italic">
                  "{currentTopic.hook}"
                </p>
              </div>

              {/* Scene Stack */}
              <div className="space-y-3">
                <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center justify-between">
                  <span>Scene Breakdown</span>
                  <span className="text-[11px] text-primary">Dynamic Background Switching</span>
                </div>

                {currentTopic.scenes.map((scene) => (
                  <div
                    key={scene.scene}
                    className="p-3.5 rounded-xl border border-border/70 bg-background/60 hover:border-primary/40 transition-colors space-y-2 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-foreground flex items-center gap-1.5">
                        <span className="w-5 h-5 rounded-md bg-muted text-muted-foreground flex items-center justify-center text-[10px]">
                          {scene.scene}
                        </span>
                        Scene {scene.scene}
                      </span>
                      <span className="text-muted-foreground font-mono">{scene.duration}</span>
                    </div>

                    <p className="text-muted-foreground">
                      <strong className="text-foreground">Visual:</strong> {scene.visual}
                    </p>
                    <p className="text-foreground/90 font-medium">
                      <strong className="text-muted-foreground">Voiceover:</strong> "{scene.narration}"
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Right Column: Live Simulated Player & Synced Captions */}
            <div className="lg:col-span-5 flex flex-col justify-between p-5 rounded-2xl bg-muted/40 border border-border space-y-5">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                    <Subtitles className="w-4 h-4 text-primary" />
                    Synchronized Captions Preview
                  </span>
                  <button
                    onClick={() => setIsPlayingDemo(!isPlayingDemo)}
                    className="text-xs px-2 py-1 rounded-md bg-card border border-border text-foreground hover:bg-accent flex items-center gap-1"
                  >
                    {isPlayingDemo ? (
                      <>
                        <Clock className="w-3 h-3 text-primary animate-spin" />
                        Simulating
                      </>
                    ) : (
                      <>
                        <Play className="w-3 h-3 text-primary" />
                        Play
                      </>
                    )}
                  </button>
                </div>

                {/* Simulated TikTok / Reels Mobile Player Mockup */}
                <div className="relative aspect-9/16 max-h-[380px] w-full mx-auto rounded-2xl bg-black border border-border/80 overflow-hidden shadow-2xl flex flex-col justify-end p-5 text-white">
                  {/* Background gradient simulating scene rendering */}
                  <div className="absolute inset-0 bg-linear-to-b from-indigo-950 via-slate-900 to-black opacity-90 -z-0" />
                  
                  {/* Subtle particle animation effect */}
                  <div className="absolute inset-0 opacity-20 bg-[radial-gradient(#a855f7_1px,transparent_1px)] [background-size:16px_16px]" />

                  {/* Top Mobile Bar */}
                  <div className="absolute top-4 inset-x-4 flex items-center justify-between text-xs text-white/70">
                    <div className="flex items-center gap-1.5 bg-black/40 backdrop-blur-xs px-2 py-1 rounded-full">
                      <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                      <span>Live 1080p</span>
                    </div>
                    <span className="text-[10px] font-mono bg-black/40 px-2 py-0.5 rounded-full">
                      Scene 1/3
                    </span>
                  </div>

                  {/* Word-by-word karaoke subtitle pill */}
                  <div className="relative z-10 space-y-3">
                    <div className="p-3.5 rounded-xl bg-black/70 backdrop-blur-md border border-white/10 text-center shadow-lg">
                      <div className="text-[10px] uppercase font-bold tracking-widest text-primary mb-1 flex items-center justify-center gap-1">
                        <Volume2 className="w-3 h-3" />
                        Word-by-Word Voice Sync
                      </div>
                      <div className="flex flex-wrap items-center justify-center gap-1.5 text-sm sm:text-base font-bold leading-relaxed">
                        {currentTopic.words.map((word, idx) => {
                          const isHighlighted = idx === activeWordIdx;
                          return (
                            <span
                              key={idx}
                              className={`transition-all duration-150 px-1 py-0.5 rounded ${
                                isHighlighted
                                  ? 'text-yellow-400 bg-yellow-400/20 scale-110 shadow-xs'
                                  : 'text-white/80'
                              }`}
                            >
                              {word}
                            </span>
                          );
                        })}
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-white/60">
                      <span>Audio: ElevenLabs AI Voice</span>
                      <span>Cloudinary 60fps</span>
                    </div>
                  </div>
                </div>
              </div>

              <button
                onClick={handleCtaClick}
                className="w-full py-2.5 rounded-xl qreate-gradient text-white text-xs font-semibold shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2"
              >
                <span>Render This Script in Studio</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ── Real Video Showcase Reel ────────────────────────────────────── */}
      <section id="showcase" className="py-20 px-6">
        <div className="max-w-6xl mx-auto space-y-12">
          <div className="text-center space-y-3 max-w-2xl mx-auto">
            <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
              <Eye className="w-4 h-4" />
              Production Showcase
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">
              Built for High-Engagement Creators
            </h2>
            <p className="text-sm sm:text-base text-muted-foreground">
              Watch real videos rendered through our Cloudinary & Agnes AI pipeline.
              Optimized for TikTok, Instagram Reels, and YouTube Shorts algorithms.
            </p>
          </div>

          {/* Video Showcase Card */}
          <div className="max-w-4xl mx-auto bg-card border border-border rounded-3xl p-6 sm:p-8 shadow-2xl grid md:grid-cols-12 gap-8 items-center">
            {/* Embedded Player */}
            <div className="md:col-span-6 flex justify-center">
              <div className="w-full max-w-[280px] aspect-9/16 rounded-2xl overflow-hidden shadow-2xl border border-border bg-black relative group">
                <video
                  src={SHOWCASE_VIDEO_URL}
                  controls
                  playsInline
                  loop
                  muted
                  autoPlay
                  className="w-full h-full object-cover"
                />
              </div>
            </div>

            {/* Video Details & Specs */}
            <div className="md:col-span-6 space-y-5">
              <div className="space-y-2">
                <span className="text-xs font-bold uppercase tracking-wider text-primary">
                  Cloudinary Verified Asset
                </span>
                <h3 className="text-2xl font-bold text-foreground">
                  Autonomous Multi-Scene Video Synthesis
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  Generated with Agnes Video 2.5 Flash and scene-by-scene script synchronization.
                  Captions are dynamically bound to speech timing markers for retention.
                </p>
              </div>

              {/* Specs Pills */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-xl border border-border bg-muted/40 space-y-0.5">
                  <div className="text-muted-foreground">Format</div>
                  <div className="font-semibold text-foreground">9:16 Vertical Shorts</div>
                </div>
                <div className="p-3 rounded-xl border border-border bg-muted/40 space-y-0.5">
                  <div className="text-muted-foreground">Resolution</div>
                  <div className="font-semibold text-foreground">1080 × 1920 Full HD</div>
                </div>
                <div className="p-3 rounded-xl border border-border bg-muted/40 space-y-0.5">
                  <div className="text-muted-foreground">Audio Track</div>
                  <div className="font-semibold text-foreground">AI Voice Narration</div>
                </div>
                <div className="p-3 rounded-xl border border-border bg-muted/40 space-y-0.5">
                  <div className="text-muted-foreground">Subtitle Engine</div>
                  <div className="font-semibold text-foreground">Word-by-Word Timed</div>
                </div>
              </div>

              <div className="pt-2">
                <button
                  onClick={handleCtaClick}
                  className="w-full py-3 rounded-xl qreate-gradient text-white text-xs font-semibold shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2"
                >
                  <span>Synthesize Your Own Video Now</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Core Features Bento Grid ────────────────────────────────────── */}
      <section id="features" className="py-20 px-6 bg-muted/20 border-t border-border/70">
        <div className="max-w-6xl mx-auto space-y-12">
          <div className="text-center space-y-3 max-w-2xl mx-auto">
            <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
              <Sparkles className="w-4 h-4" />
              Engine Features
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">
              Engineered for Maximum Viral Retention
            </h2>
            <p className="text-sm sm:text-base text-muted-foreground">
              Every component is built to keep viewers watching past the 3-second mark and all the way
              through the final call-to-action.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Feature 1 */}
            <div className="p-6 rounded-2xl border border-border bg-card hover:border-primary/50 transition-all space-y-4 shadow-xs">
              <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
                <Layers className="w-6 h-6 text-primary" />
              </div>
              <h3 className="text-lg font-bold text-foreground">Multi-Scene Storyboarding</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Breaks scripts into 3-5 distinct scenes with changing visuals, camera directions, and
                narrative pacing rather than a static boring image.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="p-6 rounded-2xl border border-border bg-card hover:border-primary/50 transition-all space-y-4 shadow-xs">
              <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
                <Subtitles className="w-6 h-6 text-primary" />
              </div>
              <h3 className="text-lg font-bold text-foreground">Word-by-Word Karaoke Subtitles</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Captions highlight each spoken word in real-time, boosting comprehension and increasing
                TikTok and Reels watch time by over 300%.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="p-6 rounded-2xl border border-border bg-card hover:border-primary/50 transition-all space-y-4 shadow-xs">
              <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
                <Cpu className="w-6 h-6 text-primary" />
              </div>
              <h3 className="text-lg font-bold text-foreground">Dual AI Engine Pipeline</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Choose between Agnes Video 2.5 Flash for pure AI video generation or our Multi-Scene
                Synthesis engine for custom backgrounds.
              </p>
            </div>

            {/* Feature 4 */}
            <div className="p-6 rounded-2xl border border-border bg-card hover:border-primary/50 transition-all space-y-4 shadow-xs">
              <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
                <Cloud className="w-6 h-6 text-primary" />
              </div>
              <h3 className="text-lg font-bold text-foreground">Cloud Native Rendering</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                No expensive Nvidia RTX GPU or local software needed. All video encoding, audio mixing,
                and subtitle burn-in runs on fast cloud servers.
              </p>
            </div>

            {/* Feature 5 */}
            <div className="p-6 rounded-2xl border border-border bg-card hover:border-primary/50 transition-all space-y-4 shadow-xs">
              <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
                <ShieldCheck className="w-6 h-6 text-primary" />
              </div>
              <h3 className="text-lg font-bold text-foreground">Cloudinary CDN Distribution</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Rendered videos are automatically uploaded to global Cloudinary edge networks for
                instant streaming, sharing, and high-speed downloads.
              </p>
            </div>

            {/* Feature 6 */}
            <div className="p-6 rounded-2xl border border-border bg-card hover:border-primary/50 transition-all space-y-4 shadow-xs">
              <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
                <Sliders className="w-6 h-6 text-primary" />
              </div>
              <h3 className="text-lg font-bold text-foreground">Full Script Customization</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Edit scenes, modify durations, tweak narrations, and regenerate individual scenes until
                the video matches your exact vision.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Workflow Steps ──────────────────────────────────────────────── */}
      <section id="workflow" className="py-20 px-6">
        <div className="max-w-6xl mx-auto space-y-12">
          <div className="text-center space-y-3 max-w-2xl mx-auto">
            <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-primary">
              <Clock className="w-4 h-4" />
              How It Works
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">
              From Idea to Published Video in Minutes
            </h2>
            <p className="text-sm sm:text-base text-muted-foreground">
              A streamlined, high-speed creative process designed for solo creators and marketing teams.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                step: '01',
                title: 'Enter Topic & Prompt',
                desc: 'Give Qreate any concept, news event, educational insight, or product pitch.',
              },
              {
                step: '02',
                title: 'Generate Scene Script',
                desc: 'AI structures a hook, timed scene narrations, and vivid visual scene cues.',
              },
              {
                step: '03',
                title: 'Review & Synthesize',
                desc: 'Approve or customize the script, then trigger cloud video generation.',
              },
              {
                step: '04',
                title: 'Export & Share',
                desc: 'Download your 1080p video with synced word-by-word subtitles ready for social media.',
              },
            ].map((item, idx) => (
              <div
                key={idx}
                className="p-6 rounded-2xl border border-border bg-card space-y-4 relative group hover:border-primary/40 transition-colors"
              >
                <div className="text-3xl font-extrabold text-primary/30 group-hover:text-primary transition-colors font-mono">
                  {item.step}
                </div>
                <h3 className="text-base font-bold text-foreground">{item.title}</h3>
                <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Comparison Table ────────────────────────────────────────────── */}
      <section id="comparison" className="py-20 px-6 bg-muted/30 border-y border-border/70">
        <div className="max-w-4xl mx-auto space-y-10">
          <div className="text-center space-y-3">
            <h2 className="text-3xl font-bold tracking-tight">Why Creators Choose Qreate</h2>
            <p className="text-sm text-muted-foreground">
              Comparing Qreate against standard video software and basic AI video generators.
            </p>
          </div>

          <div className="bg-card border border-border rounded-2xl overflow-hidden shadow-lg">
            <table className="w-full text-left text-xs sm:text-sm">
              <thead className="bg-muted/70 border-b border-border">
                <tr>
                  <th className="p-4 font-semibold text-foreground">Capability</th>
                  <th className="p-4 font-semibold text-muted-foreground">Traditional Editing</th>
                  <th className="p-4 font-semibold text-muted-foreground">Generic AI Bots</th>
                  <th className="p-4 font-bold text-primary bg-primary/10">Qreate Studio</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                <tr>
                  <td className="p-4 font-medium text-foreground">Turnaround Time</td>
                  <td className="p-4 text-muted-foreground">4-8 Hours</td>
                  <td className="p-4 text-muted-foreground">10-15 Minutes</td>
                  <td className="p-4 font-bold text-primary bg-primary/5">Under 60 Seconds</td>
                </tr>
                <tr>
                  <td className="p-4 font-medium text-foreground">Multi-Scene Transitions</td>
                  <td className="p-4 text-muted-foreground">Manual keyframing</td>
                  <td className="p-4 text-muted-foreground">Single static slide</td>
                  <td className="p-4 font-bold text-primary bg-primary/5">Automatic Scene Cuts</td>
                </tr>
                <tr>
                  <td className="p-4 font-medium text-foreground">Word-by-Word Subtitles</td>
                  <td className="p-4 text-muted-foreground">Manual typing</td>
                  <td className="p-4 text-muted-foreground">Not supported</td>
                  <td className="p-4 font-bold text-primary bg-primary/5">Native Karaoke Timing</td>
                </tr>
                <tr>
                  <td className="p-4 font-medium text-foreground">Hardware Requirement</td>
                  <td className="p-4 text-muted-foreground">Expensive GPU workstation</td>
                  <td className="p-4 text-muted-foreground">Cloud compute</td>
                  <td className="p-4 font-bold text-primary bg-primary/5">Zero GPU / 100% Cloud</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* ── Final Call to Action ────────────────────────────────────────── */}
      <section className="py-24 px-6 relative overflow-hidden">
        <div className="max-w-4xl mx-auto rounded-3xl qreate-gradient p-10 sm:p-14 text-center text-white space-y-6 shadow-2xl relative">
          <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight">
            Ready to Build Your Next Viral Video?
          </h2>
          <p className="text-white/80 max-w-xl mx-auto text-sm sm:text-base leading-relaxed">
            Join the creators producing high-retention short-form videos with automated scripts,
            dynamic scene transitions, and synced captions.
          </p>

          <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              onClick={handleCtaClick}
              className="w-full sm:w-auto px-8 py-4 rounded-2xl bg-white text-slate-900 font-bold text-sm shadow-xl hover:bg-slate-100 hover:scale-105 active:scale-95 transition-all flex items-center justify-center gap-2"
            >
              <span>{isAuthenticated ? 'Launch Studio Now' : 'Create Free Account'}</span>
              <ArrowRight className="w-4 h-4 text-slate-900" />
            </button>
          </div>

          <p className="text-xs text-white/60">No credit card required · Free plan available</p>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer className="border-t border-border py-10 px-6 bg-card text-muted-foreground text-xs">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg qreate-gradient flex items-center justify-center">
              <Video className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="font-bold text-foreground">
              Q<span className="qreate-gradient-text">reate</span>
            </span>
            <span className="text-muted-foreground ml-2">
              © {new Date().getFullYear()} Qreate AI Inc. All rights reserved.
            </span>
          </div>

          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-emerald-500" />
              <span>All Systems Operational</span>
            </div>
            <a href="#simulator" className="hover:text-foreground transition-colors">
              Interactive Demo
            </a>
            <a href="#features" className="hover:text-foreground transition-colors">
              Features
            </a>
            <span
              onClick={handleCtaClick}
              className="hover:text-foreground transition-colors cursor-pointer"
            >
              Studio
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
