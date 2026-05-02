import React, { useState, useEffect } from 'react';
import { Download, ExternalLink, Headphones, Info, Music, AudioLines } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';

export default function AudioRenderer() {
  const [script, setScript] = useState('');
  const [runId, setRunId] = useState('');
  const [soft, setSoft] = useState(true);
  const [branding, setBranding] = useState(true);
  const [force, setForce] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get('run_id');
    if (id) setRunId(id);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch('/api/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ script, run_id: runId, soft, branding, force })
      });
      const data = await res.json();
      
      if (!data.success) {
        setError(data.error + '\n' + (data.log || ''));
      } else {
        setResult(data);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full px-10 md:px-16 lg:px-24 py-16 md:py-24">
      <div className="mb-16">
        <h1 className="text-5xl md:text-6xl font-[1000] tracking-tighter mb-4 leading-tight">Script → Audio</h1>
        <p className="text-xl md:text-2xl text-muted-foreground font-medium opacity-80">将文字赋予生命，合成具有真人温度的自然播客</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-12 max-w-5xl">
        {runId && (
          <div className="flex items-center gap-4 p-6 bg-blue-500/5 border-2 border-blue-200/50 dark:border-blue-900/50 rounded-[2rem] text-lg">
            <Info size={24} className="text-blue-500 shrink-0" />
            <p className="font-medium">
              正在为 <span className="font-black text-blue-600">{runId}</span> 渲染音频。
              <span className="block md:inline md:ml-3 opacity-60 text-base">留空脚本将自动读取历史记录。</span>
            </p>
          </div>
        )}

        <div className="space-y-4">
          <Label htmlFor="script" className="text-lg font-black uppercase tracking-widest opacity-60">播客脚本 (Podcast Script)</Label>
          <Textarea 
            id="script" 
            value={script}
            onChange={e => setScript(e.target.value)}
            rows={16} 
            className="text-lg p-6 rounded-3xl border-2 focus:ring-4 focus:ring-primary/5 transition-all bg-muted/20 leading-relaxed"
            placeholder="林深：大家好，我是林深...&#10;若水：我是若水，欢迎收听..."
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {[
            { id: 'soft', label: 'Soft Edges', state: soft, setter: setSoft },
            { id: 'branding', label: 'Deepling Intro', state: branding, setter: setBranding },
            { id: 'force', label: '强制重绘', state: force, setter: setForce }
          ].map(item => (
            <div key={item.id} className="flex items-center space-x-4 bg-muted/30 p-5 rounded-2xl border-2 border-transparent hover:border-border hover:bg-background transition-all cursor-pointer">
              <Checkbox id={item.id} checked={item.state} onCheckedChange={(v) => item.setter(!!v)} className="w-6 h-6 rounded-lg" />
              <Label htmlFor={item.id} className="text-base font-bold cursor-pointer">{item.label}</Label>
            </div>
          ))}
        </div>

        <div className="pt-6">
          <Button 
            disabled={loading} 
            type="submit" 
            variant="gradient" 
            className="h-16 px-12 text-xl font-black rounded-2xl w-full md:w-auto shadow-2xl"
          >
            {loading ? <Headphones className="animate-pulse mr-3" /> : <Music className="mr-3" />}
            {loading ? '音频合成中...' : '立即渲染音频'}
          </Button>
          <p className="text-sm text-muted-foreground mt-6 font-medium">采用 MiniMax Voice 2.8 引擎，渲染时长约为脚本长度的 1/3。</p>
        </div>
      </form>

      {result && (
        <div className="mt-24 animate-in fade-in slide-in-from-bottom-8 duration-1000">
          <div className="flex items-center justify-between mb-12">
            <h3 className="text-4xl font-[1000] tracking-tight">合成结果</h3>
            <Badge variant="secondary" className="px-5 py-2 text-base font-black rounded-xl border-2">{result.line_count} LINES</Badge>
          </div>

          {result.audio && (
            <div className="space-y-6 max-w-5xl">
              {Object.entries(result.audio).map(([key, info]: [string, any]) => (
                <div key={key} className="flex flex-col md:flex-row items-center gap-8 p-8 bg-muted/20 rounded-[2.5rem] border-2 transition-all hover:bg-background hover:shadow-xl group">
                  <div className="flex flex-col items-center md:items-start gap-2 shrink-0">
                    <span className="text-xs font-black uppercase tracking-[0.3em] text-emerald-600 leading-none">{key} VERSION</span>
                    <span className="text-sm font-bold opacity-40">{info.size}</span>
                  </div>
                  <div className="flex-1 w-full">
                     <audio controls className="w-full h-12">
                       <source src={info.url} type="audio/mpeg" />
                     </audio>
                  </div>
                  <Button asChild variant="outline" size="icon" className="w-14 h-14 rounded-2xl border-2 group-hover:bg-emerald-500 group-hover:text-white group-hover:border-emerald-500 transition-all">
                    <a href={info.url} download>
                      <Download size={24} />
                    </a>
                  </Button>
                </div>
              ))}
            </div>
          )}

          <div className="mt-16 flex justify-center">
            <Button asChild variant="link" className="text-xl text-emerald-600 hover:text-emerald-700 font-black tracking-tight">
              <a href={`/run/?id=${result.run_id}`} className="flex items-center gap-3">
                <ExternalLink size={20} /> 查看详细对谈报告
              </a>
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
