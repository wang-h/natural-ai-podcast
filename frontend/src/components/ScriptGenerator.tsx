import React, { useState } from 'react';
import { Copy, ExternalLink } from 'lucide-react';

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
    <div className="feature-page" style={{ padding: '4rem 5rem' }}>
      <h1 style={{ fontSize: '2.5rem', fontWeight: 800, letterSpacing: '-0.03em', marginBottom: '0.5rem' }}>Text → Script</h1>
      <p className="sub" style={{ color: 'var(--muted-foreground)', marginBottom: '3rem' }}>任意文本 → LLM 优化 → 播客脚本</p>

      <form onSubmit={handleSubmit} className="feature-form">
        <label htmlFor="source" style={{ display: 'block', fontWeight: 700, marginBottom: '0.75rem' }}>Source text</label>
        <textarea 
          id="source" 
          value={source} 
          onChange={e => setSource(e.target.value)} 
          rows={12} 
          style={{ width: '100%', padding: '1.25rem', border: '1px solid var(--border)', borderRadius: '12px', fontFamily: 'inherit', fontSize: '1rem', background: 'var(--input-bg)' }}
          placeholder="在此处粘贴文章、笔记或任何文本..."
        ></textarea>

        <details className="advanced" style={{ marginTop: '1.5rem' }}>
          <summary style={{ fontSize: '0.85rem', color: 'var(--muted-foreground)', cursor: 'pointer', fontWeight: 600 }}>高级设置</summary>
          <div style={{ marginTop: '1rem' }}>
            <label htmlFor="model" style={{ display: 'block', fontSize: '0.9rem', marginBottom: '0.5rem' }}>LLM Model</label>
            <select 
              id="model" 
              value={model} 
              onChange={e => setModel(e.target.value)} 
              style={{ width: '100%', padding: '0.75rem', border: '1px solid var(--border)', borderRadius: '8px', background: 'var(--input-bg)', fontFamily: 'inherit', fontSize: '0.95rem', cursor: 'pointer', appearance: 'none' }}
            >
              <option value="MiniMax-Text-01">MiniMax M2.7 (Default)</option>
              <option value="kimi-latest">Kimi 2.6</option>
              <option value="deepseek-chat">DeepSeek V4</option>
              <option value="qwen-max">Qwen Max</option>
            </select>
          </div>
        </details>

        <div style={{ marginTop: '2.5rem' }}>
          <button disabled={loading} type="submit" style={{ background: 'var(--theme-gradient)', color: 'white', border: 'none', padding: '0.8rem 2rem', borderRadius: '100px', fontWeight: 700, cursor: loading ? 'wait' : 'pointer', fontSize: '1rem', boxShadow: '0 4px 12px rgba(14,165,233,0.2)', opacity: loading ? 0.7 : 1 }}>
            {loading ? '生成中...' : '生成脚本'}
          </button>
          <p className="hint" style={{ fontSize: '0.8rem', color: 'var(--muted-foreground)', marginTop: '0.75rem' }}>大约需要 60–90 秒处理 4 阶段管线</p>
        </div>
      </form>

      {error && (
        <div className="msg error" style={{ marginTop: '2rem', padding: '1.5rem', background: '#fff1f2', borderRadius: '12px', color: '#e11d48', border: '1px solid #fda4af' }}>
          <pre style={{ fontSize: '0.85rem', whiteSpace: 'pre-wrap' }}>{error}</pre>
        </div>
      )}

      {result && (
        <div className="result" style={{ marginTop: '5rem', borderTop: '1px solid var(--border)', paddingTop: '3rem' }}>
          <div className="result-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
            <span className="run-id" style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--theme-blue)' }}># {result.run_id}</span>
            <div className="result-actions" style={{ display: 'flex', gap: '1rem' }}>
              <button onClick={copyScript} className="nav-item" style={{ border: '1px solid var(--border)', background: 'var(--card-bg)', padding: '0.5rem 1rem', borderRadius: '8px', cursor: 'pointer', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--foreground)' }}>
                <Copy size={16} /> 复制
              </button>
              <a href={`/render?run_id=${result.run_id}`} style={{ background: 'var(--foreground)', color: 'var(--background)', padding: '0.5rem 1.5rem', borderRadius: '8px', fontWeight: 600, textDecoration: 'none', display: 'flex', alignItems: 'center', height: '40px' }}>
                → 渲染音频
              </a>
            </div>
          </div>

          <h3 style={{ marginBottom: '1.5rem', fontWeight: 800 }}>最终脚本</h3>
          <pre className="script-output" style={{ background: 'var(--card-bg)', border: '1px solid var(--border)', padding: '1.5rem', borderRadius: '12px', fontFamily: 'inherit', lineHeight: 1.7, fontSize: '1rem', whiteSpace: 'pre-wrap', maxHeight: '600px', overflow: 'auto', color: 'var(--foreground)' }}>
            {result.script}
          </pre>
        </div>
      )}
    </div>
  );
}
