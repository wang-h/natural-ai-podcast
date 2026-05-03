import React, { useState, useEffect } from 'react';
import { Play, Pause, VolumeX } from 'lucide-react';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

export default function EpisodeList() {
  const [runs, setRuns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [playingUrl, setPlayingUrl] = useState<string | null>(null);

  useEffect(() => {
    fetch('/static-data/runs.json')
      .then(res => {
        if (!res.ok) throw new Error('no static data');
        return res.json();
      })
      .then(data => {
        setRuns(data);
        setLoading(false);
      })
      .catch(() => {
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
      });
  }, []);

  // Listen for GlobalPlayer state changes
  useEffect(() => {
    const handlePlay = () => {
      // GlobalPlayer dispatches custom events; we sync via audio element events
    };
    const audio = document.querySelector('audio');
    if (!audio) return;

    const onPlay = () => {
      setPlayingUrl(audio.src || null);
    };
    const onPause = () => {
      setPlayingUrl(null);
    };
    const onEnded = () => {
      setPlayingUrl(null);
    };

    audio.addEventListener('play', onPlay);
    audio.addEventListener('pause', onPause);
    audio.addEventListener('ended', onEnded);

    return () => {
      audio.removeEventListener('play', onPlay);
      audio.removeEventListener('pause', onPause);
      audio.removeEventListener('ended', onEnded);
    };
  }, []);

  const handlePlay = (r: any) => {
    if (!r.audio_url) {
      toast('该节目暂无音频', { icon: '🔇' });
      return;
    }
    window.dispatchEvent(new CustomEvent('play-episode', {
      detail: { url: r.audio_url, title: r.id, date: r.created }
    }));
    toast(`正在播放: ${r.id}`, { icon: '🎧' });
  };

  if (loading) {
    return <div className="flex items-center justify-center py-40">
      <div className="w-4 h-4 border border-primary/20 border-t-primary rounded-full animate-spin" />
    </div>;
  }

  return (
    <div className="episode-list">
      {runs.map((r: any) => {
        const hasAudio = !!r.audio_url;
        const isCurrentPlaying = playingUrl && playingUrl.includes(r.audio_url);

        return (
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
                onClick={() => handlePlay(r)}
                disabled={!hasAudio}
                className={cn(
                  "flex items-center gap-2 transition-colors cursor-pointer border-none bg-transparent p-0",
                  hasAudio ? "text-foreground hover:text-[var(--theme-blue)]" : "text-muted-foreground/40 cursor-not-allowed",
                  isCurrentPlaying && "text-[var(--theme-blue)]"
                )}
              >
                {!hasAudio ? (
                  <><VolumeX size={12} /> NO AUDIO</>
                ) : isCurrentPlaying ? (
                  <><Pause size={12} /> PAUSE</>
                ) : (
                  <><Play size={12} /> PLAY</>
                )}
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
        );
      })}
    </div>
  );
}
