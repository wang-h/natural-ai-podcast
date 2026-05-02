import React, { useState, useEffect } from 'react';
import { Download, ScrollText } from 'lucide-react';

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

  if (loading) return <div style={{ padding: '8rem', textAlign: 'center' }}>Loading...</div>;
  if (error) return <div style={{ padding: '8rem', textAlign: 'center', color: 'red' }}>Error: {error}</div>;
  if (!data) return null;

  return (
    <div className="feature-page" style={{ padding: '4rem 5rem' }}>
      <div className="result-header" style={{ marginBottom: '3rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', borderBottom: '1px solid var(--border)', paddingBottom: '2rem' }}>
        <h1 style={{ fontSize: '2.5rem', fontWeight: 800, letterSpacing: '-0.03em', margin: 0 }}>{data.id}</h1>
        <div className="result-actions">
          {data.audio_url && (
            <a href={data.audio_url} download className="nav-item" style={{ border: '1px solid var(--border)', background: 'var(--card-bg)', padding: '0.6rem 1.25rem', borderRadius: '8px', cursor: 'pointer', fontSize: '0.9rem', fontWeight: 600, color: 'var(--foreground)' }}>
              <Download size={16} style={{ marginRight: '0.5rem' }} /> 下载 MP3
            </a>
          )}
        </div>
      </div>

      {data.audio_url && (
        <div className="player-bar" style={{ marginBottom: '4rem', background: 'var(--card-bg)', borderRadius: '16px', padding: '2rem', border: '1px solid var(--border)' }}>
          <audio controls style={{ width: '100%', height: '44px' }}>
            <source src={data.audio_url} type="audio/mpeg" />
          </audio>
        </div>
      )}

      <h2 style={{ fontSize: '1.5rem', fontWeight: 800, marginBottom: '2rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <ScrollText size={24} style={{ color: 'var(--theme-blue)' }} /> Script
      </h2>
      <div className="script-body">
        {data.lines.map((l: any, i: number) => (
          <div key={i} className={`line ${l.speaker === '林深' ? 'shen' : 'ruo'}`} style={{ padding: '1.5rem 0', borderBottom: '1px solid var(--border)', display: 'grid', gridTemplateColumns: '100px 1fr', gap: '1.5rem' }}>
            <span className="speaker" style={{ fontWeight: 800, fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: l.speaker === '林深' ? '#0ea5e9' : '#8b5cf6' }}>{l.speaker}</span>
            <span className="text" style={{ fontSize: '1.1rem', lineHeight: 1.7 }}>{l.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
