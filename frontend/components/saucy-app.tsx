"use client";
/* eslint-disable react-hooks/set-state-in-effect, @next/next/no-img-element */

import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  BadgeCheck,
  Building2,
  Camera,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleDot,
  Clock3,
  FileVideo,
  Flame,
  Loader2,
  MapPin,
  Navigation,
  Plus,
  ShieldCheck,
  Sparkles,
  Star,
  Truck,
  Upload,
  UserRound,
  Wrench,
} from "lucide-react";
import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Restaurant = { id: string; name: string; address: string; city: string; neighborhood: string; contact_name: string };
type Contractor = {
  id: string; name: string; company: string; specialty: string; specialty_label: string;
  available: boolean; emergency_available: boolean; rating: number; jobs_completed: number;
  eta_minutes: number; distance_miles: number; photo_initials: string; blurb: string;
};
type Event = { id: string; status: string; status_label: string; actor_role: string; actor_name: string; note?: string; created_at: string };
type Assessment = { category_label: string; severity: string; possible_issue: string; recommended_specialty_label: string; observations: string[]; immediate_action: string; source: string };
type Ticket = {
  id: string; status: string; status_label: string; title: string; description: string;
  location_note: string; urgency: string; photo_url?: string; video_url?: string; completion_note?: string;
  created_at: string; restaurant: Restaurant;
  assessment?: Assessment; assigned_contractor?: Contractor; matches: { contractor: Contractor; reasons: string[]; rank: number }[]; events: Event[];
};

const statusTone: Record<string, string> = {
  submitted: "slate", triaged: "violet", matching: "amber", accepted: "blue",
  en_route: "sky", in_progress: "orange", completed: "emerald", confirmed: "emerald",
};
const roleKey = "saucy-demo-role";
const contractorKey = "saucy-demo-contractor";

function apiUrl(path: string) {
  return `${API_URL}${path}`;
}
function mediaUrl(path?: string) {
  return path ? apiUrl(path) : undefined;
}
function cn(...items: (string | false | undefined)[]) { return items.filter(Boolean).join(" "); }
function titleFromPath(pathname: string) {
  if (pathname.includes("contractor")) return "contractor";
  if (pathname.includes("report")) return "report";
  if (pathname.includes("/tickets/")) return "ticket";
  return "restaurant";
}
async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(path), options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Something went wrong. Please try again.");
  }
  return res.json();
}

function Brand() {
  return <div className="brand"><span className="brand-mark"><Flame size={19} fill="currentColor" /></span><span>Saucy</span><em>Hospitality</em></div>;
}
function Status({ status, label }: { status: string; label?: string }) {
  return <span className={cn("status", `status-${statusTone[status] || "slate"}`)}><span className="status-dot" />{label || status.replaceAll("_", " ")}</span>;
}
function Avatar({ person, size = "md" }: { person: Contractor; size?: "sm" | "md" }) {
  return <span className={cn("avatar", `avatar-${size}`)}>{person.photo_initials}</span>;
}
function DateLabel({ date }: { date: string }) {
  const parsed = new Date(date);
  return <>{parsed.toLocaleDateString([], { month: "short", day: "numeric" })} · {parsed.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}</>;
}

function todayLabel() {
  return new Date().toLocaleDateString([], { weekday: "long", month: "long", day: "numeric" }).toUpperCase();
}

export function SaucyApp() {
  const [pathname, setPathname] = useState("/");
  const [role, setRole] = useState<"restaurant" | "contractor">("restaurant");
  const [restaurant, setRestaurant] = useState<Restaurant | null>(null);
  const [contractors, setContractors] = useState<Contractor[]>([]);
  const [contractorId, setContractorId] = useState("");
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [ticketError, setTicketError] = useState("");
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");

  const view = titleFromPath(pathname);
  const navigate = (path: string) => {
    window.history.pushState({}, "", path);
    setPathname(path);
    setNotice("");
  };

  useEffect(() => {
    setPathname(window.location.pathname);
    setRole((localStorage.getItem(roleKey) as "restaurant" | "contractor") || "restaurant");
    const sync = () => setPathname(window.location.pathname);
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);
  useEffect(() => {
    Promise.all([
      fetchApi<{ restaurants: Restaurant[] }>("/api/restaurants"),
      fetchApi<{ contractors: Contractor[] }>("/api/contractors"),
    ])
      .then(([{ restaurants }, { contractors: records }]) => {
        setRestaurant(restaurants[0] || null);
        setContractors(records);
        const persisted = localStorage.getItem(contractorKey);
        setContractorId(persisted || records[0]?.id || "");
      })
      .catch(() => setNotice("Backend is unavailable. Start FastAPI on port 8000."))
      .finally(() => setLoading(false));
  }, []);
  const refreshTickets = async () => {
    const data = await fetchApi<{ tickets: Ticket[] }>("/api/tickets");
    setTickets(data.tickets);
    return data.tickets;
  };
  useEffect(() => {
    if (!loading) refreshTickets().catch((error) => setNotice(error.message));
  }, [loading, pathname]);
  useEffect(() => {
    const match = pathname.match(/\/tickets\/([^/]+)/);
    if (!match) { setTicket(null); setTicketError(""); return; }
    let cancelled = false;
    const load = async () => {
      try {
        const data = await fetchApi<Ticket>(`/api/tickets/${match[1]}`);
        if (!cancelled) { setTicket(data); setTicketError(""); }
      } catch (error) {
        if (!cancelled) {
          setTicket(null);
          setTicketError(error instanceof Error ? error.message : "Unable to load ticket.");
        }
      }
    };
    load();
    const timer = window.setInterval(load, 4000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [pathname]);

  const switchRole = (next: "restaurant" | "contractor") => {
    setRole(next); localStorage.setItem(roleKey, next);
    if (view === "ticket") return;
    navigate(next === "restaurant" ? "/restaurant" : "/contractor");
  };
  const selectContractor = (id: string) => { setContractorId(id); localStorage.setItem(contractorKey, id); };
  const updateTicket = (next: Ticket) => { setTicket(next); refreshTickets().catch(() => undefined); };
  if (loading) return <div className="boot"><Loader2 className="spin" /><span>Preparing Saucy workspace…</span></div>;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Brand />
        <div className="workspace-label">WORKSPACE</div>
        <button className={cn("nav-item", view === "restaurant" && "nav-active")} onClick={() => navigate("/restaurant")}><Building2 size={18} />Restaurant</button>
        <button className={cn("nav-item", view === "contractor" && "nav-active")} onClick={() => navigate("/contractor")}><Wrench size={18} />Contractor network</button>
        <div className="sidebar-foot">
          <div className="safety-note"><ShieldCheck size={17} /><span>AI assessments are advisory. Always verify onsite.</span></div>
          {restaurant && <div className="restaurant-mini"><span className="mini-icon"><Building2 size={16} /></span><div><b>{restaurant.name}</b><span>{restaurant.neighborhood}, {restaurant.city}</span></div><ChevronRight size={16} /></div>}
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div className="crumb"><span>Operations</span><ChevronRight size={14} /><b>{view === "ticket" ? "Repair request" : view === "report" ? "New repair request" : view === "contractor" ? "Contractor network" : "Restaurant dashboard"}</b></div>
          <div className="top-actions">
            <div className="role-switch"><button className={cn(role === "restaurant" && "selected")} onClick={() => switchRole("restaurant")}><Building2 size={15} />Restaurant</button><button className={cn(role === "contractor" && "selected")} onClick={() => switchRole("contractor")}><Wrench size={15} />Contractor</button></div>
            <span className="demo-chip">Demo mode</span>
          </div>
        </header>
        {notice && <div className="notice"><AlertTriangle size={17} />{notice}<button onClick={() => setNotice("")}>×</button></div>}
        {view === "restaurant" && <RestaurantDashboard tickets={tickets} onReport={() => navigate("/restaurant/report")} onOpen={(id) => navigate(`/tickets/${id}`)} />}
        {view === "report" && <ReportIssue onCancel={() => navigate("/restaurant")} onCreated={(id) => navigate(`/tickets/${id}`)} setNotice={setNotice} />}
        {view === "contractor" && <ContractorDashboard tickets={tickets} contractors={contractors} contractorId={contractorId} onSelect={selectContractor} onOpen={(id) => navigate(`/tickets/${id}`)} />}
        {view === "ticket" && <TicketDetail ticket={ticket} ticketError={ticketError} role={role} contractorId={contractorId} onBack={() => navigate(role === "contractor" ? "/contractor" : "/restaurant")} onUpdate={updateTicket} onSwitchRole={switchRole} setNotice={setNotice} />}
      </main>
    </div>
  );
}

function isResolved(ticket: Ticket) {
  return ticket.status === "completed" || ticket.status === "confirmed";
}

function assignedEta(ticket: Ticket) {
  if (!ticket.assigned_contractor) return null;
  if (["accepted", "en_route", "in_progress"].includes(ticket.status)) return ticket.assigned_contractor.eta_minutes;
  return null;
}

function RestaurantDashboard({ tickets, onReport, onOpen }: { tickets: Ticket[]; onReport: () => void; onOpen: (id: string) => void }) {
  const openTickets = tickets.filter((ticket) => !isResolved(ticket));
  const waiting = openTickets.filter((ticket) => !ticket.assigned_contractor || ["submitted", "triaged", "matching"].includes(ticket.status));
  const etas = openTickets.map(assignedEta).filter((value): value is number => value != null);
  const fastestEta = etas.length ? `${Math.min(...etas)}m` : "—";
  const resolved = tickets.filter(isResolved).length;
  return <section className="page">
    <div className="hero-row"><div><p className="eyebrow">{todayLabel()}</p><h1>Keep service moving.</h1><p className="subhead">Report a facility issue and get the right restaurant technician on it.</p></div><button className="button button-primary" onClick={onReport}><Plus size={18} />Report an issue</button></div>
    <div className="stat-grid">
      <Stat icon={<Wrench />} value={String(openTickets.length).padStart(2, "0")} label="Active repairs" tone="coral" />
      <Stat icon={<Clock3 />} value={fastestEta} label="Fastest ETA" tone="blue" />
      <Stat icon={<AlertTriangle />} value={String(waiting.length).padStart(2, "0")} label="Needs attention" tone="amber" />
      <Stat icon={<CheckCircle2 />} value={String(resolved).padStart(2, "0")} label="Resolved this month" tone="green" />
    </div>
    <div className="section-row"><div><h2>Repair requests</h2><p>Live status across your restaurant.</p></div><button className="text-button" onClick={onReport}>New request <ArrowRight size={16} /></button></div>
    {tickets.length === 0 ? <div className="empty-state"><span className="empty-icon"><Wrench size={24} /></span><h3>No repair requests yet</h3><p>When something needs attention, report it here and we’ll line up the right specialist.</p><button className="button button-primary" onClick={onReport}><Plus size={17} />Report an issue</button></div> :
      <div className="ticket-list">{tickets.map((ticket) => <TicketCard key={ticket.id} ticket={ticket} onOpen={onOpen} />)}</div>}
  </section>;
}
function Stat({ icon, value, label, tone }: { icon: ReactNode; value: string; label: string; tone: string }) {
  return <div className="stat-card"><span className={cn("stat-icon", `stat-${tone}`)}>{icon}</span><div><b>{value}</b><span>{label}</span></div></div>;
}
function TicketCard({ ticket, onOpen }: { ticket: Ticket; onOpen: (id: string) => void }) {
  return <button className="ticket-card" onClick={() => onOpen(ticket.id)}>
    <div className="ticket-leading">{ticket.photo_url ? <img src={mediaUrl(ticket.photo_url)} alt="" /> : <Wrench size={22} />}</div>
    <div className="ticket-core"><div className="ticket-topline"><Status status={ticket.status} label={ticket.status_label} /><span className="ticket-date"><DateLabel date={ticket.created_at} /></span></div><h3>{ticket.title}</h3><p><MapPin size={14} />{ticket.location_note}</p></div>
    <div className="ticket-person">{ticket.assigned_contractor ? <><Avatar person={ticket.assigned_contractor} size="sm" /><span>{ticket.assigned_contractor.name}</span></> : <span className="match-label"><Sparkles size={15} />{ticket.matches.length ? `${ticket.matches.length} matches` : "Assessment pending"}</span>}</div><ChevronRight className="ticket-arrow" size={20} />
  </button>;
}

function ReportIssue({ onCancel, onCreated, setNotice }: { onCancel: () => void; onCreated: (id: string) => void; setNotice: (value: string) => void }) {
  const [description, setDescription] = useState("");
  const [location, setLocation] = useState("");
  const [urgency, setUrgency] = useState("medium");
  const [photo, setPhoto] = useState<File | null>(null);
  const [video, setVideo] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const photoPreview = useMemo(() => photo ? URL.createObjectURL(photo) : "", [photo]);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (description.trim().length < 10) return setNotice("Add a little more detail so we can triage the issue.");
    const form = new FormData();
    form.append("description", description); form.append("location_note", location); form.append("urgency", urgency);
    if (photo) form.append("photo", photo); if (video) form.append("video", video);
    setSubmitting(true);
    try {
      const ticket = await fetchApi<Ticket>("/api/tickets", { method: "POST", body: form });
      try {
        await fetchApi<Ticket>(`/api/tickets/${ticket.id}/triage`, { method: "POST" });
      } catch (error) {
        setNotice(error instanceof Error ? error.message : "Assessment is still pending. You can retry it from the request.");
      }
      onCreated(ticket.id);
    } catch (error) { setNotice(error instanceof Error ? error.message : "Unable to create request."); } finally { setSubmitting(false); }
  };
  return <section className="page report-page"><button className="back-button" onClick={onCancel}><ArrowLeft size={16} />Back to dashboard</button><div className="report-heading"><span className="eyebrow">NEW REPAIR REQUEST</span><h1>What needs attention?</h1><p>Share what’s happening. Saucy will organize the issue and find a qualified technician.</p></div>
    <form className="report-grid" onSubmit={submit}>
      <div className="form-card form-main"><label className="field-label">Describe the issue <span>Required</span></label><textarea value={description} onChange={(event) => setDescription(event.target.value)} rows={5} placeholder="Example: The walk-in refrigerator is warm and water is pooling near the door." />
        <div className="form-divider" /><label className="field-label">Where is it happening?</label><div className="input-with-icon"><MapPin size={17} /><input value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Example: Walk-in cooler, kitchen back line" /></div>
        <div className="form-divider" /><label className="field-label">How urgent is this?</label><div className="urgency-grid">{[["critical","Critical","Food safety or service stopped"],["high","High","Affects operations today"],["medium","Medium","Needs attention soon"],["low","Low","Can be scheduled"]].map(([id,label,copy]) => <button type="button" key={id} onClick={() => setUrgency(id)} className={cn("urgency-option", urgency === id && "urgency-selected")}><span className={cn("urgency-dot", `dot-${id}`)} /> <span><b>{label}</b><small>{copy}</small></span><span className="radio">{urgency === id && <Check size={13} />}</span></button>)}</div>
      </div>
      <div className="form-card evidence-card"><div><label className="field-label">Add visual evidence <span>Optional</span></label><p className="field-help">A photo helps the technician prepare. Video is shared with the technician, not analyzed.</p></div>
        <label className={cn("dropzone", photoPreview && "has-preview")}>{photoPreview ? <img src={photoPreview} alt="Selected issue" /> : <><Camera size={24}/><b>Add a photo</b><span>JPG, PNG, WebP up to 8 MB</span></>}<input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => setPhoto(event.target.files?.[0] || null)} /></label>
        <label className="video-upload"><FileVideo size={18} /><span>{video ? video.name : "Attach a short video"}</span><Upload size={15} /><input type="file" accept="video/mp4,video/quicktime,video/webm" onChange={(event) => setVideo(event.target.files?.[0] || null)} /></label>
        <div className="ai-preview"><Sparkles size={17} /><div><b>AI-assisted assessment</b><p>We’ll suggest a repair category and severity. A technician always verifies onsite.</p></div></div>
      </div>
      <div className="report-footer"><button type="button" className="button button-ghost" onClick={onCancel}>Cancel</button><button className="button button-primary" disabled={submitting}>{submitting ? <><Loader2 className="spin" size={18}/>Analyzing issue…</> : <>Create repair request <ArrowRight size={18}/></>}</button></div>
    </form>
  </section>;
}

function dispatchStatus(contractor: Contractor, tickets: Ticket[]) {
  const onJob = tickets.some((ticket) => ticket.assigned_contractor?.id === contractor.id && ["accepted", "en_route", "in_progress"].includes(ticket.status));
  if (onJob) return { tone: "busy", label: "On a job" };
  if (contractor.available) return { tone: "available", label: "Available for dispatch" };
  return { tone: "unavailable", label: "Unavailable" };
}

function ContractorDashboard({ tickets, contractors, contractorId, onSelect, onOpen }: { tickets: Ticket[]; contractors: Contractor[]; contractorId: string; onSelect: (id: string) => void; onOpen: (id: string) => void }) {
  const filtered = tickets.filter((ticket) => ticket.assigned_contractor?.id === contractorId || (ticket.status === "matching" && ticket.matches.some((match) => match.contractor.id === contractorId)));
  const contractor = contractors.find((item) => item.id === contractorId);
  const status = contractor ? dispatchStatus(contractor, tickets) : null;
  return <section className="page"><div className="hero-row contractor-hero"><div><p className="eyebrow">CONTRACTOR NETWORK</p><h1>Jobs worth taking.</h1><p className="subhead">Accept qualified restaurant work and keep every repair moving.</p></div><div className="persona-select"><label>Viewing as</label><select value={contractorId} onChange={(event) => onSelect(event.target.value)}>{contractors.map((item) => <option value={item.id} key={item.id}>{item.name} · {item.company}</option>)}</select></div></div>
    {contractor && status && <div className="contractor-banner"><Avatar person={contractor}/><div><b>{contractor.name}</b><span>{contractor.company} · {contractor.specialty_label}</span></div><span className={cn("dispatch-chip", `dispatch-${status.tone}`)}><span/>{status.label}</span><div className="banner-metrics"><span><Star size={14} fill="currentColor"/>{contractor.rating}</span><span>{contractor.jobs_completed} jobs completed</span></div></div>}
    <div className="section-row"><div><h2>Qualified work</h2><p>{filtered.length ? `${filtered.length} request${filtered.length === 1 ? "" : "s"} matched to your specialty.` : "No open jobs are currently matched to this persona."}</p></div></div>
    {filtered.length ? <div className="job-grid">{filtered.map((ticket) => <JobCard key={ticket.id} ticket={ticket} onOpen={onOpen}/>)}</div> : <div className="empty-state"><span className="empty-icon"><BadgeCheck size={24}/></span><h3>You’re all caught up</h3><p>New jobs matched to your specialty will appear here.</p></div>}
  </section>;
}
function JobCard({ ticket, onOpen }: { ticket: Ticket; onOpen: (id: string) => void }) {
  const candidate = ticket.matches[0]?.contractor;
  return <button className="job-card" onClick={() => onOpen(ticket.id)}><div className="job-card-head"><Status status={ticket.status} label={ticket.status_label}/><span className="job-time"><Clock3 size={14}/><DateLabel date={ticket.created_at}/></span></div><h3>{ticket.assessment?.category_label || "Maintenance request"}</h3><p className="job-desc">{ticket.description}</p><div className="job-meta"><span><MapPin size={15}/>{ticket.restaurant.neighborhood}</span><span><AlertTriangle size={15}/>{ticket.urgency} priority</span></div>{candidate && <div className="job-match"><Sparkles size={15}/>{candidate.eta_minutes} min away · strong specialty match <ChevronRight size={16}/></div>}</button>;
}

function TicketDetail({ ticket, ticketError, role, contractorId, onBack, onUpdate, onSwitchRole, setNotice }: { ticket: Ticket | null; ticketError: string; role: "restaurant" | "contractor"; contractorId: string; onBack: () => void; onUpdate: (ticket: Ticket) => void; onSwitchRole: (role: "restaurant" | "contractor") => void; setNotice: (message: string) => void }) {
  const [busy, setBusy] = useState(false);
  const isMatchedContractor = ticket?.matches.some((match) => match.contractor.id === contractorId);
  const isAssigned = ticket?.assigned_contractor?.id === contractorId;
  const action = async (path: string, method: string, body?: unknown) => {
    if (!ticket) return; setBusy(true);
    try { const updated = await fetchApi<Ticket>(path, { method, headers: body ? { "Content-Type": "application/json" } : undefined, body: body ? JSON.stringify(body) : undefined }); onUpdate(updated); }
    catch (error) { setNotice(error instanceof Error ? error.message : "Could not update the repair."); } finally { setBusy(false); }
  };
  if (ticketError) return <section className="page detail-page"><button className="back-button" onClick={onBack}><ArrowLeft size={16}/>Back to {role === "contractor" ? "contractor network" : "restaurant dashboard"}</button><div className="empty-state"><span className="empty-icon"><AlertTriangle size={24}/></span><h3>Repair request not found</h3><p>{ticketError}</p><button className="button button-primary" onClick={onBack}>Return to dashboard</button></div></section>;
  if (!ticket) return <section className="page detail-page"><div className="detail-loading"><Loader2 className="spin"/>Loading repair request…</div></section>;
  const nextAction: [string, string, ReactNode] | null = ticket.status === "accepted" ? ["en_route", "Mark en route", <Truck key="truck" size={17}/>] : ticket.status === "en_route" ? ["in_progress", "Start repair", <Wrench key="wrench" size={17}/>] : ticket.status === "in_progress" ? ["completed", "Mark repair complete", <CheckCircle2 key="check" size={17}/>] : null;
  return <section className="page detail-page"><button className="back-button" onClick={onBack}><ArrowLeft size={16}/>Back to {role === "contractor" ? "contractor network" : "restaurant dashboard"}</button>
    <div className="detail-header"><div><div className="detail-kicker"><Status status={ticket.status} label={ticket.status_label}/><span>#{ticket.id.slice(-6).toUpperCase()}</span></div><h1>{ticket.assessment?.category_label || "Repair request"}</h1><p><MapPin size={16}/>{ticket.restaurant.name} · {ticket.location_note}</p></div>{ticket.status === "matching" && <div className="matching-live"><span className="pulse"/><span>Technicians are reviewing this request</span></div>}</div>
    <div className="detail-grid"><div className="detail-main"><section className="detail-card"><div className="card-heading"><div><p className="eyebrow">ISSUE REPORTED</p><h2>What the team shared</h2></div><span className={cn("urgency-tag", `urgency-${ticket.urgency}`)}>{ticket.urgency} priority</span></div><div className="issue-content">{ticket.photo_url ? <img className="issue-image" src={mediaUrl(ticket.photo_url)} alt="Reported maintenance issue" /> : <div className="issue-placeholder"><Camera size={23}/><span>No photo attached</span></div>}<div><p>{ticket.description}</p>{ticket.video_url && <span className="evidence-pill"><FileVideo size={15}/>Video attached for technician</span>}<div className="reported-by"><UserRound size={15}/>Reported by {ticket.restaurant.contact_name} · <DateLabel date={ticket.created_at}/></div></div></div></section>
      {ticket.assessment && <section className="detail-card ai-card"><div className="card-heading"><div><p className="eyebrow eyebrow-ai"><Sparkles size={14}/>AI-ASSISTED ASSESSMENT</p><h2>Recommended next move</h2></div><span className="advisory">Advisory · verify onsite</span></div><div className="assessment-grid"><div><span>Likely category</span><b>{ticket.assessment.category_label}</b></div><div><span>Suggested severity</span><Status status={ticket.assessment.severity} label={ticket.assessment.severity}/></div><div><span>Recommended trade</span><b>{ticket.assessment.recommended_specialty_label}</b></div></div><div className="possible-issue"><AlertTriangle size={17}/><div><b>{ticket.assessment.possible_issue}</b><p>{ticket.assessment.observations[0]}</p></div></div><div className="immediate-action"><ShieldCheck size={17}/><span><b>Until a technician arrives:</b> {ticket.assessment.immediate_action}</span></div></section>}
      {role === "restaurant" && <section className="detail-card"><div className="card-heading"><div><p className="eyebrow">REPAIR TIMELINE</p><h2>Every handoff, in one place</h2></div></div><Timeline events={ticket.events}/></section>}
      </div>
      <aside className="detail-side"><ActionPanel ticket={ticket} role={role} isMatched={Boolean(isMatchedContractor)} isAssigned={Boolean(isAssigned)} busy={busy} nextAction={nextAction} onAccept={() => action(`/api/tickets/${ticket.id}/accept`, "POST", { contractor_id: contractorId })} onRetry={() => action(`/api/tickets/${ticket.id}/triage`, "POST")} onProgress={(status) => action(`/api/tickets/${ticket.id}/status`, "PATCH", { contractor_id: contractorId, status, note: status === "completed" ? "Cooling performance restored and leak area dried. Monitor temperatures through the next service." : undefined })} onConfirm={() => action(`/api/tickets/${ticket.id}/confirm`, "POST", { note: "Kitchen confirmed the unit is holding temperature." })} onSwitchRole={onSwitchRole}/>{role === "restaurant" && ticket.status === "matching" && <CandidateList candidates={ticket.matches}/>}</aside>
    </div>
  </section>;
}
function Timeline({ events }: { events: Event[] }) {
  return <div className="timeline">{events.map((event, index) => <div className="timeline-event" key={event.id}><div className={cn("timeline-dot", index === events.length - 1 && "timeline-current")}><Check size={12}/></div><div><div className="timeline-line"><b>{event.status_label}</b><span><DateLabel date={event.created_at}/></span></div><p>{event.note || `${event.actor_name} updated this repair.`}</p><small>{event.actor_role === "system" ? "Saucy" : event.actor_name}</small></div></div>)}</div>;
}
function ActionPanel({ ticket, role, isMatched, isAssigned, busy, nextAction, onAccept, onRetry, onProgress, onConfirm, onSwitchRole }: { ticket: Ticket; role: "restaurant" | "contractor"; isMatched: boolean; isAssigned: boolean; busy: boolean; nextAction: [string, string, ReactNode] | null; onAccept: () => void; onRetry: () => void; onProgress: (status: string) => void; onConfirm: () => void; onSwitchRole: (role: "restaurant" | "contractor") => void }) {
  const pendingAssessment = ticket.status === "submitted" || ticket.status === "triaged";
  if (role === "contractor") {
    if (pendingAssessment) return <section className="action-card"><span className="action-icon action-amber"><Loader2 className="spin" size={20}/></span><h3>Not ready for dispatch</h3><p>This request is still being assessed. It will appear as a job once a trade match is ready.</p></section>;
    if (ticket.status === "matching" && isMatched) return <section className="action-card contractor-action"><span className="action-icon action-coral"><Sparkles size={20}/></span><h3>Ready for dispatch?</h3><p>This restaurant needs a qualified {ticket.assessment?.recommended_specialty_label || "technician"}.</p><button className="button button-primary button-full" disabled={busy} onClick={onAccept}>{busy ? <Loader2 className="spin" size={17}/> : <Check size={17}/>}Accept job</button><small>Accepting reserves this request for your team.</small></section>;
    if (isAssigned && nextAction) return <section className="action-card contractor-action"><span className="action-icon action-blue">{nextAction[2]}</span><h3>{nextAction[1]}</h3><p>Keep the restaurant team informed as you work through the repair.</p><button className="button button-primary button-full" disabled={busy} onClick={() => onProgress(nextAction[0])}>{busy ? <Loader2 className="spin" size={17}/> : nextAction[2]}{nextAction[1]}</button></section>;
    if (isAssigned && ticket.status === "completed") return <section className="action-card"><span className="action-icon action-green"><CheckCircle2 size={20}/></span><h3>Repair marked complete</h3><p>Waiting for the restaurant team to confirm the equipment is back in service.</p></section>;
  }
  if (role === "restaurant") {
    if (pendingAssessment) return <section className="action-card"><span className="action-icon action-amber"><Loader2 className="spin" size={20}/></span><h3>Assessment pending</h3><p>Saucy is still organizing this report and matching a technician. Retry if this is taking too long.</p><button className="button button-primary button-full" disabled={busy} onClick={onRetry}>{busy ? <Loader2 className="spin" size={17}/> : <Sparkles size={17}/>}Retry assessment</button></section>;
    if (ticket.status === "matching") return <section className="action-card"><span className="action-icon action-amber"><Loader2 className="spin" size={20}/></span><h3>Finding the right technician</h3><p>We matched this request by trade, availability, and travel time. A contractor can accept it now.</p><button className="button button-secondary button-full" onClick={() => onSwitchRole("contractor")}><Wrench size={17}/>View contractor side</button></section>;
    if (ticket.assigned_contractor) return <section className="action-card assigned-card"><div className="assigned-head"><Avatar person={ticket.assigned_contractor}/><div><b>{ticket.assigned_contractor.name}</b><span>{ticket.assigned_contractor.company}</span></div></div><div className="assigned-meta"><span><Star size={14} fill="currentColor"/>{ticket.assigned_contractor.rating} rating</span><span><Navigation size={14}/>{ticket.assigned_contractor.eta_minutes} min away</span></div>{ticket.status === "completed" ? <button className="button button-primary button-full" disabled={busy} onClick={onConfirm}>{busy ? <Loader2 className="spin" size={17}/> : <CheckCircle2 size={17}/>}Confirm repair complete</button> : <button className="button button-secondary button-full" onClick={() => onSwitchRole("contractor")}><Wrench size={17}/>Continue demo as contractor</button>}</section>;
    if (ticket.status === "confirmed") return <section className="action-card"><span className="action-icon action-green"><BadgeCheck size={20}/></span><h3>Repair confirmed</h3><p>The restaurant team confirmed this issue is resolved. Nice work.</p></section>;
  }
  return <section className="action-card"><span className="action-icon"><CircleDot size={20}/></span><h3>This job is unavailable</h3><p>Switch personas or return to the dashboard to view active work.</p></section>;
}
function CandidateList({ candidates }: { candidates: Ticket["matches"] }) {
  return <section className="candidates"><div className="candidate-heading"><Sparkles size={16}/><span>Top technician matches</span></div>{candidates.map((match) => <div className="candidate" key={match.contractor.id}><Avatar person={match.contractor} size="sm"/><div><b>{match.contractor.name}</b><span>{match.contractor.company}</span><small>{match.reasons.join(" · ")}</small></div><strong>{match.contractor.eta_minutes}m</strong></div>)}</section>;
}
