import { useEffect, useState } from 'react';
import { percent } from './format';
type Result={window:string;mean_car:number|null;n_events:number;company_observations:number;ci_low:number|null;ci_high:number|null;t_stat:number|null;significant:boolean;warning:string};
type History={synthetic:boolean;region:string;candidates:number;skipped_companies:number;excluded_overlaps:number;results:Result[];warning:string};
export function HistoryPanel({eventId}:{eventId:string}){
 const [data,setData]=useState<History|null>(null),[error,setError]=useState('');
 useEffect(()=>{const abort=new AbortController();setData(null);setError('');fetch(`/api/events/${encodeURIComponent(eventId)}/history`,{signal:abort.signal}).then(async r=>{if(!r.ok)throw Error('Historical study unavailable.');return r.json()}).then(setData).catch(e=>{if(e.name!=='AbortError')setError(e.message)});return()=>abort.abort()},[eventId]);
 if(error)return <p role="alert">{error}</p>;if(!data)return <p role="status">Computing historical studies…</p>;
 return <div className="history"><div className="section-label">MARKET MODEL · SPY BENCHMARK</div><p>Earlier events of the same type in {data.region}. Equal-weight company CARs, aggregated by event.</p>{data.synthetic&&<p className="study-warning">Synthetic illustration · not observed returns</p>}{data.results.map(r=><div className="study" key={r.window}><div><strong>{r.window} trading days</strong><b>{percent(r.mean_car)}</b></div><p>{r.n_events} events · {r.company_observations} company observations</p><p>95% CI: {percent(r.ci_low)} to {percent(r.ci_high)} · t: {r.t_stat?.toFixed(2)??'—'}</p><span className={r.significant?'study-signal':'study-warning'}>{r.warning}</span></div>)}<p className="muted">{data.candidates} candidate events · {data.skipped_companies} companies skipped · {data.excluded_overlaps} overlapping events excluded</p><p className="muted">{data.warning}</p></div>
}
