import { useNavigate } from 'react-router-dom';
import { Video, Zap, FileText, CheckCircle, ArrowRight, Clapperboard } from 'lucide-react';
import { Button } from '../components/ui/Button';

const steps = [
  { icon: FileText, title: 'Describe your topic', description: 'Enter any topic or idea — Qreate handles the rest.' },
  { icon: Zap, title: 'Generate a script', description: 'AI creates a structured scene-by-scene script in seconds.' },
  { icon: CheckCircle, title: 'Review & edit', description: 'Refine the script before committing to video generation.' },
  { icon: Video, title: 'Generate your video', description: 'Agnes AI renders your video in the cloud. No GPU needed.' },
];

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Top Nav */}
      <header className="fixed top-0 inset-x-0 z-50 h-16 border-b border-border bg-background/80 backdrop-blur-md">
        <div className="max-w-6xl mx-auto h-full flex items-center justify-between px-6">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg qreate-gradient flex items-center justify-center">
              <Video className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold">
              Q<span className="qreate-gradient-text">reate</span>
            </span>
          </div>
          <Button onClick={() => navigate('/dashboard')} size="sm">
            Open App
          </Button>
        </div>
      </header>

      {/* Hero */}
      <section className="flex-1 flex flex-col items-center justify-center pt-16 px-6 text-center">
        <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-primary/30 bg-primary/5 text-primary text-sm font-medium mb-2">
            <Clapperboard className="w-3.5 h-3.5" />
            Powered by Agnes Video 2.5 Flash
          </div>

          <h1 className="text-5xl sm:text-6xl font-bold tracking-tight leading-tight">
            Turn ideas into{' '}
            <span className="qreate-gradient-text">AI videos</span>
          </h1>

          <p className="text-lg text-muted-foreground max-w-xl mx-auto leading-relaxed">
            Write a prompt. Get a structured script. Generate a professional video — all from your browser. No GPU, no downloads, no hassle.
          </p>

          <div className="flex items-center justify-center gap-4 pt-2">
            <Button onClick={() => navigate('/dashboard')} size="lg">
              Get Started
              <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-bold text-center mb-12">How it works</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {steps.map((step, i) => (
              <div key={i} className="rounded-xl border border-border bg-card p-6 space-y-3">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <step.icon className="w-5 h-5 text-primary" />
                </div>
                <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Step {i + 1}
                </div>
                <h3 className="font-semibold text-foreground">{step.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{step.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="border-t border-border py-6 px-6 text-center text-sm text-muted-foreground">
        Qreate · AI Video Generation Platform
      </footer>
    </div>
  );
}
