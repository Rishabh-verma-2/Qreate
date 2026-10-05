import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight, Captions, Clapperboard, FileText, Languages, Layers, Search, Sparkles, Upload, Video, type LucideIcon,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import Logo from '../components/common/Logo';
import { VerticalPlayer } from '../components/VideoCard';
import { useAuth } from '../context/AuthContext';
import { videosApi } from '../services/api';
import { thumbnailFor } from '../lib/video';
import type { GeneratedVideo } from '../types';

const STEPS = [
  { title: 'Describe a topic', desc: 'An idea, a trend or a question. Pick format, tone, length and language.' },
  { title: 'Review the script', desc: 'A hook-first script built on what people actually search. Edit any scene.' },
  { title: 'Choose the look', desc: 'Video type, colors, caption style and one of 55 natural voices.' },
  { title: 'Render and post', desc: 'A 1080×1920 video with captions and music, plus a ready caption.' },
];

const FEATURES: { icon: LucideIcon; title: string; desc: string }[] = [
  { icon: Search, title: 'Trend research', desc: 'Checks YouTube and Google searches, news and daily trends before writing.' },
  { icon: FileText, title: 'Hook in 3 seconds', desc: 'Every script opens with a hook, then is tightened by an editor pass.' },
  { icon: Clapperboard, title: 'Real footage', desc: 'Stock clips chosen by an AI that looks at each shot, edited with fast cuts.' },
  { icon: Languages, title: '16 languages', desc: 'English, Hindi, Hinglish, Tamil, Telugu, Bengali and more, with native captions.' },
  { icon: Captions, title: 'Word-by-word captions', desc: 'Captions follow the voice, in the color theme and style you pick.' },
  { icon: Layers, title: 'Batch mode', desc: 'Paste many topics and get one video per topic, rendered in parallel.' },
  { icon: Upload, title: 'Your own media', desc: 'Upload your photos and clips for personal stories like weddings and trips.' },
  { icon: Sparkles, title: 'Formats', desc: 'UGC, storytelling, explainer, listicle, news recap, motivational and POV.' },
];

export default function Landing() {
  const navigate = useNavigate();
  const { isAuthenticated, openAuthModal } = useAuth();
  const [samples, setSamples] = useState<GeneratedVideo[]>([]);

  useEffect(() => {
    document.title = 'Qreate — AI video studio';
    videosApi.list()
      .then((all: GeneratedVideo[]) => setSamples(all.filter((v) => v.title && (v.cloudinary_url || v.original_url)).slice(0, 3)))
      .catch(() => setSamples([]));
  }, []);

  const start = () => (isAuthenticated ? navigate('/create') : openAuthModal('register'));

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-30 border-b border-border bg-background/95 backdrop-blur" style={{ paddingTop: 'env(safe-area-inset-top, 0px)' }}>
        <div className="max-w-6xl mx-auto h-14 px-4 sm:px-8 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Logo className="w-7 h-7" />
            <span className="text-base font-semibold tracking-tight">Qreate</span>
          </div>
          <nav className="flex items-center gap-2">
            {isAuthenticated ? (
              <Button size="sm" onClick={() => navigate('/dashboard')}>Open dashboard</Button>
            ) : (
              <>
                <Button size="sm" variant="ghost" onClick={() => openAuthModal('login')}>Sign in</Button>
                <Button size="sm" onClick={() => openAuthModal('register')}>Get started</Button>
              </>
            )}
          </nav>
        </div>
      </header>

      <main>
        <section className="max-w-6xl mx-auto px-4 sm:px-8 pt-16 pb-20 grid gap-12 lg:grid-cols-[1.2fr_1fr] items-center">
          <div>
            <p className="text-sm font-medium text-primary mb-4">AI video studio for the Qoneqt community</p>
            <h1 className="text-4xl sm:text-5xl font-semibold tracking-tight leading-[1.1]">
              Turn any topic into a short video people finish watching.
            </h1>
            <p className="text-base text-muted-foreground mt-5 max-w-xl leading-relaxed">
              Qreate researches what people search for, writes a script with a 3-second hook, picks real footage,
              adds a natural voice and captions, and edits a vertical video ready for the feed.
            </p>
            <div className="flex flex-wrap gap-3 mt-8">
              <Button size="lg" onClick={start}>Create a video <ArrowRight className="w-4 h-4" /></Button>
              {!isAuthenticated && (
                <Button size="lg" variant="outline" onClick={() => openAuthModal('login')}>Sign in</Button>
              )}
            </div>
          </div>
          <div className="flex justify-center gap-3">
            {samples.length > 0 ? samples.slice(0, 2).map((v, i) => (
              <div key={v.id} className={i === 1 ? 'hidden sm:block mt-10' : ''}>
                <div className="w-44 sm:w-52 rounded-[24px] border-[6px] border-foreground bg-foreground overflow-hidden">
                  <VerticalPlayer
                    url={v.cloudinary_url || v.original_url}
                    poster={thumbnailFor(v.cloudinary_url, v.thumbnail_url)}
                    className="rounded-[18px]"
                    autoPlay
                    muted
                    loop
                    controls={false}
                  />
                </div>

                <p className="text-xs text-muted-foreground mt-2 text-center line-clamp-1 w-44 sm:w-52">{v.title}</p>
              </div>
            )) : (
              <div className="w-52 aspect-[9/16] rounded-[24px] border-[6px] border-foreground bg-muted flex items-center justify-center">
                <Video className="w-8 h-8 text-muted-foreground" />
              </div>
            )}
          </div>
        </section>

        <section className="border-t border-border bg-card">
          <div className="max-w-6xl mx-auto px-4 sm:px-8 py-16">
            <h2 className="text-2xl font-semibold tracking-tight">How it works</h2>
            <ol className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4 mt-8">
              {STEPS.map((s, i) => (
                <li key={s.title} className="rounded-lg border border-border bg-background p-5">
                  <span className="text-sm font-medium text-primary">Step {i + 1}</span>
                  <p className="text-base font-semibold mt-2">{s.title}</p>
                  <p className="text-sm text-muted-foreground mt-1 leading-relaxed">{s.desc}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="max-w-6xl mx-auto px-4 sm:px-8 py-16">
          <h2 className="text-2xl font-semibold tracking-tight">What's inside</h2>
          <div className="grid gap-x-8 gap-y-8 sm:grid-cols-2 lg:grid-cols-4 mt-8">
            {FEATURES.map(({ icon: Icon, title, desc }) => (
              <div key={title}>
                <Icon className="w-5 h-5 text-primary" />
                <p className="text-sm font-semibold mt-3">{title}</p>
                <p className="text-sm text-muted-foreground mt-1 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="border-t border-border">
          <div className="max-w-6xl mx-auto px-4 sm:px-8 py-16 flex flex-col sm:flex-row sm:items-center justify-between gap-6">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight">Make your first video in about two minutes.</h2>
              <p className="text-sm text-muted-foreground mt-1">No editing skills needed.</p>
            </div>
            <Button size="lg" onClick={start}>Create a video <ArrowRight className="w-4 h-4" /></Button>
          </div>
        </section>
      </main>

      <footer className="border-t border-border">
        <div className="max-w-6xl mx-auto px-4 sm:px-8 h-14 flex items-center justify-between text-hint text-muted-foreground">
          <span>Qreate · built by team NeoQuant</span>
          <span>CTRL FREAK 2026</span>
        </div>
      </footer>
    </div>
  );
}
