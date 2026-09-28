import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Field, Plate, Shell, Tag } from "@/components/chrome";
import { clockReady, nodesReady, preregComplete, useActive, useBook } from "@/lib/book";
import { identityPassCount } from "@/lib/book";
import { ART, STEPS } from "@/lib/metrology/protocol";
import { num, sigmaPhiRad, F_L1_HZ } from "@/lib/metrology/physics";
import { formatRad } from "@/lib/metrology/format";

export const Route = createFileRoute("/")({ component: Deck });

function Deck() {
  return (
    <Shell>
      <DeckBody />
    </Shell>
  );
}

function DeckBody() {
  const campaign = useActive();
  const create = useBook((s) => s.createCampaign);
  const [name, setName] = useState("");
  const [operator, setOperator] = useState("");
  const [site, setSite] = useState("");
  const [error, setError] = useState("");
  const idn = identityPassCount();
  const step = campaign ? STEPS.find((s) => s.id === campaign.stepId) : undefined;

  return (
    <div className="space-y-4">
      <section className="card relative overflow-hidden">
        <img
          src={ART.hero}
          alt="Two geodetic antennas and a field rack in the high desert at night."
          className="h-64 w-full object-cover sm:h-80"
        />
        <div className="plate-scrim absolute inset-0" />
        <div className="absolute inset-x-0 bottom-0 p-4">
          <p className="kicker">Rev 3.4 · Resonant Genesis LLC</p>
          <h1 className="mt-1 text-2xl font-semibold">Probing the Vacuum Structure</h1>
          <p className="mt-1 max-w-prose text-sm text-accent">
            Carrier-phase coherence after the null is subtracted. Two chains. Two bounds. A null is
            the expected result.
          </p>
        </div>
      </section>

      <section className="grid gap-3 sm:grid-cols-2">
        <article className="card p-4">
          <Tag>H_S · Chain S</Tag>
          <h2 className="mt-2 font-semibold">Sky gradient</h2>
          <p className="mt-1 text-sm text-muted">
            Between-satellite single difference. Blind to isotropic site phase. Bounds
            direction-dependent residual coherence.
          </p>
        </article>
        <article className="card p-4">
          <Tag tone="warn">H_C · Chain C</Tag>
          <h2 className="mt-2 font-semibold">Isotropic common phase</h2>
          <p className="mt-1 text-sm text-muted">
            Same-satellite inter-node difference. Keeps receiver-common phase. Bound set by the
            measured common-clock floor, or not quoted.
          </p>
        </article>
      </section>

      {!campaign ? (
        <form
          className="card space-y-3 p-4"
          onSubmit={(e) => {
            e.preventDefault();
            if (!name.trim()) {
              setError("A campaign needs a name. The operator and site can stay blank, but they belong in the registry.");
              return;
            }
            setError("");
            create({ name, operator, site });
          }}
        >
          <h2 className="text-lg font-semibold">Open a campaign record</h2>
          <p className="text-sm text-muted">
            Stored on this handset only. No account, no upload, no seeded run. Catalog budget rows
            from the paper are labeled catalog until you replace them.
          </p>
          <Field label="Campaign name">
            <input className="field" value={name} onChange={(e) => setName(e.target.value)} placeholder="Penrose pair, campaign 01" />
          </Field>
          <Field label="Operator">
            <input className="field" value={operator} onChange={(e) => setOperator(e.target.value)} placeholder="Name on the registry" />
          </Field>
          <Field label="Site">
            <input className="field" value={site} onChange={(e) => setSite(e.target.value)} placeholder="Penrose, Fremont County" />
          </Field>
          {error ? <p className="text-sm text-hot">{error}</p> : null}
          <button className="btn btn-primary w-full" type="submit">
            Create the record
          </button>
        </form>
      ) : (
        <section className="card space-y-3 p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="kicker">{campaign.frozen ? "Frozen registry" : "Open registry"}</p>
              <h2 className="text-lg font-semibold">{campaign.name}</h2>
              <p className="text-sm text-muted">
                {campaign.operator || "Operator unset"} · {campaign.site || "Site unset"}
              </p>
            </div>
            <Tag tone={campaign.frozen ? "ok" : "warn"}>{campaign.frozen ? "Locked" : "Unlocked"}</Tag>
          </div>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <div className="rounded-md bg-elevated px-3 py-2">
              <dt className="text-muted">Nodes</dt>
              <dd className="tabular font-mono">{campaign.nodes.length}</dd>
            </div>
            <div className="rounded-md bg-elevated px-3 py-2">
              <dt className="text-muted">Log entries</dt>
              <dd className="tabular font-mono">{campaign.logs.length}</dd>
            </div>
            <div className="rounded-md bg-elevated px-3 py-2">
              <dt className="text-muted">Pre-registration</dt>
              <dd>{preregComplete(campaign) ? "Fields filled" : "Incomplete"}</dd>
            </div>
            <div className="rounded-md bg-elevated px-3 py-2">
              <dt className="text-muted">Common-clock floor</dt>
              <dd>{clockReady(campaign) ? formatRad(num(campaign.fields.clockFloorRad)) : "Not measured"}</dd>
            </div>
          </dl>
          <p className="text-sm text-muted">
            {nodesReady(campaign) ? "Array roster meets the two-node bar." : "Roster still needs two identified nodes with measured σ_y and f_loop."}{" "}
            Walk is on {step?.section} — {step?.title}.
          </p>
          <Link to="/walk" className="btn btn-primary w-full">
            Continue the walk
          </Link>
          {campaign.frozen ? (
            <p className="break-all font-mono text-xs text-muted">{campaign.frozen.sha256}</p>
          ) : null}
          <ul className="space-y-1 text-sm">
            {campaign.nodes.map((n) => {
              const sy = num(n.sigmaY);
              return (
                <li key={n.id} className="flex justify-between gap-3 border-t border-border pt-2">
                  <span>{n.name || "Unnamed node"}</span>
                  <span className="tabular font-mono text-muted">
                    {sy == null ? "σ_y blank" : formatRad(sigmaPhiRad(F_L1_HZ, 1, sy))}
                  </span>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      <section className="card grid gap-3 p-4 sm:grid-cols-[1.2fr_1fr]">
        <div>
          <p className="kicker">GrapheneOS · Pixel 9 Pro XL</p>
          <h2 className="mt-1 font-semibold">The handset keeps the book</h2>
          <p className="mt-2 text-sm text-muted">
            Vanadium can install this as a standalone window. No Play Services. No account. The
            campaign book stays in on-device storage. Location, if you grant it, fills a site fix
            you can read before it is saved. It is not uploaded.
          </p>
          <p className="mt-2 text-sm text-muted">
            The SDR, the GPSDO, and the prompt correlator stay on the DSLV-ZPDI nodes. This app
            does not synthesize IQ, residuals, or a detection.
          </p>
        </div>
        <img
          src={ART.field}
          alt="Handset, antenna cable, and hard hat on a flight case."
          className="h-40 w-full rounded-md object-cover"
        />
      </section>

      <section className="card flex items-center justify-between gap-3 p-4">
        <div>
          <p className="kicker">Formula identity</p>
          <p className="mt-1 text-sm text-muted">
            Closed forms checked against the numbers quoted in Rev 3.4. A miss here is an app bug,
            not a measurement.
          </p>
        </div>
        <p className="tabular font-mono text-2xl text-primary">
          {idn.pass}/{idn.total}
        </p>
      </section>

      <Plate
        src={ART.companion}
        alt="An RF rack in front of a closed glass door, companion studies kept out of the array."
        caption="Appendix B stays behind the glass. It does not gate Chain S or Chain C."
      />
    </div>
  );
}
