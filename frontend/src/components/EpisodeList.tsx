import React, { useState, useEffect } from 'react';
import { Play, Database, MessageSquare, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';

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
      <div className="w-8 h-8 border-4 border-emerald-500/20 border-t-emerald-500 rounded-full animate-spin" />
      <span className="text-sm font-medium text-muted-foreground animate-pulse">正在寻找深夜对谈...</span>
    </div>;
  }

  if (runs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-40 text-center text-muted-foreground">
        <Database size={48} className="mb-6 opacity-10" />
        <p className="text-lg font-medium">暂无播客内容</p>
        <p className="text-sm opacity-60 mt-2">快去左侧生成第一场对谈吧</p>
      </div>
    );
  }

  return (
    <div className="episode-list divide-y divide-border">
      {runs.map((r: any) => (
        <article className="episode-item group" key={r.id}>
          <time className="ep-date mb-3 block">{r.created}</time>
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
            <div className="flex-1 space-y-4">
              <h3 className="ep-title group-hover:text-emerald-600 transition-colors">
                <a href={`/run/?id=${r.id}`}>{r.id}</a>
                {r.has_deepling && <Badge variant="gradient" className="ml-4 align-middle">DEEPLING</Badge>}
              </h3>
              <p className="ep-summary text-muted-foreground leading-relaxed max-w-2xl">{r.preview}</p>
            </div>
          </div>
          
          <div className="ep-actions mt-8">
            <Button 
              onClick={() => onPlay(r.audio_url, r.id, r.created)}
              variant="default"
              size="sm"
              className="rounded-full px-6 font-bold h-10 shadow-lg shadow-emerald-500/20 transition-all hover:scale-105 active:scale-95"
            >
              <Play size={16} className="fill-current mr-2" /> 播放
            </Button>
            
            <Separator orientation="vertical" className="mx-2 h-4 hidden md:block" />
            <span className="text-muted-foreground mx-1 hidden md:inline">/</span>
            
            <Button asChild variant="ghost" size="sm" className="font-semibold text-muted-foreground hover:text-foreground">
              <a href={`/run/?id=${r.id}`}>查看详情</a>
            </Button>

            <div className="ml-auto flex items-center gap-6 text-[0.8rem] font-medium text-muted-foreground/60">
              <div className="flex items-center gap-1.5">
                <MessageSquare size={14} />
                <span>{r.line_count} turns</span>
              </div>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}
