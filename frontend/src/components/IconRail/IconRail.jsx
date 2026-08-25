import { CalendarDays, Headphones, ListChecks, MessageSquare } from 'lucide-react'
import Logo from '../Logo/Logo'

const NAV_ITEMS = [
  { id: 'chat', icon: MessageSquare, label: 'Chat' },
  { id: 'voice', icon: Headphones, label: 'Voz' },
  { id: 'calendar', icon: CalendarDays, label: 'Agenda' },
  { id: 'tasks', icon: ListChecks, label: 'Tarefas' },
]

export default function IconRail({ activeTab, onSelectTab }) {
  return (
    <nav className="hidden w-16 shrink-0 flex-col items-center gap-1 bg-sidebar py-4 md:flex">
      <div className="mb-4 flex h-9 w-9 items-center justify-center">
        <Logo size={36} />
      </div>

      {NAV_ITEMS.map((item) => {
        const Icon = item.icon
        const isActive = item.id === activeTab
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => onSelectTab(item.id)}
            title={item.label}
            aria-label={item.label}
            aria-current={isActive ? 'page' : undefined}
            className={`flex h-10 w-10 items-center justify-center rounded-xl transition-colors ${
              isActive
                ? 'bg-button-primary text-button-primary-text'
                : 'text-text-secondary hover:bg-black/5 dark:hover:bg-white/10'
            }`}
          >
            <Icon size={18} strokeWidth={1.75} />
          </button>
        )
      })}
    </nav>
  )
}
