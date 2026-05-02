import React, { useState, useEffect } from 'react';
import { Play, Database, MessageSquare } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

export default function EpisodeList() {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);

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

  if (loading) {
    return <div className="flex flex-col items-center justify-center py-40 gap-4">
      <div className="w-6 h-6 border-2 border-primary/20 border-t-primary rounded-full animate-spin" />
    </div>;
  }

  if (runs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-40 text-center text-muted-foreground">
        <Database size={40} className="mb-4 opacity-10" />
        <p className="text-sm font-medium">暂无播客内容</p>
      </div>
    );
  }

  return (
    <div className="episode-list">
      {runs.map((r: any) => (
        <article className="episode-item py-12 md:py-16 border-b border-border last:border-0" key={r.id}>
          <time className="ep-date font-mono text-[0.7rem] uppercase tracking-widest text-muted-foreground mb-4 block">
            {r.created}
          </time>
          
          <h3 className="ep-title text-2xl md:text-3xl font-[900] tracking-tight mb-4">
            <a href={`/run/?id=${r.id}`} className="hover:text-[var(--theme-blue)] transition-colors">
              {r.id}
            </a>
            {r.has_deepling && (
              <Badge variant="gradient" className="ml-4 align-middle text-[0.6rem] py-0 px-2 rounded-sm">
                DEEPLING
              </Badge>
            )}
          </h3>

          <div className="ep-summary text-foreground/70 text-[0.95rem] leading-relaxed max-w-2xl mb-8">
            {r.preview}
          </div>
          
          <div className="ep-actions flex items-center gap-4 text-[0.85rem] font-bold">
            <button 
              onClick={() => {
                if (!r.audio_url) return;
                window.dispatchEvent(new CustomEvent('play-episode', { detail: { url: r.audio_url, title: r.id, date: r.created } }));
              }}
              className="flex items-center gap-2 text-foreground hover:text-[var(--theme-blue)] transition-colors cursor-pointer"
              disabled={!r.audio_url}
            >
              <Play size={14} className="fill-current" />
              <span>播放</span>
            </button>
            
            <span className="text-muted-foreground/40 font-normal">/</span>
            
            <a href={`/run/?id=${r.id}`} className="text-foreground/80 hover:text-foreground hover:underline underline-offset-4">
              查看详情
            </a>

            <span className="text-muted-foreground/40 font-normal">/</span>
            
            <span className="text-muted-foreground font-medium flex items-center gap-1.5">
              <MessageSquare size={14} />
              {r.line_count} turns
            </span>
          </div>
        </article>
      ))}
    </div>
  );
}
