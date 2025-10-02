import React, { useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8100'
const BASIC_USER = import.meta.env.VITE_BASIC_USER || 'admin'
const BASIC_PASS = import.meta.env.VITE_BASIC_PASS || 'changeme'

export default function App(){
  const [url, setUrl] = useState('')
  const [mode, setMode] = useState('editors_bench')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [force, setForce] = useState(false)
  const [showHelp, setShowHelp] = useState(false)

  const analyze = async () => {
    setLoading(true); setError(''); setResult(null)
    try {
      const res = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Basic ' + btoa(`${BASIC_USER}:${BASIC_PASS}`)
        },
        body: JSON.stringify({ url, force, mode })
      })
      if(!res.ok){
        const t = await res.text()
        throw new Error(`${res.status} ${t}`)
      }
      const json = await res.json()
      setResult(json)
    } catch(e){
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const copySummary = async () => {
    if(!result) return
    const text = result?.headline_summary?.one_sentence_summary || ''
    await navigator.clipboard.writeText(text)
  }

  const exportJson = () => {
    if(!result) return
    const blob = new Blob([JSON.stringify(result, null, 2)], {type: 'application/json'})
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'analysis.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  const helpEditors = (
    <>
      <p style={{fontSize:14, lineHeight:1.5}}>The agent evaluates one article and returns 11 criteria (0–10). It never uses outside information; all rationales must cite the article text or sections (e.g., “lede, para 2”).</p>
      <p style={{fontSize:14, lineHeight:1.5}}>Editor’s Bench applies a strict rubric directly, without assuming unstated elements.</p>
    </>
  )

  const helpIntent = (
    <>
      <p style={{fontSize:14, lineHeight:1.5}}>Intent‑Aware Accrual first infers the article’s intent (e.g., Hard News, Explainer, Opinion, Brief) and assigns a necessity weight (0–1) to each criterion based on that intent.</p>
      <p style={{fontSize:14, lineHeight:1.5}}>Scores start at 5 and adjust by +/− amounts scaled by necessity: Final = clamp(0,10, 5 + A·w·e − B·w·v). When w is low, absence isn’t penalized unless there’s clear harm/mislead.</p>
      <p style={{fontSize:12, color:'#555'}}>We also return the detected intent and the necessity map for transparency.</p>
    </>
  )

  return (
    <div style={{maxWidth: 900, margin: '0 auto', padding: 16, fontFamily: 'system-ui, sans-serif'}}>
      <h1>Agent Judge</h1>
      <div style={{display:'grid', gap: 8, marginBottom: 12}}>
        <input placeholder="Article URL" value={url} onChange={e=>setUrl(e.target.value)} />
        <div style={{display:'flex', gap:8, alignItems:'center'}}>
          <label style={{display:'inline-flex', alignItems:'center', gap:6}}>
            <input type="radio" name="mode" value="editors_bench" checked={mode==='editors_bench'} onChange={e=>setMode(e.target.value)} /> Editor's Bench
          </label>
          <label style={{display:'inline-flex', alignItems:'center', gap:6}}>
            <input type="radio" name="mode" value="intent_accrual" checked={mode==='intent_accrual'} onChange={e=>setMode(e.target.value)} /> Intent‑Aware Accrual
          </label>
        </div>
        <button onClick={analyze} disabled={!url || loading}>{loading ? 'Analyzing…' : 'Analyze'}</button>
      </div>

      {error && <div style={{color:'crimson', marginBottom: 12}}>{error}</div>}

      {result && (
        <div style={{display:'grid', gap: 12}}>
          <div style={{display:'flex', justifyContent:'flex-end'}}>
            <button onClick={()=>setShowHelp(true)} style={{fontSize:12}}>How scoring works</button>
          </div>
          <header style={{display:'flex', gap:12, alignItems:'center'}}>
            {result.meta?.thumbnail && <img alt="thumb" src={result.meta.thumbnail} style={{width:64, height:64, objectFit:'cover', borderRadius:8}} />}
            <div>
              <div style={{fontWeight:600}}>{result.meta?.title || 'Untitled'}</div>
              <div style={{fontSize:12, color:'#555'}}>{result.meta?.author || 'Unknown'}</div>
            </div>
          </header>

          <section>
            <div style={{fontSize:24, fontWeight:700}}>Overall: {result.overall?.average?.toFixed?.(2) ?? result.overall?.average}</div>
            <div style={{fontSize:12, color:'#555'}}>Method: {result.overall?.method} · Mode: {result.mode} {result.fromCache ? '· from cache' : '· fresh'}</div>
            {result.intent && <div style={{fontSize:12, color:'#555', marginTop:4}}>Intent: {result.intent}</div>}
          </section>

          <section>
            <div style={{display:'grid', gap:8}}>
              {(result.scores || []).map((s, i)=> (
                <div key={i} style={{border:'1px solid #ddd', borderRadius:8, padding:8}}>
                  <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
                    <div style={{fontWeight:600}}>{s.criterion}</div>
                    <div style={{display:'flex', alignItems:'center', gap:8}}>
                      <div style={{width:200, height:8, background:'#eee', borderRadius:4, overflow:'hidden'}}>
                        <div style={{width:`${(s.score/10)*100}%`, height:'100%', background:'#0a7'}}></div>
                      </div>
                      <div>{s.score}</div>
                    </div>
                  </div>
                  <div style={{fontSize:14, marginTop:6}}>{s.rationale}</div>
                  {s.flags && s.flags.length>0 && (
                    <div style={{display:'flex', gap:6, flexWrap:'wrap', marginTop:6}}>
                      {s.flags.map((f, fi)=> <span key={fi} style={{fontSize:12, background:'#eef', padding:'2px 6px', borderRadius:999}}>{f}</span>)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>

          {result.necessity_map && (
            <section>
              <div style={{fontSize:12, color:'#555'}}>Necessity weights used (0–1):</div>
              <div style={{display:'flex', gap:6, flexWrap:'wrap', marginTop:6}}>
                {Object.entries(result.necessity_map).map(([k,v])=> (
                  <span key={k} style={{fontSize:12, background:'#f6f6f6', padding:'2px 6px', borderRadius:999}}>{k}: {v}</span>
                ))}
              </div>
            </section>
          )}

          <section style={{display:'flex', gap:8}}>
            <button onClick={copySummary}>Copy summary</button>
            <button onClick={exportJson}>Export JSON</button>
            <label style={{display:'inline-flex', alignItems:'center', gap:6, fontSize:12}}>
              <input type="checkbox" checked={force} onChange={e=>setForce(e.target.checked)} /> Re-run (bypass cache)
            </label>
          </section>
        </div>
      )}

      {showHelp && (
        <div style={{position:'fixed', inset:0, background:'rgba(0,0,0,0.5)', display:'flex', alignItems:'center', justifyContent:'center'}} onClick={()=>setShowHelp(false)}>
          <div onClick={e=>e.stopPropagation()} style={{background:'#fff', color:'#111', width:'min(800px, 95vw)', maxHeight:'85vh', overflow:'auto', borderRadius:8, padding:16}}>
            <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:8}}>
              <div style={{fontWeight:700}}>How the Agent Scores</div>
              <button onClick={()=>setShowHelp(false)}>Close</button>
            </div>
            {mode === 'editors_bench' ? helpEditors : helpIntent}
          </div>
        </div>
      )}
    </div>
  )
}


