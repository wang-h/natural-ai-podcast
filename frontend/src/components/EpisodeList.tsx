import React, { useState, useEffect, useRef } from 'react';
import { Database } from 'lucide-react';
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
    return <div className="flex items-center justify-center py-40">
      <div className="w-4 h-4 border border-primary/20 border-t-primary rounded-full animate-spin" />
    </div>;
  }

  return (
    <div className="episode-list">
      {runs.map((r: any) => (
        <article className="episode-item" key={r.id}>
          <time className="ep-date font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground mb-4 block">
            {r.created}
          </time>
          
          <h3 className="ep-title">
            <a href={`/run/?id=${r.id}`}>
              {r.id}
            </a>
          </h3>

          <div className="ep-summary mb-8">
            {r.preview}
          </div>
          
          <div className="ep-actions flex items-center gap-4 text-[10px] font-bold uppercase tracking-[0.2em]">
            <button 
              onClick={() => togglePlay(r.audio_url)}
              className={cn(
                "hover:text-[var(--theme-blue)] transition-colors cursor-pointer",
                activeAudio === r.audio_url && isPlaying ? "text-[var(--theme-blue)]" : "text-foreground"
              )}
            >
              {activeAudio === r.audio_url && isPlaying ? 'PAUSE' : 'PLAY'}
            </button>
            
            <span className="text-border">/</span>
            
            <a href={`/run/?id=${r.id}`} className="text-muted-foreground hover:text-foreground transition-colors">
              DETAILS
            </a>

            <span className="text-border">/</span>
            
            <span className="text-muted-foreground">
              {r.line_count} TURNS
            </span>
          </div>
        </article>
      ))}

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
