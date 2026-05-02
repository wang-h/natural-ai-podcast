import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, Database, MessageSquare, Mic2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

export default function EpisodeList() {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeAudio, setActiveAudio] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    fetch('/api/runs')
      .then(res => res.json())
      .then(data => {
        setRuns(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const togglePlay = (url: string) => {
    if (activeAudio === url) {
      if (isPlaying) {
        audioRef.current?.pause();
        setIsPlaying(false);
      } else {
        audioRef.current?.play();
        setIsPlaying(true);
      }
    } else {
      setActiveAudio(url);
      setIsPlaying(true);
      if (audioRef.current) {
        audioRef.current.src = url;
        audioRef.current.play();
      }
    }
  };

  if (loading) {
    return <div className="flex flex-col items-center justify-center py-40">
      <div className="w-6 h-6 border-2 border-primary/20 border-t-primary rounded-full animate-spin" />
    </div>;
  }

  return (
    <div className="episode-list relative">
      <div className="absolute left-0 top-0 bottom-0 w-px bg-border/40 hidden md:block" />

      {runs.map((r: any, idx: number) => (
        <article className="episode-item relative pl-0 md:pl-16 py-20 border-b border-border/40 last:border-0" key={r.id}>
          {/* Index indicator */}
          <div className="absolute left-0 top-[5.5rem] hidden md:flex flex-col items-center">
            <span className="text-[0.6rem] font-mono font-black text-muted-foreground/30">
              {(runs.length - idx).toString().padStart(2, '0')}
            </span>
          </div>

          <time className="ep-date font-mono text-[0.65rem] uppercase tracking-[0.2em] text-muted-foreground/50 mb-4 block">
            {r.created}
          </time>
          
          <h3 className="ep-title text-3xl font-[1000] tracking-tighter mb-6">
            <a href={`/run/?id=${r.id}`} className="hover:text-[var(--theme-blue)] transition-colors">
              {r.id}
            </a>
            {r.has_deepling && (
              <Badge variant="gradient" className="ml-4 align-middle text-[0.55rem] py-0 px-2 rounded-sm tracking-widest font-black">
                DEEPLING
              </Badge>
            )}
          </h3>

          <div className="ep-summary text-foreground/80 text-lg leading-relaxed max-w-2xl mb-10 font-medium">
            {r.preview}
          </div>

          {/* IN-ARTICLE SCRIPT FLOW (THE SOUL) */}
          <div className="ep-script-preview space-y-6 mb-12 border-l-2 border-primary/5 pl-8 py-2">
            {r.lines && r.lines.map((line: any, i: number) => (
              <div key={i} className="flex flex-col gap-2">
                <span className={cn(
                  "text-[0.6rem] font-black uppercase tracking-[0.2em] opacity-40",
                  line.speaker === '林深' ? "text-blue-600" : "text-purple-600"
                )}>
                  {line.speaker}
                </span>
                <p className="text-[1.05rem] leading-relaxed text-foreground/90 font-medium italic">
                  “{line.text}”
                </p>
              </div>
            ))}
            <div className="pt-4">
              <a href={`/run/?id=${r.id}`} className="text-[0.7rem] font-black uppercase tracking-widest text-[var(--theme-blue)] hover:underline underline-offset-4">
                阅读完整脚本 →
              </a>
            </div>
          </div>
          
          <div className="ep-actions flex items-center gap-6">
            <button 
              onClick={() => togglePlay(r.audio_url)}
              className={cn(
                "flex items-center gap-3 px-6 py-2.5 rounded-full text-[0.8rem] font-black uppercase tracking-widest transition-all",
                activeAudio === r.audio_url && isPlaying 
                  ? "bg-foreground text-background scale-105 shadow-xl" 
                  : "bg-muted/30 text-foreground hover:bg-muted"
              )}
            >
              {activeAudio === r.audio_url && isPlaying ? <Pause size={14} className="fill-current" /> : <Play size={14} className="fill-current" />}
              <span>{activeAudio === r.audio_url && isPlaying ? '正在播放' : '点击试听'}</span>
            </button>
            
            <span className="text-border">/</span>
            
            <div className="flex items-center gap-2 text-muted-foreground opacity-40 text-xs font-bold">
              <MessageSquare size={14} />
              <span>{r.line_count} TURNS</span>
            </div>
          </div>
        </article>
      ))}

      {/* Hidden Global Audio Element */}
      <audio 
        ref={audioRef} 
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onEnded={() => { setIsPlaying(false); setActiveAudio(null); }}
        className="hidden"
      />
    </div>
  );
}
