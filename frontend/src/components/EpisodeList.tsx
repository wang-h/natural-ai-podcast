import React, { useState, useEffect } from 'react';
import { Play, Database, MessageSquare, Mic2, Hash } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

export default function EpisodeList({ onPlay }: { onPlay: (url: string, title: string, date: string) => void }) {
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

  // Helper to simulate "topics" since they might not be in API yet
  const getTopics = (id: string) => {
    if (id.includes('goblin')) return ["AI 文体测定", "身份还原", "OpenAI 封禁"];
    if (id.includes('cursor')) return ["9秒删库事故", "Cursor 安全性", "责任认定"];
    if (id.includes('deepseek')) return ["不可能三角", "多模态预览", "工程稳定性"];
    return ["AI 前沿动态", "深度技术解析", "人文视角"];
  };

  return (
    <div className="episode-list relative">
      {/* Decorative vertical line */}
      <div className="absolute left-0 top-0 bottom-0 w-px bg-border/40 hidden md:block" />

      {runs.map((r: any, idx: number) => (
        <article className="episode-item relative pl-0 md:pl-16 py-16 md:py-24 border-b border-border/40 last:border-0 group transition-all" key={r.id}>
          {/* Index Number */}
          <div className="absolute left-0 top-[4.5rem] hidden md:flex flex-col items-center">
            <span className="text-[0.7rem] font-mono font-black text-muted-foreground/30 group-hover:text-[var(--theme-blue)] transition-colors">
              {(runs.length - idx).toString().padStart(2, '0')}
            </span>
            <div className="w-2 h-2 rounded-full border-2 border-border bg-background mt-2 group-hover:border-[var(--theme-blue)] transition-colors" />
          </div>

          <time className="ep-date font-mono text-[0.7rem] uppercase tracking-[0.2em] text-muted-foreground/60 mb-4 block">
            {r.created}
          </time>
          
          <h3 className="ep-title text-3xl md:text-4xl font-[1000] tracking-tighter mb-6 group-hover:translate-x-1 transition-transform">
            <a href={`/run/?id=${r.id}`} className="hover:text-[var(--theme-blue)] transition-colors inline-flex items-center gap-4">
              {r.id}
              {r.has_deepling && (
                <Badge variant="gradient" className="text-[0.6rem] py-0 px-2 rounded-sm tracking-widest font-black">
                  DEEPLING
                </Badge>
              )}
            </a>
          </h3>

          <div className="ep-summary text-foreground/80 text-lg leading-relaxed max-w-2xl mb-6 font-medium">
            {r.preview}
          </div>

          {/* New Topics Section (Hacker Podcast Style) */}
          <div className="ep-topics mb-10">
            <ul className="flex flex-wrap gap-x-6 gap-y-2">
              {getTopics(r.id).map(topic => (
                <li key={topic} className="flex items-center gap-2 text-[0.8rem] font-bold text-muted-foreground/60">
                  <span className="w-1 h-1 rounded-full bg-border" />
                  {topic}
                </li>
              ))}
            </ul>
          </div>
          
          <div className="ep-actions flex items-center gap-6 text-[0.85rem] font-black uppercase tracking-widest">
            <button 
              onClick={() => onPlay(r.audio_url, r.id, r.created)}
              className="flex items-center gap-2 text-foreground hover:text-[var(--theme-blue)] transition-all cursor-pointer hover:scale-105 active:scale-95"
            >
              <Play size={16} className="fill-current text-[var(--theme-blue)]" />
              <span>播放</span>
            </button>
            
            <span className="text-border">/</span>
            
            <a href={`/run/?id=${r.id}`} className="text-muted-foreground hover:text-foreground hover:underline underline-offset-8 transition-colors">
              查看详情
            </a>

            <span className="text-border">/</span>
            
            <div className="flex items-center gap-2 text-muted-foreground opacity-40">
              <MessageSquare size={14} />
              <span>{r.line_count} TURNS</span>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}
