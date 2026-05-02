import React, { useRef, useEffect, useState } from 'react';
import { X, Play, Pause, Volume2, SkipForward, SkipBack } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function GlobalPlayer() {
  const [current, setCurrent] = useState<{ url: string; title: string; date: string } | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    const handlePlay = (e: any) => {
      const { url, title, date } = e.detail;
      if (!url) return;
      
      console.log('GlobalPlayer received play-episode:', title);
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

  // Always render the container, but hide it with CSS when no current episode
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
            <div className="w-10 h-10 rounded-lg bg-[var(--theme-gradient)] flex items-center justify-center text-white shrink-0 mr-4 shadow-lg shadow-emerald-500/20">
              {isPlaying ? <Pause size={16} className="fill-current" /> : <Play size={16} className="fill-current ml-0.5" />}
            </div>
            <div className="overflow-hidden">
              <div className="player-title text-sm font-black truncate">{current.title}</div>
              <div className="player-meta text-[0.6rem] font-bold uppercase tracking-widest text-muted-foreground">{current.date}</div>
            </div>
          </div>
          
          <div className="player-controls flex-1 flex flex-col items-center justify-center px-4">
            <div className="flex items-center gap-6">
               <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground">
                 <SkipBack size={18} />
               </Button>
               <Button 
                 onClick={togglePlay}
                 variant="outline" 
                 size="icon" 
                 className="w-10 h-10 rounded-full border-2 border-primary/10 hover:border-primary/20 hover:scale-105 transition-all bg-background"
               >
                 {isPlaying ? <Pause size={20} className="fill-current" /> : <Play size={20} className="fill-current ml-0.5" />}
               </Button>
               <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground">
                 <SkipForward size={18} />
               </Button>
            </div>
          </div>

          <div className="hidden md:flex items-center justify-end px-8 w-80 gap-6">
            <div className="flex items-center gap-3 text-muted-foreground opacity-40">
              <Volume2 size={18} />
              <div className="w-24 h-1 bg-muted rounded-full overflow-hidden">
                 <div className="w-2/3 h-full bg-foreground/20" />
              </div>
            </div>
            <Button 
              onClick={() => {
                if (audioRef.current) audioRef.current.pause();
                setCurrent(null);
                setIsPlaying(false);
              }} 
              variant="ghost" 
              size="icon" 
              className="rounded-full hover:bg-destructive/10 hover:text-destructive transition-colors"
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
