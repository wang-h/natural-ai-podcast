import React, { useState, useEffect } from 'react';
import { Download, ScrollText, ChevronLeft, Mic2, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { cn } from "@/lib/utils";

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
      <div className="w-8 h-8 border-3 border-blue-500/20 border-t-blue-500 rounded-full animate-spin" />
    </div>
  );
  
  if (!data) return null;

  return (
    <div className="max-w-4xl mx-auto py-12 px-10 md:px-16">
      <div className="mb-8">
        <Button asChild variant="ghost" size="sm" className="-ml-3 text-muted-foreground hover:text-foreground">
          <a href="/"><ChevronLeft size={16} className="mr-1" /> 返回</a>
        </Button>
      </div>

      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-12 pb-8 border-b">
        <div className="space-y-2">
           <Badge variant="outline" className="font-mono text-[0.6rem] opacity-50">ID: {data.id}</Badge>
           <h1 className="text-3xl md:text-4xl font-[950] tracking-tight leading-tight">{data.id}</h1>
        </div>
        {data.audio_url && (
          <Button asChild variant="gradient" className="rounded-xl font-bold">
            <a href={data.audio_url} download>
              <Download size={16} className="mr-2" /> 下载音频
            </a>
          </Button>
        )}
      </header>

      {data.audio_url && (
        <section className="mb-16 p-8 bg-muted/20 rounded-[2rem] border border-border/60">
           <div className="flex items-center gap-3 mb-6 opacity-40">
              <Mic2 size={16} /><span className="font-black text-[0.6rem] uppercase tracking-widest">Player</span>
           </div>
           <audio controls className="w-full h-10">
             <source src={data.audio_url} type="audio/mpeg" />
           </audio>
        </section>
      )}

      <section className="space-y-10">
        <div className="flex items-center gap-2 opacity-60">
           <ScrollText size={18} /><h2 className="text-xl font-[900]">对谈脚本</h2>
        </div>

        <div className="space-y-0">
          {data.lines.map((l: any, i: number) => (
            <div key={i} className="py-6 border-b last:border-0">
               <div className="flex flex-col md:flex-row gap-4 md:gap-10">
                  <div className="md:w-20 shrink-0">
                    <span className={cn(
                      "text-[0.6rem] font-black uppercase tracking-[0.2em] px-2.5 py-1 rounded-full border",
                      l.speaker === '林深' ? "bg-blue-500/5 text-blue-600 border-blue-200/50" : "bg-purple-500/5 text-purple-600 border-purple-200/50"
                    )}>
                      {l.speaker}
                    </span>
                  </div>
                  <div className="flex-1">
                    <p className="text-base md:text-lg leading-relaxed font-medium text-foreground/90">
                      {l.text}
                    </p>
                  </div>
               </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
