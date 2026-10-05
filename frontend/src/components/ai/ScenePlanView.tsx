import React from 'react';
import { Camera, Clock, User, ArrowRight, Video, Sparkles } from 'lucide-react';
import type { VideoPlan, VideoPlanScene } from '../../types';

interface ScenePlanViewProps {
  plan: VideoPlan;
  onSceneSelect?: (scene: VideoPlanScene) => void;
}

export const ScenePlanView: React.FC<ScenePlanViewProps> = ({ plan, onSceneSelect }) => {
  return (
    <div id="scene-plan-view-container" className="space-y-6">
      {/* Plan Header Summary */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-5 rounded-2xl bg-card border border-border shadow-sm">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-primary-soft text-primary border border-primary/20">
              {plan.style}
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-secondary text-secondary-foreground border border-border/60">
              {plan.aspect_ratio}
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-secondary text-secondary-foreground border border-border/60">
              {plan.fps} FPS
            </span>
          </div>
          <h2 className="text-xl font-bold tracking-tight text-foreground">{plan.title}</h2>
        </div>

        <div className="flex items-center gap-3 text-sm text-muted-foreground">
          <div className="flex items-center gap-1.5 bg-background px-3 py-1.5 rounded-xl border border-border shadow-xs">
            <Clock className="w-4 h-4 text-primary" />
            <span className="font-semibold text-foreground">{plan.total_duration}s</span> total
          </div>
          <div className="flex items-center gap-1.5 bg-background px-3 py-1.5 rounded-xl border border-border shadow-xs">
            <Video className="w-4 h-4 text-indigo-600" />
            <span className="font-semibold text-foreground">{plan.scenes.length}</span> scenes
          </div>
          {plan.characters?.length > 0 && (
            <div className="flex items-center gap-1.5 bg-background px-3 py-1.5 rounded-xl border border-border shadow-xs">
              <User className="w-4 h-4 text-purple-600" />
              <span className="font-semibold text-foreground">{plan.characters.length}</span> characters
            </div>
          )}
        </div>
      </div>

      {/* Characters Showcase */}
      {plan.characters && plan.characters.length > 0 && (
        <div className="p-4 rounded-xl border border-border bg-card space-y-3 shadow-xs">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-primary" />
            Characters & Consistency
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {plan.characters.map((char) => (
              <div
                key={char.id}
                className="flex items-start gap-3 p-3 rounded-xl bg-background border border-border hover:border-primary/40 transition-colors shadow-xs"
              >
                <div className="w-10 h-10 rounded-lg bg-primary-soft border border-primary/20 flex items-center justify-center font-bold text-sm text-primary flex-shrink-0">
                  {char.name.charAt(0)}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-foreground truncate">{char.name}</h4>
                    <span className="text-[10px] text-muted-foreground font-mono">{char.id}</span>
                  </div>
                  <p className="text-xs text-muted-foreground line-clamp-2 mt-0.5">{char.description || char.appearance}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Scenes Grid */}
      <div className="space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Storyboard Scenes ({plan.scenes.length})
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {plan.scenes.map((scene, idx) => (
            <div
              key={scene.id || idx}
              id={`scene-card-${scene.id}`}
              onClick={() => onSceneSelect?.(scene)}
              className="group relative flex flex-col justify-between p-4 rounded-2xl border border-border bg-card hover:border-primary/50 transition-all duration-200 shadow-xs hover:shadow-sm cursor-pointer"
            >
              <div className="space-y-3">
                {/* Scene Header */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="flex items-center justify-center w-6 h-6 rounded-md bg-primary-soft text-primary font-bold text-xs border border-primary/20">
                      {idx + 1}
                    </span>
                    <span className="text-xs font-mono text-muted-foreground">{scene.id}</span>
                  </div>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-secondary text-secondary-foreground border border-border/50 flex items-center gap-1">
                    <Clock className="w-3 h-3 text-primary" />
                    {scene.duration}s
                  </span>
                </div>

                {/* Narration */}
                {scene.narration && (
                  <div className="p-2.5 rounded-xl bg-muted/40 border border-border/50 text-xs text-foreground italic">
                    "{scene.narration}"
                  </div>
                )}

                {/* Visual Prompt */}
                <div>
                  <span className="text-[11px] font-semibold text-muted-foreground block mb-0.5 uppercase tracking-wide">
                    Visual Prompt
                  </span>
                  <p className="text-xs text-foreground/90 line-clamp-3 leading-relaxed">
                    {scene.visual_prompt}
                  </p>
                </div>

                {/* Motion Prompt */}
                {scene.motion_prompt && (
                  <div>
                    <span className="text-[11px] font-semibold text-muted-foreground block mb-0.5 uppercase tracking-wide">
                      Motion
                    </span>
                    <p className="text-xs text-muted-foreground line-clamp-2">
                      {scene.motion_prompt}
                    </p>
                  </div>
                )}
              </div>

              {/* Scene Footer Badges */}
              <div className="pt-3 mt-3 border-t border-border flex items-center justify-between text-[11px] text-muted-foreground">
                <div className="flex items-center gap-1.5">
                  <Camera className="w-3.5 h-3.5 text-primary" />
                  <span className="truncate max-w-[120px]">
                    {scene.camera?.movement || scene.camera?.shot_type || 'standard'}
                  </span>
                </div>

                <div className="flex items-center gap-1 font-mono text-[10px]">
                  <span>{scene.transition_in || 'cut'}</span>
                  <ArrowRight className="w-2.5 h-2.5" />
                  <span>{scene.transition_out || 'cut'}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
