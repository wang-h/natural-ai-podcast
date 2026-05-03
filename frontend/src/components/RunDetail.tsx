import React, { useState, useEffect, useCallback } from 'react';
import { Download, ScrollText, ChevronLeft, Sparkles, Copy, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { cn } from "@/lib/utils";

export default function RunDetail() {
  const BASE = import.meta.env.BASE_URL || '/';
  const resolveUrl = (url: string) => url.startsWith('/') ? `${BASE}${url.slice(1)}` : url;
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

    const BASE = import.meta.env.BASE_URL || '/';
    fetch(`${BASE}static-data/runs/${id}.json`)
      .then(res => {
        if (!res.ok) throw new Error('no static data');
        return res.json();
      })
      .then(d => {
        setData(d);
        setLoading(false);
      })
      .catch(() => {
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
            <a href={resolveUrl(data.audio_url)} download>
              <Download size={16} className="mr-2" /> 下载音频
            </a>
          </Button>
        )}
      </header>

      {data.audio_url && (
        <section className="mb-16">
           <button
             onClick={() => {
               if (data.audio_url) {
                 window.dispatchEvent(new CustomEvent('play-episode', { detail: { url: resolveUrl(data.audio_url), title: data.id, date: '' } }));
               }
             }}
             className="w-full group relative overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-r from-blue-500/5 via-emerald-500/5 to-blue-500/5 p-8 text-left transition-all hover:border-border hover:shadow-lg hover:shadow-emerald-500/5 active:scale-[0.99]"
           >
             <div className="flex items-center gap-6">
               <div className="w-14 h-14 rounded-xl bg-foreground flex items-center justify-center text-white shrink-0 shadow-lg group-hover:scale-110 transition-transform">
                 <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="currentColor" stroke="none"><path d="M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z"/></svg>
               </div>
               <div>
                 <div className="text-sm font-black tracking-tight mb-1">点击播放</div>
                 <div className="text-xs text-muted-foreground font-medium">使用底部播放器收听完整对谈</div>
               </div>
             </div>
           </button>
        </section>
      )}

      <section className="space-y-10">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2 opacity-60">
            <ScrollText size={18} /><h2 className="text-xl font-[900]">对谈脚本</h2>
          </div>
          <CopyScriptButton text={data.script_text} />
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

function CopyScriptButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [text]);

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={handleCopy}
      className="text-muted-foreground hover:text-foreground gap-1.5 shrink-0"
    >
      {copied ? <Check size={14} /> : <Copy size={14} />}
      <span className="text-xs font-bold">{copied ? '已复制' : '复制脚本'}</span>
    </Button>
  );
}
