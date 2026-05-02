import React, { useState, useEffect } from 'react';
import { Play, Database } from 'lucide-react';

export default function EpisodeList({ handlePlay }: { handlePlay: (url: string, title: string, date: string) => void }) {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/runs')
      .then(res => res.json())
      .then(data => {
        setRuns(data);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div style={{ padding: '8rem 2rem', textAlign: 'center', color: 'var(--muted-foreground)' }}>Loading episodes...</div>;
  }

  if (runs.length === 0) {
    return (
      <div style={{ padding: '8rem 2rem', textAlign: 'center', color: 'var(--muted-foreground)', fontSize: '0.9rem' }}>
        <Database style={{ width: '3rem', height: '3rem', marginBottom: '1rem', opacity: 0.2, margin: '0 auto' }} />
        <p>暂无播客内容</p>
      </div>
    );
  }

  return (
    <div className="episode-list">
      {runs.map((r: any) => (
        <article className="episode-item" key={r.id}>
          <time className="ep-date">{r.created}</time>
          <h3 className="ep-title">
            <a href={`/runs/${r.id}`}>{r.id}</a>
            {r.has_deepling && <span className="badge">DEEPLING</span>}
          </h3>
          <div className="ep-summary"><p>{r.preview}</p></div>
          <div className="ep-actions">
            <div 
              className="play-btn-wrapper" 
              onClick={() => handlePlay(r.audio_url, r.id, r.created)}
            >
              <Play className="lucide-play" />
              <span>播放</span>
            </div>
            <span style={{ color: 'var(--border)' }}>|</span>
            <a href={`/run?id=${r.id}`} className="action-link">查看详情</a>
            <span className="ep-meta-item">/ {r.line_count} turns</span>
          </div>
        </article>
      ))}
    </div>
  );
}
