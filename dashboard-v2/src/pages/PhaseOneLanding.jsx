import {
  Activity,
  Anchor,
  ArrowRight,
  BarChart3,
  CalendarClock,
  Database,
  LayoutDashboard,
  Map,
  RadioTower,
  Ship,
  Waves,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import BrandMark from "../components/BrandMark";
import { useData } from "../context/DataContext";

function formatNumber(value) {
  return new Intl.NumberFormat("en").format(Number(value) || 0);
}

function formatPercent(value) {
  return `${Number(value) || 0}%`;
}

function parseGeneratedAt(value) {
  if (!value) return null;
  const iso = value.includes("UTC") ? value.replace(" UTC", "Z").replace(" ", "T") : value;
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null : date;
}

function snapshotAge(value) {
  const generated = parseGeneratedAt(value);
  if (!generated) return "Timestamp unavailable";

  const ageHours = Math.max(0, (Date.now() - generated.getTime()) / 3.6e6);
  if (ageHours < 1) return `${Math.round(ageHours * 60)} min old`;
  if (ageHours < 24) return `${Math.round(ageHours)} h old`;
  return `${Math.round(ageHours / 24)} d old`;
}

function pressureLabel(metrics, hasSnapshot = true) {
  if (!hasSnapshot) return "Covered";
  if ((metrics?.waiting ?? 0) >= 10) return "High pressure";
  if ((metrics?.waiting ?? 0) > 0 || (metrics?.congestionPct ?? 0) >= 50) return "Watch";
  if ((metrics?.tracked ?? 0) > 0) return "Traffic visible";
  return "Clear";
}

function sourceIcon(name) {
  if (name.includes("AIS")) return "satellite_alt";
  if (name.includes("Weather")) return "water";
  return "database";
}

function MetricCard({ label, value, detail, Icon }) {
  return (
    <div className="border border-outline-variant/50 bg-surface-container p-5">
      <div className="flex items-center justify-between gap-3">
        <span className="text-[11px] font-black uppercase tracking-[0.08em] text-on-surface-variant">
          {label}
        </span>
        {Icon ? <Icon className="text-primary" size={20} /> : null}
      </div>
      <div className="mt-4 font-mono text-4xl font-black leading-none text-on-surface">
        {value}
      </div>
      <div className="mt-3 text-sm leading-6 text-on-surface-variant">{detail}</div>
    </div>
  );
}

function ModuleLink({ to, icon, title, detail, onClick }) {
  return (
    <Link
      to={to}
      onClick={onClick}
      className="group flex min-h-28 items-start justify-between gap-4 border border-outline-variant/50 bg-surface p-4 transition-colors hover:border-primary/60 hover:bg-surface-container"
    >
      <div>
        <span className="material-symbols-outlined text-[24px] text-primary">{icon}</span>
        <h3 className="mt-3 font-black text-on-surface">{title}</h3>
        <p className="mt-2 text-sm leading-6 text-on-surface-variant">{detail}</p>
      </div>
      <ArrowRight className="mt-1 shrink-0 text-on-surface-variant group-hover:text-primary" size={18} />
    </Link>
  );
}

function PortSelector({ ports, selectedCode, onSelect }) {
  return (
    <div className="grid grid-cols-3 border border-outline-variant/50 bg-surface max-lg:grid-cols-2 max-sm:grid-cols-1">
      {ports.map((portInfo) => {
        const metrics = portInfo.metrics ?? {};
        const isSelected = portInfo.code === selectedCode;

        return (
          <button
            key={portInfo.code}
            type="button"
            onClick={() => onSelect(portInfo.code)}
            className={`min-h-28 border-b border-r border-outline-variant/30 p-4 text-left transition-colors ${
              isSelected
                ? "bg-primary-container text-on-primary-container"
                : "bg-surface text-on-surface hover:bg-surface-container"
            }`}
          >
            <div className="flex items-center justify-between gap-3">
              <span className="font-mono text-sm font-black">{portInfo.code}</span>
              <span className="font-mono text-xs uppercase">
                {pressureLabel(metrics, portInfo.hasSnapshot)}
              </span>
            </div>
            <div className="mt-3 font-black">{portInfo.name}</div>
            <div className="mt-2 text-xs opacity-75">
              {formatNumber(metrics.tracked)} tracked · {formatNumber(metrics.waiting)} waiting
            </div>
          </button>
        );
      })}
    </div>
  );
}

function VesselList({ vessels, onNavigate }) {
  if (!vessels.length) {
    return (
      <div className="border border-outline-variant/50 bg-surface p-6">
        <div className="flex items-center gap-3">
          <Ship className="text-primary" size={21} />
          <h3 className="font-black text-on-surface">Vessel traffic</h3>
        </div>
        <p className="mt-3 text-sm leading-6 text-on-surface-variant">
          No vessels are surfaced in the selected port snapshot.
        </p>
        <Link
          to="/map"
          onClick={onNavigate}
          className="mt-5 inline-flex min-h-10 items-center justify-center gap-2 border border-primary/60 px-4 text-xs font-black uppercase tracking-[0.08em] text-primary hover:bg-primary/10"
        >
          Open traffic map
          <ArrowRight size={15} />
        </Link>
      </div>
    );
  }

  return (
    <div className="border border-outline-variant/50 bg-surface">
      <div className="flex items-center justify-between gap-3 border-b border-outline-variant/40 px-4 py-4">
        <div className="flex items-center gap-3">
          <Ship className="text-primary" size={21} />
          <h3 className="font-black text-on-surface">Vessels to watch</h3>
        </div>
        <Link to="/map" onClick={onNavigate} className="font-mono text-xs uppercase text-primary">
          Map
        </Link>
      </div>
      {vessels.slice(0, 5).map((vessel) => (
        <Link
          key={`${vessel.mmsi ?? vessel.name}-${vessel.zone}`}
          to="/map"
          onClick={onNavigate}
          className="grid grid-cols-[minmax(0,1fr)_80px_80px] gap-3 border-t border-outline-variant/30 px-4 py-3 first:border-t-0 hover:bg-surface-container max-sm:grid-cols-2"
        >
          <div>
            <div className="truncate font-mono text-sm font-black text-on-surface">{vessel.name}</div>
            <div className="font-mono text-xs uppercase text-on-surface-variant">{vessel.zone}</div>
          </div>
          <div className="font-mono text-sm text-on-surface max-sm:text-right">{vessel.sog} kts</div>
          <div className="text-right font-mono text-sm text-primary max-sm:col-span-2 max-sm:text-left">
            {vessel.eta || "--:--"} est.
          </div>
        </Link>
      ))}
    </div>
  );
}

function TerminalList({ terminals, onNavigate }) {
  return (
    <div className="border border-outline-variant/50 bg-surface">
      <div className="flex items-center justify-between gap-3 border-b border-outline-variant/40 px-4 py-4">
        <div className="flex items-center gap-3">
          <Anchor className="text-secondary" size={21} />
          <h3 className="font-black text-on-surface">Terminals and berths</h3>
        </div>
        <Link to="/berth" onClick={onNavigate} className="font-mono text-xs uppercase text-primary">
          Berths
        </Link>
      </div>
      {terminals.length === 0 ? (
        <div className="px-4 py-6 text-sm leading-6 text-on-surface-variant">
          Terminal detail is not published for this port in the current operating snapshot.
        </div>
      ) : null}
      {terminals.slice(0, 6).map((terminal) => (
        <Link
          key={terminal.id}
          to="/berth"
          onClick={onNavigate}
          className="flex items-center justify-between gap-4 border-t border-outline-variant/30 px-4 py-3 first:border-t-0 hover:bg-surface-container"
        >
          <div>
            <div className="font-black text-on-surface">{terminal.name}</div>
            <div className="text-xs text-on-surface-variant">
              {terminal.vessel ? terminal.vessel : "No vessel assigned"}
            </div>
          </div>
          <span className="font-mono text-xs uppercase text-secondary">{terminal.status}</span>
        </Link>
      ))}
    </div>
  );
}

function SourceRow({ source }) {
  return (
    <div className="border-t border-outline-variant/30 px-4 py-3 first:border-t-0">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined text-[18px] text-primary">
            {sourceIcon(source.name)}
          </span>
          <div className="font-black text-on-surface">{source.name}</div>
        </div>
        <div className="font-mono text-xs uppercase text-secondary">{source.status}</div>
      </div>
      <div className="mt-1 text-sm leading-6 text-on-surface-variant">{source.detail}</div>
      <div className="mt-2 font-mono text-xs text-on-surface-variant">
        Freshness: {source.freshness}
      </div>
    </div>
  );
}

export default function PhaseOneLanding() {
  const { ports, currentPortCode, setCurrentPortCode, metadata, sources } = useData();
  const [selectedCode, setSelectedCode] = useState(currentPortCode);

  const portRows = useMemo(
    () =>
      Object.values(ports).sort((leftPort, rightPort) => {
        const leftMetrics = leftPort.metrics ?? {};
        const rightMetrics = rightPort.metrics ?? {};
        return (
          (rightMetrics.congestionPct ?? 0) - (leftMetrics.congestionPct ?? 0) ||
          (rightMetrics.waiting ?? 0) - (leftMetrics.waiting ?? 0) ||
          (rightMetrics.tracked ?? 0) - (leftMetrics.tracked ?? 0) ||
          leftPort.name.localeCompare(rightPort.name)
        );
      }),
    [ports]
  );

  useEffect(() => {
    if (!selectedCode && currentPortCode) setSelectedCode(currentPortCode);
  }, [currentPortCode, selectedCode]);

  const selectedPort = ports[selectedCode] ?? portRows[0] ?? null;
  const selectedMetrics = selectedPort?.metrics ?? {};

  const snapshot = useMemo(() => {
    const totalTracked = portRows.reduce(
      (total, portInfo) => total + (portInfo.metrics?.tracked ?? 0),
      0
    );
    const totalWaiting = portRows.reduce(
      (total, portInfo) => total + (portInfo.metrics?.waiting ?? 0),
      0
    );
    const terminalCount = portRows.reduce(
      (total, portInfo) => total + (portInfo.berthAllocations?.length ?? 0),
      0
    );
    const vesselCount = portRows.reduce(
      (total, portInfo) => total + (portInfo.vesselsTotal ?? portInfo.vessels?.length ?? 0),
      0
    );
    const activeSources = sources.filter((source) => source.status === "active").length;

    return { activeSources, terminalCount, totalTracked, totalWaiting, vesselCount };
  }, [portRows, sources]);

  useEffect(() => {
    const previousTitle = document.title;
    document.title = "Data Party Logistics — Port Intelligence";

    return () => {
      document.title = previousTitle;
    };
  }, []);

  function selectPort(code) {
    setSelectedCode(code);
    setCurrentPortCode(code);
  }

  const navigateWithSelectedPort = () => {
    if (selectedPort?.code) setCurrentPortCode(selectedPort.code);
  };

  return (
    <div className="min-h-screen bg-surface-container-lowest text-on-surface">
      <header className="border-b border-outline-variant/50 bg-surface">
        <div className="mx-auto flex h-16 w-[min(1180px,calc(100%_-_32px))] items-center justify-between gap-4">
          <a href="#top" className="flex min-w-0 items-center gap-3" aria-label="Data Party Logistics">
            <BrandMark className="h-10 w-10" alt="Data Party Logistics logo" />
            <span className="min-w-0">
              <span className="block truncate text-sm font-black uppercase tracking-[0.08em]">
                Data Party Logistics
              </span>
              <span className="block truncate text-xs text-on-surface-variant">
                Port intelligence
              </span>
            </span>
          </a>

          <nav className="hidden items-center gap-1 md:flex" aria-label="Primary">
            <a href="#ports" className="px-3 py-2 text-sm text-on-surface-variant hover:text-on-surface">
              Ports
            </a>
            <a href="#operations" className="px-3 py-2 text-sm text-on-surface-variant hover:text-on-surface">
              Operations
            </a>
            <a href="#sources" className="px-3 py-2 text-sm text-on-surface-variant hover:text-on-surface">
              Sources
            </a>
            <Link
              to="/"
              onClick={navigateWithSelectedPort}
              className="ml-2 border border-primary/60 px-4 py-2 text-xs font-black uppercase tracking-[0.08em] text-primary hover:bg-primary/10"
            >
              Open platform
            </Link>
          </nav>

          <Link
            to="/"
            onClick={navigateWithSelectedPort}
            className="border border-primary/60 px-3 py-2 text-[11px] font-black uppercase tracking-[0.08em] text-primary hover:bg-primary/10 md:hidden"
          >
            Platform
          </Link>
        </div>
      </header>

      <main id="top">
        <section className="mx-auto grid w-[min(1180px,calc(100%_-_32px))] grid-cols-[minmax(0,1fr)_390px] gap-8 py-16 max-lg:grid-cols-1 max-sm:py-10">
          <div>
            <h1 className="max-w-4xl text-[clamp(42px,6vw,78px)] font-black leading-[0.96] tracking-normal">
              Know which ports need attention before exceptions become escalations.
            </h1>

            <p className="mt-5 max-w-2xl text-lg leading-8 text-on-surface-variant">
              DPL turns vessel traffic, terminal availability, weather, and freshness
              signals into a focused operating view for maritime stakeholders.
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                to="/"
                onClick={navigateWithSelectedPort}
                className="inline-flex min-h-12 items-center justify-center gap-2 border border-primary bg-primary px-5 text-xs font-black uppercase tracking-[0.08em] text-[#101b30]"
              >
                Open command view
                <LayoutDashboard size={16} strokeWidth={2.2} />
              </Link>
              <Link
                to="/map"
                onClick={navigateWithSelectedPort}
                className="inline-flex min-h-12 items-center justify-center gap-2 border border-outline-variant/70 bg-surface-container px-5 text-xs font-black uppercase tracking-[0.08em] text-on-surface hover:bg-surface-variant"
              >
                Vessel traffic
                <ArrowRight size={16} strokeWidth={2.2} />
              </Link>
            </div>
          </div>

          <aside className="border border-outline-variant bg-surface-container p-5">
            <div className="mb-5 flex items-center gap-3">
              <BrandMark className="h-11 w-11" alt="" />
              <div>
                <div className="text-[11px] font-black uppercase tracking-[0.08em] text-on-surface-variant">
                  Latest operating snapshot
                </div>
                <div className="mt-1 font-mono text-sm text-secondary">
                  {metadata?.generatedAt ?? "Loading"}
                </div>
                <div className="mt-1 font-mono text-xs text-on-surface-variant">
                  {snapshotAge(metadata?.generatedAt)}
                </div>
              </div>
            </div>

            <div className="grid gap-3">
              <MetricCard
                label="Ports monitored"
                value={formatNumber(portRows.length)}
                detail={`${formatNumber(snapshot.terminalCount)} terminals and berths in view`}
                Icon={Map}
              />
              <MetricCard
                label="Traffic signal"
                value={snapshot.vesselCount > 0 ? formatNumber(snapshot.vesselCount) : "Quiet"}
                detail={
                  snapshot.vesselCount > 0
                    ? `${formatNumber(snapshot.totalWaiting)} waiting at anchor across monitored ports`
                    : "No vessel positions surfaced in the current snapshot"
                }
                Icon={Ship}
              />
              <MetricCard
                label="Live sources"
                value={`${formatNumber(snapshot.activeSources)}/${formatNumber(sources.length)}`}
                detail="AIS, weather, and operational reference signals"
                Icon={Database}
              />
            </div>
          </aside>
        </section>

        <section id="ports" className="border-t border-outline-variant/40">
          <div className="mx-auto w-[min(1180px,calc(100%_-_32px))] py-12">
            <div className="mb-6 flex items-end justify-between gap-6 max-lg:flex-col max-lg:items-start">
              <div>
                <h2 className="text-[clamp(28px,4vw,44px)] font-black leading-tight tracking-normal">
                  Port coverage and current pressure
                </h2>
                <p className="mt-3 max-w-2xl leading-7 text-on-surface-variant">
                  Select a port to update the operating summary, vessel panel, terminal list, and dashboard links.
                </p>
              </div>
              {selectedPort ? (
                <div className="border border-outline-variant/50 bg-surface px-4 py-3">
                  <div className="font-mono text-xs uppercase text-on-surface-variant">Selected port</div>
                  <div className="mt-1 font-black">{selectedPort.name} · {selectedPort.code}</div>
                </div>
              ) : null}
            </div>

            <PortSelector ports={portRows} selectedCode={selectedPort?.code} onSelect={selectPort} />
          </div>
        </section>

        {selectedPort ? (
          <section id="operations" className="border-t border-outline-variant/40">
            <div className="mx-auto grid w-[min(1180px,calc(100%_-_32px))] grid-cols-[minmax(0,1fr)_390px] gap-6 py-12 max-lg:grid-cols-1">
              <div>
                <div className="mb-4 flex items-center gap-3">
                  <RadioTower className="text-primary" size={24} />
                  <div>
                    <div className="text-[11px] font-black uppercase tracking-[0.08em] text-on-surface-variant">
                      Port operating view
                    </div>
                    <h2 className="mt-1 text-[clamp(28px,4vw,44px)] font-black leading-tight tracking-normal">
                      {selectedPort.name}
                    </h2>
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-3 max-lg:grid-cols-2 max-sm:grid-cols-1">
                  <MetricCard
                    label="Pressure"
                    value={pressureLabel(selectedMetrics, selectedPort.hasSnapshot)}
                    detail={
                      selectedPort.hasSnapshot === false
                        ? "Coverage is configured; operational metrics are not in this snapshot"
                        : `${formatPercent(selectedMetrics.congestionPct)} congestion signal`
                    }
                    Icon={Activity}
                  />
                  <MetricCard
                    label="Tracked"
                    value={formatNumber(selectedMetrics.tracked)}
                    detail={
                      selectedPort.hasSnapshot === false
                        ? "Awaiting the latest AIS traffic snapshot"
                        : "Active vessels in the current snapshot"
                    }
                    Icon={Ship}
                  />
                  <MetricCard
                    label="Waiting"
                    value={formatNumber(selectedMetrics.waiting)}
                    detail="Vessels at anchor or queue positions"
                    Icon={Anchor}
                  />
                  <MetricCard
                    label="Max wave"
                    value={`${Number(selectedMetrics.maxWave ?? 0).toFixed(1)} m`}
                    detail={`${Number(selectedMetrics.avgSpeed ?? 0).toFixed(1)} kts average speed`}
                    Icon={Waves}
                  />
                </div>

                <div className="mt-6 grid grid-cols-2 gap-4 max-md:grid-cols-1">
                  <ModuleLink
                    to="/"
                    onClick={navigateWithSelectedPort}
                    icon="dashboard"
                    title="Executive dashboard"
                    detail="Summary metrics, freshness, and port-level operating status."
                  />
                  <ModuleLink
                    to="/map"
                    onClick={navigateWithSelectedPort}
                    icon="directions_boat"
                    title="Vessel traffic"
                    detail="Active vessel positions, speed, distance, ETA, and confidence."
                  />
                  <ModuleLink
                    to="/schedule"
                    onClick={navigateWithSelectedPort}
                    icon="schedule"
                    title="Arrival schedule"
                    detail="Approaching and in-transit vessel timing for operations planning."
                  />
                  <ModuleLink
                    to="/berth"
                    onClick={navigateWithSelectedPort}
                    icon="calendar_view_day"
                    title="Terminal berths"
                    detail="Terminal availability and berth allocation for the selected port."
                  />
                  <ModuleLink
                    to="/insights"
                    onClick={navigateWithSelectedPort}
                    icon="analytics"
                    title="Congestion insights"
                    detail="Trend context and operating pressure signals for stakeholder review."
                  />
                  <ModuleLink
                    to="/predictive"
                    onClick={navigateWithSelectedPort}
                    icon="query_stats"
                    title="Predictive outlook"
                    detail="Forward-looking risk indicators for proactive customer communication."
                  />
                </div>
              </div>

              <div className="grid content-start gap-4">
                <VesselList vessels={selectedPort.vessels ?? []} onNavigate={navigateWithSelectedPort} />
                <TerminalList terminals={selectedPort.berthAllocations ?? []} onNavigate={navigateWithSelectedPort} />
              </div>
            </div>
          </section>
        ) : null}

        <section id="sources" className="border-t border-outline-variant/40">
          <div className="mx-auto grid w-[min(1180px,calc(100%_-_32px))] grid-cols-[minmax(0,1fr)_430px] gap-6 py-12 max-lg:grid-cols-1">
            <div>
              <h2 className="max-w-2xl text-[clamp(28px,4vw,44px)] font-black leading-tight tracking-normal">
                Built for credible decisions, not decorative screens.
              </h2>
              <p className="mt-4 max-w-2xl leading-7 text-on-surface-variant">
                Every homepage number reflects the current operating snapshot used across
                the platform. If a port has no surfaced queue or vessel traffic, the page
                shows that directly.
              </p>
              <div className="mt-6 grid grid-cols-2 gap-4 max-sm:grid-cols-1">
                <MetricCard
                  label="Decision path"
                  value="Port → Vessel → Terminal"
                  detail="Stakeholders can move from network-level pressure to specific operational screens."
                  Icon={BarChart3}
                />
                <MetricCard
                  label="Planning window"
                  value="Now"
                  detail="Snapshot-based operating status with freshness visible at the top of the page."
                  Icon={CalendarClock}
                />
              </div>
            </div>

            <article className="border border-outline-variant/50 bg-surface">
              <div className="flex items-center gap-3 border-b border-outline-variant/40 px-4 py-4">
                <Database className="text-primary" size={21} />
                <h2 className="text-xl font-black tracking-normal">Signal sources</h2>
              </div>
              {sources.length > 0 ? (
                sources.map((source) => <SourceRow key={source.name} source={source} />)
              ) : (
                <div className="px-4 py-6 text-sm text-on-surface-variant">
                  Source metadata is unavailable for the current operating snapshot.
                </div>
              )}
            </article>
          </div>
        </section>
      </main>

      <footer className="border-t border-outline-variant/40 bg-surface px-6 py-6">
        <div className="mx-auto flex w-[min(1180px,100%)] items-center justify-between gap-4 text-xs text-on-surface-variant max-sm:flex-col max-sm:items-start">
          <span>Data Party Logistics</span>
          <span>Port intelligence for vessel, terminal, and congestion decisions.</span>
        </div>
      </footer>
    </div>
  );
}
