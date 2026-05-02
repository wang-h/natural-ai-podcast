import React, { useState, useEffect } from 'react';
import { Download, ExternalLink, Headphones, Info, Music } from 'lucide-react';
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
    <div className="w-full px-10 md:px-16 py-12 md:py-16">
      <div className="mb-12">
        <h1 className="text-4xl md:text-5xl font-[950] tracking-tight mb-3 leading-tight">Script → Audio</h1>
        <p className="text-lg text-muted-foreground font-medium opacity-70">将文字赋予生命，合成具有真人温度的自然播客</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8 max-w-4xl">
        {runId && (
          <div className="flex items-center gap-3 p-5 bg-blue-500/5 border border-blue-200/50 rounded-2xl text-base">
            <Info size={20} className="text-blue-500 shrink-0" />
            <p className="font-medium">
              正在为 <span className="font-black">{runId}</span> 渲染。
              <span className="opacity-60 ml-2 text-sm">留空则自动读取历史记录。</span>
            </p>
          </div>
        )}

        <div className="space-y-3">
          <Label htmlFor="script" className="text-sm font-black uppercase tracking-widest opacity-50">播客脚本 (Script)</Label>
          <Textarea 
            id="script" 
            value={script}
            onChange={e => setScript(e.target.value)}
            rows={14} 
            className="text-base p-5 rounded-2xl border-2 focus:ring-4 focus:ring-primary/5 transition-all bg-muted/20"
            placeholder="林深：大家好...&#10;若水：我是若水..."
          />
        </div>

        <div className="flex flex-col md:flex-row items-stretch md:items-center gap-4 bg-muted/30 p-4 rounded-2xl border">
          <div className="flex-1 flex flex-wrap items-center gap-6">
            {[
              { id: 'soft', label: 'Soft Edges', state: soft, setter: setSoft },
              { id: 'branding', label: 'Intro', state: branding, setter: setBranding },
              { id: 'force', label: '强制重绘', state: force, setter: setForce }
            ].map(item => (
              <div key={item.id} className="flex items-center space-x-2 cursor-pointer">
                <Checkbox id={item.id} checked={item.state} onCheckedChange={(v) => item.setter(!!v)} className="w-4 h-4 rounded" />
                <Label htmlFor={item.id} className="text-xs font-bold cursor-pointer opacity-70 tracking-tight">{item.label}</Label>
              </div>
            ))}
          </div>

          <Button 
            disabled={loading} 
            type="submit" 
            variant="gradient" 
            className="h-11 px-8 text-sm font-black rounded-xl w-full md:w-auto shadow-lg"
          >
            {loading ? <Headphones className="animate-pulse mr-2" size={16} /> : <Music className="mr-2" size={16} />}
            {loading ? '正在合成...' : '渲染音频'}
          </Button>
        </div>
      </form>

      {result && (
        <div className="mt-20 animate-in fade-in slide-in-from-bottom-6 duration-700">
          <div className="flex items-center justify-between mb-8">
            <h3 className="text-2xl font-[950] tracking-tight">合成结果</h3>
            <Badge variant="secondary" className="px-3 py-1 text-xs font-bold border-2">{result.line_count} LINES</Badge>
          </div>

          {result.audio && (
            <div className="space-y-4 max-w-4xl">
              {Object.entries(result.audio).map(([key, info]: [string, any]) => (
                <div key={key} className="flex flex-col md:flex-row items-center gap-6 p-6 bg-muted/20 rounded-3xl border transition-all hover:bg-background group">
                  <div className="flex flex-col items-center md:items-start gap-1 shrink-0">
                    <span className="text-[0.65rem] font-black uppercase tracking-widest text-emerald-600">{key} VERSION</span>
                    <span className="text-[0.65rem] font-bold opacity-30">{info.size}</span>
                  </div>
                  <div className="flex-1 w-full">
                     <audio controls className="w-full h-10">
                       <source src={info.url} type="audio/mpeg" />
                     </audio>
                  </div>
                  <Button asChild variant="outline" size="icon" className="w-10 h-10 rounded-xl group-hover:bg-emerald-500 group-hover:text-white transition-all">
                    <a href={info.url} download><Download size={16} /></a>
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
