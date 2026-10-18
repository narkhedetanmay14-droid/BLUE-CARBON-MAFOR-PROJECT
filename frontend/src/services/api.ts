const BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";
export function token(){ return localStorage.getItem("bc_token"); }
export async function api(path:string, options:RequestInit={}) {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type","application/json");
  const t=token(); if(t) headers.set("Authorization",`Bearer ${t}`);
  const response=await fetch(`${BASE}${path}`,{...options,headers});
  const data=await response.json().catch(()=>({detail:response.statusText}));
  if(!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
  return data;
}
