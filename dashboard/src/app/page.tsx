"use client";

import Link from "next/link";
import { useState } from "react";
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  BarChart2,
  Check,
  CheckCircle2,
  CheckSquare,
  ChevronRight,
  Download,
  ExternalLink,
  Filter,
  FolderKanban,
  Gift,
  HelpCircle,
  Home,
  LayoutDashboard,
  Lock,
  Mail,
  MoreVertical,
  MousePointer,
  Pencil,
  Play,
  Search,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Trash2,
  Users
} from "lucide-react";

export default function HomePage() {
  const [activeNav, setActiveNav] = useState("Dashboard");
  const [searchFilter, setSearchFilter] = useState("");

  const vendorRows = [
    {
      id: "ephemeral",
      name: "Ephemeral",
      domain: "ephemeral.io",
      initial: "E",
      initialBg: "bg-purple-600/30 text-purple-300 border-purple-500/40",
      rating: 90,
      ratingChange: "+1.5%",
      changePositive: true,
      lastAssessed: "22 Jan 2026",
      badges: [
        { label: "Active", style: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" },
        { label: "Customer data", style: "bg-blue-500/15 text-blue-300 border-blue-500/30" },
        { label: "Admin", style: "bg-indigo-500/15 text-indigo-300 border-indigo-500/30" },
        { label: "+5", style: "bg-white/10 text-slate-300 border-white/10" }
      ]
    },
    {
      id: "slacklm",
      name: "SlackLM Lab",
      domain: "slacklm.com",
      initial: "S",
      initialBg: "bg-blue-600/30 text-blue-300 border-blue-500/40",
      rating: 72,
      ratingChange: "+4%",
      changePositive: true,
      lastAssessed: "20 Jan 2026",
      badges: [
        { label: "Active", style: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" },
        { label: "Business data", style: "bg-blue-500/15 text-blue-300 border-blue-500/30" },
        { label: "Admin", style: "bg-indigo-500/15 text-indigo-300 border-indigo-500/30" },
        { label: "+4", style: "bg-white/10 text-slate-300 border-white/10" }
      ]
    },
    {
      id: "warpseed",
      name: "Warpspeed AI",
      domain: "getwarpseed.com",
      initial: "W",
      initialBg: "bg-cyan-600/30 text-cyan-300 border-cyan-500/40",
      rating: 78,
      ratingChange: "+6%",
      changePositive: true,
      lastAssessed: "24 Jan 2026",
      badges: [
        { label: "Active", style: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" },
        { label: "Customer data", style: "bg-blue-500/15 text-blue-300 border-blue-500/30" },
        { label: "Financial", style: "bg-pink-500/15 text-pink-300 border-pink-500/30" }
      ]
    },
    {
      id: "cloudwatch",
      name: "CloudWatch Guard",
      domain: "cloudwatch.app",
      initial: "C",
      initialBg: "bg-amber-600/30 text-amber-300 border-amber-500/40",
      rating: 58,
      ratingChange: "-3%",
      changePositive: false,
      lastAssessed: "26 Jan 2026",
      badges: [
        { label: "Active", style: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" },
        { label: "Database access", style: "bg-amber-500/15 text-amber-300 border-amber-500/30" },
        { label: "Admin", style: "bg-indigo-500/15 text-indigo-300 border-indigo-500/30" }
      ]
    },
    {
      id: "contractai",
      name: "ContractAI",
      domain: "contractai.io",
      initial: "C",
      initialBg: "bg-purple-600/30 text-purple-300 border-purple-500/40",
      rating: 42,
      ratingChange: "-7%",
      changePositive: false,
      lastAssessed: "10 Jan 2026",
      badges: [
        { label: "Active", style: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" },
        { label: "Salesforce", style: "bg-cyan-500/15 text-cyan-300 border-cyan-500/30" },
        { label: "Admin", style: "bg-indigo-500/15 text-indigo-300 border-indigo-500/30" },
        { label: "+4", style: "bg-white/10 text-slate-300 border-white/10" }
      ]
    }
  ];

  const filteredRows = vendorRows.filter((r) =>
    r.name.toLowerCase().includes(searchFilter.toLowerCase()) ||
    r.domain.toLowerCase().includes(searchFilter.toLowerCase())
  );

  // Subtle organic twinkling cosmic stars
  const cosmicStars = [
    { top: "10%", left: "14%", size: "w-1 h-1", delay: "0.2s" },
    { top: "18%", left: "6%", size: "w-1.5 h-1.5", delay: "1.4s" },
    { top: "7%", left: "32%", size: "w-1 h-1", delay: "2.1s" },
    { top: "14%", left: "68%", size: "w-1.5 h-1.5", delay: "0.8s" },
    { top: "25%", left: "84%", size: "w-1 h-1", delay: "3.2s" },
    { top: "38%", left: "93%", size: "w-1.5 h-1.5", delay: "1.7s" },
    { top: "52%", left: "89%", size: "w-1 h-1", delay: "2.5s" },
    { top: "32%", left: "10%", size: "w-1 h-1", delay: "1.1s" },
    { top: "64%", left: "5%", size: "w-1.5 h-1.5", delay: "2.8s" },
    { top: "75%", left: "95%", size: "w-1 h-1", delay: "0.5s" },
    { top: "85%", left: "12%", size: "w-1 h-1", delay: "1.9s" },
    { top: "90%", left: "80%", size: "w-1.5 h-1.5", delay: "2.4s" }
  ];

  return (
    <div className="marketing-site relative min-h-screen bg-[#040408] text-white selection:bg-purple-600 selection:text-white">
      {/* ------------------------------------------------------------- */}
      {/* 1. CINEMATIC CELESTIAL PLANETARY ATMOSPHERE & ANIMATED ARC */}
      {/* ------------------------------------------------------------- */}
      <div className="pointer-events-none absolute top-[-60px] left-1/2 -translate-x-1/2 w-full max-w-[1920px] h-[1050px] overflow-hidden z-0">
        {/* Origin Coronal Light Flare (Top-Left entrance of the planetary beam) */}
        <div className="absolute -top-16 -left-16 w-[700px] h-[520px] rounded-full bg-gradient-to-br from-cyan-400/35 via-purple-600/30 to-transparent blur-[100px] animate-nebula-1" />

        {/* Ambient Center Sky Nebula Bloom */}
        <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-[950px] h-[480px] rounded-full bg-purple-700/22 blur-[130px]" />

        {/* Right Flank Celestial Aura */}
        <div className="absolute top-16 right-[-80px] w-[750px] h-[850px] rounded-full bg-gradient-to-bl from-purple-600/32 via-fuchsia-600/22 to-transparent blur-[115px] animate-nebula-2" />

        {/* Twinkling Cosmic Celestial Stars */}
        {cosmicStars.map((star, idx) => (
          <div
            key={idx}
            className={`absolute rounded-full bg-white shadow-[0_0_8px_rgba(255,255,255,0.95)] animate-star-twinkle ${star.size}`}
            style={{ top: star.top, left: star.left, animationDelay: star.delay }}
          />
        ))}

        {/* Multi-layered Radiant Celestial Planetary Ring / Arc */}
        <svg
          viewBox="0 0 1800 1000"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="absolute inset-0 w-full h-full animate-beam-shimmer"
        >
          <defs>
            {/* Atmospheric Outer Flare Gradient */}
            <linearGradient id="auroraAtmosphereGrad" x1="0" y1="80" x2="1800" y2="700" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.8" />
              <stop offset="20%" stopColor="#818cf8" stopOpacity="0.9" />
              <stop offset="45%" stopColor="#c084fc" stopOpacity="0.95" />
              <stop offset="70%" stopColor="#a855f7" stopOpacity="0.85" />
              <stop offset="92%" stopColor="#e879f9" stopOpacity="0.5" />
              <stop offset="100%" stopColor="#6366f1" stopOpacity="0" />
            </linearGradient>

            {/* Mid Plasma Ion Gradient */}
            <linearGradient id="auroraPlasmaGrad" x1="0" y1="80" x2="1800" y2="700" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#e0f2fe" stopOpacity="1" />
              <stop offset="18%" stopColor="#38bdf8" stopOpacity="0.95" />
              <stop offset="45%" stopColor="#c084fc" stopOpacity="1" />
              <stop offset="75%" stopColor="#a855f7" stopOpacity="0.95" />
              <stop offset="100%" stopColor="#818cf8" stopOpacity="0.2" />
            </linearGradient>

            {/* Core Razor Light Gradient */}
            <linearGradient id="auroraRazorGrad" x1="0" y1="80" x2="1800" y2="700" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#ffffff" stopOpacity="1" />
              <stop offset="35%" stopColor="#ffffff" stopOpacity="1" />
              <stop offset="65%" stopColor="#f5d0fe" stopOpacity="1" />
              <stop offset="100%" stopColor="#c084fc" stopOpacity="0.4" />
            </linearGradient>

            {/* Animated Energy Stream Gradient */}
            <linearGradient id="auroraStreamGrad" x1="0" y1="80" x2="1800" y2="700" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#ffffff" stopOpacity="1" />
              <stop offset="50%" stopColor="#f472b6" stopOpacity="1" />
              <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.9" />
            </linearGradient>

            {/* Heavy Atmospheric Blur Filter */}
            <filter id="heavyAtmosphereBlur" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="38" />
            </filter>

            {/* Mid Plasma Blur Filter */}
            <filter id="midPlasmaBlur" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="14" />
            </filter>

            {/* Tight Core Glow Filter */}
            <filter id="tightCoreBlur" x="-10%" y="-10%" width="120%" height="120%">
              <feGaussianBlur stdDeviation="4" />
            </filter>
          </defs>

          {/* Sweeping Path Coordinates: Enters high at left (-60, 90), arches majestically over top, sweeps down right (1720, 620) */}
          {/* Layer 1: Atmospheric Outer Bloom (Thick, diffused celestial haze) */}
          <path
            d="M -150 420 C 220 30, 1420 20, 1980 450"
            stroke="url(#auroraAtmosphereGrad)"
            strokeWidth="80"
            strokeLinecap="round"
            filter="url(#heavyAtmosphereBlur)"
            opacity="0.38"
          />

          {/* Layer 2: Mid Plasma Ion Glow (Vibrant violet/cyan radiance) */}
          <path
            d="M -150 420 C 220 30, 1420 20, 1980 450"
            stroke="url(#auroraPlasmaGrad)"
            strokeWidth="24"
            strokeLinecap="round"
            filter="url(#midPlasmaBlur)"
            opacity="0.78"
          />

          {/* Layer 3: Luminous Core Beam */}
          <path
            d="M -150 420 C 220 30, 1420 20, 1980 450"
            stroke="url(#auroraPlasmaGrad)"
            strokeWidth="6"
            strokeLinecap="round"
            filter="url(#tightCoreBlur)"
            opacity="0.95"
          />

          {/* Layer 4: Razor-sharp Pure White Light Rim */}
          <path
            d="M -150 420 C 220 30, 1420 20, 1980 450"
            stroke="url(#auroraRazorGrad)"
            strokeWidth="2"
            strokeLinecap="round"
            opacity="1"
          />

          {/* Layer 5: Animated Energy Stream (Traveling pulses along the planetary ring) */}
          <path
            d="M -150 420 C 220 30, 1420 20, 1980 450"
            stroke="url(#auroraStreamGrad)"
            strokeWidth="3.2"
            strokeDasharray="24 160"
            strokeLinecap="round"
            className="animate-stream-flow"
            opacity="0.9"
          />
        </svg>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* 2. TOP NAVIGATION BAR */}
      {/* ------------------------------------------------------------- */}
      <header className="relative z-30 pt-7 px-6 md:px-12 max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand Logo with 3 Vertical Bar Marks */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="flex items-end gap-1 h-5">
            <span className="w-1.5 h-3 rounded-full bg-gradient-to-t from-purple-600 to-indigo-400 group-hover:h-3.5 transition-all" />
            <span className="w-1.5 h-5 rounded-full bg-gradient-to-t from-purple-500 to-fuchsia-400 group-hover:h-5.5 transition-all shadow-[0_0_10px_rgba(168,85,247,0.7)]" />
            <span className="w-1.5 h-3.5 rounded-full bg-gradient-to-t from-indigo-500 to-purple-400 group-hover:h-4 transition-all" />
          </div>
          <span className="font-extrabold text-lg tracking-tight text-white group-hover:text-purple-200 transition-colors">
            AgentWarden
          </span>
        </Link>

        {/* Center Nav Links */}
        <nav className="hidden md:flex items-center gap-8 text-[13px] text-slate-300/90 font-medium">
          <Link href="/" className="text-white hover:text-purple-300 transition-colors">
            Home
          </Link>
          <Link href="#product" className="hover:text-white transition-colors">
            Product
          </Link>
          <Link href="#pricing" className="hover:text-white transition-colors">
            Pricing
          </Link>
          <Link href="#resources" className="hover:text-white transition-colors">
            Resources
          </Link>
        </nav>

        {/* Right Action: Luminous Sign In Pill */}
        <div className="flex items-center gap-3">
          <Link
            href="/signin"
            className="px-6 py-2 rounded-full text-xs font-semibold bg-gradient-to-r from-[#6e44ff] to-[#8b5cf6] text-white shadow-[0_0_24px_rgba(110,68,255,0.65)] hover:shadow-[0_0_32px_rgba(110,68,255,0.9)] hover:scale-[1.03] active:scale-[0.98] transition-all"
          >
            Sign In
          </Link>
        </div>
      </header>

      {/* ------------------------------------------------------------- */}
      {/* 3. HERO SECTION (100% CENTERED - EXACT REFERENCE LAYOUT) */}
      {/* ------------------------------------------------------------- */}
      <section className="relative z-20 pt-16 md:pt-24 pb-12 px-4 max-w-6xl mx-auto flex flex-col items-center text-center">
        {/* Massive Centered Headline */}
        <h1 className="text-4xl sm:text-6xl md:text-7xl font-extrabold tracking-tight text-white uppercase leading-[1.06] max-w-4xl drop-shadow-[0_4px_30px_rgba(0,0,0,0.9)]">
          NEXT-GEN AI <br />
          <span className="text-white">
            FOR AGENT SECURITY
          </span>
        </h1>

        {/* Centered Subtitle */}
        <p className="mt-6 text-sm sm:text-base text-slate-400 max-w-2xl leading-relaxed">
          Stay ahead of risks with AI-powered insights. Our platform continuously monitors third-party
          vendors and autonomous agents, delivers real-time security ratings, and ensures compliance with global standards&mdash;so
          you can focus on growing your business with confidence.
        </p>

        {/* Dual Centered CTA Pill Buttons */}
        <div className="mt-8 flex items-center justify-center gap-4 flex-wrap">
          <Link
            href="/dashboard"
            className="px-7 py-3 rounded-full text-xs sm:text-sm font-semibold bg-gradient-to-r from-[#6e44ff] to-[#8b5cf6] text-white shadow-[0_0_28px_rgba(110,68,255,0.7)] hover:shadow-[0_0_38px_rgba(110,68,255,0.95)] hover:scale-105 active:scale-95 transition-all"
          >
            Get started
          </Link>
          <Link
            href="/dashboard/agent-graph"
            className="px-7 py-3 rounded-full text-xs sm:text-sm font-semibold bg-white/[0.06] text-white border border-white/20 backdrop-blur-md hover:bg-white/[0.12] hover:border-white/35 transition-all"
          >
            Book A Demo
          </Link>
        </div>

        {/* ------------------------------------------------------------- */}
        {/* 4. PRODUCT DASHBOARD SHOWCASE CARD (CENTERED DIRECTLY BELOW) */}
        {/* Matches the "Organization overview" card from reference image */}
        {/* ------------------------------------------------------------- */}
        <div
          id="product"
          className="mt-16 w-full max-w-5xl rounded-2xl bg-[#0c0d16]/95 border border-white/15 shadow-[0_30px_100px_rgba(0,0,0,0.95),0_0_60px_rgba(139,92,246,0.15)] backdrop-blur-2xl overflow-hidden text-left relative"
        >
          {/* Subtle Top Rim Highlight */}
          <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-purple-400 to-transparent opacity-60" />
          {/* Luminous Ambient Halo behind Showcase */}
          <div className="pointer-events-none absolute -inset-1 rounded-2xl bg-gradient-to-b from-purple-500/20 via-transparent to-purple-600/10 blur-xl -z-10" />

          <div className="flex flex-col md:flex-row min-h-[640px]">
            {/* Left Mini-Sidebar inside Dashboard Mockup */}
            <aside className="w-full md:w-56 bg-[#090a10] border-b md:border-b-0 md:border-r border-white/10 p-4 flex flex-col justify-between">
              <div>
                {/* Brand in Mockup */}
                <div className="flex items-center gap-2 px-2 py-1 mb-4">
                  <div className="flex items-end gap-0.5 h-4">
                    <span className="w-1 h-2 rounded-full bg-purple-400" />
                    <span className="w-1 h-4 rounded-full bg-purple-300" />
                    <span className="w-1 h-3 rounded-full bg-purple-400" />
                  </div>
                  <span className="font-bold text-sm text-white tracking-tight">AgentWarden</span>
                </div>

                {/* Search Bar in Mockup */}
                <div className="relative mb-4">
                  <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input
                    type="text"
                    readOnly
                    placeholder="Search..."
                    className="w-full pl-7 pr-2 py-1.5 text-[11px] rounded-lg bg-white/5 border border-white/10 text-slate-300 placeholder-slate-500"
                  />
                </div>

                {/* Nav Links in Mockup */}
                <div className="space-y-1 text-xs">
                  <button
                    type="button"
                    onClick={() => setActiveNav("Home")}
                    className={`w-full flex items-center gap-2.5 px-3 py-1.5 rounded-lg font-medium transition-colors ${
                      activeNav === "Home"
                        ? "bg-[#6e44ff] text-white shadow-[0_0_15px_rgba(110,68,255,0.5)]"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    <Home size={13} /> Home
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveNav("Dashboard")}
                    className={`w-full flex items-center gap-2.5 px-3 py-1.5 rounded-lg font-medium transition-colors ${
                      activeNav === "Dashboard"
                        ? "bg-[#6e44ff] text-white shadow-[0_0_15px_rgba(110,68,255,0.5)]"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    <LayoutDashboard size={13} /> Dashboard
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveNav("Projects")}
                    className={`w-full flex items-center gap-2.5 px-3 py-1.5 rounded-lg font-medium transition-colors ${
                      activeNav === "Projects"
                        ? "bg-[#6e44ff] text-white shadow-[0_0_15px_rgba(110,68,255,0.5)]"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    <FolderKanban size={13} /> Projects
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveNav("Tasks")}
                    className={`w-full flex items-center gap-2.5 px-3 py-1.5 rounded-lg font-medium transition-colors ${
                      activeNav === "Tasks"
                        ? "bg-[#6e44ff] text-white shadow-[0_0_15px_rgba(110,68,255,0.5)]"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    <CheckSquare size={13} /> Tasks
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveNav("Reporting")}
                    className={`w-full flex items-center gap-2.5 px-3 py-1.5 rounded-lg font-medium transition-colors ${
                      activeNav === "Reporting"
                        ? "bg-[#6e44ff] text-white shadow-[0_0_15px_rgba(110,68,255,0.5)]"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    <BarChart2 size={13} /> Reporting
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveNav("Users")}
                    className={`w-full flex items-center gap-2.5 px-3 py-1.5 rounded-lg font-medium transition-colors ${
                      activeNav === "Users"
                        ? "bg-[#6e44ff] text-white shadow-[0_0_15px_rgba(110,68,255,0.5)]"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    <Users size={13} /> Users
                  </button>
                  <div className="pt-2 text-[11px] text-slate-500 uppercase px-3 font-semibold tracking-wider">
                    Settings
                  </div>
                  <button
                    type="button"
                    onClick={() => setActiveNav("Support")}
                    className="w-full flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-slate-400 hover:text-white font-medium"
                  >
                    <HelpCircle size={13} /> Support
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveNav("Settings")}
                    className="w-full flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-slate-400 hover:text-white font-medium"
                  >
                    <Settings size={13} /> Settings
                  </button>
                </div>
              </div>

              {/* Callout Card: New features available! with Video preview */}
              <div className="mt-4 p-3 rounded-xl bg-white/[0.04] border border-white/10 text-[11px]">
                <div className="text-white font-semibold mb-1">New features available!</div>
                <p className="text-slate-400 text-[10px] leading-tight">
                  Check out the new dashboard view. Pages now load faster.
                </p>
                {/* Video Mockup Thumbnail */}
                <div className="mt-2.5 h-16 rounded-lg bg-gradient-to-br from-purple-900/60 to-slate-900 border border-white/10 relative flex items-center justify-center overflow-hidden group cursor-pointer">
                  <div className="w-6 h-6 rounded-full bg-white/20 backdrop-blur-md flex items-center justify-center group-hover:scale-110 transition-transform">
                    <Play size={10} className="fill-white text-white ml-0.5" />
                  </div>
                  <span className="absolute bottom-1 right-1 text-[8px] px-1 bg-black/60 rounded text-slate-300">
                    1:24
                  </span>
                </div>
                <div className="mt-2 text-slate-400 text-[10px] flex items-center justify-between">
                  <span className="hover:text-slate-200 cursor-pointer">Dismiss</span>
                  <span className="text-purple-400 font-medium hover:underline cursor-pointer">
                    What&apos;s new?
                  </span>
                </div>
              </div>

              {/* User Profile Footer */}
              <div className="mt-3 pt-3 border-t border-white/10 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-purple-500 to-indigo-400 flex items-center justify-center text-[10px] font-bold text-white">
                    AV
                  </div>
                  <div className="text-left">
                    <div className="text-[11px] font-semibold text-white leading-none">Alex Vance</div>
                    <div className="text-[9px] text-slate-500 leading-tight">alex@warden.io</div>
                  </div>
                </div>
                <MoreVertical size={13} className="text-slate-500 hover:text-white cursor-pointer" />
              </div>
            </aside>

            {/* Main Content Area inside Dashboard Mockup */}
            <div className="flex-1 p-5 md:p-6 overflow-hidden flex flex-col justify-between">
              {/* Header Bar */}
              <div className="flex items-center justify-between pb-4 border-b border-white/10 flex-wrap gap-3">
                <div>
                  <h3 className="font-bold text-lg text-white tracking-tight">Organization overview</h3>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <div className="p-1.5 rounded-lg bg-white/5 border border-white/10 text-slate-300 hover:text-white cursor-pointer">
                    <Search size={13} />
                  </div>
                  <button
                    type="button"
                    className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-slate-300 hover:text-white flex items-center gap-1.5 font-medium transition-colors"
                  >
                    <Filter size={12} /> Filters
                  </button>
                  <button
                    type="button"
                    className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-slate-300 hover:text-white flex items-center gap-1.5 font-medium transition-colors"
                  >
                    <SlidersHorizontal size={12} /> Customize
                  </button>
                  <button
                    type="button"
                    className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-slate-300 hover:text-white flex items-center gap-1.5 font-medium transition-colors"
                  >
                    <Download size={12} /> Export
                  </button>
                </div>
              </div>

              {/* Row 1: Donut Breakdown + Multi-wave Line Graph */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 py-4">
                {/* Donut Card (5 cols) */}
                <div className="lg:col-span-5 p-4 rounded-xl bg-[#0e101a] border border-white/10 flex flex-col justify-between">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-white">Vendor breakdown</span>
                  </div>
                  {/* Visual SVG Donut chart with legend */}
                  <div className="my-3 flex items-center justify-around gap-2">
                    <div className="relative w-28 h-28 flex items-center justify-center">
                      <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
                        {/* Segment 1: Purple 38% */}
                        <circle
                          cx="50"
                          cy="50"
                          r="38"
                          fill="none"
                          stroke="#8b5cf6"
                          strokeWidth="12"
                          strokeDasharray="90 240"
                          strokeDashoffset="0"
                        />
                        {/* Segment 2: Cyan 24% */}
                        <circle
                          cx="50"
                          cy="50"
                          r="38"
                          fill="none"
                          stroke="#06b6d4"
                          strokeWidth="12"
                          strokeDasharray="57 240"
                          strokeDashoffset="-92"
                        />
                        {/* Segment 3: Indigo 18% */}
                        <circle
                          cx="50"
                          cy="50"
                          r="38"
                          fill="none"
                          stroke="#6366f1"
                          strokeWidth="12"
                          strokeDasharray="43 240"
                          strokeDashoffset="-151"
                        />
                        {/* Segment 4: Fuchsia 12% */}
                        <circle
                          cx="50"
                          cy="50"
                          r="38"
                          fill="none"
                          stroke="#d946ef"
                          strokeWidth="12"
                          strokeDasharray="29 240"
                          strokeDashoffset="-196"
                        />
                        {/* Segment 5: Slate 8% */}
                        <circle
                          cx="50"
                          cy="50"
                          r="38"
                          fill="none"
                          stroke="#475569"
                          strokeWidth="12"
                          strokeDasharray="19 240"
                          strokeDashoffset="-227"
                        />
                      </svg>
                      {/* Donut Center */}
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className="w-12 h-12 rounded-full bg-[#0e101a] flex items-center justify-center">
                          <span className="text-[10px] font-bold text-slate-300">100%</span>
                        </div>
                      </div>
                    </div>

                    {/* Legend */}
                    <div className="space-y-1 text-[10px]">
                      <div className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-[#8b5cf6]" />
                        <span className="text-slate-300">20-100</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-[#06b6d4]" />
                        <span className="text-slate-300">81-100</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-[#6366f1]" />
                        <span className="text-slate-300">61-80</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-[#d946ef]" />
                        <span className="text-slate-300">41-60</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-[#475569]" />
                        <span className="text-slate-300">21-40</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-[#1e293b]" />
                        <span className="text-slate-400">0-20</span>
                      </div>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="w-full mt-1 py-1 rounded-lg border border-white/10 hover:border-white/20 text-center text-[10px] text-slate-300 hover:text-white transition-colors"
                  >
                    View full report
                  </button>
                </div>

                {/* Line Chart Card (7 cols) */}
                <div className="lg:col-span-7 p-4 rounded-xl bg-[#0e101a] border border-white/10 flex flex-col justify-between">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-xs font-semibold text-white">Average vendor rating</span>
                      <p className="text-[10px] text-slate-400">Track how your rating compares to your industry average.</p>
                    </div>
                    <div className="flex items-center gap-3 text-[10px]">
                      <span className="flex items-center gap-1 text-purple-300">
                        <span className="w-2 h-2 rounded-full bg-purple-500" /> Your rating
                      </span>
                      <span className="flex items-center gap-1 text-slate-400">
                        <span className="w-2 h-2 rounded-full bg-slate-500" /> Industry Average
                      </span>
                    </div>
                  </div>

                  {/* Multi-Wave SVG Neon Line Chart */}
                  <div className="my-2 h-28 w-full flex">
                    {/* Y-axis values */}
                    <div className="flex flex-col justify-between text-[8px] text-slate-500 pr-2 py-1 font-mono">
                      <span>100</span>
                      <span>80</span>
                      <span>60</span>
                      <span>40</span>
                      <span>20</span>
                      <span>0</span>
                    </div>

                    <div className="flex-1 relative">
                      <svg viewBox="0 0 360 80" className="w-full h-full" fill="none">
                        <defs>
                          <linearGradient id="purpleAreaWave" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.35" />
                            <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.0" />
                          </linearGradient>
                        </defs>
                        {/* Grid lines */}
                        <line x1="0" y1="16" x2="360" y2="16" stroke="rgba(255,255,255,0.05)" />
                        <line x1="0" y1="32" x2="360" y2="32" stroke="rgba(255,255,255,0.05)" />
                        <line x1="0" y1="48" x2="360" y2="48" stroke="rgba(255,255,255,0.05)" />
                        <line x1="0" y1="64" x2="360" y2="64" stroke="rgba(255,255,255,0.05)" />

                        {/* Area gradient under rating line */}
                        <path
                          d="M 0,55 Q 35,45 70,38 T 140,30 T 210,18 T 280,12 T 360,8 L 360,80 L 0,80 Z"
                          fill="url(#purpleAreaWave)"
                        />
                        {/* Glowing Purple "Your rating" spline */}
                        <path
                          d="M 0,55 Q 35,45 70,38 T 140,30 T 210,18 T 280,12 T 360,8"
                          stroke="#a855f7"
                          strokeWidth="2.2"
                          strokeLinecap="round"
                        />
                        {/* Pulse dot on line */}
                        <circle cx="210" cy="18" r="3" fill="#c084fc" />
                        <circle cx="210" cy="18" r="6" fill="#c084fc" fillOpacity="0.3" />

                        {/* Dotted Industry Average spline */}
                        <path
                          d="M 0,65 Q 45,62 90,58 T 180,54 T 270,50 T 360,46"
                          stroke="#64748b"
                          strokeWidth="1.5"
                          strokeDasharray="4 4"
                        />
                      </svg>
                    </div>
                  </div>

                  {/* X-axis months */}
                  <div className="flex items-center justify-between text-[9px] text-slate-500 font-mono pl-6">
                    <span>Jan</span>
                    <span>Feb</span>
                    <span>Mar</span>
                    <span>Apr</span>
                    <span>May</span>
                    <span>Jun</span>
                    <span>Jul</span>
                    <span>Aug</span>
                    <span>Sep</span>
                    <span>Oct</span>
                    <span>Nov</span>
                    <span>Dec</span>
                  </div>
                </div>
              </div>

              {/* Row 2: Vendor Movements Table */}
              <div className="pt-2">
                <div className="flex items-center justify-between pb-2">
                  <div>
                    <h4 className="text-xs font-semibold text-white">Vendor movements</h4>
                    <p className="text-[10px] text-slate-400">Keep track of vendors and their security ratings.</p>
                  </div>
                  <div className="relative">
                    <Search size={11} className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-500" />
                    <input
                      type="text"
                      placeholder="Search..."
                      value={searchFilter}
                      onChange={(e) => setSearchFilter(e.target.value)}
                      className="pl-6 pr-2 py-1 text-[10px] rounded-md bg-white/5 border border-white/10 text-slate-200 placeholder-slate-500"
                    />
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="text-slate-400 text-[10px] border-b border-white/10 uppercase font-mono">
                        <th className="py-2 w-6">
                          <input type="checkbox" className="rounded bg-white/10 border-white/20" />
                        </th>
                        <th className="py-2">Vendor</th>
                        <th className="py-2">Rating</th>
                        <th className="py-2">Last assessed</th>
                        <th className="py-2">Categories</th>
                        <th className="py-2 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 text-[11px]">
                      {filteredRows.map((row) => (
                        <tr key={row.id} className="hover:bg-white/[0.02] transition-colors">
                          <td className="py-2.5">
                            <input type="checkbox" className="rounded bg-white/10 border-white/20" />
                          </td>
                          <td className="py-2.5 font-medium text-white flex items-center gap-2">
                            <div className={`w-5 h-5 rounded flex items-center justify-center font-bold text-[10px] border ${row.initialBg}`}>
                              {row.initial}
                            </div>
                            <div>
                              <div className="leading-none">{row.name}</div>
                              <div className="text-[9px] text-slate-500 leading-tight">{row.domain}</div>
                            </div>
                          </td>
                          <td className="py-2.5 font-mono">
                            <span className="font-semibold text-white">{row.rating}</span>
                            <span
                              className={`ml-1.5 text-[9px] px-1 py-0.2 rounded font-sans ${
                                row.changePositive
                                  ? "bg-emerald-500/15 text-emerald-400"
                                  : "bg-rose-500/15 text-rose-400"
                              }`}
                            >
                              {row.ratingChange}
                            </span>
                          </td>
                          <td className="py-2.5 text-slate-400 text-[10px] font-mono">{row.lastAssessed}</td>
                          <td className="py-2.5">
                            <div className="flex items-center gap-1 flex-wrap">
                              {row.badges.map((b, idx) => (
                                <span
                                  key={idx}
                                  className={`px-1.5 py-0.5 rounded text-[9px] border font-medium ${b.style}`}
                                >
                                  {b.label}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td className="py-2.5 text-right">
                            <div className="inline-flex items-center gap-2 text-slate-500">
                              <Pencil size={11} className="hover:text-white cursor-pointer" />
                              <Trash2 size={11} className="hover:text-rose-400 cursor-pointer" />
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ------------------------------------------------------------- */}
        {/* 5. SOCIAL PROOF LOGO BAR */}
        {/* ------------------------------------------------------------- */}
        <div className="mt-20 w-full max-w-4xl flex flex-col items-center">
          <p className="text-xs uppercase tracking-wider text-slate-400 font-medium mb-8">
            More than 200+ Companies trusted us worldwide
          </p>
          <div className="flex items-center justify-between w-full opacity-65 grayscale hover:grayscale-0 transition-all gap-8 flex-wrap justify-center">
            {/* Apple */}
            <div className="flex items-center gap-1.5 font-bold text-sm tracking-tight text-slate-200">
              <svg className="w-5 h-5 fill-current" viewBox="0 0 170 170">
                <path d="M150.37 130.25c-2.45 5.66-5.35 10.87-8.71 15.66-4.58 6.53-8.33 11.05-11.22 13.56-4.48 4.12-9.28 6.23-14.42 6.35-3.69 0-8.14-1.05-13.32-3.18-5.19-2.12-9.97-3.17-14.34-3.17-4.58 0-9.49 1.05-14.75 3.17-5.26 2.13-9.5 3.24-12.74 3.35-4.35.13-9.16-1.9-14.42-6.08-3.69-3.04-7.67-7.81-11.96-14.34-6.41-9.79-11.35-20.84-14.82-33.15-3.47-12.31-5.2-23.77-5.2-34.38 0-14.58 3.58-26.68 10.74-36.3 7.16-9.62 16.39-14.54 27.69-14.76 4.78 0 10.23 1.25 16.34 3.76 6.11 2.51 10.05 3.84 11.83 3.98 1.45 0 5.46-1.39 12.03-4.17 6.57-2.77 12.18-4.04 16.83-3.8 12.63.87 22.84 5.76 30.63 14.67-11.1 6.75-16.54 15.99-16.32 27.72.22 9.14 3.79 16.92 10.72 23.34 6.93 6.42 15.22 10.12 24.87 11.1-2.17 6.53-4.8 13.04-7.89 19.53zM119.22 31.84c0-7.39 2.65-14.34 7.95-20.85 5.3-6.51 11.85-10.49 19.65-11.94.22 1.3.33 2.45.33 3.45 0 7.39-2.76 14.49-8.28 21.31-5.52 6.82-12.09 10.7-19.71 11.64-.11-1.09-.16-2.19-.16-3.32z" />
              </svg>
              <span>Apple</span>
            </div>

            {/* Google */}
            <div className="font-bold text-base tracking-tight text-slate-200">
              Google
            </div>

            {/* Amazon */}
            <div className="font-bold text-base tracking-tight text-slate-200 flex items-center gap-0.5">
              <span>amazon</span>
            </div>

            {/* Leafe */}
            <div className="font-bold text-base tracking-tight text-slate-200 flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
              <span>Leafe</span>
            </div>

            {/* Mindfulness */}
            <div className="font-bold text-base tracking-tight text-slate-200 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-purple-400" />
              <span>Mindfulness</span>
            </div>

            {/* Microsoft */}
            <div className="flex items-center gap-1.5 font-bold text-base tracking-tight text-slate-200">
              <div className="grid grid-cols-2 gap-0.5 w-3.5 h-3.5">
                <span className="bg-red-400 rounded-[1px]" />
                <span className="bg-emerald-400 rounded-[1px]" />
                <span className="bg-blue-400 rounded-[1px]" />
                <span className="bg-amber-400 rounded-[1px]" />
              </div>
              <span>Microsoft</span>
            </div>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------- */}
      {/* 6. WORKFLOW AUTOMATION SECTION ("How to setup") */}
      {/* Matches Section 4 from reference image */}
      {/* ------------------------------------------------------------- */}
      <section id="workflow" className="relative z-20 py-24 px-6 md:px-12 max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-12">
        {/* Left Column: Headline & Action */}
        <div className="flex-1 text-left max-w-lg">
          <div className="inline-flex items-center gap-1 px-3 py-1 rounded-full border border-purple-500/30 bg-purple-950/20 text-[11px] font-semibold text-purple-300 mb-6 shadow-[0_0_12px_rgba(168,85,247,0.2)]">
            How to setup &rarr;
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-white leading-tight">
            It takes less than <br />
            a minute to create <br />
            automations
          </h2>
          <p className="mt-5 text-sm sm:text-base text-slate-400 leading-relaxed">
            See how you can setup an account within a few seconds and start your automation process seamlessly.
          </p>
          <div className="mt-8">
            <Link
              href="/dashboard"
              className="px-7 py-3 rounded-full text-xs sm:text-sm font-semibold bg-gradient-to-r from-[#6e44ff] to-[#8b5cf6] text-white shadow-[0_0_24px_rgba(110,68,255,0.6)] hover:shadow-[0_0_32px_rgba(110,68,255,0.85)] hover:scale-105 transition-all inline-block"
            >
              Get started
            </Link>
          </div>
        </div>

        {/* Right Column: Sleek Automation Diagram Mockup */}
        <div className="flex-1 w-full max-w-lg p-7 rounded-3xl bg-[#0c0d16]/90 border border-white/10 shadow-2xl relative">
          <div className="flex flex-col items-center gap-8">
            {/* Top Node: Create Automation */}
            <div className="flex flex-col items-center">
              <span className="text-[10px] uppercase font-bold text-slate-400 mb-1">Trigger</span>
              <div className="px-5 py-3 rounded-2xl bg-[#141624] border border-purple-500/40 text-white text-xs font-semibold flex items-center gap-2.5 shadow-[0_0_25px_rgba(168,85,247,0.3)]">
                <div className="w-5 h-5 rounded-md bg-purple-600/40 flex items-center justify-center text-purple-300">
                  <Sparkles size={12} />
                </div>
                <span>Create Automation</span>
              </div>
            </div>

            {/* Curved Connecting Wires SVG */}
            <div className="relative w-full max-w-md h-12 flex justify-center">
              <svg viewBox="0 0 360 48" className="w-full h-full" fill="none">
                <path
                  d="M 180,0 C 180,24 80,24 80,48"
                  stroke="#a855f7"
                  strokeWidth="2"
                  filter="drop-shadow(0 0 6px #a855f7)"
                />
                <path
                  d="M 180,0 C 180,24 280,24 280,48"
                  stroke="#a855f7"
                  strokeWidth="2"
                  filter="drop-shadow(0 0 6px #a855f7)"
                />
              </svg>
            </div>

            {/* Two Lower Action Cards */}
            <div className="grid grid-cols-2 gap-4 w-full">
              {/* Left Branch */}
              <div className="flex flex-col items-center">
                <span className="text-[9px] uppercase font-bold text-indigo-400 mb-1">Action</span>
                <div className="w-full p-3.5 rounded-2xl bg-[#131522] border border-white/10 hover:border-purple-500/40 transition-colors text-left">
                  <div className="w-6 h-6 rounded-lg bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-300 mb-2">
                    <Mail size={12} />
                  </div>
                  <div className="text-xs font-bold text-white">Send in Email</div>
                  <div className="text-[10px] text-slate-400">to Customers</div>
                </div>
              </div>

              {/* Right Branch */}
              <div className="flex flex-col items-center">
                <span className="text-[9px] uppercase font-bold text-purple-400 mb-1">Condition</span>
                <div className="w-full p-3.5 rounded-2xl bg-[#131522] border border-white/10 hover:border-purple-500/40 transition-colors text-left">
                  <div className="w-6 h-6 rounded-lg bg-purple-500/20 border border-purple-500/30 flex items-center justify-center text-purple-300 mb-2">
                    <Gift size={12} />
                  </div>
                  <div className="text-xs font-bold text-white">Give them</div>
                  <div className="text-[10px] text-slate-400">Loyalty Points</div>
                </div>
              </div>
            </div>

            {/* Bottom Status Pill */}
            <div className="px-4 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-[10px] font-semibold text-emerald-400 flex items-center gap-1.5 shadow-[0_0_15px_rgba(16,185,129,0.2)]">
              <CheckCircle2 size={11} /> Complete &bull; 100% Automated
            </div>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------- */}
      {/* 7. POWER FEATURES (2x2 BENTO GRID - EXACT REFERENCE MATCH) */}
      {/* Matches Section 5 from reference image */}
      {/* ------------------------------------------------------------- */}
      <section id="features" className="relative z-20 py-24 px-4 max-w-6xl mx-auto flex flex-col items-center text-center">
        {/* Eyebrow Pill */}
        <div className="inline-flex items-center gap-1 px-3 py-1 rounded-full border border-purple-500/30 bg-purple-950/20 text-[11px] font-semibold text-purple-300 mb-4 shadow-[0_0_12px_rgba(168,85,247,0.2)]">
          Features
        </div>
        <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-white max-w-2xl leading-tight">
          Power Features to Supercharge <br />
          Your Automation
        </h2>
        <p className="mt-4 text-sm sm:text-base text-slate-400 max-w-xl">
          AgentWarden is packed with smart, scalable features designed to simplify workflows, boost efficiency
        </p>

        {/* 2x2 Bento Grid */}
        <div className="mt-14 grid grid-cols-1 md:grid-cols-2 gap-6 w-full text-left">
          {/* Card 1: Scale Without the Scream */}
          <div className="p-7 rounded-3xl bg-[#0c0d16]/90 border border-white/10 shadow-2xl flex flex-col justify-between hover:border-purple-500/30 transition-all group">
            <div>
              <h3 className="text-xl font-bold text-white tracking-tight">Scale Without the Scream</h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Whether you&apos;ve got 10 users or 10,000, Flowmate grows with you&mdash;minus the tech headaches.
              </p>
            </div>

            {/* Widget: Semi-circle Gauge Chart with Profit Breakdown */}
            <div className="mt-8 p-5 rounded-2xl bg-[#11121d] border border-white/5">
              <div className="flex items-center justify-between pb-3">
                <span className="text-xs font-semibold text-white">Profit Breakdown</span>
              </div>
              <div className="flex items-center gap-6">
                <div className="relative w-32 h-20 flex flex-col items-center justify-end">
                  <svg viewBox="0 0 100 50" className="w-full h-full" fill="none">
                    <path
                      d="M 10 50 A 40 40 0 0 1 90 50"
                      stroke="rgba(255,255,255,0.1)"
                      strokeWidth="10"
                      strokeLinecap="round"
                    />
                    <path
                      d="M 10 50 A 40 40 0 0 1 82 25"
                      stroke="#a855f7"
                      strokeWidth="10"
                      strokeLinecap="round"
                      filter="drop-shadow(0 0 6px #a855f7)"
                    />
                  </svg>
                  <span className="text-sm font-bold text-white mt-1">$15,987</span>
                  <span className="text-[9px] text-slate-400 uppercase">Total Profit</span>
                </div>
                <div className="flex-1 space-y-1.5 text-[11px]">
                  <div className="flex justify-between text-slate-300">
                    <span className="flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-purple-400" />
                      Product A (54%)
                    </span>
                    <strong className="text-white">$7,900</strong>
                  </div>
                  <div className="flex justify-between text-slate-300">
                    <span className="flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                      Product B (32%)
                    </span>
                    <strong className="text-white">$5,900</strong>
                  </div>
                  <div className="flex justify-between text-slate-300">
                    <span className="flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
                      Product C (14%)
                    </span>
                    <strong className="text-white">$2,123</strong>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Card 2: Drag, Drop, Automate */}
          <div className="p-7 rounded-3xl bg-[#0c0d16]/90 border border-white/10 shadow-2xl flex flex-col justify-between hover:border-purple-500/30 transition-all group">
            <div>
              <h3 className="text-xl font-bold text-white tracking-tight">Drag, Drop, Automate</h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                No code? No problem. Build powerful workflows with an interface so smooth, it&apos;s almost fun.
              </p>
            </div>

            {/* Widget: Draggable workflow pill with realistic cursor */}
            <div className="mt-8 p-6 rounded-2xl bg-[#11121d] border border-white/5 relative min-h-[140px] flex flex-col items-center justify-center gap-3">
              {/* Floating Active Drag Card */}
              <div className="px-4 py-2.5 rounded-xl bg-[#6e44ff]/40 border border-[#8b5cf6]/60 text-white text-xs font-semibold flex items-center gap-2.5 shadow-[0_10px_25px_rgba(110,68,255,0.45)] transform -rotate-1 scale-105">
                <div className="w-4 h-4 rounded bg-purple-500 flex items-center justify-center text-[10px]">M</div>
                <span>Update newsletter</span>
                <Lock size={11} className="text-slate-300 ml-1" />
              </div>

              {/* Realistic White Mouse Pointer Cursor */}
              <div className="absolute right-16 bottom-7 text-white flex items-center gap-1 pointer-events-none drop-shadow-[0_0_8px_rgba(255,255,255,0.8)] z-10">
                <MousePointer size={18} className="fill-white" />
              </div>

              {/* Drop Target Outline */}
              <div className="w-full max-w-xs py-2 px-3 rounded-lg border border-dashed border-white/15 text-[11px] text-slate-500 flex items-center justify-between">
                <span>Update your email</span>
                <span className="text-[10px] text-slate-600">Drop here</span>
              </div>
            </div>
          </div>

          {/* Card 3: Smart Enough to Chill */}
          <div className="p-7 rounded-3xl bg-[#0c0d16]/90 border border-white/10 shadow-2xl flex flex-col justify-between hover:border-purple-500/30 transition-all group">
            <div>
              <h3 className="text-xl font-bold text-white tracking-tight">Smart Enough to Chill</h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Our AI does the thinking, so you don&apos;t have to. Optimize, predict, and adapt on autopilot.
              </p>
            </div>

            {/* Widget: Autopilot AI & 99% Stat */}
            <div className="mt-8 p-5 rounded-2xl bg-[#11121d] border border-white/5 flex items-center justify-between gap-4">
              <div>
                <span className="px-2.5 py-1 rounded-full bg-purple-600/30 border border-purple-500/40 text-[10px] font-bold text-purple-200">
                  Autopilot AI
                </span>
                <div className="mt-3 flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-[11px] font-bold text-purple-300">
                    F
                  </div>
                  <div className="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-[11px] font-bold text-blue-300">
                    G
                  </div>
                  <div className="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-[11px] font-bold text-cyan-300">
                    S
                  </div>
                </div>
              </div>

              <div className="text-right">
                <div className="text-4xl font-extrabold text-white tracking-tight drop-shadow-[0_0_20px_rgba(168,85,247,0.5)]">
                  99%
                </div>
                <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
                  Accuracy
                </div>
              </div>
            </div>
          </div>

          {/* Card 4: Plug It All In */}
          <div className="p-7 rounded-3xl bg-[#0c0d16]/90 border border-white/10 shadow-2xl flex flex-col justify-between hover:border-purple-500/30 transition-all group">
            <div>
              <h3 className="text-xl font-bold text-white tracking-tight">Plug It All In</h3>
              <p className="mt-2 text-xs text-slate-400 leading-relaxed">
                Integrates with your favorite tools like it was born to. Zapier, Slack, Google&mdash;you name it.
              </p>
            </div>

            {/* Widget: Central Hub with 6 Connected Bezier Tools */}
            <div className="mt-8 p-5 rounded-2xl bg-[#11121d] border border-white/5 relative min-h-[140px] flex items-center justify-between">
              {/* Left 3 Tool Icons */}
              <div className="space-y-2 z-10">
                <div className="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-[11px] font-bold text-purple-300">
                  F
                </div>
                <div className="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-[11px] font-bold text-indigo-300">
                  D
                </div>
                <div className="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-[11px] font-bold text-blue-300">
                  B
                </div>
              </div>

              {/* Connecting SVG Bezier Lines */}
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <svg viewBox="0 0 320 120" className="w-full h-full" fill="none">
                  {/* Left branch curves */}
                  <path d="M 40,25 C 100,25 120,60 160,60" stroke="#8b5cf6" strokeWidth="1.5" strokeOpacity="0.6" />
                  <path d="M 40,60 C 100,60 120,60 160,60" stroke="#8b5cf6" strokeWidth="1.5" strokeOpacity="0.8" />
                  <path d="M 40,95 C 100,95 120,60 160,60" stroke="#8b5cf6" strokeWidth="1.5" strokeOpacity="0.6" />
                  {/* Right branch curves */}
                  <path d="M 280,25 C 220,25 200,60 160,60" stroke="#8b5cf6" strokeWidth="1.5" strokeOpacity="0.6" />
                  <path d="M 280,60 C 220,60 200,60 160,60" stroke="#8b5cf6" strokeWidth="1.5" strokeOpacity="0.8" />
                  <path d="M 280,95 C 220,95 200,60 160,60" stroke="#8b5cf6" strokeWidth="1.5" strokeOpacity="0.6" />
                </svg>
              </div>

              {/* Center Glowing Hub */}
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-purple-600 to-indigo-500 border border-purple-400 p-0.5 shadow-[0_0_24px_rgba(168,85,247,0.7)] z-10 flex items-center justify-center">
                <div className="flex items-end gap-0.5 h-4">
                  <span className="w-1 h-2 rounded-full bg-white" />
                  <span className="w-1 h-4 rounded-full bg-white" />
                  <span className="w-1 h-3 rounded-full bg-white" />
                </div>
              </div>

              {/* Right 3 Tool Icons */}
              <div className="space-y-2 z-10">
                <div className="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-[11px] font-bold text-amber-300">
                  G
                </div>
                <div className="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-[11px] font-bold text-orange-300">
                  Z
                </div>
                <div className="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-[11px] font-bold text-emerald-300">
                  S
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------------------- */}
      {/* 8. BOTTOM CELESTIAL PLANETARY CRESCENT & CTA */}
      {/* Matches bottom fold of reference image */}
      {/* ------------------------------------------------------------- */}
      <section className="relative z-20 pt-36 pb-24 px-4 overflow-hidden flex flex-col items-center text-center">
        {/* Giant Rising Planetary Crescent Arch at Bottom */}
        <div className="pointer-events-none absolute bottom-[-180px] left-1/2 -translate-x-1/2 w-full max-w-[1600px] h-[640px] overflow-hidden z-0">
          {/* Radial Light Burst rising upwards from below */}
          <div
            className="absolute inset-0"
            style={{
              background:
                "radial-gradient(ellipse 90% 65% at 50% 100%, rgba(168, 85, 247, 0.48), transparent 72%), radial-gradient(ellipse 65% 45% at 50% 100%, rgba(99, 102, 241, 0.38), transparent 75%)"
            }}
          />

          {/* Multi-layered Glowing Planetary Rim Arc */}
          <svg viewBox="0 0 1600 550" fill="none" className="absolute inset-0 w-full h-full animate-beam-shimmer">
            <defs>
              <linearGradient id="bottomPlanetArcGrad" x1="100" y1="500" x2="1500" y2="500" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.4" />
                <stop offset="25%" stopColor="#c084fc" stopOpacity="0.95" />
                <stop offset="50%" stopColor="#e879f9" stopOpacity="1" />
                <stop offset="75%" stopColor="#a855f7" stopOpacity="0.95" />
                <stop offset="100%" stopColor="#6366f1" stopOpacity="0.3" />
              </linearGradient>

              <filter id="bottomHeavyBlur" x="-30%" y="-30%" width="160%" height="160%">
                <feGaussianBlur stdDeviation="35" />
              </filter>
              <filter id="bottomMidBlur" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="12" />
              </filter>
            </defs>

            {/* Layer 1: Atmospheric Outer Bloom */}
            <path
              d="M 60 520 C 380 180, 1220 180, 1540 520"
              stroke="url(#bottomPlanetArcGrad)"
              strokeWidth="80"
              strokeLinecap="round"
              filter="url(#bottomHeavyBlur)"
              opacity="0.38"
            />

            {/* Layer 2: Mid Plasma Glow */}
            <path
              d="M 60 520 C 380 180, 1220 180, 1540 520"
              stroke="url(#bottomPlanetArcGrad)"
              strokeWidth="24"
              strokeLinecap="round"
              filter="url(#bottomMidBlur)"
              opacity="0.8"
            />

            {/* Layer 3: Core Luminous Beam */}
            <path
              d="M 60 520 C 380 180, 1220 180, 1540 520"
              stroke="#f5d0fe"
              strokeWidth="8"
              strokeLinecap="round"
              opacity="0.95"
            />

            {/* Layer 4: Razor Pure White Rim */}
            <path
              d="M 60 520 C 380 180, 1220 180, 1540 520"
              stroke="#ffffff"
              strokeWidth="2.2"
              strokeLinecap="round"
              opacity="1"
            />

            {/* Layer 5: Animated Energy Stream */}
            <path
              d="M 60 520 C 380 180, 1220 180, 1540 520"
              stroke="url(#bottomPlanetArcGrad)"
              strokeWidth="3"
              strokeDasharray="22 140"
              strokeLinecap="round"
              className="animate-stream-flow"
              opacity="0.9"
            />
          </svg>
        </div>

        {/* Centered CTA Content */}
        <div className="relative z-10 max-w-3xl flex flex-col items-center">
          <div className="inline-flex items-center gap-1 px-3 py-1 rounded-full border border-purple-500/30 bg-purple-950/20 text-[11px] font-semibold text-purple-300 mb-4 shadow-[0_0_12px_rgba(168,85,247,0.2)]">
            Start your journey
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-white max-w-xl leading-tight">
            Ready to dive in? <br />
            Start your journey today
          </h2>
          <p className="mt-4 text-sm sm:text-base text-slate-400 max-w-md leading-relaxed">
            Schedule posts, launch cold DMs, and track performance with seamless automation.
          </p>
          <Link
            href="/dashboard"
            className="mt-8 px-8 py-3.5 rounded-full text-xs sm:text-sm font-semibold bg-gradient-to-r from-[#6e44ff] to-[#8b5cf6] text-white shadow-[0_0_32px_rgba(110,68,255,0.75)] hover:shadow-[0_0_42px_rgba(110,68,255,0.95)] hover:scale-105 active:scale-95 transition-all"
          >
            Get started
          </Link>
        </div>
      </section>

      {/* ------------------------------------------------------------- */}
      {/* 9. LUXURY MINIMALIST FOOTER */}
      {/* ------------------------------------------------------------- */}
      <footer className="relative z-20 border-t border-white/10 py-10 px-6 md:px-12 max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
        <div className="flex items-center gap-2">
          <span className="font-bold text-white">AgentWarden</span>
          <span>&bull;</span>
          <span>Next-Gen Autonomous Agent Security</span>
        </div>
        <div className="flex items-center gap-6">
          <Link href="/dashboard" className="hover:text-white transition-colors">
            Command Center
          </Link>
          <Link href="/dashboard/agent-graph" className="hover:text-white transition-colors">
            Agent Graph
          </Link>
          <Link href="/dashboard/enforcement" className="hover:text-white transition-colors">
            Enforcement
          </Link>
          <Link href="/dashboard/audit" className="hover:text-white transition-colors">
            Audit
          </Link>
        </div>
        <div>&copy; {new Date().getFullYear()} AgentWarden Inc. All rights reserved.</div>
      </footer>
    </div>
  );
}
