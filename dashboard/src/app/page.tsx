import Link from "next/link";
import "./globals.css";
import {
  Activity,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronRight,
  CircleDot,
  Fingerprint,
  GitBranch,
  LockKeyhole,
  ScanEye,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Workflow
} from "lucide-react";

const capabilities = [
  {
    icon: Fingerprint,
    number: "01",
    title: "Identity is only the beginning",
    text: "Bind every agent to a declared role, toolset, and resource boundary. A valid token never becomes a blank check."
  },
  {
    icon: ScanEye,
    number: "02",
    title: "Understand behavior in context",
    text: "Evaluate each action against role fit, behavior history, provenance, and sensitive-resource signals."
  },
  {
    icon: ShieldCheck,
    number: "03",
    title: "Put a control point in the loop",
    text: "Observe decisions in shadow mode or apply configured allow, pause, block, and restriction responses."
  }
];

const flow = [
  { icon: Workflow, label: "Agent action", detail: "A tool call is requested" },
  { icon: Shield, label: "Runtime gateway", detail: "Identity and policy are checked" },
  { icon: Sparkles, label: "Risk analysis", detail: "Signals are combined with context" },
  { icon: LockKeyhole, label: "Policy response", detail: "Allow, pause, block, or observe" }
];

export default function HomePage() {
  return (
    <main className="marketing-site">
      <header className="marketing-header">
        <nav className="marketing-nav" aria-label="Main navigation">
          <Link className="marketing-brand" href="/" aria-label="DRISHTI home">
            <span className="marketing-brand-mark">D</span>
            <span>DRISHTI<span className="brand-period">.</span></span>
          </Link>
          <div className="marketing-nav-links">
            <Link href="#platform">Platform</Link>
            <Link href="#how-it-works">How it works</Link>
            <Link href="#security">Security model</Link>
          </div>
          <div className="marketing-nav-actions">
            <Link className="marketing-login" href="/dashboard">Sign in</Link>
            <Link className="marketing-nav-cta" href="/dashboard">Open dashboard <ArrowUpRight size={15} /></Link>
          </div>
        </nav>
      </header>

      <section className="marketing-hero">
        <div className="hero-copy">
          <div className="marketing-eyebrow"><span className="eyebrow-spark"><Sparkles size={13} /></span> RUNTIME SECURITY FOR AI AGENTS</div>
          <h1>Protect your agents.<br /><span>Secure your enterprise.</span></h1>
          <p className="hero-description">
            DRISHTI provides the critical governance layer for autonomous agents. Detect identity drift, enforce runtime policies, and maintain full visibility into every tool call.
          </p>
          <div className="hero-actions">
            <Link className="hero-primary-cta" href="/dashboard">Get Started Free <ArrowRight size={16} /></Link>
            <Link className="hero-secondary-cta" href="#how-it-works">Watch Demo <ChevronRight size={16} /></Link>
          </div>
          <div className="hero-trust-line">
            <div className="trust-logos">
              <span>Trusted by innovative teams at</span>
              <div className="logo-strip">
                <div className="logo-placeholder">VELOCITY</div>
                <div className="logo-placeholder">CORE AI</div>
                <div className="logo-placeholder">NEXUS</div>
              </div>
            </div>
          </div>
        </div>

        <div className="hero-visual" aria-label="DRISHTI Command Center Preview">
          <div className="preview-window">
            <div className="preview-titlebar">
              <div className="preview-brand">
                <div className="preview-brand-mark">D</div>
                <span>DRISHTI <span>/ Command Center</span></span>
              </div>
              <div className="preview-demo-tag"><Activity size={10} /> LIVE SIMULATION</div>
            </div>
            <div className="preview-content">
              <div className="preview-heading">
                <div>
                  <small>SYSTEM STATUS</small>
                  <strong>Operational</strong>
                </div>
                <div className="preview-live"><i /> 14 Agents Active</div>
              </div>
              
              <div className="preview-metrics">
                <div className="preview-metric">
                  <span>TOOL CALLS</span>
                  <strong>1,248</strong>
                  <small className="mini-up">+12% vs last hour</small>
                </div>
                <div className="preview-metric">
                  <span>RISK SCORE</span>
                  <strong className="metric-warn">62</strong>
                  <small>Elevated activity</small>
                </div>
                <div className="preview-metric">
                  <span>BLOCKED</span>
                  <strong>17</strong>
                  <small>Policy enforcement</small>
                </div>
              </div>

              <div className="preview-lower">
                <div className="preview-activity">
                  <div className="preview-section-heading">RECENT EVENTS <span>View all</span></div>
                  <div className="preview-event">
                    <div className="event-icon event-ok"><ShieldCheck size={12} /></div>
                    <div><strong>Customer Support Agent</strong><small>GET /services/slack/discussions</small></div>
                    <span className="event-verdict verdict-allow">ALLOW</span>
                  </div>
                  <div className="preview-event">
                    <div className="event-icon event-alert"><ShieldAlert size="12" /></div>
                    <div><strong>Finance Assistant</strong><small>POST /payments/refunds</small></div>
                    <span className="event-verdict verdict-review">REVIEW</span>
                  </div>
                </div>
                <div className="preview-risk">
                  <div className="preview-section-heading">RISK PROFILE <Shield size={10} /></div>
                  <div className="risk-ring">
                    <div><strong>62</strong><small>/100</small></div>
                  </div>
                  <div className="risk-legend">
                    <span><i className="legend-role" /> Role fit</span>
                    <b>High</b>
                  </div>
                  <div className="risk-legend">
                    <span><i className="legend-source" /> Provenance</span>
                    <b>Secure</b>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div className="floating-signal signal-left">
            <div className="signal-icon signal-green"><ShieldCheck size={14} /></div>
            <span><b>Identity Verified</b><small>Agent: Support-01</small></span>
          </div>
          <div className="floating-signal signal-right">
            <div className="signal-icon signal-amber"><Activity size={14} /></div>
            <span><b>Anomaly Detected</b><small>Drift: +24%</small></span>
          </div>
        </div>
      </section>

      <section className="marketing-proof">
        <span>POWERING SECURE AGENT WORKFLOWS</span>
        <div><Activity size={14} /> 2.4M Tool calls monitored</div>
        <div><Shield size={14} /> 99.9% Policy uptime</div>
        <div><LockKeyhole size={14} /> SOC2 Type II Compliant</div>
      </section>

      <section className="marketing-section marketing-section-alt" id="analytics">
        <div className="analytics-preview-grid">
          <div className="chart-mockup">
            <div className="preview-section-heading">THREAT TRENDS <span>Last 30 days</span></div>
            <div className="chart-visual">
              <svg viewBox="0 0 400 120" className="chart-svg" fill="none">
                <defs>
                  <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#10b981" stopOpacity="0.18" />
                    <stop offset="100%" stopColor="#10b981" stopOpacity="0" />
                  </linearGradient>
                </defs>
                <path d="M 0,95 Q 50,85 100,65 T 200,70 T 280,35 T 350,45 T 400,20 L 400,120 L 0,120 Z" fill="url(#chartGradient)" />
                <path d="M 0,95 Q 50,85 100,65 T 200,70 T 280,35 T 350,45 T 400,20" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" />
                <circle cx="280" cy="35" r="4" fill="#10b981" />
                <circle cx="280" cy="35" r="8" fill="#10b981" fillOpacity="0.25" />
              </svg>
            </div>
            <div className="preview-metrics" style={{ marginTop: '1.5rem' }}>
              <div className="preview-metric">
                <span>PEAK RISK</span>
                <strong>84</strong>
              </div>
              <div className="preview-metric">
                <span>AVG DRIFT</span>
                <strong>+4.2%</strong>
              </div>
            </div>
          </div>
          <div className="section-intro">
            <div className="marketing-eyebrow">DEEP ANALYTICS</div>
            <h2>Turn agent activity into <span>actionable intelligence.</span></h2>
            <p>
              Move beyond simple logging. DRISHTI analyzes behavioral patterns to identify systemic risks, optimize agent performance, and prove compliance to stakeholders.
            </p>
            <div className="hero-actions">
              <Link className="hero-secondary-cta" href="/dashboard">Explore Analytics</Link>
            </div>
          </div>
        </div>
      </section>

      <section className="marketing-section capabilities-section" id="platform">
        <div className="section-intro">
          <div className="marketing-eyebrow">A CONTROL PLANE FOR AGENT ACTIONS</div>
          <h2>Trust the identity.<br /><span>Verify the behavior.</span></h2>
          <p>Agents are dynamic. Their security model should account for more than who they are—it should consider what they are doing, why, and with what authority.</p>
        </div>
        <div className="capability-grid">
          {capabilities.map(({ icon: Icon, number, title, text }) => (
            <article className="capability-card" key={number}>
              <div className="capability-topline"><span className="capability-icon"><Icon size={19} /></span><span>{number}</span></div>
              <h3>{title}</h3>
              <p>{text}</p>
              <Link href="/dashboard" aria-label={`Explore ${title}`}><ArrowUpRight size={16} /></Link>
            </article>
          ))}
        </div>
      </section>

      <section className="marketing-section workflow-section" id="how-it-works">
        <div className="workflow-header">
          <div><div className="marketing-eyebrow">FROM REQUEST TO RESPONSE</div><h2>Security at the moment<br />an action is requested.</h2></div>
          <p>DRISHTI evaluates activity at the runtime gateway. Risk, alerts, and enforcement decisions remain under backend policy control.</p>
        </div>
        <div className="workflow-track">
          {flow.map(({ icon: Icon, label, detail }, index) => (
            <div className="workflow-step" key={label}>
              <div className="workflow-node"><Icon size={19} /><span>0{index + 1}</span></div>
              <h3>{label}</h3><p>{detail}</p>
              {index < flow.length - 1 && <ArrowRight className="workflow-arrow" size={18} />}
            </div>
          ))}
        </div>
      </section>

      <section className="security-band" id="security">
        <div className="security-band-icon"><ShieldCheck size={22} /></div>
        <div><div className="marketing-eyebrow">A CLEAR SECURITY MODEL</div><h2>Policy decisions, not marketing promises.</h2><p>DRISHTI surfaces backend verdicts and evidence. In shadow mode it observes and records; enforcement requires the backend to be configured for enforce mode.</p></div>
        <Link href="/dashboard/enforcement">Explore enforcement <ArrowRight size={16} /></Link>
      </section>

      <section className="marketing-bottom-cta">
        <div className="cta-decoration"><ArrowDownRight size={90} /></div>
        <div className="marketing-eyebrow">SEE YOUR AGENT FLEET CLEARLY</div>
        <h2>Know what your agents are doing.<br /><span>Stay in control of what they can do.</span></h2>
        <p>Explore agent posture, security events, approvals, and runtime policy in the DRISHTI command center.</p>
        <Link className="hero-primary-cta" href="/dashboard">Open the command center <ArrowRight size={16} /></Link>
      </section>

      <footer className="marketing-footer">
        <Link className="marketing-brand" href="/" aria-label="DRISHTI home"><span className="marketing-brand-mark">D</span><span>DRISHTI<span className="brand-period">.</span></span></Link>
        <span>Runtime security and identity-drift detection for autonomous AI agents.</span>
        <div><Link href="/dashboard">Dashboard</Link><Link href="/dashboard/scenarios">Scenarios</Link><Link href="/dashboard/policies">Policies</Link></div>
        <small>DRISHTI · Agent runtime security</small>
      </footer>
    </main>
  );
}
