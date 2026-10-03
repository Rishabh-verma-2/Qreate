import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Save,
  RefreshCw,
  ChevronRight,
  Plus,
  Trash2,
  Edit3,
  Check,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { scriptsApi } from '../services/api';
import type { Script, Scene } from '../types';
import { Button } from '../components/ui/Button';
import { Input, Textarea } from '../components/ui/Input';
import { Card } from '../components/ui/Card';

export default function ScriptEditor() {
  const { scriptId } = useParams<{ scriptId: string }>();
  const navigate = useNavigate();

  const [script, setScript] = useState<Script | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState('');
  const [editingScene, setEditingScene] = useState<number | null>(null);

  useEffect(() => {
    if (!scriptId) return;
    scriptsApi.get(scriptId)
      .then(setScript)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [scriptId]);

  function updateField<K extends keyof Script>(key: K, value: Script[K]) {
    setScript((prev) => prev ? { ...prev, [key]: value } : prev);
    setDirty(true);
  }

  function updateScene(index: number, field: keyof Scene, value: string | number) {
    setScript((prev) => {
      if (!prev) return prev;
      const scenes = [...prev.scenes];
      scenes[index] = { ...scenes[index], [field]: value };
      return { ...prev, scenes };
    });
    setDirty(true);
  }

  function addScene() {
    setScript((prev) => {
      if (!prev) return prev;
      const newScene: Scene = {
        scene_number: prev.scenes.length + 1,
        duration_seconds: 10,
        narration: '',
        visual_description: '',
        camera_notes: '',
      };
      return { ...prev, scenes: [...prev.scenes, newScene] };
    });
    setDirty(true);
  }

  function removeScene(index: number) {
    setScript((prev) => {
      if (!prev) return prev;
      const scenes = prev.scenes
        .filter((_, i) => i !== index)
        .map((s, i) => ({ ...s, scene_number: i + 1 }));
      return { ...prev, scenes };
    });
    setDirty(true);
  }

  async function handleSave() {
    if (!script || !scriptId) return;
    setSaving(true);
    try {
      const updated = await scriptsApi.update(scriptId, {
        title: script.title,
        hook: script.hook,
        closing: script.closing,
        scenes: script.scenes,
      });
      setScript(updated);
      setDirty(false);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function handleRegenerate() {
    if (!scriptId) return;
    setRegenerating(true);
    setError('');
    try {
      const updated = await scriptsApi.regenerate(scriptId);
      setScript(updated);
      setDirty(false);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setRegenerating(false);
    }
  }

  async function handleApproveAndContinue() {
    if (!script || !scriptId) return;
    setSaving(true);
    try {
      if (dirty) await handleSave();
      await scriptsApi.update(scriptId, { approved: true });
      navigate(`/generate-video/${scriptId}`, { state: { projectId: script.project_id } });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!script) {
    return (
      <div className="p-8 text-center">
        <p className="text-muted-foreground">{error || 'Script not found'}</p>
      </div>
    );
  }

  const totalDuration = script.scenes.reduce((sum, s) => sum + (s.duration_seconds || 0), 0);

  return (
    <div className="p-8 max-w-4xl mx-auto animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between mb-6 gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {dirty && (
              <span className="text-xs text-yellow-400 bg-yellow-400/10 px-2 py-0.5 rounded-full">
                Unsaved changes
              </span>
            )}
          </div>
          <h1 className="text-2xl font-bold truncate">{script.title || 'Untitled Script'}</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {script.scenes.length} scenes · ~{totalDuration}s · {script.language} · {Array.isArray(script.tone) ? script.tone.join(', ') : script.tone}
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRegenerate}
            loading={regenerating}
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Regenerate
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleSave}
            loading={saving}
            disabled={!dirty}
          >
            <Save className="w-3.5 h-3.5" />
            Save
          </Button>
          <Button size="sm" onClick={handleApproveAndContinue} loading={saving}>
            Generate Video
            <ChevronRight className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>

      {error && (
        <div className="mb-6 flex items-start gap-2 p-4 rounded-lg border border-destructive/30 bg-destructive/10 text-sm text-red-400">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          {error}
        </div>
      )}

      <div className="space-y-6">
        {/* Title & Hook */}
        <Card>
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4">Script Overview</h2>
          <div className="space-y-4">
            <Input
              label="Title"
              value={script.title}
              onChange={(e) => updateField('title', e.target.value)}
            />
            <Textarea
              label="Opening Hook"
              value={script.hook || ''}
              onChange={(e) => updateField('hook', e.target.value)}
              rows={2}
              placeholder="The attention-grabbing opening line..."
            />
          </div>
        </Card>

        {/* Scenes */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold">Scenes</h2>
            <button
              onClick={addScene}
              className="flex items-center gap-1.5 text-sm text-primary hover:text-primary/80 font-medium"
            >
              <Plus className="w-4 h-4" />
              Add Scene
            </button>
          </div>

          {script.scenes.map((scene, idx) => (
            <Card key={idx} className="relative">
              <div className="flex items-start justify-between mb-4 gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-primary bg-primary/10 px-2 py-1 rounded-md">
                    Scene {scene.scene_number}
                  </span>
                  <span className="text-xs text-muted-foreground">{scene.duration_seconds}s</span>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setEditingScene(editingScene === idx ? null : idx)}
                    className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
                  >
                    {editingScene === idx ? <Check className="w-4 h-4 text-green-400" /> : <Edit3 className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={() => removeScene(idx)}
                    className="p-1.5 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {editingScene === idx ? (
                <div className="space-y-3">
                  <div className="grid sm:grid-cols-2 gap-3">
                    <Input
                      label="Duration (seconds)"
                      type="number"
                      min={3}
                      max={60}
                      value={String(scene.duration_seconds)}
                      onChange={(e) => updateScene(idx, 'duration_seconds', parseInt(e.target.value) || 10)}
                    />
                  </div>
                  <Textarea
                    label="Narration"
                    value={scene.narration}
                    onChange={(e) => updateScene(idx, 'narration', e.target.value)}
                    rows={3}
                  />
                  <Textarea
                    label="Visual Description"
                    value={scene.visual_description}
                    onChange={(e) => updateScene(idx, 'visual_description', e.target.value)}
                    rows={3}
                  />
                  <Input
                    label="Camera Notes"
                    value={scene.camera_notes || ''}
                    onChange={(e) => updateScene(idx, 'camera_notes', e.target.value)}
                    placeholder="Optional camera direction..."
                  />
                </div>
              ) : (
                <div className="space-y-3">
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">Narration</p>
                    <p className="text-sm leading-relaxed">{scene.narration || '—'}</p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">Visuals</p>
                    <p className="text-sm leading-relaxed text-muted-foreground">{scene.visual_description || '—'}</p>
                  </div>
                  {scene.camera_notes && (
                    <div>
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">Camera</p>
                      <p className="text-sm text-muted-foreground">{scene.camera_notes}</p>
                    </div>
                  )}
                </div>
              )}
            </Card>
          ))}
        </div>

        {/* Closing */}
        <Card>
          <Textarea
            label="Closing / Call to Action"
            value={script.closing || ''}
            onChange={(e) => updateField('closing', e.target.value)}
            rows={2}
            placeholder="Closing statement or call to action..."
          />
        </Card>

        {/* Bottom actions */}
        <div className="flex items-center justify-end gap-3 pb-8">
          <Button variant="outline" onClick={() => navigate('/projects')}>
            Back to Projects
          </Button>
          <Button onClick={handleApproveAndContinue} loading={saving}>
            Approve & Generate Video
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
