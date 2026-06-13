import { NavLink } from "react-router-dom";
import { useData } from '../context/DataContext';
import BrandMark from './BrandMark';

function NavItem({ to, icon, label, end, onNavigate }) {
  return (
    <NavLink
      onClick={onNavigate}
      to={to}
      end={end}
      className={({ isActive }) => `px-4 py-3 flex items-center gap-3 rounded-lg mx-2 my-1 group transition-all duration-200 ${isActive ? 'bg-secondary-container text-on-secondary-container active:scale-95' : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-variant'}`}
    >
      {({ isActive }) => (
        <>
          <span className={`material-symbols-outlined ${isActive ? 'fill' : ''}`}>{icon}</span>
          <span className="font-body-md text-body-md">{label}</span>
        </>
      )}
    </NavLink>
  );
}

export default function Sidebar({ isOpen, setIsOpen }) {
  const { port } = useData();
  const close = () => setIsOpen(false);

  return (
    <nav className={`bg-surface-container dark:bg-surface-container flex flex-col h-screen fixed left-0 top-0 z-50 docked full-height w-64 border-r border-outline-variant flat no shadows transition-transform duration-300 md:translate-x-0 ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}>
      <div className="p-container-padding flex items-center gap-3 border-b border-outline-variant/30 h-16 shrink-0">
        <BrandMark />
        <div className="flex flex-col overflow-hidden">
          <span className="font-title-sm text-title-sm truncate text-on-surface font-bold">{port?.name || 'Port Ops'}</span>
          <span className="font-body-sm text-body-sm text-on-surface-variant truncate">Vessel Traffic Control</span>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto py-4 px-2 space-y-1">
        <NavItem to="/" icon="dashboard" label="Dashboard" end={true} onNavigate={close} />
        <NavItem to="/map" icon="directions_boat" label="Traffic" onNavigate={close} />
        <NavItem to="/schedule" icon="schedule" label="Schedule" onNavigate={close} />
        <NavItem to="/berth" icon="calendar_view_day" label="Berthing" onNavigate={close} />
        <NavItem to="/insights" icon="analytics" label="Insights" onNavigate={close} />
        <NavItem to="/predictive" icon="query_stats" label="Predictive" onNavigate={close} />
      </div>
      <div className="p-4 border-t border-outline-variant/30 space-y-1">
        <a className="text-on-surface-variant hover:text-on-surface px-4 py-3 flex items-center gap-3 hover:bg-surface-variant transition-colors duration-200 rounded-lg mx-2 my-1 group" href="#">
          <span className="material-symbols-outlined">settings</span>
          <span className="font-body-md text-body-md">Settings</span>
        </a>
        <a className="text-on-surface-variant hover:text-on-surface px-4 py-3 flex items-center gap-3 hover:bg-surface-variant transition-colors duration-200 rounded-lg mx-2 my-1 group" href="#">
          <span className="material-symbols-outlined">help</span>
          <span className="font-body-md text-body-md">Support</span>
        </a>
      </div>
    </nav>
  );
}
