import React, { useState } from 'react';
import { Play, RotateCw, Sparkles, Clock, Check, AlertCircle } from 'lucide-react';
import type { VideoPlanScene } from '../../types';

interface SceneCardProps {
  scene: VideoPlanScene;
  index: number;
  onRegenerate: (sceneId: string, instruction: string) => Promise<void>;
  isRegenerating?: boolean;
}

export const SceneCard: React.FC<SceneCardProps> = ({
  scene,
  index,
  onRegenerate,
  isRegenerating = false,
}) => {
  const [showModal, setShowModal] = useState(false);
  const [instruction, setInstruction] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRegenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!instruction.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await onRegenerate(scene.id, instruction.trim());
      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        setShowModal(false);
        setInstruction('');
      }, 1500);
    } catch (err: any) {
      setError(err?.message || 'Failed to regenerate scene');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div
        id={`scene-render-card-${scene.id}`}
        className="group relative flex flex-col justify-between overflow-hidden rounded-2xl border border-border bg-card hover:border-primary/50 transition-all duration-300 shadow-xs hover:shadow-md"
      >
        {/* Media / Video Container */}
        <div className="relative aspect-video w-full bg-muted/50 overflow-hidden flex items-center justify-center border-b border-border">
          {scene.generated_clip_url ? (
            <video
              src={scene.generated_clip_url}
              controls
              className="w-full h-full object-cover"
              preload="metadata"
            />
          ) : (
            <div className="flex flex-col items-center justify-center p-6 text-center text-muted-foreground space-y-2">
              <div className="w-12 h-12 rounded-full bg-primary-soft border border-primary/20 flex items-center justify-center text-primary group-hover:scale-105 transition-transform">
                <Play className="w-5 h-5 ml-0.5" />
              </div>
              <span className="text-xs font-medium">Scene clip rendering</span>
            </div>
          )}

          <div className="absolute top-2 left-2 flex items-center gap-1.5">
            <span className="px-2 py-0.5 rounded-md text-[11px] font-bold bg-background/90 backdrop-blur-xs border border-border text-foreground shadow-xs">
              Scene {index + 1}
            </span>
            <span className="px-2 py-0.5 rounded-md text-[11px] font-mono bg-background/90 backdrop-blur-xs border border-border text-muted-foreground shadow-xs">
              {scene.id}
            </span>
          </div>

          <div className="absolute top-2 right-2">
            <span className="flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold bg-background/90 backdrop-blur-xs border border-border text-foreground shadow-xs">
              <Clock className="w-3 h-3 text-primary" />
              {scene.duration}s
            </span>
          </div>
        </div>

        {/* Content */}
        <div className="p-4 space-y-3 flex-1 flex flex-col justify-between">
          <div className="space-y-2">
            {scene.narration && (
              <p className="text-xs italic text-foreground bg-muted/40 p-2 rounded-lg border border-border/50 line-clamp-2">
                "{scene.narration}"
              </p>
            )}

            <div>
              <span className="text-[10px] font-bold tracking-wider text-muted-foreground uppercase">
                Visual Description
              </span>
              <p className="text-xs text-foreground/80 line-clamp-2 mt-0.5">
                {scene.visual_prompt}
              </p>
            </div>
          </div>

          {/* Action Footer */}
          <div className="pt-2 border-t border-border flex items-center justify-between gap-2">
            <span className="text-[11px] text-muted-foreground truncate font-medium">
              Camera: {scene.camera?.movement || 'static'}
            </span>

            <button
              type="button"
              id={`regenerate-scene-btn-${scene.id}`}
              onClick={() => setShowModal(true)}
              disabled={isRegenerating}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-primary-soft text-primary hover:bg-primary/20 border border-primary/20 transition-colors disabled:opacity-50"
            >
              <RotateCw className={`w-3.5 h-3.5 ${isRegenerating ? 'animate-spin' : ''}`} />
              Regenerate
            </button>
          </div>
        </div>
      </div>

      {/* Regeneration Modal */}
      {showModal && (
        <div
          id="regenerate-modal-backdrop"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-foreground/30 backdrop-blur-xs animate-in fade-in duration-200"
        >
          <div
            id="regenerate-modal-content"
            className="w-full max-w-md p-6 rounded-2xl border border-border bg-card shadow-xl space-y-4"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-primary/10 text-primary border border-primary/20">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-foreground">Regenerate Scene {index + 1}</h3>
                  <p className="text-xs text-muted-foreground">Modify prompt and camera instruction with AI</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="text-muted-foreground hover:text-foreground text-sm font-semibold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleRegenerate} className="space-y-4">
              <div>
                <label
                  htmlFor="regen-instruction"
                  className="block text-xs font-semibold text-foreground uppercase tracking-wide mb-1"
                >
                  Directing Instruction
                </label>
                <textarea
                  id="regen-instruction"
                  rows={3}
                  value={instruction}
                  onChange={(e) => setInstruction(e.target.value)}
                  placeholder="e.g., Make the camera zoom in faster, and change the background nebula from blue to glowing fiery red..."
                  className="w-full px-3 py-2 text-xs rounded-xl border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                  required
                />
              </div>

              {error && (
                <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {success && (
                <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 text-xs flex items-center gap-2">
                  <Check className="w-4 h-4 flex-shrink-0" />
                  <span>Scene updated successfully!</span>
                </div>
              )}

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-xs font-medium rounded-lg border border-border hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  id="submit-regen-btn"
                  disabled={loading || !instruction.trim()}
                  className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors shadow disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <RotateCw className="w-3.5 h-3.5 animate-spin" />
                      Regenerating...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-3.5 h-3.5" />
                      Apply & Regenerate
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
};
