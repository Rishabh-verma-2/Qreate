import React from 'react';
import { Loader2, CheckCircle2, AlertCircle, Sparkles, Film, Wand2, Music, Clapperboard } from 'lucide-react';
import { cn } from '../../lib/utils';

interface GenerationProgressProps {
  status: string;
  progress: number;
  stage?: string;
  currentScene?: number;
  totalScenes?: number;
  errorMessage?: string;
  onRetry?: () => void;
}

const STAGES = [
  { key: 'plan', label: 'AI Director Planning', icon: Wand2, minProgress: 0 },
  { key: 'storyboard', label: 'Storyboard & Scenes', icon: Clapperboard, minProgress: 10 },
  { key: 'characters', label: 'Character References', icon: Sparkles, minProgress: 15 },
  { key: 'scenes', label: 'Scene Video Generation', icon: Film, minProgress: 20 },
  { key: 'audio', label: 'Audio & Narration', icon: Music, minProgress: 75 },
  { key: 'compose', label: 'Composing & Concat', icon: Film, minProgress: 85 },
];

export const GenerationProgress: React.FC<GenerationProgressProps> = ({
  status,
  progress,
  stage,
  currentScene,
  totalScenes,
  errorMessage,
  onRetry,
}) => {
  const isFailed = status === 'failed';
  const isCompleted = status === 'completed';

  return (
    <div
      id="generation-progress-container"
      className="p-6 rounded-2xl border border-border bg-card shadow-sm space-y-6"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {isCompleted ? (
            <div className="p-2.5 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-200">
              <CheckCircle2 className="w-6 h-6" />
            </div>
          ) : isFailed ? (
            <div className="p-2.5 rounded-xl bg-destructive/10 text-destructive border border-destructive/20">
              <AlertCircle className="w-6 h-6" />
            </div>
          ) : (
            <div className="p-2.5 rounded-xl bg-primary-soft text-primary border border-primary/20 animate-pulse">
              <Loader2 className="w-6 h-6 animate-spin" />
            </div>
          )}
          <div>
            <h3 className="text-base font-semibold text-foreground">
              {isCompleted
                ? 'Video Generation Complete'
                : isFailed
                ? 'Generation Failed'
                : 'AI Director Generating Video'}
            </h3>
            <p className="text-sm text-muted-foreground">
              {stage || (isCompleted ? 'Finished rendering final video' : 'Processing your scene plan...')}
              {currentScene && totalScenes ? ` (${currentScene}/${totalScenes} scenes)` : ''}
            </p>
          </div>
        </div>

        <div className="text-right">
          <span className="text-2xl font-bold tracking-tight text-foreground">{progress}%</span>
          <p className="text-xs uppercase tracking-wider text-muted-foreground font-medium">{status}</p>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="relative w-full h-3 bg-secondary rounded-full overflow-hidden p-0.5 border border-border/60">
        <div
          id="progress-fill-bar"
          className={cn(
            'h-full rounded-full transition-all duration-500 ease-out',
            isFailed
              ? 'bg-destructive'
              : isCompleted
              ? 'bg-emerald-500'
              : 'bg-primary'
          )}
          style={{ width: `${Math.max(progress, 3)}%` }}
        />
      </div>

      {/* Stage milestones */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2 pt-2">
        {STAGES.map((s) => {
          const Icon = s.icon;
          const isDone = isCompleted || progress > s.minProgress + 10;
          const isCurrent = !isCompleted && !isFailed && progress >= s.minProgress && progress <= s.minProgress + 15;

          return (
            <div
              key={s.key}
              className={cn(
                'flex flex-col items-center text-center p-2.5 rounded-xl border text-xs transition-all duration-200',
                isDone
                  ? 'border-emerald-300 bg-emerald-50 text-emerald-800'
                  : isCurrent
                  ? 'border-primary/40 bg-primary-soft text-primary font-medium shadow-xs ring-1 ring-primary/20'
                  : 'border-border/60 bg-muted/40 text-muted-foreground opacity-80'
              )}
            >
              <Icon className={cn('w-4 h-4 mb-1', isDone ? 'text-emerald-600' : isCurrent ? 'text-primary' : 'text-muted-foreground')} />
              <span className="truncate w-full">{s.label}</span>
            </div>
          );
        })}
      </div>

      {/* Error state */}
      {isFailed && (
        <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-center justify-between">
          <div className="space-y-1">
            <span className="font-semibold">Error occurred during generation:</span>
            <p className="text-xs text-destructive/80">{errorMessage || 'Scene rendering timed out or encountered GPU memory limit.'}</p>
          </div>
          {onRetry && (
            <button
              id="retry-generation-btn"
              onClick={onRetry}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-destructive text-destructive-foreground hover:bg-destructive/90 transition-colors shadow"
            >
              Retry
            </button>
          )}
        </div>
      )}
    </div>
  );
};
