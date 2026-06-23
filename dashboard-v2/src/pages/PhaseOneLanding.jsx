import {
  Activity,
  Anchor,
  ArrowRight,
  BarChart3,
  CalendarClock,
  Database,
  LayoutDashboard,
  RadioTower,
  Ship,
  Waves,
} from "lucide-react";
import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import BrandMark from "../components/BrandMark";
import { useData } from "../context/DataContext";

const CostCalculator = lazy(() => import("../components/CostCalculator"));

function formatNumber(value) {
  return new Intl.NumberFormat("en").format(Number(value) || 0);
}

function formatPercent(value) {
  return `${Number(value) || 0}%`;
}

function hasProviderCoverageIssue(port) {
  return ['coverage_limited', 'no_provider_messages'].includes(port?.aisDiagnostics?.status);
}

function pressureLabel(metrics, hasSnapshot = true, port = null) {
  if (hasProviderCoverageIssue(port)) return "Coverage limited";
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

function SideNote({ className = "" }) {
  return (
    <aside className={`max-w-2xl border-l border-outline-variant/70 pl-4 text-sm leading-6 text-on-surface-variant ${className}`}>
      <span className="font-black text-on-surface">Built as a hobby project.</span>{" "}
      This product is still under development. Live operational data brings
      cloud, time, and cost requirements, so support from anyone who finds it
      useful is genuinely appreciated.
    </aside>
  );
}

function SnapshotLinkCard({ to, label, value, detail, Icon, onClick }) {
  return (
    <Link
      to={to}
      onClick={onClick}
      className="group rounded-[6px] border border-outline-variant/50 bg-surface p-3 transition-colors hover:border-primary/60 hover:bg-surface-container"
    >
      <div className="flex items-center justify-between gap-3">
        <span className="text-[10px] font-black uppercase tracking-[0.08em] text-on-surface-variant">
          {label}
        </span>
        {Icon ? <Icon className="text-primary" size={16} /> : null}
      </div>
      <div className="mt-2 font-mono text-2xl font-black leading-none text-on-surface">
        {value}
      </div>
      <div className="mt-2 flex items-center justify-between gap-2 text-xs leading-4 text-on-surface-variant">
        <span className="truncate">{detail}</span>
        <ArrowRight className="shrink-0 text-on-surface-variant group-hover:text-primary" size={14} />
      </div>
    </Link>
  );
}

function ModuleLink({ to, icon, title, detail, onClick }) {
  return (
    <Link
      to={to}
      onClick={onClick}
      className="group flex min-h-14 items-center justify-between gap-3 rounded-[6px] border border-outline-variant/50 bg-surface px-3 py-2 transition-colors hover:border-primary/60 hover:bg-surface-container"
    >
      <div className="flex min-w-0 items-center gap-2">
        <span className="material-symbols-outlined shrink-0 text-[20px] text-primary">{icon}</span>
        <div className="min-w-0">
          <h3 className="truncate text-sm font-black text-on-surface">{title}</h3>
          <p className="truncate text-xs leading-4 text-on-surface-variant">{detail}</p>
        </div>
      </div>
      <ArrowRight className="shrink-0 text-on-surface-variant group-hover:text-primary" size={15} />
    </Link>
  );
}

function PortSelector({ ports, selectedCode, onSelect }) {
  return (
    <div className="overflow-hidden rounded-[6px] border border-outline-variant/50 bg-surface">
      <div className="flex items-center justify-between gap-3 border-b border-outline-variant/40 px-3 py-1.5">
        <div>
          <div className="text-[10px] font-black uppercase tracking-[0.08em] text-on-surface-variant">
            Port selection
          </div>
          <div className="mt-0.5 text-[10px] text-on-surface-variant">Choose one snapshot</div>
        </div>
        <span className="rounded-[6px] border border-outline-variant/50 px-2 py-1 font-mono text-[10px] text-on-surface-variant">
          {formatNumber(ports.length)}
        </span>
      </div>

      <div className="divide-y divide-outline-variant/30">
        {ports.map((portInfo) => {
          const metrics = portInfo.metrics ?? {};
          const isSelected = portInfo.code === selectedCode;
          const providerCoverageIssue = hasProviderCoverageIssue(portInfo);

          return (
            <button
              key={portInfo.code}
              type="button"
              onClick={() => onSelect(portInfo.code)}
              className={`group grid w-full grid-cols-[4px_minmax(0,1fr)_auto] items-center gap-2.5 px-0 py-0 text-left transition-colors ${
                isSelected
                  ? "bg-primary-container text-on-primary-container"
                  : "bg-surface text-on-surface hover:bg-surface-container"
              }`}
            >
              <span className={`h-full min-h-10 ${isSelected ? "bg-primary" : "bg-transparent"}`} />
              <span className="min-w-0 py-1">
                <span className="flex items-center gap-2">
                  <span className="font-mono text-[11px] font-black uppercase">{portInfo.code}</span>
                  <span className="truncate text-xs font-black leading-4">{portInfo.name}</span>
                </span>
                <span className="block truncate text-[10px] opacity-75">
                  {providerCoverageIssue
                    ? "No AIS messages received from provider"
                    : `${formatNumber(metrics.tracked)} tracked · ${formatNumber(metrics.waiting)} waiting`}
                </span>
              </span>
              <span className="flex items-center gap-2 pr-3">
                <span className="text-right font-mono text-[10px] uppercase opacity-80">
                  {pressureLabel(metrics, portInfo.hasSnapshot, portInfo)}
                </span>
                <ArrowRight
                  className={`shrink-0 transition-colors ${
                    isSelected ? "text-on-primary-container" : "text-on-surface-variant group-hover:text-primary"
                  }`}
                  size={13}
                />
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function CompactInfoTile({ label, value, detail, Icon }) {
  return (
    <div className="rounded-[6px] border border-outline-variant/50 bg-surface px-3 py-3">
      <div className="flex items-center justify-between gap-3">
        <span className="text-[10px] font-black uppercase tracking-[0.08em] text-on-surface-variant">
          {label}
        </span>
        {Icon ? <Icon className="text-primary" size={16} /> : null}
      </div>
      <div className="mt-2 font-mono text-xl font-black leading-tight text-on-surface">
        {value}
      </div>
      <p className="mt-1 text-xs leading-4 text-on-surface-variant">{detail}</p>
    </div>
  );
}

function SourceRow({ source }) {
  return (
    <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-4 gap-y-1 border-t border-outline-variant/30 px-3 py-2.5 first:border-t-0">
      <div className="flex min-w-0 items-center gap-2">
        <span className="material-symbols-outlined shrink-0 text-[17px] text-primary">
          {sourceIcon(source.name)}
        </span>
        <div className="min-w-0">
          <div className="truncate text-sm font-black text-on-surface">{source.name}</div>
          <div className="truncate text-xs text-on-surface-variant">{source.detail}</div>
        </div>
      </div>
      <div className="text-right">
        <div className="font-mono text-[11px] uppercase text-secondary">{source.status}</div>
        <div className="mt-1 font-mono text-[11px] text-on-surface-variant">{source.freshness}</div>
      </div>
    </div>
  );
}

function CostExplorerFallback() {
  return (
    <div className="flex min-h-64 items-center justify-center rounded-[6px] border border-outline-variant/50 bg-surface-container text-sm text-on-surface-variant">
      Loading impact explorer...
    </div>
  );
}

function DelayImpactPanel() {
  return (
    <aside className="rounded-[6px] border border-outline-variant bg-surface-container p-5">
      <div className="mb-5">
        <div className="text-[11px] font-black uppercase tracking-[0.08em] text-on-surface-variant">
          Delay impact explorer
        </div>
        <h2 className="mt-2 text-2xl font-black leading-tight text-on-surface">
          Model the cost of waiting time.
        </h2>
        <p className="mt-3 text-sm leading-6 text-on-surface-variant">
          Estimate how vessel scale, demurrage, and storage fees can compound
          when congestion holds cargo in the wrong place.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 max-sm:grid-cols-1">
        <CompactInfoTile
          label="Vessel wait"
          value="$20k-$100k+"
          detail="Typical daily exposure."
          Icon={BarChart3}
        />
        <CompactInfoTile
          label="Container fees"
          value="$50-$300+"
          detail="Daily fee range."
          Icon={CalendarClock}
        />
      </div>
    </aside>
  );
}

export default function PhaseOneLanding() {
  const { ports, currentPortCode, setCurrentPortCode, sources } = useData();
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

  const effectiveSelectedCode = selectedCode ?? currentPortCode;
  const selectedPort = ports[effectiveSelectedCode] ?? portRows[0] ?? null;
  const selectedMetrics = selectedPort?.metrics ?? {};
  const selectedProviderCoverageIssue = hasProviderCoverageIssue(selectedPort);

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
            <BrandMark alt="Data Party Logistics logo" />
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
            <Link to="/dashboard/map" className="px-3 py-2 text-sm text-on-surface-variant hover:text-on-surface">
              Vessel traffic
            </Link>
            <Link to="/docs" className="px-3 py-2 text-sm text-on-surface-variant hover:text-on-surface">
              Docs
            </Link>
            <Link
              to="/dashboard"
              onClick={navigateWithSelectedPort}
              className="ml-2 rounded-[6px] border border-primary/60 px-4 py-2 text-xs font-black uppercase tracking-[0.08em] text-primary hover:bg-primary/10"
            >
              Open platform
            </Link>
          </nav>

          <Link
            to="/dashboard"
            onClick={navigateWithSelectedPort}
            className="rounded-[6px] border border-primary/60 px-3 py-2 text-[11px] font-black uppercase tracking-[0.08em] text-primary hover:bg-primary/10 md:hidden"
          >
            Platform
          </Link>
        </div>
      </header>

      <main id="top">
        <section className="mx-auto grid w-[min(1180px,calc(100%_-_32px))] grid-cols-[minmax(0,1fr)_430px] gap-8 py-12 max-lg:grid-cols-1 max-sm:py-10">
          <div>
            <div className="mb-4 inline-flex rounded-[6px] border border-outline-variant/60 bg-surface px-3 py-1.5 font-mono text-[10px] font-black uppercase tracking-[0.08em] text-secondary">
              Snapshot based port operations
            </div>
            <h1 className="max-w-4xl text-[clamp(36px,5.4vw,72px)] font-black leading-[1.01] tracking-normal">
              Know port pressure. Open the right view.
            </h1>

            <p className="mt-5 max-w-2xl text-lg leading-8 text-on-surface-variant">
              DPL turns vessel traffic, berth coverage, weather, and freshness
              signals into a focused operating view for maritime decisions.
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                to="/dashboard"
                onClick={navigateWithSelectedPort}
                className="inline-flex min-h-12 items-center justify-center gap-2 rounded-[6px] border border-primary bg-primary px-5 text-xs font-black uppercase tracking-[0.08em] text-[#101b30]"
              >
                Open platform
                <LayoutDashboard size={16} strokeWidth={2.2} />
              </Link>
              <Link
                to="/dashboard/map"
                onClick={navigateWithSelectedPort}
                className="inline-flex min-h-12 items-center justify-center gap-2 rounded-[6px] border border-outline-variant/70 bg-surface px-5 text-xs font-black uppercase tracking-[0.08em] text-on-surface hover:bg-surface-container"
              >
                Vessel map
                <ArrowRight size={16} strokeWidth={2.2} />
              </Link>
            </div>
          </div>

          <DelayImpactPanel />

          <SideNote className="lg:col-start-1 lg:row-start-2 lg:-mt-5" />
        </section>

        <section id="impact" className="border-t border-outline-variant/40 bg-surface">
          <div className="mx-auto w-[min(980px,calc(100%_-_32px))] py-7">
            <Suspense fallback={<CostExplorerFallback />}>
              <CostCalculator />
            </Suspense>
          </div>
        </section>

        <section id="ports" className="border-t border-outline-variant/40">
          <div className="mx-auto w-[min(1180px,calc(100%_-_32px))] py-8">
            <div className="mb-4 flex items-end justify-between gap-6 max-lg:flex-col max-lg:items-start">
              <div>
                <h2 className="text-[clamp(28px,3.4vw,38px)] font-black leading-tight tracking-normal">
                  Port snapshots
                </h2>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-on-surface-variant">
                  Select a port for a fast read, then jump into the right dashboard view for detail.
                </p>
              </div>
              {selectedPort ? (
                <div className="rounded-[6px] border border-outline-variant/50 bg-surface px-3 py-2">
                  <div className="font-mono text-[10px] uppercase text-on-surface-variant">Selected port</div>
                  <div className="mt-0.5 text-sm font-black">{selectedPort.name} · {selectedPort.code}</div>
                </div>
              ) : null}
            </div>

            <div className="grid grid-cols-[minmax(300px,380px)_minmax(0,1fr)] items-start gap-4 max-lg:grid-cols-1">
              <PortSelector ports={portRows} selectedCode={selectedPort?.code} onSelect={selectPort} />

              {selectedPort ? (
                <div id="operations" className="rounded-[6px] border border-outline-variant/50 bg-surface-container p-4">
                  <div className="mb-3 flex items-start justify-between gap-4 max-sm:flex-col">
                    <div className="flex items-center gap-3">
                      <RadioTower className="text-primary" size={20} />
                      <div>
                        <div className="text-[10px] font-black uppercase tracking-[0.08em] text-on-surface-variant">
                          Port operating overview
                        </div>
                        <h2 className="mt-0.5 text-[clamp(24px,3vw,34px)] font-black leading-tight tracking-normal">
                          {selectedPort.name}
                        </h2>
                      </div>
                    </div>
                    <Link
                      to="/dashboard"
                      onClick={navigateWithSelectedPort}
                      className="inline-flex min-h-9 shrink-0 items-center justify-center gap-2 rounded-[6px] border border-primary/60 px-3 text-[11px] font-black uppercase tracking-[0.08em] text-primary hover:bg-primary/10"
                    >
                      Full dashboard
                      <ArrowRight size={14} />
                    </Link>
                  </div>

                  <div className="grid grid-cols-4 gap-3 max-xl:grid-cols-2 max-sm:grid-cols-1">
                    <SnapshotLinkCard
                      to="/dashboard/insights"
                      onClick={navigateWithSelectedPort}
                      label="Congestion"
                      value={
                        selectedPort.hasSnapshot === false
                          ? "No snapshot"
                          : formatPercent(selectedMetrics.congestionPct)
                      }
                      detail={pressureLabel(selectedMetrics, selectedPort.hasSnapshot, selectedPort)}
                      Icon={Activity}
                    />
                    <SnapshotLinkCard
                      to="/dashboard/map"
                      onClick={navigateWithSelectedPort}
                      label="Active"
                      value={selectedProviderCoverageIssue ? "--" : formatNumber(selectedMetrics.tracked)}
                      detail={
                        selectedProviderCoverageIssue
                          ? "Provider coverage limited"
                          : selectedPort.hasSnapshot === false
                          ? "Awaiting AIS traffic"
                          : "Traffic map"
                      }
                      Icon={Ship}
                    />
                    <SnapshotLinkCard
                      to="/dashboard/schedule"
                      onClick={navigateWithSelectedPort}
                      label="Waiting"
                      value={formatNumber(selectedMetrics.waiting)}
                      detail="Schedule"
                      Icon={Anchor}
                    />
                    <SnapshotLinkCard
                      to="/dashboard/berth"
                      onClick={navigateWithSelectedPort}
                      label="Berths"
                      value={formatNumber(selectedPort.berthAllocations?.length ?? 0)}
                      detail="Terminal view"
                      Icon={Waves}
                    />
                  </div>

                  <div className="mt-3 grid grid-cols-3 gap-2 border-t border-outline-variant/40 pt-3 max-sm:grid-cols-1">
                    <CompactInfoTile
                      label="Vessels"
                      value={
                        selectedProviderCoverageIssue
                          ? "--"
                          : formatNumber(selectedPort.vesselsTotal ?? selectedPort.vessels?.length ?? 0)
                      }
                      detail={
                        selectedProviderCoverageIssue
                          ? "No AIS messages received from provider."
                          : "Total surfaced in snapshot."
                      }
                      Icon={Ship}
                    />
                    <CompactInfoTile
                      label="Avg speed"
                      value={`${Number(selectedMetrics.avgSpeed ?? 0).toFixed(1)} kts`}
                      detail="Movement signal."
                      Icon={Activity}
                    />
                    <CompactInfoTile
                      label="Max wave"
                      value={`${Number(selectedMetrics.maxWave ?? 0).toFixed(1)} m`}
                      detail="Marine condition."
                      Icon={Waves}
                    />
                  </div>

                  <div className="mt-3 grid grid-cols-2 gap-2 border-t border-outline-variant/40 pt-3 max-sm:grid-cols-1">
                    <ModuleLink
                      to="/dashboard"
                      onClick={navigateWithSelectedPort}
                      icon="dashboard"
                      title="Dashboard"
                      detail="Snapshot, freshness, status."
                    />
                    <ModuleLink
                      to="/dashboard/map"
                      onClick={navigateWithSelectedPort}
                      icon="directions_boat"
                      title="Vessel traffic"
                      detail="Positions, speed, ETA."
                    />
                    <ModuleLink
                      to="/dashboard/schedule"
                      onClick={navigateWithSelectedPort}
                      icon="schedule"
                      title="Arrival schedule"
                      detail="Waiting and inbound timing."
                    />
                    <ModuleLink
                      to="/dashboard/berth"
                      onClick={navigateWithSelectedPort}
                      icon="calendar_view_day"
                      title="Berths"
                      detail="Berth allocation detail."
                    />
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </section>

        <section id="sources" className="border-t border-outline-variant/40">
          <div className="mx-auto grid w-[min(1180px,calc(100%_-_32px))] grid-cols-[minmax(0,1fr)_390px] gap-4 py-8 max-lg:grid-cols-1">
            <div>
              <h2 className="max-w-2xl text-[clamp(24px,3vw,34px)] font-black leading-tight tracking-normal">
                Simple operating flow.
              </h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-on-surface-variant">
                Pick a port, check pressure, then open the exact dashboard view
                needed for the next decision.
              </p>
              <div className="mt-4 grid grid-cols-2 gap-3 max-sm:grid-cols-1">
                <CompactInfoTile
                  label="Decision path"
                  value="Port → Vessel → Terminal"
                  detail="Move from pressure to the operational page."
                  Icon={BarChart3}
                />
                <CompactInfoTile
                  label="Planning window"
                  value="Now"
                  detail="Freshness is visible before action."
                  Icon={CalendarClock}
                />
              </div>
            </div>

            <article className="overflow-hidden rounded-[6px] border border-outline-variant/50 bg-surface">
              <div className="flex items-center gap-2 border-b border-outline-variant/40 px-3 py-3">
                <Database className="text-primary" size={18} />
                <h2 className="text-base font-black tracking-normal">Signal sources</h2>
              </div>
              {sources.length > 0 ? (
                sources.map((source) => <SourceRow key={source.name} source={source} />)
              ) : (
                <div className="px-3 py-4 text-sm text-on-surface-variant">
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
