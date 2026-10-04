import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  User,
  Mail,
  ShieldCheck,
  Calendar,
  Sparkles,
  Server,
  Cloud,
  Cpu,
  Video,
  Layers,
  LogOut,
  LogIn,
  CheckCircle2,
  Copy,
  Check,
  Smartphone,
  Monitor,
  Flame,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { formatDate } from '../lib/utils';

export default function Profile() {
  const navigate = useNavigate();
  const { user, isAuthenticated, logout, openAuthModal } = useAuth();
  const { theme, toggleTheme } = useTheme();

  const [copiedId, setCopiedId] = useState(false);
  const [defaultAspect, setDefaultAspect] = useState<'9:16' | '16:9'>(() => {
    return (localStorage.getItem('qreate_pref_aspect') as '9:16' | '16:9') || '9:16';
  });
  const defaultEngine = 'purffle';
  const [prefSaved, setPrefSaved] = useState(false);

  const handleCopyId = () => {
    if (user?.id) {
      navigator.clipboard.writeText(user.id);
      setCopiedId(true);
      setTimeout(() => setCopiedId(false), 2000);
    }
  };

  const handleSavePreferences = () => {
    localStorage.setItem('qreate_pref_aspect', defaultAspect);
    localStorage.setItem('qreate_pref_engine', defaultEngine);
    setPrefSaved(true);
    setTimeout(() => setPrefSaved(false), 2500);
  };

  const displayName = user?.full_name || user?.name || (user?.email ? user.email.split('@')[0] : 'Creator');
  const userInitial = displayName.charAt(0).toUpperCase();

  return (
    <div className="p-6 md:p-10 max-w-5xl mx-auto space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <User className="w-7 h-7 text-primary" />
            User Profile & Preferences
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage your account credentials, engine configurations, and studio defaults
          </p>
        </div>

        {isAuthenticated ? (
          <Button
            variant="outline"
            onClick={() => logout()}
            className="text-destructive hover:bg-destructive/10 border-destructive/30 self-start sm:self-auto"
          >
            <LogOut className="w-4 h-4 mr-2" />
            Sign Out
          </Button>
        ) : (
          <Button
            onClick={() => openAuthModal('login')}
            className="qreate-gradient text-white shadow-sm self-start sm:self-auto"
          >
            <LogIn className="w-4 h-4 mr-2" />
            Sign In / Register
          </Button>
        )}
      </div>

      {/* Guest Mode Banner */}
      {!isAuthenticated && (
        <Card className="p-6 border-dashed border-primary/40 bg-primary/5">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse" />
                <h3 className="font-semibold text-foreground">Browsing in Guest Mode</h3>
              </div>
              <p className="text-xs text-muted-foreground max-w-xl">
                You can create scripts and generate videos locally, but creating an account persists your projects,
                saves custom settings, and synchronizes your video history across devices.
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Button size="sm" variant="outline" onClick={() => openAuthModal('login')}>
                Log In
              </Button>
              <Button size="sm" className="qreate-gradient text-white" onClick={() => openAuthModal('register')}>
                Create Free Account
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Hero Profile Card */}
      <Card className="p-6 md:p-8 bg-gradient-to-br from-card via-card to-primary/5 border border-border relative overflow-hidden shadow-sm">
        <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6 relative z-10">
          {/* Avatar */}
          <div className="relative shrink-0">
            <div className="w-20 h-20 md:w-24 md:h-24 rounded-2xl qreate-gradient p-0.5 shadow-md flex items-center justify-center">
              <div className="w-full h-full rounded-[14px] bg-card flex items-center justify-center text-primary font-bold text-3xl md:text-4xl shadow-inner">
                {isAuthenticated ? userInitial : <User className="w-10 h-10 text-muted-foreground" />}
              </div>
            </div>
            <div className="absolute -bottom-1 -right-1 p-1 bg-card rounded-full border border-border shadow-xs">
              <Sparkles className="w-4 h-4 text-purple-400" />
            </div>
          </div>

          {/* User Details */}
          <div className="space-y-2 flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2.5">
              <h2 className="text-xl md:text-2xl font-bold text-foreground truncate">
                {isAuthenticated ? displayName : 'Guest Creator'}
              </h2>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary/10 text-primary border border-primary/20 flex items-center gap-1">
                <Flame className="w-3 h-3 text-primary" />
                {isAuthenticated ? (user?.tier ? user.tier.toUpperCase() : 'PRO CREATOR') : 'FREE GUEST'}
              </span>
              {isAuthenticated && (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3" />
                  Verified
                </span>
              )}
            </div>

            <p className="text-sm text-muted-foreground flex items-center gap-1.5 truncate">
              <Mail className="w-4 h-4 shrink-0 text-muted-foreground/70" />
              {isAuthenticated ? user?.email : 'No email linked (Sign in to attach your account)'}
            </p>

            <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground pt-1">
              <span className="flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" />
                Joined: {isAuthenticated && user?.created_at ? formatDate(user.created_at) : 'Today'}
              </span>
              {isAuthenticated && user?.id && (
                <button
                  onClick={handleCopyId}
                  className="flex items-center gap-1 hover:text-foreground transition-colors group cursor-pointer"
                  title="Click to copy Account ID"
                >
                  <span>ID: <code className="text-[11px] font-mono opacity-80">{user.id.slice(0, 10)}...</code></span>
                  {copiedId ? (
                    <Check className="w-3 h-3 text-emerald-500" />
                  ) : (
                    <Copy className="w-3 h-3 opacity-60 group-hover:opacity-100" />
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      </Card>

      {/* Grid: Connected Engines & Studio Preferences */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Studio Preferences */}
        <Card className="p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-primary" />
              <h3 className="font-semibold text-foreground text-sm">Studio Defaults</h3>
            </div>
            <span className="text-xs text-muted-foreground">Local Preferences</span>
          </div>

          {/* Default Aspect Ratio */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-foreground block">
              Default Aspect Ratio
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setDefaultAspect('9:16')}
                className={`flex items-center gap-2.5 p-3 rounded-xl border text-xs font-medium transition-all ${
                  defaultAspect === '9:16'
                    ? 'border-primary bg-primary/10 text-primary shadow-xs'
                    : 'border-border bg-card hover:bg-muted/40 text-muted-foreground'
                }`}
              >
                <Smartphone className="w-4 h-4 shrink-0" />
                <div className="text-left">
                  <div className="font-semibold">9:16 Vertical</div>
                  <div className="text-[10px] opacity-75">Shorts, Reels, TikTok</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setDefaultAspect('16:9')}
                className={`flex items-center gap-2.5 p-3 rounded-xl border text-xs font-medium transition-all ${
                  defaultAspect === '16:9'
                    ? 'border-primary bg-primary/10 text-primary shadow-xs'
                    : 'border-border bg-card hover:bg-muted/40 text-muted-foreground'
                }`}
              >
                <Monitor className="w-4 h-4 shrink-0" />
                <div className="text-left">
                  <div className="font-semibold">16:9 Landscape</div>
                  <div className="text-[10px] opacity-75">YouTube, Web, TV</div>
                </div>
              </button>
            </div>
          </div>

          {/* Default Engine */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-foreground block">
              Default Video Generator
            </label>
            <div className="p-3.5 rounded-xl border border-primary/40 bg-primary/10 text-xs">
              <div className="font-semibold flex items-center justify-between text-foreground">
                <span className="flex items-center gap-1.5">
                  🎬 PurffleShorts V3 (Procedural Motion Graphics)
                </span>
                <CheckCircle2 className="w-3.5 h-3.5 text-primary" />
              </div>
              <div className="text-[11px] text-muted-foreground mt-1">
                Dynamic animated explainer diagrams, word-by-word synced subtitles, and professional voiceover — 100% animated.
              </div>
            </div>
          </div>

          {/* Theme Preference */}
          <div className="flex items-center justify-between pt-2 border-t border-border">
            <div>
              <p className="text-xs font-semibold text-foreground">Visual Theme</p>
              <p className="text-[11px] text-muted-foreground">Current appearance mode: {theme === 'dark' ? 'Dark Mode' : 'Light Mode'}</p>
            </div>
            <Button size="sm" variant="outline" onClick={toggleTheme}>
              Switch to {theme === 'dark' ? 'Light' : 'Dark'} Mode
            </Button>
          </div>

          {/* Save Action */}
          <div className="pt-2 flex items-center justify-between">
            <Button size="sm" onClick={handleSavePreferences} className="qreate-gradient text-white">
              Save Studio Preferences
            </Button>
            {prefSaved && (
              <span className="text-xs text-emerald-500 font-medium flex items-center gap-1 animate-fade-in">
                <Check className="w-3.5 h-3.5" /> Preferences saved!
              </span>
            )}
          </div>
        </Card>

        {/* System & Integrations Status */}
        <Card className="p-6 space-y-6">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-emerald-500" />
              <h3 className="font-semibold text-foreground text-sm">System & AI Infrastructure</h3>
            </div>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
              All Systems Operational
            </span>
          </div>

          <div className="space-y-3">
            {/* MongoDB Atlas */}
            <div className="p-3 rounded-xl border border-border/70 bg-card/60 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center">
                  <Server className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-xs font-semibold text-foreground">MongoDB Atlas Cluster</p>
                  <p className="text-[11px] text-muted-foreground">User auth, scripts, and video metadata synced</p>
                </div>
              </div>
              <span className="text-[11px] font-medium text-emerald-500 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Connected
              </span>
            </div>

            {/* Cloudinary CDN */}
            <div className="p-3 rounded-xl border border-border/70 bg-card/60 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center">
                  <Cloud className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-xs font-semibold text-foreground">Cloudinary Video CDN</p>
                  <p className="text-[11px] text-muted-foreground">High-bandwidth video streaming & downloads</p>
                </div>
              </div>
              <span className="text-[11px] font-medium text-blue-400 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Active
              </span>
            </div>

            {/* Agnes AI */}
            <div className="p-3 rounded-xl border border-border/70 bg-card/60 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-purple-500/10 text-purple-400 flex items-center justify-center">
                  <Cpu className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-xs font-semibold text-foreground">Agnes AI Platform</p>
                  <p className="text-[11px] text-muted-foreground">Chat completions + Agnes Video 2.5 Flash</p>
                </div>
              </div>
              <span className="text-[11px] font-medium text-purple-400 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Ready
              </span>
            </div>

            {/* PurffleShorts V3 */}
            <div className="p-3 rounded-xl border border-border/70 bg-card/60 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center">
                  <Video className="w-4 h-4" />
                </div>
                <div>
                  <p className="text-xs font-semibold text-foreground">PurffleShorts V3 Engine</p>
                  <p className="text-[11px] text-muted-foreground">NASA imagery & Pillow procedural motion graphics</p>
                </div>
              </div>
              <span className="text-[11px] font-medium text-amber-400 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Integrated
              </span>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-muted/40 text-xs text-muted-foreground space-y-1">
            <p className="font-semibold text-foreground">Security & Data Privacy</p>
            <p className="text-[11px]">
              Passwords are salted and hashed using Bcrypt before storage. JWT sessions expire after 7 days of inactivity.
            </p>
          </div>
        </Card>
      </div>

      {/* Quick Jump Bar */}
      <Card className="p-6 flex flex-col sm:flex-row items-center justify-between gap-4 bg-muted/20">
        <div>
          <h4 className="font-semibold text-sm text-foreground">Ready to create your next video?</h4>
          <p className="text-xs text-muted-foreground mt-0.5">
            Hop right back into the studio to craft a multi-scene educational short or full cinematic video.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => navigate('/projects')}>
            View Projects
          </Button>
          <Button size="sm" className="qreate-gradient text-white" onClick={() => navigate('/create')}>
            Start New Video
          </Button>
        </div>
      </Card>
    </div>
  );
}
