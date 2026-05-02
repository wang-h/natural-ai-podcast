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
    <div className="max-w-3xl mx-auto py-12 px-6 lg:px-10">
      <div className="mb-10 text-center md:text-left">
        <h1 className="text-4xl font-extrabold tracking-tight mb-2">Text → Script</h1>
        <p className="text-muted-foreground text-lg">将碎片化素材转化为极具生命力的对谈脚本</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        <div className="space-y-3">
          <Label htmlFor="source" className="text-base font-bold">源素材 (Source Text)</Label>
          <Textarea 
            id="source" 
            value={source} 
            onChange={e => setSource(e.target.value)} 
            rows={12} 
            className="text-base p-4 resize-none focus:ring-2 focus:ring-primary/20"
            placeholder="在此处粘贴文章、笔记或任何想要转化为播客的文本..."
          />
        </div>

        <div className="flex flex-col md:flex-row gap-6 md:items-end">
          <div className="flex-1 space-y-3">
            <Label htmlFor="model" className="text-sm font-bold opacity-70">LLM Model</Label>
            <Select value={model} onValueChange={setModel}>
              <SelectTrigger className="w-full h-11 bg-background">
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
            size="pill" 
            className="h-12 text-base font-bold w-full md:w-auto"
          >
            {loading ? <Sparkles className="animate-spin mr-2" /> : <Wand2 className="mr-2" />}
            {loading ? '生成中...' : '生成脚本'}
          </Button>
        </div>
        <p className="text-xs text-muted-foreground text-center md:text-left">4 阶段 LLM 协同管线处理，大约需要 60–90 秒。</p>
      </form>

      {error && (
        <div className="mt-8 p-4 bg-destructive/10 border border-destructive/20 rounded-xl text-destructive text-sm font-mono overflow-auto">
          {error}
        </div>
      )}

      {result && (
        <div className="mt-16 pt-10 border-t animate-in fade-in slide-in-from-bottom-4 duration-700">
          <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
            <div className="flex items-center gap-2">
               <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
               <span className="font-mono text-sm font-bold text-emerald-600">RUN_ID: {result.run_id}</span>
            </div>
            <div className="flex gap-3">
              <Button onClick={copyScript} variant="outline" size="sm" className="h-10 rounded-lg">
                <Copy size={16} className="mr-2" /> 复制脚本
              </Button>
              <Button asChild variant="default" size="sm" className="h-10 rounded-lg">
                <a href={`/render/?run_id=${result.run_id}`}>→ 渲染音频</a>
              </Button>
            </div>
          </div>

          <div className="bg-muted/30 border rounded-2xl p-8 lg:p-10">
            <h3 className="text-xl font-black mb-6 flex items-center gap-2">
              <Sparkles size={20} className="text-amber-500" /> 最终脚本预览
            </h3>
            <pre className="text-base leading-loose whitespace-pre-wrap font-sans text-foreground/90">
              {result.script}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
