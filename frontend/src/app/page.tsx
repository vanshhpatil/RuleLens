"use client";

import { useEffect, useState } from "react";
import { FileText, Moon, Sun, Upload, Search, ShieldCheck, AlertTriangle, Menu, X, Send, Trash2, Loader2 } from "lucide-react";
import { useTheme } from "next-themes";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type DocumentItem = { document_id: string; filename: string; chunks: number; pages: number; status: string };
type Answer = {
  status: string; answer: string; summary: string; conflict_detected: boolean;
  conflict_type: string; conflict_explanation?: string | null;
  sources: { document: string; page: number; relevance: number }[];
  evidence: { text: string; document: string; page: number; relevance: number }[];
};

export default function Home() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);

  async function refreshDocs() {
    try {
      const r = await fetch(`${API}/api/documents`);
      const data = await r.json();
      setDocs(data.documents || []);
    } catch {}
  }

  useEffect(() => { refreshDocs(); }, []);

  async function upload(file: File) {
    setUploading(true);
    const form = new FormData();
    form.append("file", file);
    try {
      const r = await fetch(`${API}/api/documents/upload`, { method: "POST", body: form });
      if (!r.ok) throw new Error((await r.json()).detail || "Upload failed");
      await refreshDocs();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Upload failed");
    } finally { setUploading(false); }
  }

  async function remove(id: string) {
    await fetch(`${API}/api/documents/${id}`, { method: "DELETE" });
    await refreshDocs();
  }

  async function ask() {
    if (!question.trim()) return;
    setBusy(true); setAnswer(null);
    try {
      const r = await fetch(`${API}/api/questions/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, top_k: 5 }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "Request failed");
      setAnswer(data);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Request failed");
    } finally { setBusy(false); }
  }

  const status = answer?.status;
  return (
    <main className="min-h-screen bg-zinc-50 text-zinc-950 dark:bg-zinc-950 dark:text-zinc-100">
      <nav className="sticky top-0 z-20 border-b border-zinc-200/80 bg-white/85 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/85">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-5">
          <div className="flex items-center gap-2 font-semibold">
            <div className="grid h-9 w-9 place-items-center rounded-xl bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"><ShieldCheck size={19}/></div>
            <span>RuleLens</span>
          </div>
          <div className="hidden items-center gap-7 text-sm md:flex">
            <a href="#dashboard" className="hover:opacity-60">Dashboard</a>
            <a href="#documents" className="hover:opacity-60">Documents</a>
            <a href="#ask" className="hover:opacity-60">Ask AI</a>
          </div>
          <div className="flex items-center gap-2">
            <button aria-label="Toggle theme" onClick={() => setTheme(theme === "dark" ? "light" : "dark")} className="rounded-xl border p-2 hover:bg-zinc-100 dark:border-zinc-700 dark:hover:bg-zinc-900">
              {mounted ? (
  theme === "dark" ? <Sun size={18}/> : <Moon size={18}/>
) : (
  <Moon size={18}/>
)}
            </button>
            <button className="rounded-xl border p-2 md:hidden" onClick={() => setMobileNav(!mobileNav)}>{mobileNav ? <X size={18}/> : <Menu size={18}/>}</button>
          </div>
        </div>
        {mobileNav && <div className="border-t px-5 py-3 md:hidden"><div className="flex flex-col gap-3 text-sm"><a href="#dashboard" onClick={()=>setMobileNav(false)}>Dashboard</a><a href="#documents" onClick={()=>setMobileNav(false)}>Documents</a><a href="#ask" onClick={()=>setMobileNav(false)}>Ask AI</a></div></div>}
      </nav>

      <section id="dashboard" className="mx-auto max-w-7xl px-5 pb-10 pt-16 md:pt-24">
        <div className="max-w-3xl">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white px-3 py-1 text-xs dark:border-zinc-800 dark:bg-zinc-900">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"/> Conflict-aware RAG
          </div>
          <h1 className="text-4xl font-semibold tracking-tight md:text-6xl">Understand your rules.<br/><span className="text-zinc-500 dark:text-zinc-400">Even when they disagree.</span></h1>
          <p className="mt-6 max-w-2xl text-base leading-7 text-zinc-600 dark:text-zinc-400">Upload policy documents and ask questions. RuleLens retrieves evidence, identifies exceptions and conflicts, and gives grounded answers with sources.</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <label className="cursor-pointer rounded-xl bg-zinc-900 px-5 py-3 text-sm font-medium text-white hover:opacity-90 dark:bg-white dark:text-zinc-900">
              <span className="flex items-center gap-2"><Upload size={17}/> {uploading ? "Processing..." : "Upload Rulebook"}</span>
              <input type="file" accept=".pdf,.txt,.md" className="hidden" disabled={uploading} onChange={e=>e.target.files?.[0] && upload(e.target.files[0])}/>
            </label>
            <a href="#ask" className="rounded-xl border border-zinc-300 bg-white px-5 py-3 text-sm font-medium hover:bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-900 dark:hover:bg-zinc-800">Ask a Question</a>
          </div>
        </div>
        <div className="mt-14 grid gap-4 sm:grid-cols-3">
          {[["Documents", docs.length],["Chunks Indexed", docs.reduce((a,d)=>a+d.chunks,0)],["Retrieval", "Semantic"]].map(([label,value])=>(
            <div key={String(label)} className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-soft dark:border-zinc-800 dark:bg-zinc-900">
              <p className="text-sm text-zinc-500">{label}</p><p className="mt-2 text-2xl font-semibold">{value}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="documents" className="mx-auto max-w-7xl px-5 py-10">
        <div className="mb-5 flex items-end justify-between"><div><h2 className="text-2xl font-semibold">Documents</h2><p className="mt-1 text-sm text-zinc-500">Your indexed policy knowledge base.</p></div></div>
        <div className="grid gap-4 md:grid-cols-2">
          {docs.length === 0 ? (
            <label className="cursor-pointer rounded-2xl border border-dashed border-zinc-300 bg-white p-10 text-center dark:border-zinc-700 dark:bg-zinc-900 md:col-span-2">
              <FileText className="mx-auto mb-3 text-zinc-400"/><p className="font-medium">No documents yet</p><p className="mt-1 text-sm text-zinc-500">Upload a PDF, TXT or Markdown rulebook.</p>
              <input type="file" accept=".pdf,.txt,.md" className="hidden" onChange={e=>e.target.files?.[0] && upload(e.target.files[0])}/>
            </label>
          ) : docs.map(d=>(
            <div key={d.document_id} className="flex items-center justify-between rounded-2xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900">
              <div className="flex min-w-0 items-center gap-3"><div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-zinc-100 dark:bg-zinc-800"><FileText size={19}/></div><div className="min-w-0"><p className="truncate font-medium">{d.filename}</p><p className="text-xs text-zinc-500">{d.chunks} chunks · {d.pages} pages · Processed</p></div></div>
              <button aria-label={`Delete ${d.filename}`} onClick={()=>remove(d.document_id)} className="ml-3 rounded-lg p-2 text-zinc-500 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950"><Trash2 size={17}/></button>
            </div>
          ))}
        </div>
      </section>

      <section id="ask" className="mx-auto max-w-7xl px-5 py-10 pb-24">
        <div className="rounded-3xl border border-zinc-200 bg-white p-5 shadow-soft dark:border-zinc-800 dark:bg-zinc-900 md:p-8">
          <div className="mb-7"><div className="flex items-center gap-2"><Search size={20}/><h2 className="text-2xl font-semibold">Ask AI</h2></div><p className="mt-1 text-sm text-zinc-500">Answers are grounded in your indexed documents.</p></div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <textarea value={question} onChange={e=>setQuestion(e.target.value)} onKeyDown={e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();ask()}}} placeholder="Ask something about your uploaded rules..." rows={3} className="min-h-[96px] flex-1 resize-none rounded-2xl border border-zinc-300 bg-zinc-50 p-4 outline-none focus:ring-2 focus:ring-zinc-400 dark:border-zinc-700 dark:bg-zinc-950"/>
            <button onClick={ask} disabled={busy || !question.trim()} className="self-end rounded-xl bg-zinc-900 px-5 py-3 text-sm font-medium text-white disabled:opacity-40 dark:bg-white dark:text-zinc-900"><span className="flex items-center gap-2">{busy ? <Loader2 className="animate-spin" size={17}/> : <Send size={17}/>} Ask</span></button>
          </div>

          {answer && <div className="mt-8 space-y-5">
            <div className={`rounded-2xl border p-5 ${status==="CONFLICT" ? "border-amber-300 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/30" : status==="INSUFFICIENT_INFORMATION" ? "border-zinc-300 bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-950" : "border-emerald-200 bg-emerald-50 dark:border-emerald-900 dark:bg-emerald-950/30"}`}>
              <div className="flex items-center gap-2 font-semibold">{status==="CONFLICT" ? <AlertTriangle size={18}/> : status==="INSUFFICIENT_INFORMATION" ? <Search size={18}/> : <ShieldCheck size={18}/>} {status === "ANSWERED" ? "Answer" : status === "CONFLICT" ? "Conflict Detected" : "Insufficient Information"}</div>
              <p className="mt-4 whitespace-pre-wrap leading-7">{answer.answer}</p>
              {answer.conflict_explanation && <div className="mt-4 rounded-xl border border-current/10 p-4 text-sm"><b>Analysis:</b> {answer.conflict_explanation}</div>}
            </div>

            {answer.sources?.length > 0 && <div><h3 className="mb-3 font-semibold">Sources</h3><div className="grid gap-3 md:grid-cols-2">{answer.sources.map((s,i)=><div key={i} className="rounded-2xl border border-zinc-200 p-4 dark:border-zinc-800"><div className="flex items-start gap-3"><FileText size={18} className="mt-0.5 shrink-0 text-zinc-500"/><div><p className="font-medium">{s.document}</p><p className="mt-1 text-sm text-zinc-500">Page {s.page} · Relevance {Math.round(s.relevance*100)}%</p></div></div></div>)}</div></div>}

            {answer.evidence?.length > 0 && <details className="rounded-2xl border border-zinc-200 dark:border-zinc-800"><summary className="cursor-pointer px-5 py-4 font-medium">View Retrieved Evidence</summary><div className="space-y-4 border-t p-5 dark:border-zinc-800">{answer.evidence.map((e,i)=><div key={i} className="rounded-xl bg-zinc-50 p-4 dark:bg-zinc-950"><div className="mb-2 text-xs font-medium text-zinc-500">Source {i+1} · {e.document} · Page {e.page} · {Math.round(e.relevance*100)}%</div><p className="text-sm leading-6 text-zinc-700 dark:text-zinc-300">{e.text}</p></div>)}</div></details>}
          </div>}
        </div>
      </section>

      <footer className="border-t border-zinc-200 px-5 py-8 text-center text-xs text-zinc-500 dark:border-zinc-800">
        RuleLens · Conflict-Aware RAG for Policy Documents
      </footer>
    </main>
  );
}
