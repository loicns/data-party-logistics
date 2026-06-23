import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, Navigate, NavLink, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  Chart as ChartJS,
  ArcElement,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar, Doughnut, getElementAtEvent } from 'react-chartjs-2';
import BrandMark from '../components/BrandMark';
import { useRoadmap } from '../hooks/useRoadmap';

ChartJS.register(ArcElement, BarElement, CategoryScale, LinearScale, Tooltip, Legend);

const AREA_STATUS_ORDER = ['completed', 'doing', 'backlog'];
const TASK_STATUS_ORDER = ['done', 'doing', 'todo'];
const ROADMAP_VIEWS = [
  { id: 'overview', path: '/roadmap/overview', label: 'Overview', icon: 'space_dashboard' },
  { id: 'tasks', path: '/roadmap/tasks', label: 'Tasks', icon: 'checklist' },
  { id: 'board', path: '/roadmap/board', label: 'Kanban Board', icon: 'view_kanban' },
  { id: 'sources', path: '/roadmap/sources', label: 'Sources & Admin', icon: 'admin_panel_settings' },
];

const STATUS_META = {
  completed: {
    label: 'Completed',
    icon: 'task_alt',
    badge: 'bg-secondary-container text-on-secondary-container border-secondary/40',
    dot: 'bg-secondary',
    bar: 'bg-secondary',
    chart: '#afc9ea',
  },
  doing: {
    label: 'Doing',
    icon: 'hourglass_top',
    badge: 'bg-primary-container text-primary border-primary/40',
    dot: 'bg-primary',
    bar: 'bg-primary',
    chart: '#bbc6e2',
  },
  backlog: {
    label: 'Backlog',
    icon: 'inventory_2',
    badge: 'bg-surface-container-high text-on-surface-variant border-outline-variant',
    dot: 'bg-outline',
    bar: 'bg-outline',
    chart: '#8f9097',
  },
};

const TASK_STATUS_META = {
  done: {
    label: 'Done',
    icon: 'check_circle',
    badge: 'bg-secondary-container text-on-secondary-container border-secondary/40',
    dot: 'bg-secondary',
  },
  doing: {
    label: 'Doing',
    icon: 'radio_button_checked',
    badge: 'bg-primary-container text-primary border-primary/40',
    dot: 'bg-primary',
  },
  todo: {
    label: 'To do',
    icon: 'radio_button_unchecked',
    badge: 'bg-surface-container-high text-on-surface-variant border-outline-variant',
    dot: 'bg-outline',
  },
};

function getStatusMeta(status) {
  return STATUS_META[status] ?? STATUS_META.backlog;
}

function getTaskStatusMeta(status) {
  return TASK_STATUS_META[status] ?? TASK_STATUS_META.todo;
}

function flattenMilestones(areas) {
  return areas.flatMap((area) =>
    area.milestones.map((milestone) => ({
      ...milestone,
      areaId: area.id,
      areaName: area.name,
    }))
  );
}

function flattenTasks(milestones) {
  return milestones.flatMap((milestone) =>
    milestone.tasks.map((task) => ({
      ...task,
      areaId: milestone.areaId,
      areaName: milestone.areaName,
      milestoneId: milestone.id,
      milestoneName: milestone.name,
      milestoneStatus: milestone.status,
      milestoneTimeframe: milestone.timeframe,
    }))
  );
}

function countBy(items, keys) {
  return keys.reduce((counts, key) => {
    counts[key] = items.filter((item) => item.status === key).length;
    return counts;
  }, {});
}

function taskProgress(tasks) {
  if (!tasks.length) return 0;
  const done = tasks.filter((task) => task.status === 'done').length;
  return Math.round((done / tasks.length) * 100);
}

function areaTasks(area) {
  return area.milestones.flatMap((milestone) => milestone.tasks);
}

function statusCountLabel(label, count) {
  return `${label} ${count}`;
}

function roadmapPath(view, params = {}) {
  const search = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '' && value !== 'all') {
      search.set(key, value);
    }
  });

  const query = search.toString();
  return `/roadmap/${view}${query ? `?${query}` : ''}`;
}

function sourceFocusPath(path) {
  return roadmapPath('sources', { doc: path });
}

function findTask(tasks, taskId) {
  if (!taskId) return null;
  return tasks.find((task) => task.id === taskId) ?? null;
}

function focusRing(isFocused) {
  return isFocused ? 'ring-2 ring-primary border-primary/70 bg-primary-container/20' : '';
}

function ProgressBar({ value, tone = 'doing' }) {
  const safeValue = Number.isFinite(value) ? Math.min(Math.max(value, 0), 100) : 0;
  const meta = getStatusMeta(tone);

  return (
    <div className="h-2 w-full rounded-full bg-surface-variant overflow-hidden" aria-label={`${safeValue}% complete`}>
      <div className={`h-full rounded-full ${meta.bar}`} style={{ width: `${safeValue}%` }} />
    </div>
  );
}

function StatusBadge({ status, task = false }) {
  const meta = task ? getTaskStatusMeta(status) : getStatusMeta(status);

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-none border px-2 py-1 text-xs font-semibold ${meta.badge}`}>
      <span className="material-symbols-outlined text-[16px]">{meta.icon}</span>
      {meta.label}
    </span>
  );
}

function ActionLink({ to, children, icon = 'arrow_forward' }) {
  return (
    <Link
      to={to}
      className="inline-flex items-center gap-1 rounded-none px-2 py-1 text-xs font-bold text-primary hover:bg-primary-container/40 focus:outline-none focus:ring-2 focus:ring-primary"
    >
      {children}
      <span className="material-symbols-outlined text-[14px]">{icon}</span>
    </Link>
  );
}

function MetricCard({ label, value, detail, icon, tone = 'doing', to, children }) {
  const meta = getStatusMeta(tone);
  const content = (
    <>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] uppercase tracking-[0.08em] text-on-surface-variant font-semibold">{label}</p>
          <p className="mt-2 text-2xl font-black text-on-surface">{value}</p>
        </div>
        <span className={`material-symbols-outlined text-[20px] ${meta.dot.replace('bg-', 'text-')}`}>{icon}</span>
      </div>
      <p className="mt-2 text-xs text-on-surface-variant leading-relaxed">{detail}</p>
      {children && <div className="mt-3 flex flex-wrap gap-1.5">{children}</div>}
    </>
  );

  const className = `bg-surface-container border border-outline-variant/50 border-l-4 ${meta.dot.replace('bg-', 'border-')} rounded-none p-4 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md`;

  if (to) {
    return (
      <Link
        to={to}
        className={`${className} block hover:border-primary/50 hover:bg-surface-container-high focus:outline-none focus:ring-2 focus:ring-primary`}
      >
        {content}
      </Link>
    );
  }

  return (
    <div className={className}>
      {content}
    </div>
  );
}

function SourceList({ docs }) {
  if (!docs?.length) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {docs.map((doc) => (
        <Link
          key={doc}
          to={sourceFocusPath(doc)}
          className="inline-flex items-center gap-1 rounded-none border border-outline-variant/50 bg-surface-container-high px-2 py-1 text-xs text-on-surface-variant font-data-mono break-all hover:border-primary/50 hover:text-primary"
        >
          {doc}
          <span className="material-symbols-outlined text-[13px]">pageview</span>
        </Link>
      ))}
    </div>
  );
}

function MilestoneModal({ milestone, area, onClose }) {
  if (!milestone) return null;

  const progress = taskProgress(milestone.tasks);
  const counts = countBy(milestone.tasks, TASK_STATUS_ORDER);

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/70 p-4">
      <div
        className="w-full max-w-4xl max-h-[88vh] overflow-y-auto rounded-none border border-outline-variant/70 bg-surface-container shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-labelledby="roadmap-milestone-title"
      >
        <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-outline-variant/50 bg-surface-container px-5 py-4">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge status={milestone.status} />
              <span className="text-sm text-on-surface-variant">{area?.name}</span>
            </div>
            <h2 id="roadmap-milestone-title" className="mt-3 text-2xl font-black text-on-surface leading-tight">
              {milestone.name}
            </h2>
          </div>
          <button
            type="button"
            className="rounded-none p-2 text-on-surface-variant hover:bg-surface-variant hover:text-on-surface"
            onClick={onClose}
            aria-label="Close milestone details"
          >
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        <div className="p-5 space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-[1.2fr_0.8fr] gap-5">
            <section className="space-y-4">
              <div>
                <p className="text-xs uppercase tracking-[0.08em] text-on-surface-variant font-semibold">Stakeholder outcome</p>
                <p className="mt-2 text-base text-on-surface leading-relaxed">{milestone.stakeholderOutcome}</p>
              </div>
              <SourceList docs={milestone.sourceDocs} />
            </section>

            <section className="rounded-none border border-outline-variant/50 bg-surface-container-low p-4 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <p className="text-xs text-on-surface-variant uppercase tracking-[0.08em] font-semibold">Timeframe</p>
                  <p className="mt-1 text-sm text-on-surface">{milestone.timeframe}</p>
                </div>
                <div>
                  <p className="text-xs text-on-surface-variant uppercase tracking-[0.08em] font-semibold">Owner</p>
                  <p className="mt-1 text-sm text-on-surface">{milestone.owner}</p>
                </div>
              </div>
              <div>
                <div className="mb-2 flex items-center justify-between gap-3">
                  <span className="text-xs uppercase tracking-[0.08em] text-on-surface-variant font-semibold">Task completion</span>
                  <span className="text-sm font-data-mono text-on-surface">{progress}%</span>
                </div>
                <ProgressBar value={progress} tone={milestone.status} />
              </div>
              <div className="grid grid-cols-3 gap-2">
                {TASK_STATUS_ORDER.map((status) => (
                  <div key={status} className="rounded-none bg-surface-container p-3 border border-outline-variant/30">
                    <p className="text-lg font-black text-on-surface">{counts[status]}</p>
                    <p className="text-xs text-on-surface-variant">{getTaskStatusMeta(status).label}</p>
                  </div>
                ))}
              </div>
            </section>
          </div>

          <section>
            <div className="mb-3 flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-[20px]">checklist</span>
              <h3 className="text-lg font-bold text-on-surface">Tasks</h3>
            </div>
            <div className="space-y-3">
              {milestone.tasks.map((task) => (
                <article key={task.id} className="rounded-none border border-outline-variant/50 bg-surface-container-low p-4">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <StatusBadge status={task.status} task />
                        <span className="text-xs text-on-surface-variant">{task.timeframe}</span>
                      </div>
                      <p className="mt-3 text-base font-semibold text-on-surface leading-snug">{task.label}</p>
                      {task.notes && (
                        <p className="mt-2 text-sm text-on-surface-variant leading-relaxed">{task.notes}</p>
                      )}
                    </div>
                    <div className="flex shrink-0 flex-wrap gap-2">
                      <Link
                        to={roadmapPath('tasks', { milestone: milestone.id, task: task.id, status: task.status })}
                        onClick={onClose}
                        className="inline-flex items-center gap-1 rounded-none border border-outline-variant/60 px-3 py-1.5 text-xs font-bold text-primary hover:bg-primary-container/40"
                      >
                        <span className="material-symbols-outlined text-[15px]">checklist</span>
                        Task list
                      </Link>
                      <Link
                        to={roadmapPath('board', { status: task.status, task: task.id })}
                        onClick={onClose}
                        className="inline-flex items-center gap-1 rounded-none border border-outline-variant/60 px-3 py-1.5 text-xs font-bold text-primary hover:bg-primary-container/40"
                      >
                        <span className="material-symbols-outlined text-[15px]">view_kanban</span>
                        Board
                      </Link>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function RoadmapShell({ roadmap, children }) {
  return (
    <div className="min-h-screen bg-background text-on-background flex flex-col overflow-hidden lg:flex-row">
      {/* Context Sidebar */}
      <aside className="w-full border-b border-outline-variant/50 bg-surface-container shrink-0 flex flex-col lg:h-screen lg:w-56 lg:sticky lg:top-0 lg:border-b-0 lg:border-r">
        <div className="p-3 border-b border-outline-variant/50 shrink-0">
          <div className="flex items-center gap-2">
            <Link
              to="/"
              className="rounded-none p-1 hover:bg-surface-variant focus:outline-none focus:ring-2 focus:ring-primary"
              aria-label="Go to home dashboard"
            >
              <BrandMark />
            </Link>
            <div className="min-w-0">
              <p className="text-[9px] font-semibold uppercase tracking-[0.08em] text-on-surface-variant">Planning workspace</p>
              <h1 className="truncate text-sm font-black text-on-surface">{roadmap.title}</h1>
            </div>
          </div>
        </div>

        <nav className="flex gap-2 overflow-x-auto p-3 lg:block lg:flex-1 lg:space-y-1 lg:overflow-y-auto">
          {ROADMAP_VIEWS.map((view) => (
            <NavLink
              key={view.id}
              to={view.path}
              className={({ isActive }) => `flex items-center gap-2.5 rounded-none px-3 py-2 text-xs font-semibold transition-colors ${isActive
                ? 'bg-primary-container text-primary'
                : 'text-on-surface-variant hover:bg-surface-variant hover:text-on-surface'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">{view.icon}</span>
              {view.label}
            </NavLink>
          ))}
        </nav>

        <div className="hidden p-4 border-t border-outline-variant/50 shrink-0 lg:block">
          <Link
            to="/dashboard"
            className="flex items-center justify-center gap-2 rounded-none border border-outline-variant/60 px-4 py-2 text-sm font-bold text-primary hover:bg-primary-container/40"
          >
            <span className="material-symbols-outlined text-[18px]">dashboard</span>
            Ops Dashboard
          </Link>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto lg:h-screen">
        <div className="mx-auto max-w-[1500px] px-4 py-6 sm:px-6 lg:py-8">
          {children}
        </div>
      </main>
    </div>
  );
}

function PageIntro({ eyebrow, title, description, children }) {
  return (
    <div className="mb-6 flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
      <div className="max-w-5xl">
        <p className="text-xs font-semibold uppercase tracking-[0.08em] text-on-surface-variant">{eyebrow}</p>
        <h2 className="mt-2 text-3xl font-black tracking-tight text-on-surface sm:text-4xl">{title}</h2>
        <p className="mt-3 max-w-4xl text-base leading-relaxed text-on-surface-variant">{description}</p>
      </div>
      {children}
    </div>
  );
}

function OverviewView({
  roadmap,
  milestones,
  taskCounts,
  milestoneCounts,
  tasks,
  activeMilestone,
  activeTasks,
  statusFilter,
  onStatusFilterChange,
  progressChartRef,
  progressChartData,
  progressChartOptions,
  handleProgressChartClick,
  statusChartRef,
  statusChartData,
  statusChartOptions,
  handleStatusChartClick,
}) {
  const totalProgress = taskProgress(tasks);

  return (
    <>
      <PageIntro
        eyebrow="Stakeholder roadmap"
        title="One planning source for done, doing, and backlog work"
        description={roadmap.publicAudience}
      >
        <div className="rounded-none border border-outline-variant/50 bg-surface-container px-4 py-3 text-sm text-on-surface-variant xl:max-w-md">
          <div className="flex items-center gap-2 text-on-surface">
            <span className="material-symbols-outlined text-primary text-[20px]">lock</span>
            <span className="font-bold">Edit policy</span>
          </div>
          <p className="mt-2 leading-relaxed">{roadmap.sourceOfTruth.writePolicy}</p>
        </div>
      </PageIntro>

      <div className="mb-6 grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Milestones complete"
          value={`${milestoneCounts.completed}/${milestones.length}`}
          detail={`${milestoneCounts.doing} active and ${milestoneCounts.backlog} in backlog.`}
          icon="flag"
          tone="completed"
          to={roadmapPath('tasks', { milestoneStatus: 'completed' })}
        />
        <MetricCard
          label="Task completion"
          value={`${totalProgress}%`}
          detail={`${taskCounts.done} done, ${taskCounts.doing} doing, ${taskCounts.todo} to do.`}
          icon="checklist"
          tone="doing"
        >
          {TASK_STATUS_ORDER.map((status) => (
            <ActionLink key={status} to={roadmapPath('board', { status })}>
              {statusCountLabel(getTaskStatusMeta(status).label, taskCounts[status])}
            </ActionLink>
          ))}
        </MetricCard>
        <MetricCard
          label="Current focus"
          value={activeMilestone ? activeMilestone.name : 'No active milestone'}
          detail={activeMilestone ? `${activeMilestone.areaName} · ${activeMilestone.timeframe}` : 'All active work is waiting for assignment.'}
          icon="target"
          tone="doing"
          to={activeMilestone ? roadmapPath('tasks', { milestone: activeMilestone.id, milestoneStatus: activeMilestone.status }) : undefined}
        />
        <MetricCard
          label="Master source"
          value={roadmap.sourceOfTruth.currentMode}
          detail={roadmap.sourceOfTruth.publicReadPath}
          icon="cloud_done"
          tone="backlog"
          to={roadmapPath('sources')}
        />
      </div>

      {activeTasks.length > 0 && (
        <section className="mb-6 rounded-none border border-outline-variant/50 bg-surface-container p-4 shadow-sm">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-[20px]">bolt</span>
                <h2 className="text-lg font-bold text-on-surface">Now</h2>
              </div>
              <p className="mt-1 text-sm text-on-surface-variant">Active tasks that need the clearest next action.</p>
            </div>
            <Link
              to={roadmapPath('board', { status: 'doing' })}
              className="inline-flex items-center justify-center gap-2 rounded-none border border-outline-variant/60 px-4 py-2 text-sm font-bold text-primary hover:bg-primary-container/40"
            >
              <span className="material-symbols-outlined text-[18px]">view_kanban</span>
              Open doing board
            </Link>
          </div>
          <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-3">
            {activeTasks.slice(0, 3).map((task) => (
              <Link
                key={task.id}
                to={roadmapPath('board', { status: task.status, task: task.id })}
                className="rounded-none border border-outline-variant/50 bg-surface-container-low p-3 hover:border-primary/50 hover:bg-surface-variant"
              >
                <p className="text-xs font-semibold uppercase text-on-surface-variant">{task.milestoneName}</p>
                <p className="mt-1 text-sm font-bold leading-snug text-on-surface">{task.label}</p>
              </Link>
            ))}
          </div>
        </section>
      )}

      <div className="mb-6 grid grid-cols-1 gap-6 xl:grid-cols-[1.25fr_0.75fr]">
        <section className="rounded-none border border-outline-variant/50 bg-surface-container p-5 shadow-sm">
          <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-bold text-on-surface">Roadmap Progress</h2>
              <p className="mt-1 text-sm text-on-surface-variant">Level-one areas by task completion.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {['all', ...AREA_STATUS_ORDER].map((status) => {
                const active = statusFilter === status;
                const label = status === 'all' ? 'All' : getStatusMeta(status).label;
                return (
                  <button
                    type="button"
                    key={status}
                    className={`rounded-none border px-3 py-2 text-sm font-semibold transition-colors ${active
                      ? 'border-primary bg-primary-container text-primary'
                      : 'border-outline-variant/60 bg-surface-container-low text-on-surface-variant hover:bg-surface-variant hover:text-on-surface'
                    }`}
                    onClick={() => onStatusFilterChange(status)}
                  >
                    {status === 'all' ? label : statusCountLabel(label, milestoneCounts[status])}
                  </button>
                );
              })}
            </div>
          </div>
          <div className="h-[280px]">
            <Bar ref={progressChartRef} data={progressChartData} options={progressChartOptions} onClick={handleProgressChartClick} />
          </div>
        </section>

        <section className="rounded-none border border-outline-variant/50 bg-surface-container p-5 shadow-sm">
          <div className="mb-5">
            <h2 className="text-lg font-bold text-on-surface">Milestone Mix</h2>
            <p className="mt-1 text-sm text-on-surface-variant">Completed, doing, and backlog milestones.</p>
          </div>
          <div className="h-[220px]">
            <Doughnut ref={statusChartRef} data={statusChartData} options={statusChartOptions} onClick={handleStatusChartClick} />
          </div>
          <div className="mt-5 grid grid-cols-3 gap-2">
            {AREA_STATUS_ORDER.map((status) => (
              <button
                type="button"
                key={status}
                className="rounded-none border border-outline-variant/50 bg-surface-container-low p-3 text-left hover:bg-surface-variant"
                onClick={() => onStatusFilterChange(status)}
              >
                <div className="flex items-center gap-2">
                  <span className={`h-2.5 w-2.5 rounded-full ${getStatusMeta(status).dot}`} />
                  <span className="text-xs text-on-surface-variant">{getStatusMeta(status).label}</span>
                </div>
                <p className="mt-2 text-xl font-black text-on-surface">{milestoneCounts[status]}</p>
              </button>
            ))}
          </div>
        </section>
      </div>
    </>
  );
}

function TasksView({ milestones, tasks, onOpenMilestone }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [searchTerm, setSearchTerm] = useState('');

  const milestoneFilter = searchParams.get('milestoneStatus') ?? 'all';
  const areaFilter = searchParams.get('area') ?? 'all';
  const taskFilter = searchParams.get('status') ?? 'all';
  const focusedTaskId = searchParams.get('task') ?? '';
  const requestedMilestoneId = searchParams.get('milestone') ?? '';
  const focusedTask = findTask(tasks, focusedTaskId);
  const selectedMilestoneId = requestedMilestoneId || focusedTask?.milestoneId || '';

  const visibleMilestones = milestones.filter((milestone) => {
    const matchesStatus = milestoneFilter === 'all' || milestone.status === milestoneFilter;
    const matchesArea = areaFilter === 'all' || milestone.areaId === areaFilter;
    return matchesStatus && matchesArea;
  });

  const selectedMilestone = visibleMilestones.find((m) => m.id === selectedMilestoneId) || visibleMilestones[0];
  const normalizedSearch = searchTerm.trim().toLowerCase();

  const visibleTasks = selectedMilestone
    ? selectedMilestone.tasks.filter((task) => {
      const matchesStatus = taskFilter === 'all' || task.status === taskFilter;
      const searchable = [
        task.label,
        task.notes,
        selectedMilestone.name,
        selectedMilestone.areaName,
      ].filter(Boolean).join(' ').toLowerCase();
      const matchesSearch = !normalizedSearch || searchable.includes(normalizedSearch);
      return matchesStatus && matchesSearch;
    })
    : [];

  const milestoneCounts = countBy(milestones, AREA_STATUS_ORDER);
  const selectedMilestoneTaskCounts = selectedMilestone ? countBy(selectedMilestone.tasks, TASK_STATUS_ORDER) : countBy([], TASK_STATUS_ORDER);

  useEffect(() => {
    if (!focusedTaskId) return;
    document.getElementById(`roadmap-task-${focusedTaskId}`)?.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }, [focusedTaskId, selectedMilestone?.id, taskFilter]);

  function updateTaskParams(next = {}) {
    const params = {
      milestoneStatus: milestoneFilter,
      area: areaFilter,
      status: taskFilter,
      milestone: selectedMilestone?.id,
      ...next,
    };
    navigate(roadmapPath('tasks', params));
  }

  return (
    <>
      <PageIntro
        eyebrow="Task directory"
        title="Tasks organized by milestone"
        description="Select a milestone, search across task text, or use a deep link from the overview and board to land on exact work."
      >
        <div className="flex w-full flex-col gap-2 sm:w-auto">
          <label className="text-xs font-semibold uppercase tracking-[0.08em] text-on-surface-variant" htmlFor="roadmap-task-search">
            Search tasks
          </label>
          <div className="flex items-center gap-2 rounded-none border border-outline-variant/60 bg-surface-container px-3 py-2">
            <span className="material-symbols-outlined text-[18px] text-on-surface-variant">search</span>
            <input
              id="roadmap-task-search"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Task, note, milestone, area"
              className="w-64 bg-transparent text-sm text-on-surface placeholder:text-on-surface-variant focus:outline-none"
            />
          </div>
        </div>
      </PageIntro>
      <div className="flex h-[calc(100vh-14rem)] bg-surface-container border border-outline-variant/50 rounded-none overflow-hidden shadow-sm">
        {/* Sidebar for milestones */}
        <div className="w-72 border-r border-outline-variant/50 bg-surface-container-low flex flex-col shrink-0">
          <div className="p-4 border-b border-outline-variant/50 bg-surface-container shrink-0">
            <h2 className="font-bold text-on-surface mb-3">Milestones</h2>
            <div className="flex flex-wrap gap-1.5">
              {['all', ...AREA_STATUS_ORDER].map((status) => {
                const active = milestoneFilter === status;
                const label = status === 'all' ? 'All' : getStatusMeta(status).label;
                return (
                  <button
                    key={status}
                    onClick={() => updateTaskParams({ milestoneStatus: status, milestone: null, task: null })}
                    className={`px-2 py-1 text-xs font-semibold rounded-none transition-colors ${
                      active ? 'bg-primary-container text-primary' : 'bg-surface-container border border-outline-variant/50 text-on-surface-variant hover:text-on-surface'
                    }`}
                  >
                    {status === 'all' ? label : statusCountLabel(label, milestoneCounts[status])}
                  </button>
                );
              })}
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {visibleMilestones.length > 0 ? (
              visibleMilestones.map((milestone) => {
                const active = selectedMilestone?.id === milestone.id;
                const progress = taskProgress(milestone.tasks);
                return (
                  <button
                    key={milestone.id}
                    onClick={() => updateTaskParams({ milestone: milestone.id, task: null })}
                    className={`w-full text-left p-3 rounded-none border transition-colors flex flex-col gap-2 ${
                      active
                        ? 'bg-primary-container/40 border-primary/30 text-on-surface'
                        : 'bg-surface-container border-outline-variant/30 hover:bg-surface-variant text-on-surface-variant'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <StatusBadge status={milestone.status} />
                      <span className="text-xs truncate">{milestone.areaName}</span>
                    </div>
                    <h3 className="text-sm font-bold leading-tight mt-1 text-on-surface">{milestone.name}</h3>
                    <div className="mt-2 flex items-center justify-between gap-3 opacity-80">
                      <ProgressBar value={progress} tone={milestone.status} />
                      <span className="text-[10px] font-data-mono">{progress}%</span>
                    </div>
                  </button>
                );
              })
            ) : (
              <p className="text-center text-sm text-on-surface-variant py-8">No milestones match the filter.</p>
            )}
          </div>
        </div>

        {/* Main content for tasks */}
        <div className="flex-1 flex flex-col min-w-0 bg-background">
          {selectedMilestone ? (
            <>
              <div className="p-6 border-b border-outline-variant/50 shrink-0">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-[0.08em] text-on-surface-variant mb-2">
                      {selectedMilestone.areaName} · {selectedMilestone.timeframe}
                    </p>
                    <h1 className="text-2xl font-black text-on-surface leading-tight">{selectedMilestone.name}</h1>
                    <p className="mt-3 text-sm text-on-surface-variant leading-relaxed max-w-2xl">{selectedMilestone.stakeholderOutcome}</p>
                  </div>
                  <button
                    className="shrink-0 flex items-center gap-2 rounded-none border border-outline-variant/60 px-4 py-2 text-sm font-semibold text-primary hover:bg-primary-container/40"
                    onClick={() => onOpenMilestone(selectedMilestone)}
                  >
                    <span className="material-symbols-outlined text-[18px]">open_in_full</span>
                    Milestone Details
                  </button>
                </div>

                <div className="mt-6 flex flex-wrap gap-2">
                  {['all', ...TASK_STATUS_ORDER].map((status) => {
                    const active = taskFilter === status;
                    const label = status === 'all' ? 'All tasks' : getTaskStatusMeta(status).label;
                    return (
                      <button
                        key={status}
                        onClick={() => updateTaskParams({ status, task: null })}
                        className={`px-3 py-1.5 text-xs font-semibold rounded-none transition-colors border ${
                          active ? 'bg-secondary-container border-secondary/40 text-on-secondary-container' : 'bg-surface-container-low border-outline-variant/50 text-on-surface-variant hover:bg-surface-variant hover:text-on-surface'
                        }`}
                      >
                        {status === 'all' ? label : statusCountLabel(label, selectedMilestoneTaskCounts[status])}
                      </button>
                    );
                  })}
                  {(taskFilter !== 'all' || milestoneFilter !== 'all' || areaFilter !== 'all' || focusedTaskId || searchTerm) && (
                    <button
                      type="button"
                      onClick={() => {
                        setSearchTerm('');
                        navigate(roadmapPath('tasks', { milestone: selectedMilestone.id }));
                      }}
                      className="px-3 py-1.5 text-xs font-semibold rounded-none transition-colors border border-outline-variant/50 bg-surface-container-low text-on-surface-variant hover:bg-surface-variant hover:text-on-surface"
                    >
                      Clear filters
                    </button>
                  )}
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-6">
                <div className="max-w-4xl space-y-4">
                  {visibleTasks.length > 0 ? (
                    visibleTasks.map((task) => {
                      const isFocused = task.id === focusedTaskId;
                      return (
                      <article
                        key={task.id}
                        id={`roadmap-task-${task.id}`}
                        className={`rounded-none border border-outline-variant/50 border-l-4 ${getTaskStatusMeta(task.status).dot.replace('bg-', 'border-')} bg-surface-container-low p-5 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md ${focusRing(isFocused)}`}
                      >
                        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                          <div className="flex items-start gap-4">
                          <span className={`material-symbols-outlined mt-0.5 text-[24px] ${getTaskStatusMeta(task.status).dot.replace('bg-', 'text-')}`}>
                            {getTaskStatusMeta(task.status).icon}
                          </span>
                          <div>
                            <div className="flex items-center gap-2 mb-2">
                              <StatusBadge status={task.status} task />
                              <span className="text-xs font-semibold uppercase text-on-surface-variant">{task.timeframe}</span>
                              {isFocused && (
                                <span className="inline-flex items-center gap-1 rounded-none bg-primary-container px-2 py-1 text-xs font-bold text-primary">
                                  <span className="material-symbols-outlined text-[14px]">my_location</span>
                                  Focused
                                </span>
                              )}
                            </div>
                            <p className="text-base font-bold text-on-surface leading-snug">{task.label}</p>
                            {task.notes && (
                              <p className="mt-2 text-sm text-on-surface-variant leading-relaxed">{task.notes}</p>
                            )}
                          </div>
                        </div>
                          <div className="flex shrink-0 flex-wrap gap-2 lg:justify-end">
                            <button
                              type="button"
                              onClick={() => onOpenMilestone(selectedMilestone)}
                              className="inline-flex items-center gap-1 rounded-none border border-outline-variant/60 px-3 py-1.5 text-xs font-bold text-primary hover:bg-primary-container/40"
                            >
                              <span className="material-symbols-outlined text-[15px]">open_in_full</span>
                              Milestone
                            </button>
                            <Link
                              to={roadmapPath('board', { status: task.status, task: task.id })}
                              className="inline-flex items-center gap-1 rounded-none border border-outline-variant/60 px-3 py-1.5 text-xs font-bold text-primary hover:bg-primary-container/40"
                            >
                              <span className="material-symbols-outlined text-[15px]">view_kanban</span>
                              Board
                            </Link>
                          </div>
                        </div>
                      </article>
                      );
                    })
                  ) : (
                    <div className="rounded-none border border-dashed border-outline-variant/60 p-8 text-center">
                      <span className="material-symbols-outlined text-4xl text-on-surface-variant/50 mb-2">task</span>
                      <p className="text-on-surface-variant">No tasks match the selected filter for this milestone.</p>
                      <button
                        type="button"
                        onClick={() => {
                          setSearchTerm('');
                          navigate(roadmapPath('tasks', { milestone: selectedMilestone.id }));
                        }}
                        className="mt-4 rounded-none border border-outline-variant/60 px-4 py-2 text-sm font-bold text-primary hover:bg-primary-container/40"
                      >
                        Clear filters
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center h-full text-on-surface-variant">
              Select a milestone to view tasks.
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function KanbanBoardView({ tasks, milestones, onOpenMilestone }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const selectedStatus = searchParams.get('status') ?? 'all';
  const focusedTaskId = searchParams.get('task') ?? '';

  const tasksByStatus = TASK_STATUS_ORDER.reduce((columns, status) => {
    columns[status] = tasks.filter((task) => task.status === status);
    return columns;
  }, {});

  const visibleStatuses = selectedStatus === 'all' || !TASK_STATUS_ORDER.includes(selectedStatus)
    ? TASK_STATUS_ORDER
    : [selectedStatus];

  useEffect(() => {
    if (!focusedTaskId) return;
    document.getElementById(`roadmap-board-task-${focusedTaskId}`)?.scrollIntoView({ block: 'center', inline: 'center', behavior: 'smooth' });
  }, [focusedTaskId, selectedStatus]);

  return (
    <>
      <PageIntro
        eyebrow="Kanban board"
        title="Task buckets for done, doing, and to do"
        description="This view is shaped for delivery work: each task stays connected to its milestone, area, timeframe, and source-backed notes."
      >
        <div className="flex flex-wrap gap-2">
          {['all', ...TASK_STATUS_ORDER].map((status) => {
            const active = selectedStatus === status;
            const label = status === 'all' ? 'All tasks' : getTaskStatusMeta(status).label;
            const count = status === 'all' ? tasks.length : tasksByStatus[status].length;
            return (
              <button
                type="button"
                key={status}
                onClick={() => navigate(roadmapPath('board', { status }))}
                className={`rounded-none border px-3 py-2 text-sm font-semibold transition-colors ${active
                  ? 'border-primary bg-primary-container text-primary'
                  : 'border-outline-variant/60 bg-surface-container-low text-on-surface-variant hover:bg-surface-variant hover:text-on-surface'
                }`}
              >
                {statusCountLabel(label, count)}
              </button>
            );
          })}
        </div>
      </PageIntro>

      <div className="flex gap-4 overflow-x-auto pb-4 h-[calc(100vh-12rem)] snap-x">
        {visibleStatuses.map((status) => {
          const meta = getTaskStatusMeta(status);
          return (
            <section key={status} className="w-80 min-w-[320px] flex-none flex flex-col rounded-none border border-outline-variant/50 bg-surface-container p-3 shadow-sm snap-start">
              <div className="mb-4 flex items-center justify-between gap-3 shrink-0">
                <div className="flex items-center gap-2">
                  <span className={`h-2.5 w-2.5 rounded-full ${meta.dot}`} />
                  <h2 className="text-sm font-bold uppercase tracking-wide text-on-surface">{meta.label}</h2>
                </div>
                <span className="rounded-none border border-outline-variant/50 bg-surface-container-high px-2 py-1 font-data-mono text-[10px] text-on-surface">
                  {tasksByStatus[status].length}
                </span>
              </div>

              <div className="flex-1 overflow-y-auto space-y-3 pr-1">
                {tasksByStatus[status].map((task) => {
                  const milestone = milestones.find((item) => item.id === task.milestoneId);
                  const isFocused = task.id === focusedTaskId;
                  return (
                    <article
                      key={task.id}
                      id={`roadmap-board-task-${task.id}`}
                      className={`rounded-none border border-outline-variant/50 border-l-4 ${getTaskStatusMeta(task.status).dot.replace('bg-', 'border-')} bg-surface-container-low p-3 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md ${focusRing(isFocused)}`}
                    >
                      <div className="flex flex-wrap items-center gap-2 mb-1.5">
                        <StatusBadge status={task.status} task />
                        <span className="text-[10px] uppercase font-semibold text-on-surface-variant">{task.timeframe}</span>
                        {isFocused && (
                          <span className="inline-flex items-center gap-1 rounded-none bg-primary-container px-2 py-1 text-[10px] font-bold text-primary">
                            <span className="material-symbols-outlined text-[12px]">my_location</span>
                            Focused
                          </span>
                        )}
                      </div>
                      <h3 className="text-sm font-bold leading-snug text-on-surface">{task.label}</h3>
                      <div className="mt-3 flex items-center justify-between border-t border-outline-variant/40 pt-2">
                        <div className="min-w-0 pr-2">
                          <p className="text-[10px] font-semibold text-on-surface truncate">{task.milestoneName}</p>
                        </div>
                        <button
                          type="button"
                          className="shrink-0 text-[10px] font-semibold text-primary hover:text-secondary flex items-center gap-0.5"
                          onClick={() => milestone && onOpenMilestone(milestone)}
                          aria-label="Open milestone"
                        >
                          <span className="material-symbols-outlined text-[14px]">open_in_full</span>
                        </button>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <Link
                          to={roadmapPath('tasks', { milestone: task.milestoneId, task: task.id, status: task.status })}
                          className="inline-flex items-center gap-1 rounded-none border border-outline-variant/50 px-2 py-1 text-[10px] font-bold text-primary hover:bg-primary-container/40"
                        >
                          <span className="material-symbols-outlined text-[13px]">checklist</span>
                          Task list
                        </Link>
                        <button
                          type="button"
                          onClick={() => navigate(roadmapPath('board', { status: task.status, task: task.id }))}
                          className="inline-flex items-center gap-1 rounded-none border border-outline-variant/50 px-2 py-1 text-[10px] font-bold text-primary hover:bg-primary-container/40"
                        >
                          <span className="material-symbols-outlined text-[13px]">link</span>
                          Focus
                        </button>
                      </div>
                    </article>
                  );
                })}
                {tasksByStatus[status].length === 0 && (
                  <div className="rounded-none border border-dashed border-outline-variant/60 p-6 text-center text-sm text-on-surface-variant">
                    No tasks in this column.
                  </div>
                )}
              </div>
            </section>
          );
        })}
      </div>
    </>
  );
}

function SourcesAdminView({ roadmap }) {
  const [searchParams] = useSearchParams();
  const focusedDoc = searchParams.get('doc') ?? '';

  return (
    <>
      <PageIntro
        eyebrow="Sources and controls"
        title="Where the plan comes from and who can change it"
        description="The roadmap is public for stakeholders, but write access remains controlled through code review today and an audited serverless admin path later."
      />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1fr_1fr]">
        <section className="rounded-none border border-outline-variant/50 bg-surface-container p-5 shadow-sm">
          <div className="mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[20px]">storage</span>
            <h2 className="text-lg font-bold text-on-surface">Storage and Control Plane</h2>
          </div>
          <div className="space-y-4 text-sm leading-relaxed">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.08em] text-on-surface-variant">Current source</p>
              <p className="mt-1 font-data-mono text-on-surface-variant break-all">{roadmap.sourceOfTruth.currentPath}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.08em] text-on-surface-variant">Public read path</p>
              <p className="mt-1 text-on-surface">{roadmap.sourceOfTruth.publicReadPath}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.08em] text-on-surface-variant">Authorized admin path</p>
              <p className="mt-1 text-on-surface">{roadmap.sourceOfTruth.authorizedAdminPath}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.08em] text-on-surface-variant">Write policy</p>
              <p className="mt-1 text-on-surface">{roadmap.sourceOfTruth.writePolicy}</p>
            </div>
          </div>
        </section>

        <section className="rounded-none border border-outline-variant/50 bg-surface-container p-5 shadow-sm">
          <div className="mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-[20px]">rule</span>
            <h2 className="text-lg font-bold text-on-surface">Status Definitions</h2>
          </div>
          <div className="space-y-3">
            {AREA_STATUS_ORDER.map((status) => (
              <div key={status} className="rounded-none border border-outline-variant/40 bg-surface-container-low p-3">
                <div className="mb-1 flex items-center gap-2">
                  <StatusBadge status={status} />
                </div>
                <p className="text-sm leading-relaxed text-on-surface-variant">{roadmap.statusDefinitions[status]}</p>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="mt-6 rounded-none border border-outline-variant/50 bg-surface-container p-5 shadow-sm">
        <div className="mb-4 flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-[20px]">description</span>
          <h2 className="text-lg font-bold text-on-surface">Planning Inputs</h2>
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {roadmap.sourceDocuments.map((doc) => (
            <Link
              key={doc.path}
              to={"/" + doc.path.replace('.md', '')}
              className={`rounded-none border border-outline-variant/40 bg-surface-container-low p-3 hover:border-primary/50 hover:bg-surface-variant transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-bold text-on-surface">{doc.label}</p>
                  <p className="mt-1 break-all font-data-mono text-xs text-on-surface-variant">{doc.path}</p>
                </div>
                <span className="material-symbols-outlined shrink-0 text-[16px] text-primary">pageview</span>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </>
  );
}

export default function RoadmapDashboard() {
  const { view } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { roadmap, loading, error, url } = useRoadmap();
  const [selectedMilestone, setSelectedMilestone] = useState(null);
  const progressChartRef = useRef(null);
  const statusChartRef = useRef(null);
  const statusFilter = searchParams.get('status') ?? 'all';

  const areas = useMemo(() => roadmap?.areas ?? [], [roadmap]);
  const visibleAreas = useMemo(() => (
    statusFilter === 'all'
      ? areas
      : areas.filter((area) => area.status === statusFilter || area.milestones.some((milestone) => milestone.status === statusFilter))
  ), [areas, statusFilter]);

  const milestones = useMemo(() => flattenMilestones(areas), [areas]);
  const tasks = useMemo(() => flattenTasks(milestones), [milestones]);
  const milestoneCounts = useMemo(() => countBy(milestones, AREA_STATUS_ORDER), [milestones]);
  const taskCounts = useMemo(() => countBy(tasks, TASK_STATUS_ORDER), [tasks]);
  const selectedArea = selectedMilestone ? areas.find((area) => area.id === selectedMilestone.areaId) : null;
  const activeMilestone = milestones.find((milestone) => milestone.status === 'doing');
  const activeTasks = tasks.filter((task) => task.status === 'doing');

  const progressChartData = useMemo(() => ({
    labels: visibleAreas.map((area) => area.name),
    datasets: [
      {
        label: 'Task completion',
        data: visibleAreas.map((area) => taskProgress(areaTasks(area))),
        backgroundColor: visibleAreas.map((area) => getStatusMeta(area.status).chart),
        borderColor: '#45474d',
        borderWidth: 1,
        borderRadius: 6,
      },
    ],
  }), [visibleAreas]);

  const statusChartData = useMemo(() => ({
    labels: AREA_STATUS_ORDER.map((status) => getStatusMeta(status).label),
    datasets: [
      {
        data: AREA_STATUS_ORDER.map((status) => milestoneCounts[status]),
        backgroundColor: AREA_STATUS_ORDER.map((status) => getStatusMeta(status).chart),
        borderColor: '#1e201e',
        borderWidth: 3,
      },
    ],
  }), [milestoneCounts]);

  const progressChartOptions = {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (context) => `${context.parsed.x}% complete`,
        },
      },
    },
    scales: {
      x: {
        min: 0,
        max: 100,
        grid: { color: 'rgba(143, 144, 151, 0.18)' },
        ticks: { color: '#c5c6cd' },
      },
      y: {
        grid: { display: false },
        ticks: { color: '#c5c6cd' },
      },
    },
  };

  const statusChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          color: '#c5c6cd',
          boxWidth: 12,
          boxHeight: 12,
        },
      },
    },
  };

  function handleProgressChartClick(event) {
    const chart = progressChartRef.current;
    if (!chart) return;
    const [element] = getElementAtEvent(chart, event);
    if (!element) return;
    const area = visibleAreas[element.index];
    if (!area) return;
    navigate(roadmapPath('tasks', { area: area.id, milestoneStatus: statusFilter }));
  }

  function handleStatusChartClick(event) {
    const chart = statusChartRef.current;
    if (!chart) return;
    const [element] = getElementAtEvent(chart, event);
    if (!element) return;
    navigate(roadmapPath('overview', { status: AREA_STATUS_ORDER[element.index] ?? 'all' }));
  }

  function updateOverviewStatus(status) {
    navigate(roadmapPath('overview', { status }));
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background text-on-surface-variant">
        <div className="flex items-center gap-3">
          <span className="h-2.5 w-2.5 rounded-full bg-primary animate-pulse" />
          Loading roadmap…
        </div>
      </div>
    );
  }

  if (error || !roadmap) {
    return (
      <div className="min-h-screen bg-background p-6 text-on-background">
        <div className="mx-auto max-w-3xl rounded-none border border-error/50 bg-error-container/20 p-6 text-on-error-container">
          <div className="flex items-center gap-2 font-bold">
            <span className="material-symbols-outlined">error</span>
            Roadmap could not be loaded
          </div>
          <p className="mt-3 text-sm">Checked {url}. The bundled roadmap fallback was not available.</p>
        </div>
      </div>
    );
  }

  const currentView = view ?? 'overview';
  if (!ROADMAP_VIEWS.some((item) => item.id === currentView)) {
    return <Navigate to="/roadmap" replace />;
  }

  function openMilestone(milestone) {
    setSelectedMilestone(milestone);
  }

  const viewContent = {
    overview: (
      <OverviewView
        roadmap={roadmap}
        milestones={milestones}
        taskCounts={taskCounts}
        milestoneCounts={milestoneCounts}
        tasks={tasks}
        activeMilestone={activeMilestone}
        activeTasks={activeTasks}
        visibleAreas={visibleAreas}
        statusFilter={statusFilter}
        onStatusFilterChange={updateOverviewStatus}
        progressChartRef={progressChartRef}
        progressChartData={progressChartData}
        progressChartOptions={progressChartOptions}
        handleProgressChartClick={handleProgressChartClick}
        statusChartRef={statusChartRef}
        statusChartData={statusChartData}
        statusChartOptions={statusChartOptions}
        handleStatusChartClick={handleStatusChartClick}
      />
    ),
    tasks: (
      <TasksView
        milestones={milestones}
        tasks={tasks}
        onOpenMilestone={openMilestone}
      />
    ),
    board: (
      <KanbanBoardView
        tasks={tasks}
        milestones={milestones}
        onOpenMilestone={openMilestone}
      />
    ),
    sources: <SourcesAdminView roadmap={roadmap} />,
  };

  return (
    <RoadmapShell roadmap={roadmap}>
      {viewContent[currentView]}
      <MilestoneModal
        milestone={selectedMilestone}
        area={selectedArea}
        onClose={() => setSelectedMilestone(null)}
      />
    </RoadmapShell>
  );
}
