// Astrobalance — NASA Space Apps Challenge 2026
// AI-assisted: drafted with Claude (Anthropic), reviewed by the team. License: Apache-2.0

import { useState } from "react";
import { EARTH_REPORTS, META, oneWayText, realDelaySeconds, roundTripText } from "../data.js";
import { BLACKOUT, ESCALATION_TEXT, EVENT_TEXT, PROMPTS, SBAR, STATUS_LABEL } from "../content/texts.js";
import { Glyph, StatusIcon } from "../components/icons.jsx";
import { Panel, SourceLink, TapButton } from "../components/ui.jsx";

// ===== Earth link: signal delay and reports queued for the next communication window =====
// Each report can be opened to see exactly what goes to the flight surgeons (a compact summary,
// not raw data), with the one-way delay and the earliest possible reply for this environment.

/** What one report contains, as an SBAR handover (Situation, Background, Assessment, Recommendation). */
function ReportBody({ report, env }) {
  const moved = Object.entries(report.top_contributions ?? {}).filter(([f]) => f !== "other");
  const name = META.crew.find((c) => c.id === report.astronaut)?.display_name ?? report.astronaut;
  const sai = report.sai_last_7_days?.at(-1);
  const rows = [
    ["S", `${name}, mission day ${report.day}: ${STATUS_LABEL[report.level] ?? report.level}`
          + (sai != null ? ` (index ${sai} of 100)` : "") + `. ${ESCALATION_TEXT[report.escalation]}.`],
    ["B", `Index over the last 7 days: ${report.sai_last_7_days.map((v) => v ?? "—").join(" · ")}. `
          + `Personal normal learned on days 1–${META.mission.calibration_days}. ${META.environments[env].name}.`
          + (report.events?.length ? ` Events: ${report.events.map((e) => EVENT_TEXT[e]?.title ?? e).join(", ")}.` : "")],
    ["A", moved.length ? `Moved away from the personal normal: ${moved.map(([f, v]) => `${META.features[f]?.name ?? f} ${Math.round(v * 100)}%`).join(", ")}.`
                       : "No clear driver."],
    ["R", `${report.open_prompts?.length ? `On board: ${report.open_prompts.map((p) => PROMPTS[p]?.title ?? p).join("; ")}. ` : ""}${SBAR.request}`],
  ];
  return (
    <dl className="grid gap-3 mt-3 text-lg">
      {rows.map(([k, text]) => (
        <div key={k} className="grid grid-cols-[2.5rem_1fr] gap-3 items-start">
          <dt className="grid place-items-center w-10 h-10 rounded-xl bg-line font-bold" title={SBAR[k]}>
            <span aria-hidden="true">{k}</span><span className="sr-only">{SBAR[k]}</span>
          </dt>
          <dd><span className="text-ink-2 text-base block">{SBAR[k]}</span>{text}</dd>
        </div>
      ))}
      <dd className="text-sm"><SourceLink id={SBAR.source} /></dd>
    </dl>
  );
}

/** A report built on board from today's record (the same fields as the automatic ones). */
function reportFromRecord(record, records) {
  const last7 = records.filter((r) => r.day > record.day - 7 && r.day <= record.day);
  return {
    astronaut: record.astronaut, day: record.day, level: record.level, escalation: record.escalation,
    sai_last_7_days: last7.map((r) => r.sai), top_contributions: record.contributions,
    open_prompts: record.prompts, events: record.events, manual: true,
  };
}

export default function EarthLink({ astronaut, day, env, record, records, queued, onQueue }) {
  const e = META.environments[env];
  const [open, setOpen] = useState(null);
  const auto = EARTH_REPORTS.filter((r) => r.astronaut === astronaut && r.day <= day);
  const manual = queued.filter((q) => q.astronaut === astronaut);
  const all = [...auto, ...manual].sort((a, b) => b.day - a.day);
  const canBlackout = env.startsWith("mars");
  const [blackoutOn, setBlackout] = useState(false);
  const blackout = canBlackout && blackoutOn;

  return (
    <div className="grid gap-4">
      <Panel>
        <h2 className="flex items-center gap-3 text-xl font-semibold"><Glyph name="distance" /> Earth link · {e.name}</h2>
        {canBlackout && (
          <label className="tap mt-3 inline-flex items-center gap-3 px-4 rounded-2xl bg-panel-2 glass-control text-lg cursor-pointer">
            <input type="checkbox" className="w-6 h-6 accent-[var(--color-warning)]" checked={blackoutOn}
                   onChange={(ev) => setBlackout(ev.target.checked)} />
            {BLACKOUT.toggle}
          </label>
        )}
        {blackout ? (
          <div className="mt-3 p-4 rounded-2xl border-2 border-warning grid gap-2" role="status">
            <p className="flex items-center gap-3 text-xl font-semibold"><StatusIcon status="orange" /> {BLACKOUT.title}</p>
            <p className="text-lg">{BLACKOUT.body}</p>
            <p className="text-lg font-semibold">{BLACKOUT.rule}</p>
            <SourceLink id={BLACKOUT.source} />
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 gap-3 mt-3 text-lg">
            <div className="p-3 rounded-xl bg-panel-2"><div className="text-ink-2 text-base">Report reaches Earth after</div>{oneWayText(env, day)}</div>
            <div className="p-3 rounded-xl bg-panel-2"><div className="text-ink-2 text-base">Earliest possible reply</div>{roundTripText(env, day)} round trip, plus review time</div>
            {realDelaySeconds(env, day) != null && (
              <p className="sm:col-span-2 text-sm text-ink-2">Today’s Earth–Mars distance from <a href={META.mars_delay.link} target="_blank" rel="noreferrer" className="underline underline-offset-2">NASA/JPL Horizons</a>, divided by the speed of light.</p>
            )}
          </div>
        )}
        <TapButton onClick={() => onQueue(reportFromRecord(record, records))} className="mt-4 bg-model! text-on-status font-semibold">
          {blackout ? BLACKOUT.queueButton : "Send today’s summary to Earth"}
        </TapButton>
        <p className="mt-3 text-ink-2">One message in SBAR form (situation, background, assessment, recommendation), because every question to Earth costs a round trip. Reports are stored on board and sent in the next communication window. Act on board first; do not wait for a reply in an emergency.</p>
        <div className="mt-1"><SourceLink id={["hrp_distance", "cpr_microgravity"]} /></div>
      </Panel>

      <Panel title={blackout ? "Queued until the link returns" : "Waiting to be sent to Earth"}>
        {all.length === 0 && <p className="text-lg">None yet.</p>}
        <ul className="grid gap-2">
          {all.map((r) => {
            const key = `${r.manual ? "m" : "a"}-${r.day}`, isOpen = open === key;
            return (
              <li key={key} className="rounded-xl bg-panel-2">
                <button type="button" onClick={() => setOpen(isOpen ? null : key)} aria-expanded={isOpen}
                        className="tap w-full flex flex-wrap items-center gap-3 px-4 text-lg text-left">
                  <span aria-hidden="true">{isOpen ? "▼" : "▶"}</span>
                  <StatusIcon status={r.level} />
                  <span className="font-semibold">Day {r.day}</span>
                  <span>{ESCALATION_TEXT[r.escalation]}</span>
                  <span className="text-ink-2">{r.manual ? "added by you" : "automatic, after an escalation"}</span>
                </button>
                {isOpen && <div className="px-4 pb-4"><ReportBody report={r} env={env} /></div>}
              </li>
            );
          })}
        </ul>
      </Panel>
    </div>
  );
}
