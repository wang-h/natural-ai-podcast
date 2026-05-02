import React, { useState, useEffect } from 'react';
import { Download, ExternalLink } from 'lucide-react';

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
    // If run_id is in URL params, set it
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
    <div className="feature-page" style={{ padding: '4rem 5rem' }}>
      <h1 style={{ fontSize: '2.5rem', fontWeight: 800, letterSpacing: '-0.03em', marginBottom: '0.5rem' }}>Script → Audio</h1>
      <p className="sub" style={{ color: 'var(--muted-foreground)', marginBottom: '3rem' }}>播客脚本 → MiniMax TTS → 自然音频</p>

      <form onSubmit={handleSubmit} className="feature-form">
        {runId && (
          <div style={{ background: 'var(--muted)', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
            <span style={{ fontWeight: 600 }}>Info:</span> 正在为 <strong>{runId}</strong> 渲染。如果留空脚本，将自动读取该 Run 的最终脚本。
          </div>
        )}

        <label htmlFor="script" style={{ display: 'block', fontWeight: 700, marginBottom: '0.75rem' }}>Podcast script</label>
        <textarea 
          id="script" 
          value={script}
          onChange={e => setScript(e.target.value)}
          rows={14} 
          style={{ width: '100%', padding: '1.25rem', border: '1px solid var(--border)', borderRadius: '12px', fontFamily: 'inherit', fontSize: '1rem', background: 'var(--input-bg)' }}
          placeholder="林深：大家好...&#10;若水：我是若水..."
        ></textarea>

        <div className="checkbox-group" style={{ marginTop: '1.5rem', display: 'flex', gap: '2rem' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
            <input type="checkbox" checked={soft} onChange={e => setSoft(e.target.checked)} /> <span>Soft edges</span>
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
            <input type="checkbox" checked={branding} onChange={e => setBranding(e.target.checked)} /> <span>Deepling branding</span>
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
            <input type="checkbox" checked={force} onChange={e => setForce(e.target.checked)} /> <span>强制重绘</span>
          </label>
        </div>

        <div style={{ marginTop: '2.5rem' }}>
          <button disabled={loading} type="submit" style={{ background: 'var(--theme-gradient)', color: 'white', border: 'none', padding: '0.8rem 2rem', borderRadius: '100px', fontWeight: 700, cursor: loading ? 'wait' : 'pointer', fontSize: '1rem', boxShadow: '0 4px 12px rgba(14,165,233,0.2)', opacity: loading ? 0.7 : 1 }}>
            {loading ? '渲染中...' : '渲染音频'}
          </button>
          <p className="hint" style={{ fontSize: '0.8rem', color: 'var(--muted-foreground)', marginTop: '0.75rem' }}>大约需要 30–60 秒处理 TTS 合成</p>
        </div>
      </form>

      {error && (
        <div className="msg error" style={{ marginTop: '2rem', padding: '1.5rem', background: '#fff1f2', borderRadius: '12px', color: '#e11d48', border: '1px solid #fda4af' }}>
          <pre style={{ fontSize: '0.85rem', whiteSpace: 'pre-wrap' }}>{error}</pre>
        </div>
      )}

      {result && (
        <div className="result" style={{ marginTop: '5rem', borderTop: '1px solid var(--border)', paddingTop: '3rem' }}>
          <div className="result-header" style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontWeight: 800 }}>合成结果</h3>
            <span style={{ color: 'var(--muted-foreground)', fontSize: '0.9rem' }}>{result.line_count} lines rendered</span>
          </div>

          {result.audio && (
            <div className="audio-results" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {Object.entries(result.audio).map(([key, info]: [string, any]) => (
                <div key={key} className="audio-item" style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', padding: '1.25rem', background: 'var(--card-bg)', borderRadius: '12px', border: '1px solid var(--border)' }}>
                  <div style={{ width: '80px', fontWeight: 700, textTransform: 'uppercase', fontSize: '0.8rem', color: 'var(--theme-blue)' }}>{key}</div>
                  <audio controls style={{ flex: 1, height: '36px' }}>
                    <source src={info.url} type="audio/mpeg" />
                  </audio>
                  <a href={info.url} download style={{ color: 'var(--foreground)', textDecoration: 'none' }}>
                    <Download size={20} />
                  </a>
                </div>
              ))}
            </div>
          )}

          <div style={{ marginTop: '2.5rem' }}>
            <a href={`/run?id=${result.run_id}`} style={{ color: 'var(--theme-blue)', fontWeight: 600, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <ExternalLink size={16} /> 查看完整详情
            </a>
          </div>
        </div>
      )}
    </div>
  );
}
