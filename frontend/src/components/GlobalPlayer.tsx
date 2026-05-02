import React, { useRef, useEffect } from 'react';
import { X } from 'lucide-react';

interface GlobalPlayerProps {
  currentEpisode: { url: string; title: string; date: string } | null;
  onClose: () => void;
}

export default function GlobalPlayer({ currentEpisode, onClose }: GlobalPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    if (currentEpisode && currentEpisode.url && audioRef.current) {
      audioRef.current.src = currentEpisode.url;
      audioRef.current.play().catch(err => console.log('Autoplay blocked:', err));
    }
  }, [currentEpisode]);

  if (!currentEpisode) return null;

  return (
    <div className="global-player active">
      <div className="player-info">
        <div className="player-title">{currentEpisode.title}</div>
        <div className="player-meta">{currentEpisode.date}</div>
      </div>
      <div className="player-controls">
        <audio ref={audioRef} controls className="main-audio-element">
          <source src="" type="audio/mpeg" />
        </audio>
      </div>
      <div style={{ width: '40px', display: 'flex', justifyContent: 'flex-end' }}>
        <button onClick={() => {
          if (audioRef.current) audioRef.current.pause();
          onClose();
        }} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted-foreground)' }}>
          <X />
        </button>
      </div>
    </div>
  );
}
