import React, { useRef, useEffect, useState } from 'react';
import { X, Play, Pause } from 'lucide-react';

export default function GlobalPlayer() {
  const [current, setCurrent] = useState<{ url: string; title: string; date: string } | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    const handlePlay = (e: any) => {
      const { url, title, date } = e.detail;
      if (!url) return;
      
      setCurrent({ url, title, date });
      setIsPlaying(true);
      
      if (audioRef.current) {
        audioRef.current.src = url;
        audioRef.current.play().catch(err => console.log('Autoplay blocked:', err));
      }
    };

    window.addEventListener('play-episode', handlePlay);
    return () => window.removeEventListener('play-episode', handlePlay);
  }, []);

  if (!current) return null;

  return (
    <div className="global-player active">
      <div className="player-info">
        <div className="player-title">{current.title}</div>
        <div className="player-meta">{current.date}</div>
      </div>
      
      <div className="player-controls">
        <audio 
          ref={audioRef} 
          controls 
          className="main-audio-element"
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
        >
          <source src={current.url} type="audio/mpeg" />
        </audio>
      </div>

      <div style={{ width: '40px', display: 'flex', justifyContent: 'flex-end' }}>
        <button 
          onClick={() => {
            if (audioRef.current) audioRef.current.pause();
            setCurrent(null);
          }} 
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted-foreground)' }}
        >
          <X size={20} />
        </button>
      </div>
    </div>
  );
}
