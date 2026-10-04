import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Check, LogOut, Monitor, Smartphone } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { healthApi } from '../services/api';
import { Button } from '../components/ui/Button';
import { PageHeader, Skeleton } from '../components/ui/States';
import { useToast } from '../components/ui/Toast';
import { cn, formatDate } from '../lib/utils';

const ENGINES = [
  { value: 'qreate', label: 'Qreate reel engine', desc: 'Real footage, trend research, reel-style edit (9:16)' },
  { value: 'purffle', label: 'Motion graphics engine', desc: 'Diagrams and motion graphics, any aspect ratio' },
  { value: 'free', label: 'Classic engine', desc: 'Photo slideshow with narration' },
];

interface Health {
  status: string;
  database: string;
  cloudinary: string;
  llm_providers?: string[];
  stock_media_sources?: string[];
  output?: string;
}

function Section({ title, description, children }: { title: string; description?: string; children: React.ReactNode }) {
  return (
    <section className="grid gap-6 md:grid-cols-[240px_1fr] py-8 border-b border-border last:border-0">
      <div>
        <h2 className="text-base font-semibold">{title}</h2>
        {description && <p className="text-hint text-muted-foreground mt-1">{description}</p>}
      </div>
      <div>{children}</div>
    </section>
  );
}

function StatusRow({ label, ok, detail }: { label: string; ok: boolean; detail: string }) {
  return (
    <li className="flex items-center justify-between gap-4 py-2.5 text-sm">
      <span className="flex items-center gap-2.5">
        <span className={cn('w-2 h-2 rounded-full', ok ? 'bg-success' : 'bg-destructive')} aria-hidden="true" />
        {label}
      </span>
      <span className="text-muted-foreground text-right truncate">{detail}</span>
    </li>
  );
}

export default function Profile() {
  const navigate = useNavigate();
  const toast = useToast();
  const { user, logout } = useAuth();
  const [aspect, setAspect] = useState(() => localStorage.getItem('qreate_pref_aspect') || '9:16');
  const [engine, setEngine] = useState(() => localStorage.getItem('qreate_pref_engine') || 'qreate');
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState(false);

  useEffect(() => {
    healthApi.check().then(setHealth).catch(() => setHealthError(true));
  }, []);

  function saveDefaults(nextAspect: string, nextEngine: string) {
    setAspect(nextAspect);
    setEngine(nextEngine);
    localStorage.setItem('qreate_pref_aspect', nextAspect);
    localStorage.setItem('qreate_pref_engine', nextEngine);
    toast.success('Defaults saved');
  }

  const name = user?.full_name || user?.name || user?.email?.split('@')[0] || '';

  return (
    <div className="px-4 py-8 sm:px-8 max-w-4xl mx-auto">
      <PageHeader title="Settings" description="Your account, defaults for new videos, and system status." />

      <Section title="Account">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="w-12 h-12 rounded-full bg-primary-soft text-primary text-lg font-semibold flex items-center justify-center">
              {(name[0] || '?').toUpperCase()}
            </span>
            <div>
              <p className="text-sm font-medium">{name}</p>
              <p className="text-sm text-muted-foreground">{user?.email}</p>
              {user?.created_at && <p className="text-hint text-muted-foreground">Joined {formatDate(user.created_at)}</p>}
            </div>
          </div>
          <Button variant="outline" onClick={() => { logout(); navigate('/'); }}>
            <LogOut className="w-4 h-4" /> Log out
          </Button>
        </div>
      </Section>

      <Section title="Defaults" description="Used when you start a new video. Saved on this device.">
        <div className="space-y-6">
          <div className="space-y-2">
            <p className="text-sm font-medium">Format</p>
            <div className="grid sm:grid-cols-2 gap-3">
              {[
                { value: '9:16', icon: Smartphone, label: 'Vertical 9:16', desc: 'Qoneqt feed, Reels and Shorts' },
                { value: '16:9', icon: Monitor, label: 'Widescreen 16:9', desc: 'YouTube and presentations' },
              ].map(({ value, icon: Icon, label, desc }) => (
                <button
                  key={value}
                  type="button"
                  aria-pressed={aspect === value}
                  onClick={() => saveDefaults(value, value === '16:9' && engine === 'qreate' ? 'purffle' : engine)}
                  className={cn(
                    'flex items-start gap-3 rounded-lg border p-3 text-left',
                    aspect === value ? 'border-primary bg-primary-soft' : 'border-border hover:border-primary/40'
                  )}
                >
                  <Icon className={cn('w-5 h-5 mt-0.5', aspect === value ? 'text-primary' : 'text-muted-foreground')} />
                  <span>
                    <span className="block text-sm font-medium">{label}</span>
                    <span className="block text-hint text-muted-foreground">{desc}</span>
                  </span>
                </button>
              ))}
            </div>
          </div>
          <div className="space-y-2">
            <p className="text-sm font-medium">Render engine</p>
            <div className="grid gap-2">
              {ENGINES.filter((e) => aspect === '9:16' || e.value !== 'qreate').map((e) => (
                <button
                  key={e.value}
                  type="button"
                  aria-pressed={engine === e.value}
                  onClick={() => saveDefaults(aspect, e.value)}
                  className={cn(
                    'flex items-center justify-between gap-3 rounded-lg border p-3 text-left',
                    engine === e.value ? 'border-primary bg-primary-soft' : 'border-border hover:border-primary/40'
                  )}
                >
                  <span>
                    <span className="block text-sm font-medium">{e.label}</span>
                    <span className="block text-hint text-muted-foreground">{e.desc}</span>
                  </span>
                  {engine === e.value && <Check className="w-4 h-4 text-primary shrink-0" />}
                </button>
              ))}
            </div>
          </div>
        </div>
      </Section>

      <Section title="System status" description="Live check of the services Qreate depends on.">
        {healthError ? (
          <p className="text-sm text-destructive">The API is not reachable right now.</p>
        ) : !health ? (
          <div className="space-y-2">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-6 w-full" />)}</div>
        ) : (
          <ul className="divide-y divide-border">
            <StatusRow label="Database" ok={health.database === 'connected'} detail={health.database} />
            <StatusRow label="Video storage" ok={health.cloudinary === 'configured'} detail={health.cloudinary} />
            <StatusRow
              label="Script AI"
              ok={!!health.llm_providers?.length}
              detail={health.llm_providers?.length ? health.llm_providers.join(', ') : 'not configured'}
            />
            <StatusRow
              label="Stock footage"
              ok={!!health.stock_media_sources?.length && !health.stock_media_sources[0].startsWith('none')}
              detail={(health.stock_media_sources || []).join(', ')}
            />
            {health.output && <StatusRow label="Output" ok detail={health.output} />}
          </ul>
        )}
      </Section>
    </div>
  );
}
