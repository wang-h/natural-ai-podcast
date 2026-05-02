import React, { useState, useEffect } from 'react';
import { Download, ScrollText, ChevronLeft, Mic2, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';

export default function RunDetail() {
  const [runId, setRunId] = useState('');
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get('id');
    if (!id) {
      setError('No ID provided');
      setLoading(false);
      return;
    }
    setRunId(id);

    fetch(`/api/runs/${id}`)
      .then(res => {
        if (!res.ok) throw new Error('Run not found');
        return res.json();
      })
      .then(d => {
        setData(d);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) return (
    <div className="flex flex-col items-center justify-center py-60 gap-4">
      <div className="w-10 h-10 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin" />
    </div>
  );
  
  if (error) return (
    <div className="max-w-xl mx-auto py-40 text-center">
      <div className="bg-destructive/10 text-destructive p-6 rounded-2xl border border-destructive/20 font-mono text-sm">
        Error: {error}
      </div>
      <Button asChild variant="link" className="mt-8">
        <a href="/">← 返回首页</a>
      </Button>
    </div>
  );

  if (!data) return null;

  return (
    <div className="max-w-4xl mx-auto py-12 px-6 lg:px-12">
      <div className="mb-10">
        <Button asChild variant="ghost" size="sm" className="-ml-3 text-muted-foreground">
          <a href="/"><ChevronLeft size={16} className="mr-1" /> 返回列表</a>
        </Button>
      </div>

      <header className="flex flex-col md:flex-row md:items-end justify-between gap-8 mb-12 pb-8 border-b">
        <div className="space-y-4">
           <Badge variant="outline" className="font-mono opacity-60">ID: {data.id}</Badge>
           <h1 className="text-4xl lg:text-5xl font-[950] tracking-tight leading-tight">{data.id}</h1>
        </div>
        <div className="flex gap-4">
          {data.audio_url && (
            <Button asChild variant="gradient" size="lg" className="rounded-xl font-bold shadow-xl shadow-emerald-500/20 transition-transform hover:scale-105">
              <a href={data.audio_url} download>
                <Download size={18} className="mr-2" /> 下载音频
              </a>
            </Button>
          )}
        </div>
      </header>

      {data.audio_url && (
        <section className="mb-20 p-8 bg-muted/20 rounded-[2rem] border-2 border-dashed border-border/60">
           <div className="flex items-center gap-3 mb-6">
             <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white">
                <Mic2 size={16} />
             </div>
             <span className="font-black text-sm uppercase tracking-widest opacity-60">Audio Player</span>
           </div>
           <audio controls className="w-full h-12">
             <source src={data.audio_url} type="audio/mpeg" />
           </audio>
        </section>
      )}

      <section className="space-y-12">
        <div className="flex items-center gap-3">
           <ScrollText size={24} className="text-emerald-500" />
           <h2 className="text-2xl font-[900]">对谈脚本 (Script)</h2>
        </div>

        <div className="space-y-2">
          {data.lines.map((l: any, i: number) => (
            <div key={i} className="group py-8 first:pt-0 border-b last:border-0">
               <div className="flex flex-col md:flex-row gap-6 md:gap-12">
                  <div className="md:w-24 shrink-0 pt-1">
                    <span className={cn(
                      "text-[0.7rem] font-black uppercase tracking-[0.2em] px-2.5 py-1 rounded-full border",
                      l.speaker === '林深' ? "bg-blue-500/10 text-blue-600 border-blue-200" : "bg-purple-500/10 text-purple-600 border-purple-200"
                    )}>
                      {l.speaker}
                    </span>
                  </div>
                  <div className="flex-1">
                    <p className="text-lg md:text-xl leading-[1.8] font-medium text-foreground/90">
                      {l.text}
                    </p>
                  </div>
               </div>
            </div>
          ))}
        </div>
      </section>

      <div className="mt-24 pt-12 border-t text-center">
         <p className="text-sm text-muted-foreground flex items-center justify-center gap-2">
           <Sparkles size={14} /> 这一场对谈由 AI 自动编排并录制
         </p>
      </div>
    </div>
  );
}
