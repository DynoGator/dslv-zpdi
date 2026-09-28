import { createFileRoute } from "@tanstack/react-router";
import { Plate, Shell, Tag } from "@/components/chrome";
import { useActive } from "@/lib/book";
import { ART, SWITCHES } from "@/lib/metrology/protocol";

export const Route = createFileRoute("/doctrine")({ component: DoctrinePage });

function DoctrinePage() {
  const c = useActive();
  const calls = c?.logs.filter((l) => l.kind === "switch") ?? [];
  return (
    <Shell>
      <div className="space-y-4">
        <header>
          <p className="kicker">§7 · firewall</p>
          <h1 className="text-2xl font-semibold">Kill switches</h1>
          <p className="mt-1 text-sm text-muted">
            Instrument switches only. Nothing in the appendices is required to run the array, and a
            story about the vacuum is not a bound.
          </p>
        </header>
        <Plate
          src={ART.null}
          alt="A straight null fringe on a dark optical table."
          caption="Systematics-limited describes the bound, not a failure."
        />
        <ul className="space-y-3">
          {SWITCHES.map((s) => {
            const latest = calls.find((l) => l.title.startsWith(`Switch ${s.n}`));
            return (
              <li key={s.n} className="card p-4">
                <div className="flex items-center justify-between gap-2">
                  <Tag>Switch {s.n}</Tag>
                  {latest ? <Tag tone="warn">{latest.title.replace(`Switch ${s.n} · `, "")}</Tag> : <Tag tone="steel">No call</Tag>}
                </div>
                <h2 className="mt-2 font-semibold">{s.title}</h2>
                <p className="mt-2 text-sm text-muted">{s.body}</p>
                <p className="mt-2 text-sm">
                  <span className="text-subtle">Blast radius. </span>
                  {s.blast}
                </p>
              </li>
            );
          })}
        </ul>

        <section className="card space-y-3 p-4">
          <Tag tone="steel">[E] · [I] · [H]</Tag>
          <h2 className="text-lg font-semibold">How to read a sentence</h2>
          <ul className="space-y-2 text-sm text-muted">
            <li>
              <span className="text-foreground">[E]</span> Established result. GPS, IGS, the Beta law,
              the Holometer’s optical null, the ionospheric 1/f² delay.
            </li>
            <li>
              <span className="text-foreground">[I]</span> Interpretive. Not required by the data. Appendix A.
            </li>
            <li>
              <span className="text-foreground">[H]</span> This program’s hypothesis. Contingent. Kill-switched.
              H_S and H_C are the only two that the array is built to bound.
            </li>
          </ul>
        </section>

        <section className="space-y-3">
          <Plate
            src={ART.companion}
            alt="Companion studies kept behind a closed laboratory door, the RF rack in front."
            caption="Appendix B. Gated separately. Aqueous, somatic, and Schumann work does not open or close Chain C."
          />
          <article className="card p-4">
            <h2 className="font-semibold">What this handset will not do</h2>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted">
              <li>Invent a residual, a γ̂, or a lag.</li>
              <li>Treat a GPS fix as carrier phase.</li>
              <li>Quote a Chain C bound tighter than the common-clock floor you typed.</li>
              <li>Call a τ≈0 excess superluminal. Common-mode is not a channel.</li>
              <li>Let Appendix A’s ontology into the detection statistic.</li>
            </ul>
          </article>
        </section>

        <section className="card p-4 text-sm text-muted">
          <p>
            Prior art, so a reviewer does not have to reconstruct it: the Holometer is co-located
            optical strain (Chou et al., Phys. Rev. Lett. 117, 111102, 2016; arXiv:1611.08265). This
            program is RF carrier phase across geographic baselines. Clock-network dark-matter
            searches look for transients in frequency. This one looks for stationary phase coherence
            after geodetic subtraction. A bound here is a different channel.
          </p>
          <p className="mt-2">
            Sibling stack: the node software and the existing handset shell live in DynoGator/dslv-zpdi,
            package labs.dynogator.dslvzpdi. This record is the Rev 3.4 campaign book beside that
            array, not a second simulator.
          </p>
        </section>
      </div>
    </Shell>
  );
}
