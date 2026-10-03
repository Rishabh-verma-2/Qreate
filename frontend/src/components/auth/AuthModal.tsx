import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  X,
  Mail,
  Lock,
  User as UserIcon,
  Eye,
  EyeOff,
  Loader2,
  Video,
  Sparkles,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export default function AuthModal() {
  const navigate = useNavigate();
  const { isAuthModalOpen, authModalMode, closeAuthModal, openAuthModal, login, register } =
    useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isAuthModalOpen) return null;

  const isLogin = authModalMode === 'login';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      if (isLogin) {
        await login({ email: email.trim(), password });
      } else {
        await register({
          email: email.trim(),
          password,
          name: fullName.trim() || undefined,
          full_name: fullName.trim() || undefined,
        });
      }
      // Navigate to dashboard upon successful authentication
      navigate('/dashboard');
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        'Authentication failed. Please check your credentials and try again.';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDemoLogin = async () => {
    setError(null);
    setIsSubmitting(true);
    try {
      await login({
        email: 'rishabh@qreate.ai',
        password: 'password123',
      });
      navigate('/dashboard');
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
        'Demo login failed. Make sure the backend server is running.';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 bg-black/70 backdrop-blur-md animate-fade-in">
      {/* Backdrop overlay dismiss */}
      <div className="fixed inset-0 -z-10" onClick={closeAuthModal} />

      {/* Modal Dialog Card */}
      <div
        className="relative w-full max-w-md max-h-[88vh] my-auto flex flex-col bg-card border border-border rounded-3xl shadow-2xl overflow-hidden animate-scale-up z-20"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Glow Header Top Line */}
        <div className="h-1.5 w-full qreate-gradient shrink-0" />

        {/* Close Button */}
        <button
          onClick={closeAuthModal}
          className="absolute top-4 right-4 p-2 rounded-xl text-muted-foreground hover:text-foreground hover:bg-muted transition-colors z-10"
          aria-label="Close dialog"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Scrollable Container */}
        <div className="overflow-y-auto px-7 py-6 space-y-5">
          {/* Logo & Headline */}
          <div className="text-center space-y-1.5 pt-1">
            <div className="inline-flex items-center justify-center w-11 h-11 rounded-2xl qreate-gradient shadow-md mb-1">
              <Video className="w-5 h-5 text-white" />
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-foreground">
              {isLogin ? 'Welcome back to ' : 'Start creating with '}
              <span className="qreate-gradient-text">Qreate</span>
            </h2>
            <p className="text-xs sm:text-sm text-muted-foreground max-w-xs mx-auto">
              {isLogin
                ? 'Sign in to access your projects and studio.'
                : 'Create your account to render AI videos with synchronized captions.'}
            </p>
          </div>

          {/* Mode Tabs */}
          <div className="flex p-1 bg-muted/70 rounded-2xl border border-border/60">
            <button
              type="button"
              onClick={() => {
                setError(null);
                openAuthModal('login');
              }}
              className={`flex-1 py-2 text-xs sm:text-sm font-semibold rounded-xl transition-all ${
                isLogin
                  ? 'bg-card text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setError(null);
                openAuthModal('register');
              }}
              className={`flex-1 py-2 text-xs sm:text-sm font-semibold rounded-xl transition-all ${
                !isLogin
                  ? 'bg-card text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Create Account
            </button>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="p-3 text-xs rounded-xl bg-destructive/10 border border-destructive/20 text-destructive flex items-start gap-2.5 animate-fade-in">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-destructive" />
              <div className="flex-1 leading-relaxed font-medium">{error}</div>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
              <div className="space-y-1.5">
                <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                  Full Name
                </label>
                <div className="relative">
                  <UserIcon className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => {
                      setFullName(e.target.value);
                      if (error) setError(null);
                    }}
                    placeholder="Rishabh Verma"
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-border bg-background text-foreground text-sm focus:outline-hidden focus:ring-2 focus:ring-primary/40 focus:border-primary transition-all placeholder:text-muted-foreground/50"
                  />
                </div>
              </div>
            )}

            <div className="space-y-1.5">
              <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (error) setError(null);
                  }}
                  placeholder="creator@qreate.ai"
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-border bg-background text-foreground text-sm focus:outline-hidden focus:ring-2 focus:ring-primary/40 focus:border-primary transition-all placeholder:text-muted-foreground/50"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                  Password
                </label>
                {isLogin && (
                  <span className="text-[11px] text-primary hover:underline cursor-pointer">
                    Forgot password?
                  </span>
                )}
              </div>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (error) setError(null);
                  }}
                  placeholder="At least 6 characters"
                  className="w-full pl-10 pr-10 py-2.5 rounded-xl border border-border bg-background text-foreground text-sm focus:outline-hidden focus:ring-2 focus:ring-primary/40 focus:border-primary transition-all placeholder:text-muted-foreground/50"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3 px-4 rounded-xl qreate-gradient text-white font-semibold text-sm shadow-md hover:shadow-lg hover:opacity-95 transition-all flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>{isLogin ? 'Signing In...' : 'Creating Account...'}</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>{isLogin ? 'Sign In to Studio' : 'Create Free Account'}</span>
                </>
              )}
            </button>
          </form>

          {/* Instant Test Credentials */}
          <div className="pt-1">
            <div className="relative flex py-2 items-center">
              <div className="flex-grow border-t border-border"></div>
              <span className="shrink-0 mx-3 text-[11px] text-muted-foreground uppercase tracking-wider font-semibold">
                Quick Test Account
              </span>
              <div className="flex-grow border-t border-border"></div>
            </div>

            <button
              type="button"
              onClick={handleDemoLogin}
              disabled={isSubmitting}
              className="w-full mt-1 py-2 px-3 rounded-xl border border-border/80 bg-accent/40 hover:bg-accent text-foreground text-xs font-medium transition-colors flex items-center justify-center gap-2"
            >
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
              Sign In with Test Account (rishabh@qreate.ai)
            </button>
          </div>
        </div>

        {/* Footer info */}
        <div className="py-3 px-6 bg-muted/30 border-t border-border text-center text-[11px] text-muted-foreground shrink-0">
          Protected by MongoDB Atlas Auth & JWT encryption.
        </div>
      </div>
    </div>
  );
}
