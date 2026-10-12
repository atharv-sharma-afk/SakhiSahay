import { NavLink, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { BookOpenText, CalendarHeart, HeartHandshake, House, MessageCircleHeart, Stethoscope } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/cn";

const nav = [
  { to: "/", label: "Home", icon: House, end: true },
  { to: "/assistant", label: "Assistant", icon: MessageCircleHeart },
  { to: "/tracker", label: "Tracker", icon: CalendarHeart },
  { to: "/doctors", label: "Doctor Connect", icon: Stethoscope },
  { to: "/sources", label: "Sources", icon: BookOpenText },
];

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <span className="flex size-10 items-center justify-center rounded-2xl bg-plum-700 text-white shadow-soft">
        <HeartHandshake className="size-5" aria-hidden />
      </span>
      <div className="leading-tight">
        <p className="font-display text-xl font-semibold text-plum-800">SakhiSahay</p>
        <p className="text-[0.7rem] text-ink-500">सखी · सहाय</p>
      </div>
    </div>
  );
}

function StatusPill() {
  const { data } = useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 30_000, retry: 1 });
  if (!data) {
    return <span className="inline-flex items-center gap-2 text-xs text-ink-400"><span className="size-2 rounded-full bg-ink-300" />Connecting...</span>;
  }
  const live = data.llm.configured && data.knowledge.index_ready;
  return (
    <div className="space-y-1 text-xs text-ink-500">
      <p className="flex items-center gap-2">
        <span className={cn("size-2 rounded-full", live ? "bg-sage-500" : "bg-amber-600")} aria-hidden />
        {live ? `Assistant live · ${data.llm.model}` : data.knowledge.index_ready ? "Retrieval only (no model key)" : "Knowledge index not built"}
      </p>
      <p className="pl-4">{data.knowledge.indexed_sources} cited sources · {data.knowledge.chunk_count} passages</p>
    </div>
  );
}

export function AppShell() {
  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[17rem_1fr]">
      <aside className="hidden lg:flex lg:flex-col lg:gap-8 lg:border-r lg:border-ivory-300/80 lg:bg-ivory-50 lg:px-6 lg:py-8 lg:sticky lg:top-0 lg:h-dvh">
        <Brand />
        <nav aria-label="Primary" className="flex flex-col gap-1">
          {nav.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive ? "bg-plum-700 text-white shadow-soft" : "text-ink-700 hover:bg-plum-50 hover:text-plum-800",
                )
              }
            >
              <Icon className="size-[18px]" aria-hidden />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto space-y-4">
          <StatusPill />
          <p className="text-[0.7rem] leading-relaxed text-ink-400">
            Educational information from cited public sources. Not a substitute for a clinician.
          </p>
        </div>
      </aside>

      <div className="flex min-h-dvh flex-col">
        <header className="flex items-center justify-between border-b border-ivory-300/80 bg-ivory-50/90 px-4 py-3 backdrop-blur lg:hidden">
          <Brand />
        </header>
        <main className="flex-1 px-4 pb-24 pt-6 sm:px-6 lg:px-10 lg:pb-12 lg:pt-10">
          <div className="mx-auto w-full max-w-6xl">
            <Outlet />
          </div>
        </main>
        <nav
          aria-label="Primary"
          className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-t border-ivory-300 bg-white/95 px-1 pb-[max(env(safe-area-inset-bottom),0.4rem)] pt-1.5 backdrop-blur lg:hidden"
        >
          {nav.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn("flex min-h-12 flex-col items-center justify-center gap-0.5 rounded-xl text-[0.68rem] font-medium", isActive ? "text-plum-700" : "text-ink-500")
              }
            >
              {({ isActive }) => (
                <>
                  <span className={cn("rounded-full px-3 py-0.5", isActive && "bg-plum-100")}>
                    <Icon className="size-5" aria-hidden />
                  </span>
                  {label.replace("Doctor Connect", "Doctors")}
                </>
              )}
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  );
}
