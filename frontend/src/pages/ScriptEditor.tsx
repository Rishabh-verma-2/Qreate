import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { ArrowRight, FileWarning, Loader2, Plus, RefreshCw, Trash2 } from 'lucide-react';
import { scriptsApi } from '../services/api';
import type { Scene, Script } from '../types';
import { Button } from '../components/ui/Button';
import { useToast } from '../components/ui/Toast';
import { EmptyState, Skeleton } from '../components/ui/States';
import Stepper from '../components/create/Stepper';
import { InspirationPanel } from '../components/VideoCard';
import { cn } from '../lib/utils';

const WORDS_PER_SECOND = 2.5;

function seconds(text: string) {
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  return Math.max(1, Math.round(words / WORDS_PER_SECOND));
}

function fmt(t: number) {
  return `0:${String(Math.round(t)).padStart(2, '0')}`;
}

/** Textarea that grows with its content and looks like plain text until hovered/focused. */
function InlineText({ value, onChange, placeholder, label, className }: {
  value: string; onChange: (v: string) => void; placeholder: string; label: string; className?: string;
}) {
  return (
    <textarea
      aria-label={label}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      rows={1}
      onInput={(e) => {
        const el = e.currentTarget;
        el.style.height = 'auto';
        el.style.height = `${el.scrollHeight}px`;
      }}
      ref={(el) => {
        if (el) {
          el.style.height = 'auto';
          el.style.height = `${el.scrollHeight}px`;
        }
      }}
      className={cn(
        'w-full resize-none overflow-hidden rounded-md border border-transparent bg-transparent px-2 py-1.5 text-sm leading-relaxed',
        'hover:border-border focus:border-primary focus:bg-background focus:outline-none focus:ring-2 focus:ring-primary/20',
        className
      )}
    />
  );
}

export default function ScriptEditor() {
  const { scriptId } = useParams<{ scriptId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const toast = useToast();

  const [script, setScript] = useState<Script | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [regeneratingAll, setRegeneratingAll] = useState(false);
  const [regeneratingScene, setRegeneratingScene] = useState<number | null>(null);

  useEffect(() => {
    if (!scriptId) return;
    scriptsApi.get(scriptId)
      .then(setScript)
      .catch((err) => setLoadError((err as Error).message))
      .finally(() => setLoading(false));
  }, [scriptId]);

  // Warn before leaving with unsaved edits
  useEffect(() => {
    if (!dirty) return;
    const handler = (e: BeforeUnloadEvent) => { e.preventDefault(); };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [dirty]);

  const timeline = useMemo(() => {
    let t = 0;
    return (script?.scenes || []).map((s) => {
      const start = t;
      t += seconds(s.narration);
      return { start, end: t };
    });
  }, [script]);
  const total = timeline.length ? timeline[timeline.length - 1].end : 0;

  function updateScene(index: number, field: keyof Scene, value: string) {
    setScript((prev) => {
      if (!prev) return prev;
      const scenes = [...prev.scenes];
      scenes[index] = { ...scenes[index], [field]: value };
      return { ...prev, scenes };
    });
    setDirty(true);
  }

  function addScene() {
    setScript((prev) => prev && ({
      ...prev,
      scenes: [...prev.scenes, { scene_number: prev.scenes.length + 1, duration_seconds: 3, narration: '', visual_description: '' }],
    }));
    setDirty(true);
  }

  function removeScene(index: number) {
    setScript((prev) => prev && ({
      ...prev,
      scenes: prev.scenes.filter((_, i) => i !== index).map((s, i) => ({ ...s, scene_number: i + 1 })),
    }));
    setDirty(true);
  }

  async function save(quiet = false) {
    if (!script || !scriptId) return null;
    setSaving(true);
    try {
      const scenes = script.scenes
        .filter((s) => s.narration.trim())
        .map((s, i) => ({ ...s, scene_number: i + 1, duration_seconds: seconds(s.narration) }));
      const updated = await scriptsApi.update(scriptId, { title: script.title, hook: script.hook, closing: script.closing, scenes });
      setScript(updated);
      setDirty(false);
      if (!quiet) toast.success('Script saved');
      return updated;
    } catch (err) {
      toast.error((err as Error).message);
      return null;
    } finally {
      setSaving(false);
    }
  }

  async function regenerateAll() {
    if (!scriptId) return;
    setRegeneratingAll(true);
    try {
      setScript(await scriptsApi.regenerate(scriptId));
      setDirty(false);
      toast.success('New version of the script is ready');
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setRegeneratingAll(false);
    }
  }

  async function regenerateScene(index: number) {
    if (!scriptId) return;
    if (dirty && !(await save(true))) return;
    setRegeneratingScene(index);
    try {
      setScript(await scriptsApi.regenerateScene(scriptId, index));
      toast.success(`Scene ${index + 1} rewritten`);
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setRegeneratingScene(null);
    }
  }

  async function continueToRender() {
    if (!script || !scriptId) return;
    if (!script.scenes.some((s) => s.narration.trim())) {
      toast.error('Add narration to at least one scene');
      return;
    }
    if (dirty && !(await save(true))) return;
    try {
      await scriptsApi.update(scriptId, { approved: true });
      navigate(`/generate-video/${scriptId}`, {
        state: { projectId: script.project_id, aspectRatio: (location.state as { aspectRatio?: string })?.aspectRatio },
      });
    } catch (err) {
      toast.error((err as Error).message);
    }
  }

  if (loading) {
    return (
      <div className="px-4 py-8 sm:px-8 max-w-6xl mx-auto space-y-4">
        <Skeleton className="h-6 w-80" />
        <Skeleton className="h-8 w-1/2" />
        {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-16 w-full" />)}
      </div>
    );
  }

  if (!script) {
    return (
      <div className="px-4 py-8 sm:px-8 max-w-3xl mx-auto">
        <EmptyState
          icon={FileWarning}
          title="Script not found"
          description={loadError || 'It may have been deleted.'}
          action={<Button onClick={() => navigate('/create')}>Create a new video</Button>}
        />
      </div>
    );
  }

  const busy = saving || regeneratingAll || regeneratingScene !== null;

  return (
    <div className="px-4 py-8 sm:px-8 max-w-6xl mx-auto">
      <div className="mb-8 space-y-6">
        <Stepper current={2} onSelect={(i) => i < 2 && navigate('/create')} />
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="min-w-0 flex-1">
            <input
              aria-label="Video title"
              value={script.title}
              onChange={(e) => { setScript({ ...script, title: e.target.value }); setDirty(true); }}
              className="w-full text-2xl font-semibold tracking-tight bg-transparent rounded-md -mx-2 px-2 border border-transparent hover:border-border focus:border-primary focus:outline-none"
            />
            <p className="text-sm text-muted-foreground mt-1">
              {script.scenes.length} scenes · about {total}s · {script.language}
              {script.format ? ` · ${script.format.toLowerCase()}` : ''}
              {dirty && <span className="text-warning"> · Unsaved changes</span>}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={regenerateAll} loading={regeneratingAll} disabled={busy}>
              {!regeneratingAll && <RefreshCw className="w-4 h-4" />}
              Rewrite all
            </Button>
            {dirty && (
              <Button variant="outline" onClick={() => save()} loading={saving} disabled={busy}>Save</Button>
            )}
            <Button onClick={continueToRender} disabled={busy}>
              Continue to render <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {script.angle && (
        <p className="text-sm text-muted-foreground mb-4">
          <span className="text-foreground font-medium">Angle: </span>{script.angle}
        </p>
      )}

      <div className="rounded-lg border border-border overflow-hidden">
        <div className="hidden md:grid grid-cols-[56px_88px_1fr_1fr_72px] gap-4 px-4 h-10 items-center bg-card border-b border-border text-xs font-medium text-muted-foreground">
          <span>Scene</span><span>Time</span><span>Narration</span><span>Visual</span><span className="sr-only">Actions</span>
        </div>
        <ul className="divide-y divide-border">
          {script.scenes.map((scene, i) => {
            const isHook = i === 0;
            const rewriting = regeneratingScene === i;
            return (
              <li
                key={i}
                className={cn(
                  'grid gap-2 md:gap-4 px-4 py-3 md:grid-cols-[56px_88px_1fr_1fr_72px] items-start',
                  isHook && 'bg-primary-soft/60',
                  rewriting && 'opacity-60'
                )}
              >
                <div className="flex md:flex-col items-center md:items-start gap-2 pt-1.5">
                  <span className="text-sm font-medium">{i + 1}</span>
                  {isHook && <span className="px-1.5 py-0.5 rounded-md bg-primary text-primary-foreground text-[11px] font-medium">Hook</span>}
                  <span className="md:hidden text-xs text-muted-foreground ml-auto">{fmt(timeline[i]?.start ?? 0)}–{fmt(timeline[i]?.end ?? 0)}</span>
                </div>
                <span className="hidden md:block pt-2 text-sm tabular-nums text-muted-foreground">
                  {fmt(timeline[i]?.start ?? 0)}–{fmt(timeline[i]?.end ?? 0)}
                </span>
                <div>
                  <p className="md:hidden text-xs text-muted-foreground px-2">Narration</p>
                  <InlineText label={`Scene ${i + 1} narration`} value={scene.narration} placeholder="What the voice says"
                    onChange={(v) => updateScene(i, 'narration', v)} />
                </div>
                <div>
                  <p className="md:hidden text-xs text-muted-foreground px-2">Visual</p>
                  <InlineText label={`Scene ${i + 1} visual`} value={scene.visual_description} placeholder="What the viewer sees"
                    onChange={(v) => updateScene(i, 'visual_description', v)} className="text-muted-foreground" />
                </div>
                <div className="flex md:justify-end gap-1 pt-1">
                  <button
                    type="button"
                    onClick={() => regenerateScene(i)}
                    disabled={busy}
                    title="Rewrite this scene"
                    aria-label={`Rewrite scene ${i + 1}`}
                    className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent disabled:opacity-40"
                  >
                    {rewriting ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                  </button>
                  <button
                    type="button"
                    onClick={() => removeScene(i)}
                    disabled={busy || script.scenes.length <= 1}
                    title="Delete scene"
                    aria-label={`Delete scene ${i + 1}`}
                    className="p-1.5 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10 disabled:opacity-40"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
        <button
          type="button"
          onClick={addScene}
          disabled={busy}
          className="w-full flex items-center justify-center gap-2 h-11 border-t border-border text-sm text-muted-foreground hover:text-foreground hover:bg-accent disabled:opacity-40"
        >
          <Plus className="w-4 h-4" /> Add scene
        </button>
      </div>

      {(script.post?.caption || script.research) && (
        <div className="grid gap-6 md:grid-cols-2 mt-8">
          {script.post?.caption && (
            <div className="rounded-lg border border-border p-4">
              <p className="text-sm font-medium mb-1">Post caption</p>
              <p className="text-sm text-muted-foreground">{script.post.caption}</p>
              {!!script.post.hashtags?.length && (
                <p className="text-sm text-primary mt-2">{script.post.hashtags.map((h) => `#${h}`).join(' ')}</p>
              )}
            </div>
          )}
          {script.research && (
            <div className="rounded-lg border border-border p-4">
              <InspirationPanel inspiration={script.research} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
