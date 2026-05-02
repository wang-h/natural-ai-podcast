import React, { useState, useEffect } from 'react';
import { Download, ExternalLink, Headphones, Info, Music } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';

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
    <div className="max-w-3xl mx-auto py-12 px-6 lg:px-10">
      <div className="mb-10 text-center md:text-left">
        <h1 className="text-4xl font-extrabold tracking-tight mb-2">Script → Audio</h1>
        <p className="text-muted-foreground text-lg">将文字赋予生命，合成具有真人温度的自然播客</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {runId && (
          <div className="flex items-center gap-3 p-4 bg-blue-500/5 border border-blue-200/50 dark:border-blue-900/50 rounded-xl text-sm">
            <Info size={18} className="text-blue-500 shrink-0" />
            <p>
              正在为 <strong>{runId}</strong> 进行渲染。
              <span className="block md:inline md:ml-2 opacity-70">留空脚本将自动读取该 Run 的最终脚本。</span>
            </p>
          </div>
        )}

        <div className="space-y-3">
          <Label htmlFor="script" className="text-base font-bold">播客脚本 (Script)</Label>
          <Textarea 
            id="script" 
            value={script}
            onChange={e => setScript(e.target.value)}
            rows={14} 
            className="text-base p-4 resize-none"
            placeholder="林深：大家好，我是林深。&#10;若水：我是若水，欢迎收听 Natural AI 播客。"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="flex items-center space-x-3 bg-muted/20 p-3 rounded-lg border border-transparent hover:border-border transition-colors">
            <Checkbox id="soft" checked={soft} onCheckedChange={(v) => setSoft(!!v)} />
            <Label htmlFor="soft" className="cursor-pointer">Soft Edges</Label>
          </div>
          <div className="flex items-center space-x-3 bg-muted/20 p-3 rounded-lg border border-transparent hover:border-border transition-colors">
            <Checkbox id="branding" checked={branding} onCheckedChange={(v) => setBranding(!!v)} />
            <Label htmlFor="branding" className="cursor-pointer">Deepling Intro</Label>
          </div>
          <div className="flex items-center space-x-3 bg-muted/20 p-3 rounded-lg border border-transparent hover:border-border transition-colors">
            <Checkbox id="force" checked={force} onCheckedChange={(v) => setForce(!!v)} />
            <Label htmlFor="force" className="cursor-pointer">强制重绘</Label>
          </div>
        </div>

        <div className="pt-4">
          <Button 
            disabled={loading} 
            type="submit" 
            variant="gradient" 
            size="pill" 
            className="h-12 text-base font-bold w-full md:w-auto"
          >
            {loading ? <Headphones className="animate-pulse mr-2" /> : <Music className="mr-2" />}
            {loading ? '音频合成中...' : '渲染音频'}
          </Button>
          <p className="text-xs text-muted-foreground mt-4 text-center md:text-left">大约需要 30–60 秒，完成后可立即试听。</p>
        </div>
      </form>

      {error && (
        <div className="mt-8 p-4 bg-destructive/10 border border-destructive/20 rounded-xl text-destructive text-sm font-mono overflow-auto">
          {error}
        </div>
      )}

      {result && (
        <div className="mt-16 pt-10 border-t animate-in fade-in slide-in-from-bottom-4 duration-700">
          <div className="flex items-center justify-between mb-8">
            <h3 className="text-2xl font-black">合成结果</h3>
            <Badge variant="secondary" className="px-3 py-1 font-mono">{result.line_count} LINES</Badge>
          </div>

          {result.audio && (
            <div className="space-y-4">
              {Object.entries(result.audio).map(([key, info]: [string, any]) => (
                <div key={key} className="flex flex-col sm:flex-row items-center gap-6 p-6 bg-muted/30 rounded-2xl border transition-all hover:shadow-md">
                  <div className="flex flex-col items-center sm:items-start gap-1">
                    <span className="text-[0.7rem] font-black uppercase tracking-widest text-emerald-600 leading-none">{key} VERSION</span>
                    <span className="text-[0.65rem] text-muted-foreground">{info.size}</span>
                  </div>
                  <audio controls className="flex-1 h-10">
                    <source src={info.url} type="audio/mpeg" />
                  </audio>
                  <Button asChild variant="outline" size="icon" className="shrink-0 rounded-full">
                    <a href={info.url} download>
                      <Download size={18} />
                    </a>
                  </Button>
                </div>
              ))}
            </div>
          )}

          <div className="mt-12 flex justify-center">
            <Button asChild variant="link" className="text-emerald-600 hover:text-emerald-700 font-bold">
              <a href={`/run/?id=${result.run_id}`} className="flex items-center gap-2">
                <ExternalLink size={16} /> 查看该 Run 的完整详情
              </a>
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
