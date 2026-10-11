import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CalendarClock, Languages, MapPin, ShieldQuestion, Stethoscope } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Dialog } from "@/components/ui/Dialog";
import { Skeleton } from "@/components/ui/EmptyState";
import { Notice } from "@/components/ui/Notice";
import { api } from "@/lib/api";
import type { DemoDoctor } from "@/lib/types";

const ROADMAP = [
  { phase: "Phase 5", title: "Doctor discovery", text: "Searchable profiles by specialty, language and city, with verified credentials." },
  { phase: "Phase 5", title: "Appointment requests", text: "Request, confirm or reschedule; status visible to both sides; reminders." },
  { phase: "Phase 5+", title: "Secure consultation", text: "Encrypted messaging, then audio/video only if it can be done safely." },
];

export function DoctorsPage() {
  const { data, isLoading } = useQuery({ queryKey: ["doctors"], queryFn: api.doctors });
  const [selected, setSelected] = useState<DemoDoctor | null>(null);

  return (
    <div>
      <PageHeader
        eyebrow="Consult · preview"
        title="Doctor Connect"
        description="A clearly labelled preview of how SakhiSahay will connect education and tracking to professional care. Nothing here is a real clinician or booking."
      />

      <Notice tone="advisory" title="Preview with fictional sample data">
        {data?.notice?.replace(/^Demonstration only\.\s*/, "") ?? "Sample profiles are fictional placeholders used to preview the experience."}
      </Notice>

      <div className="mt-6 grid gap-4 md:grid-cols-3">
        {isLoading && [1, 2, 3].map((i) => <Skeleton key={i} className="h-64" />)}
        {data?.doctors.map((d) => (
          <Card key={d.id} className="flex flex-col">
            <div className="flex items-start justify-between gap-3">
              <span className="flex size-12 items-center justify-center rounded-2xl bg-lavender-100 text-lavender-700">
                <Stethoscope className="size-5" aria-hidden />
              </span>
              <Badge tone="amber">Sample profile</Badge>
            </div>
            <h2 className="mt-4 font-sans text-base font-semibold text-ink-900">{d.display_name}</h2>
            <p className="text-sm text-plum-700">{d.specialty}</p>
            <ul className="mt-3 flex flex-wrap gap-1.5">
              {d.focus_areas.map((f) => (
                <li key={f}>
                  <Badge tone="plum">{f}</Badge>
                </li>
              ))}
            </ul>
            <dl className="mt-4 space-y-1.5 text-sm text-ink-700">
              <div className="flex items-center gap-2">
                <Languages className="size-4 text-ink-400" aria-hidden />
                <dd>{d.languages.join(", ")}</dd>
              </div>
              <div className="flex items-center gap-2">
                <CalendarClock className="size-4 text-ink-400" aria-hidden />
                <dd>{d.consultation_types.join(" · ")}</dd>
              </div>
              <div className="flex items-center gap-2">
                <MapPin className="size-4 text-ink-400" aria-hidden />
                <dd>{d.city}</dd>
              </div>
            </dl>
            <Button variant="secondary" className="mt-5" onClick={() => setSelected(d)}>
              Preview appointment request
            </Button>
          </Card>
        ))}
      </div>

      <section className="mt-10">
        <h2 className="text-xl font-semibold text-ink-900">What real Doctor Connect will require</h2>
        <p className="mt-1 text-sm text-ink-500">Planned after the mid-semester evaluation; each step depends on authentication, consent and credential verification being in place first.</p>
        <ol className="mt-4 grid gap-3 md:grid-cols-3">
          {ROADMAP.map((r) => (
            <li key={r.title} className="card-muted p-4">
              <Badge tone="lavender">{r.phase}</Badge>
              <p className="mt-2 font-sans text-sm font-semibold text-ink-900">{r.title}</p>
              <p className="mt-1 text-sm text-ink-500">{r.text}</p>
            </li>
          ))}
        </ol>
      </section>

      <Dialog
        open={!!selected}
        onClose={() => setSelected(null)}
        title="Appointment request - preview"
        description="This shows the intended request flow. Nothing is sent or stored; no appointment exists."
        footer={
          <Button onClick={() => setSelected(null)}>Close preview</Button>
        }
      >
        {selected && (
          <div className="space-y-3 text-sm">
            <div className="rounded-2xl bg-ivory-100 p-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-ink-400">Request to</p>
              <p className="font-medium text-ink-900">{selected.display_name} · {selected.specialty}</p>
            </div>
            <ol className="space-y-2 text-ink-700">
              <li className="flex gap-2"><span className="font-semibold text-plum-700">1.</span> Choose a consultation type and preferred time window.</li>
              <li className="flex gap-2"><span className="font-semibold text-plum-700">2.</span> Optionally share a summary of your tracker records (with explicit consent).</li>
              <li className="flex gap-2"><span className="font-semibold text-plum-700">3.</span> The clinic confirms, proposes another time, or declines; you are notified.</li>
            </ol>
            <p className="flex items-start gap-2 rounded-xl bg-amber-100/70 p-3 text-xs text-amber-800">
              <ShieldQuestion className="mt-0.5 size-4 shrink-0" aria-hidden />
              Real bookings need verified clinician onboarding, authentication, and consent management. These are planned for Phase 5 and are not part of this prototype.
            </p>
          </div>
        )}
      </Dialog>
    </div>
  );
}
