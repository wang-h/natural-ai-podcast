import React, { useState } from 'react';
import { Copy, Sparkles, Wand2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function ScriptGenerator() {
  const [source, setSource] = useState('');
  const [model, setModel] = useState('MiniMax-Text-01');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch('/api/script', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source, model })
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

  const copyScript = () => {
    if (result?.script) {
      navigator.clipboard.writeText(result.script);
      alert('已复制到剪贴板');
    }
  };

  return (
    <div className="w-full px-10 md:px-16 lg:px-24 py-16 md:py-24">
      <div className="mb-16">
        <h1 className="text-5xl md:text-6xl font-[1000] tracking-tighter mb-4 leading-tight">Text → Script</h1>
        <p className="text-xl md:text-2xl text-muted-foreground font-medium opacity-80">将碎片化素材转化为极具生命力的对谈脚本</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-12 max-w-5xl">
        <div className="space-y-4">
          <Label htmlFor="source" className="text-lg font-black uppercase tracking-widest opacity-60">源素材 (Source Text)</Label>
          <Textarea 
            id="source" 
            value={source} 
            onChange={e => setSource(e.target.value)} 
            rows={14} 
            className="text-lg p-6 rounded-3xl border-2 focus:ring-4 focus:ring-primary/5 transition-all bg-muted/20"
            placeholder="在此处粘贴文章、笔记或任何想要转化为播客的文本..."
          />
        </div>

        <div className="flex flex-col md:flex-row gap-8 md:items-end bg-muted/30 p-8 rounded-[2.5rem] border">
          <div className="flex-1 space-y-4">
            <Label htmlFor="model" className="text-sm font-black uppercase tracking-widest opacity-40">LLM Model</Label>
            <Select value={model} onValueChange={setModel}>
              <SelectTrigger className="w-full h-14 bg-background rounded-2xl text-base font-bold border-2">
                <SelectValue placeholder="选择模型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="MiniMax-Text-01">MiniMax M2.7 (Default)</SelectItem>
                <SelectItem value="kimi-latest">Kimi 2.6</SelectItem>
                <SelectItem value="deepseek-chat">DeepSeek V4</SelectItem>
                <SelectItem value="qwen-max">Qwen Max</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Button 
            disabled={loading} 
            type="submit" 
            variant="gradient" 
            className="h-14 px-10 text-lg font-black rounded-2xl w-full md:w-auto shadow-2xl"
          >
            {loading ? <Sparkles className="animate-spin mr-3" /> : <Wand2 className="mr-3" />}
            {loading ? '正在生成...' : '开始生成脚本'}
          </Button>
        </div>
      </form>

      {error && (
        <div className="mt-12 p-8 bg-destructive/5 border-2 border-destructive/20 rounded-[2rem] text-destructive font-mono text-sm overflow-auto">
          <div className="font-black mb-2 uppercase tracking-widest">Error Log</div>
          {error}
        </div>
      )}

      {result && (
        <div className="mt-24 animate-in fade-in slide-in-from-bottom-8 duration-1000">
          <div className="flex flex-wrap items-center justify-between gap-6 mb-12">
            <div className="flex items-center gap-3">
               <div className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse" />
               <span className="font-mono text-lg font-black text-emerald-600">RUN_ID: {result.run_id}</span>
            </div>
            <div className="flex gap-4">
              <Button onClick={copyScript} variant="outline" className="h-12 px-6 rounded-xl font-bold border-2">
                <Copy size={18} className="mr-2" /> 复制脚本
              </Button>
              <Button asChild variant="default" className="h-12 px-8 rounded-xl font-bold">
                <a href={`/render/?run_id=${result.run_id}`}>→ 渲染音频</a>
              </Button>
            </div>
          </div>

          <div className="bg-muted/10 border-2 rounded-[3rem] p-10 md:p-16 relative overflow-hidden">
            <div className="absolute top-0 right-0 p-8 opacity-5">
              <Sparkles size={120} />
            </div>
            <h3 className="text-3xl font-[1000] mb-10 flex items-center gap-3">
              <Sparkles size={32} className="text-amber-500" /> 脚本预览
            </h3>
            <pre className="text-xl leading-[2] whitespace-pre-wrap font-medium text-foreground/90 max-w-4xl">
              {result.script}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
