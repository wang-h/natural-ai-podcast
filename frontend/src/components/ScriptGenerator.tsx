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
    <div className="w-full px-10 md:px-16 py-12 md:py-16">
      <div className="mb-12">
        <h1 className="text-4xl md:text-5xl font-[950] tracking-tight mb-3 leading-tight">Text → Script</h1>
        <p className="text-lg text-muted-foreground font-medium opacity-70">将碎片化素材转化为极具生命力的对谈脚本</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8 max-w-4xl">
        <div className="space-y-3">
          <Label htmlFor="source" className="text-sm font-black uppercase tracking-widest opacity-50">源素材 (Source Text)</Label>
          <Textarea 
            id="source" 
            value={source} 
            onChange={e => setSource(e.target.value)} 
            rows={12} 
            className="text-base p-5 rounded-2xl border-2 focus:ring-4 focus:ring-primary/5 transition-all bg-muted/20"
            placeholder="在此处粘贴文章、笔记或任何想要转化为播客的文本..."
          />
        </div>

        <div className="flex flex-col md:flex-row gap-4 md:items-end bg-muted/30 p-6 rounded-[2rem] border">
          <div className="md:w-72 lg:w-80 space-y-3">
            <Label htmlFor="model" className="text-xs font-black uppercase tracking-widest opacity-40">LLM Model</Label>
            <Select value={model} onValueChange={setModel}>
              <SelectTrigger className="w-full h-12 bg-background rounded-xl text-sm font-bold border-2">
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
            className="h-12 px-8 text-base font-black rounded-xl w-full md:w-auto shadow-xl shrink-0"
          >
            {loading ? <Sparkles className="animate-spin mr-2" /> : <Wand2 className="mr-2" />}
            {loading ? '生成中...' : '生成脚本'}
          </Button>
        </div>
      </form>

      {result && (
        <div className="mt-20 animate-in fade-in slide-in-from-bottom-6 duration-700">
          <div className="flex flex-wrap items-center justify-between gap-6 mb-8">
            <div className="flex items-center gap-2.5">
               <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
               <span className="font-mono text-sm font-black text-emerald-600">RUN_ID: {result.run_id}</span>
            </div>
            <div className="flex gap-3">
              <Button onClick={copyScript} variant="outline" size="sm" className="h-10 rounded-lg font-bold">
                <Copy size={14} className="mr-2" /> 复制
              </Button>
              <Button asChild variant="default" size="sm" className="h-10 rounded-lg font-bold">
                <a href={`/render/?run_id=${result.run_id}`}>→ 渲染音频</a>
              </Button>
            </div>
          </div>

          <div className="bg-muted/10 border-2 rounded-[2rem] p-8 md:p-12 relative overflow-hidden">
            <h3 className="text-2xl font-[950] mb-8 flex items-center gap-3">
              <Sparkles size={24} className="text-amber-500" /> 脚本预览
            </h3>
            <pre className="text-base md:text-lg leading-relaxed whitespace-pre-wrap font-medium text-foreground/90 max-w-4xl">
              {result.script}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
