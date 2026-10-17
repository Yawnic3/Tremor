import React from 'react';
import { createRoot } from 'react-dom/client';
import { useEffect, useRef } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
function App(){const ref=useRef<HTMLDivElement>(null);useEffect(()=>{const m=new maplibregl.Map({container:ref.current!,style:'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',center:[-98,38],zoom:3});return()=>m.remove()},[]);return <main><h1>EventMap</h1><div ref={ref} style={{height:'85vh'}}/></main>}
createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);

