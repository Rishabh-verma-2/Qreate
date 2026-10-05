import React, { useState, useEffect, useRef } from 'react';
import {
  Wand2,
  Film,
  Sparkles,
  RotateCw,
  Cpu,
  Layers,
  Download,
  CheckCircle2,
} from 'lucide-react';
import { aiDirectorApi } from '../services/api';
import type { VideoPlan, DiagnosticsResponse } from '../types';
import { ScenePlanView } from '../components/ai/ScenePlanView';
import { SceneCard } from '../components/ai/SceneCard';
import { GenerationProgress } from '../components/ai/GenerationProgress';
import { useToast } from '../components/ui/Toast';

const PROMPT_SUGGESTIONS = [
  'A lone astronaut discovers an ancient glowing alien temple buried deep within Martian red dust dunes.',
  'Cyberpunk ramen stall in a rainy Tokyo back-alley, holographic neon reflections splashing across puddles.',
  'Bioluminescent deep-sea jellyfish interacting with a futuristic robotic submersible near hydrothermal vents.',
  'A craftsman blacksmith forging an enchanted sword that glows with emerald embers under starlight.',
];

const STYLES = [
  { id: 'cinematic 3D animation', label: 'Cinematic 3D', desc: 'Pixar / Unreal Engine style visuals' },
  { id: 'photorealistic', label: 'Photorealistic', desc: 'Lifelike camera lenses and cinematic lighting' },
  { id: 'cyberpunk sci-fi', label: 'Cyberpunk Sci-Fi', desc: 'Vibrant neon hues and gritty retrofuturism' },
  { id: 'dark fantasy', label: 'Dark Fantasy', desc: 'Moody atmospheric lighting and rich textures' },
  { id: 'documentary', label: 'Documentary', desc: 'Naturalistic handheld camera and realistic color grading' },
];

export const AiDirectorStudio: React.FC = () => {
  const toast = useToast();
  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    if (type === 'success') toast.success(message);
    else if (type === 'error') toast.error(message);
    else toast.info(message);
  };

  // Form State
  const [prompt, setPrompt] = useState('');
  const [style, setStyle] = useState('cinematic 3D animation');
  const [duration, setDuration] = useState<number>(30);
  const [aspectRatio, setAspectRatio] = useState<'16:9' | '9:16' | '1:1'>('16:9');
  const [wanMode, setWanMode] = useState<'t2v' | 'i2v'>('t2v');
  const [quality, setQuality] = useState<'development' | 'production'>('development');

  // Async & Execution State
  const [diagnostics, setDiagnostics] = useState<DiagnosticsResponse | null>(null);

  const [isPlanning, setIsPlanning] = useState(false);
  const [videoPlan, setVideoPlan] = useState<VideoPlan | null>(null);
  const [planId, setPlanId] = useState<string | null>(null);

  const [taskId, setTaskId] = useState<string | null>(null);
  const [taskStatus, setTaskStatus] = useState<string>('idle');
  const [taskProgress, setTaskProgress] = useState<number>(0);
  const [taskStage, setTaskStage] = useState<string>('');
  const [currentScene, setCurrentScene] = useState<number>(0);
  const [totalScenes, setTotalScenes] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [finalVideoUrl, setFinalVideoUrl] = useState<string | null>(null);

  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Load diagnostics on mount
  useEffect(() => {
    aiDirectorApi.diagnostics().then((diag) => {
      setDiagnostics(diag);
    }).catch(() => {});

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  // Poll video generation task status
  const startPolling = (id: string) => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);

    pollIntervalRef.current = setInterval(async () => {
      try {
        const res = await aiDirectorApi.getStatus(id);
        if (!res) return;

        setTaskStatus(res.status);
        setTaskProgress(res.progress || 0);
        setTaskStage(res.stage || '');
        if (res.current_scene) setCurrentScene(res.current_scene);
        if (res.total_scenes) setTotalScenes(res.total_scenes);

        if (res.status === 'completed') {
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          setFinalVideoUrl(res.cloudinary_url || null);
          showToast('Video generation completed successfully!', 'success');
        } else if (res.status === 'failed') {
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          setErrorMessage(res.error_message || 'Video generation failed.');
          showToast(res.error_message || 'Video generation failed', 'error');
        }
      } catch (err: any) {
        console.error('Error polling status:', err);
      }
    }, 3000);
  };

  // Step 1: Plan with Qwen3
  const handlePlanVideo = async () => {
    if (!prompt.trim()) {
      showToast('Please enter a video concept first', 'error');
      return;
    }

    setIsPlanning(true);
    setVideoPlan(null);
    setErrorMessage(null);

    try {
      showToast('AI Director is planning your screenplay...', 'info');
      const res = await aiDirectorApi.plan({
        prompt: prompt.trim(),
        style,
        duration,
        aspect_ratio: aspectRatio,
      });

      if (res.plan) {
        setVideoPlan(res.plan);
        setPlanId(res.plan_id);
        showToast('Storyboard planned successfully!', 'success');
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to generate video plan');
      showToast(err.message || 'Video planning failed', 'error');
    } finally {
      setIsPlanning(false);
    }
  };

  // Step 2: Kick off Wan2.1 Generation Pipeline
  const handleGenerateVideo = async () => {
    if (!prompt.trim()) {
      showToast('Please enter a video concept first', 'error');
      return;
    }

    setTaskStatus('queued');
    setTaskProgress(0);
    setTaskStage('Queueing task...');
    setErrorMessage(null);
    setFinalVideoUrl(null);

    try {
      const task = await aiDirectorApi.generate({
        prompt: prompt.trim(),
        style,
        duration,
        aspect_ratio: aspectRatio,
        engine: 'wan',
        wan_mode: wanMode,
        quality,
        plan_id: planId || undefined,
      });

      setTaskId(task.id);
      showToast('Custom video generation queued!', 'info');
      startPolling(task.id);
    } catch (err: any) {
      setTaskStatus('failed');
      setErrorMessage(err.message || 'Failed to submit generation task');
      showToast(err.message || 'Failed to queue generation', 'error');
    }
  };

  // Scene regeneration handler
  const handleRegenerateScene = async (sceneId: string, instruction: string) => {
    const targetId = taskId || planId;
    if (!targetId) {
      showToast('No active video or plan to regenerate scene for', 'error');
      return;
    }

    const res = await aiDirectorApi.regenerateScene(targetId, sceneId, instruction);
    if (res?.scene && videoPlan) {
      const updatedScenes = videoPlan.scenes.map((s) => (s.id === sceneId ? res.scene : s));
      setVideoPlan({ ...videoPlan, scenes: updatedScenes });
      showToast(`Scene ${sceneId} instruction updated!`, 'success');
    }
  };

  return (
    <div id="ai-director-studio" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-card border border-border p-6 sm:p-8 shadow-xs">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 rounded-full text-xs font-semibold bg-primary-soft text-primary border border-primary/20 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5" />
                AI Video Director
              </span>
              <span className="px-3 py-1 rounded-full text-xs font-semibold bg-secondary text-secondary-foreground border border-border">
                Custom Video Mode
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground">
              Autonomous AI Video Director
            </h1>
            <p className="text-sm text-muted-foreground max-w-2xl leading-relaxed">
              Generate completely custom videos from scratch with full creative control and no limits.
              AI plans the screenplay, camera direction, and transitions for each unique piece.
            </p>
          </div>

          {/* Diagnostics Widget */}
          <div className="flex flex-col gap-2 p-4 rounded-xl bg-background border border-border shadow-xs min-w-[240px]">
            <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-primary" />
              Engine Diagnostics
            </span>
            <div className="space-y-1.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Qwen3 LLM:</span>
                <span className={diagnostics?.qwen?.available ? 'text-emerald-600 font-semibold' : 'text-amber-600 font-semibold'}>
                  {diagnostics?.qwen?.available ? 'Ready (Local)' : 'Cloud Fallback'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">ComfyUI:</span>
                <span className={diagnostics?.comfyui?.available ? 'text-emerald-600 font-semibold' : 'text-muted-foreground'}>
                  {diagnostics?.comfyui?.available ? 'Connected' : 'CLI Fallback'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Wan Video Engine:</span>
                <span className={diagnostics?.video_engine_ready ? 'text-emerald-600 font-semibold' : 'text-amber-600 font-semibold'}>
                  {diagnostics?.video_engine_ready ? 'Ready (GPU)' : 'Native Engine'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Studio Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Directing Console (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          <div className="p-6 rounded-2xl bg-card border border-border shadow-xs space-y-6">
            <div className="flex items-center justify-between border-b border-border pb-4">
              <h2 className="text-base font-bold text-foreground flex items-center gap-2">
                <Wand2 className="w-4 h-4 text-primary" />
                Director Console
              </h2>
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-primary-soft text-primary font-medium border border-primary/20">
                Custom Video
              </span>
            </div>

            {/* Prompt Input */}
            <div className="space-y-2">
              <label htmlFor="director-prompt" className="block text-xs font-semibold text-foreground uppercase tracking-wide">
                Video Concept & Vision
              </label>
              <textarea
                id="director-prompt"
                rows={4}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Describe your custom video concept in natural language (no limits — stories, tutorials, scenes)..."
                className="w-full px-3.5 py-2.5 text-sm rounded-xl border border-input bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary leading-relaxed"
              />

              {/* Suggestions */}
              <div className="space-y-1 pt-1">
                <span className="text-[11px] text-muted-foreground font-medium">Quick Starters:</span>
                <div className="flex flex-wrap gap-1.5">
                  {PROMPT_SUGGESTIONS.map((s, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => setPrompt(s)}
                      className="text-xs px-2.5 py-1 rounded-lg bg-secondary hover:bg-primary-soft hover:text-primary border border-border text-muted-foreground transition-colors text-left truncate max-w-full"
                    >
                      {s.slice(0, 48)}...
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Visual Style */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-foreground uppercase tracking-wide">
                Visual Art Style
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {STYLES.map((st) => (
                  <button
                    key={st.id}
                    type="button"
                    onClick={() => setStyle(st.id)}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      style === st.id
                        ? 'border-primary bg-primary-soft text-primary ring-1 ring-primary/30'
                        : 'border-border bg-background hover:border-primary/40 text-muted-foreground'
                    }`}
                  >
                    <div className="font-semibold text-xs text-foreground">{st.label}</div>
                    <div className="text-[11px] text-muted-foreground truncate mt-0.5">{st.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Duration & Aspect Ratio */}
            <div className="space-y-3">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="block text-xs font-semibold text-foreground uppercase tracking-wide">
                    Duration
                  </label>
                  <span className="text-xs font-medium text-primary">{duration}s</span>
                </div>
                <div className="flex flex-wrap gap-1.5 items-center">
                  {[15, 30, 60, 90, 120].map((sec) => (
                    <button
                      key={sec}
                      type="button"
                      onClick={() => setDuration(sec)}
                      className={`px-3 py-1.5 text-xs font-semibold rounded-lg border transition-all ${
                        duration === sec
                          ? 'border-primary bg-primary text-primary-foreground shadow-xs'
                          : 'border-border bg-background text-foreground hover:bg-secondary'
                      }`}
                    >
                      {sec}s
                    </button>
                  ))}
                  <div className="flex items-center gap-1 ml-auto">
                    <input
                      type="number"
                      min={5}
                      max={600}
                      value={duration}
                      onChange={(e) => setDuration(Math.max(5, parseInt(e.target.value) || 5))}
                      aria-label="Custom duration in seconds"
                      className="w-16 px-2 py-1 text-xs rounded-lg border border-border bg-background text-foreground text-center focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                    <span className="text-xs text-muted-foreground">sec</span>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <label className="block text-xs font-semibold text-foreground uppercase tracking-wide">
                  Aspect Ratio
                </label>
                <div className="flex gap-2">
                  {(['16:9', '9:16', '1:1'] as const).map((ratio) => (
                    <button
                      key={ratio}
                      type="button"
                      onClick={() => setAspectRatio(ratio)}
                      className={`flex-1 py-2 text-xs font-semibold rounded-lg border transition-all ${
                        aspectRatio === ratio
                          ? 'border-primary bg-primary text-primary-foreground shadow-xs'
                          : 'border-border bg-background text-foreground hover:bg-secondary'
                      }`}
                    >
                      {ratio}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Video Engine & Quality Mode */}
            <div className="grid grid-cols-2 gap-4 pt-2 border-t border-border">
              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-foreground uppercase tracking-wide">
                  Generation Mode
                </label>
                <select
                  value={wanMode}
                  onChange={(e) => setWanMode(e.target.value as any)}
                  className="w-full px-3 py-2 text-xs rounded-xl border border-input bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="t2v">T2V (Scene-based)</option>
                  <option value="i2v">I2V (Character Consistent)</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-foreground uppercase tracking-wide">
                  Quality Tier
                </label>
                <select
                  value={quality}
                  onChange={(e) => setQuality(e.target.value as any)}
                  className="w-full px-3 py-2 text-xs rounded-xl border border-input bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="development">Dev (Fast 1.3B)</option>
                  <option value="production">Prod (Wan2.1 14B)</option>
                </select>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-3 pt-2">
              <button
                type="button"
                id="plan-video-btn"
                onClick={handlePlanVideo}
                disabled={isPlanning || !prompt.trim()}
                className="flex-1 inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl font-semibold text-xs border border-primary/30 bg-primary-soft text-primary hover:bg-primary/20 transition-all shadow-xs disabled:opacity-50"
              >
                {isPlanning ? (
                  <>
                    <RotateCw className="w-4 h-4 animate-spin" />
                    Planning Storyboard...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    1. Plan Storyboard
                  </>
                )}
              </button>

              <button
                type="button"
                id="generate-video-btn"
                onClick={handleGenerateVideo}
                disabled={taskStatus === 'in_progress' || !prompt.trim()}
                className="flex-1 inline-flex items-center justify-center gap-2 px-5 py-3 rounded-xl font-semibold text-xs bg-primary text-primary-foreground hover:bg-primary/90 transition-all shadow-sm disabled:opacity-50"
              >
                <Film className="w-4 h-4" />
                2. Generate Video
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Storyboard, Progress & Scene Outputs (7 cols) */}
        <div className="lg:col-span-7 space-y-8">
          {/* Active Generation Progress */}
          {taskStatus !== 'idle' && (
            <GenerationProgress
              status={taskStatus}
              progress={taskProgress}
              stage={taskStage}
              currentScene={currentScene}
              totalScenes={totalScenes}
              errorMessage={errorMessage || undefined}
              onRetry={handleGenerateVideo}
            />
          )}

          {/* Finished Master Video Showcase */}
          {finalVideoUrl && (
            <div
              id="final-video-showcase"
              className="p-6 rounded-2xl bg-card border border-border shadow-sm space-y-4 animate-in fade-in duration-300"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-200">
                    <CheckCircle2 className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-foreground">Finished Custom AI Video</h3>
                    <p className="text-xs text-muted-foreground">Composed scenes with voiceover narration and transitions</p>
                  </div>
                </div>

                <a
                  href={finalVideoUrl}
                  download="qreate_custom_video.mp4"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 transition-colors shadow-xs"
                >
                  <Download className="w-4 h-4" />
                  Download MP4
                </a>
              </div>

              <div className="rounded-xl overflow-hidden aspect-video bg-neutral-900 border border-border shadow-inner">
                <video
                  src={finalVideoUrl}
                  controls
                  className="w-full h-full object-contain"
                  autoPlay
                />
              </div>
            </div>
          )}

          {/* Storyboard Plan View */}
          {videoPlan ? (
            <div className="space-y-6">
              <ScenePlanView plan={videoPlan} />

              {/* Rendered Scene Clips Grid with Individual Regenerate Buttons */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                    <Layers className="w-4 h-4 text-primary" />
                    Scene Clips & Director Re-Shoots
                  </h3>
                  <span className="text-xs text-muted-foreground">
                    Click "Regenerate" on any scene to give directing notes
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {videoPlan.scenes.map((scene, idx) => (
                    <SceneCard
                      key={scene.id || idx}
                      scene={scene}
                      index={idx}
                      onRegenerate={handleRegenerateScene}
                    />
                  ))}
                </div>
              </div>
            </div>
          ) : (
            /* Empty State */
            <div className="flex flex-col items-center justify-center p-12 rounded-2xl border border-dashed border-border bg-card/40 text-center space-y-4">
              <div className="w-16 h-16 rounded-2xl bg-primary-soft border border-primary/20 flex items-center justify-center text-primary">
                <Sparkles className="w-8 h-8" />
              </div>
              <div className="space-y-1 max-w-sm">
                <h3 className="text-base font-bold text-foreground">No Storyboard Planned Yet</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Enter your custom video idea on the left and click <strong className="text-foreground">"1. Plan Storyboard"</strong> to preview
                  scenes, camera angles, and character consistency.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AiDirectorStudio;
