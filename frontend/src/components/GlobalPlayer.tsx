import React, { useRef, useEffect, useState, useCallback } from 'react';
import { X, Volume2, VolumeX, SkipForward, SkipBack } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';

export default function GlobalPlayer() {
  const [current, setCurrent] = useState<{ url: string; title: string; date: string } | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [volume, setVolume] = useState(1);
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    const handlePlay = (e: any) => {
      const { url, title, date } = e.detail;
      if (!url) return;

      setCurrent({ url, title, date });
      setIsPlaying(true);

      if (audioRef.current) {
        audioRef.current.src = url;
        audioRef.current.play().catch(err => console.error('Playback error:', err));
      }
    };

    window.addEventListener('play-episode', handlePlay);
    return () => window.removeEventListener('play-episode', handlePlay);
  }, []);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setProgress((audioRef.current.currentTime / audioRef.current.duration) * 100);
    }
  };

  const handleVolumeChange = useCallback((value: number[]) => {
    const v = value[0];
    setVolume(v);
    if (audioRef.current) {
      audioRef.current.volume = v;
    }
  }, []);

  const toggleMute = () => {
    if (!audioRef.current) return;
    if (volume > 0) {
      setVolume(0);
      audioRef.current.volume = 0;
    } else {
      setVolume(1);
      audioRef.current.volume = 1;
    }
  };

  return (
    <div className={`global-player ${current ? 'active' : ''} flex flex-col h-auto py-3 md:h-20 md:flex-row md:py-0 border-t bg-background/95 backdrop-blur-xl shadow-[0_-10px_40px_rgba(0,0,0,0.05)]`}>
      <div className="absolute top-0 left-0 right-0 h-1 bg-muted/30">
         <div
           className="h-full bg-emerald-500 transition-all duration-300"
           style={{ width: `${progress}%` }}
         />
      </div>

      {current && (
        <>
          <div className="player-info flex items-center px-6 md:w-80 shrink-0">
            <div className="w-10 h-10 rounded-lg bg-foreground flex items-center justify-center shrink-0 mr-4 shadow-lg">
              {isPlaying ? (
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="white" stroke="none"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="white" stroke="none" className="ml-0.5"><path d="M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z"/></svg>
              )}
            </div>
            <div className="overflow-hidden">
              <div className="player-title text-sm font-black truncate">{current.title}</div>
              <div className="player-meta text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground">{current.date}</div>
            </div>
          </div>

          <div className="player-controls flex-1 flex flex-col items-center justify-center px-4">
            <div className="flex items-center gap-6">
               <Button variant="ghost" size="icon" className="text-foreground/60 hover:text-foreground">
                 <SkipBack size={18} />
               </Button>
               <Button
                 onClick={togglePlay}
                 variant="outline"
                 size="icon"
                 className="w-10 h-10 rounded-full border-2 border-foreground/20 hover:border-foreground/40 hover:scale-105 transition-all bg-background text-foreground"
               >
                 {isPlaying ? (
                   <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor" stroke="none"><rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/></svg>
                 ) : (
                   <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor" stroke="none" className="ml-0.5"><path d="M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z"/></svg>
                 )}
               </Button>
               <Button variant="ghost" size="icon" className="text-foreground/60 hover:text-foreground">
                 <SkipForward size={18} />
               </Button>
            </div>
          </div>

          <div className="hidden md:flex items-center justify-end px-8 w-80 gap-4">
            <button onClick={toggleMute} className="text-foreground/60 hover:text-foreground transition-colors p-0 border-none bg-transparent cursor-pointer">
              {volume === 0 ? <VolumeX size={18} /> : <Volume2 size={18} />}
            </button>
            <Slider
              value={[volume]}
              max={1}
              step={0.01}
              onValueChange={handleVolumeChange}
              className="w-24"
            />
            <Button
              onClick={() => {
                if (audioRef.current) audioRef.current.pause();
                setCurrent(null);
                setIsPlaying(false);
              }}
              variant="ghost"
              size="icon"
              className="rounded-full text-foreground/40 hover:bg-destructive/10 hover:text-destructive transition-colors"
            >
              <X size={20} />
            </Button>
          </div>
        </>
      )}

      <audio
        ref={audioRef}
        onTimeUpdate={handleTimeUpdate}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        className="hidden"
      />
    </div>
  );
}
