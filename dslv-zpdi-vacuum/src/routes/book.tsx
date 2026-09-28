import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Field, NeedCampaign, Shell, Tag } from "@/components/chrome";
import { useActive, useBook } from "@/lib/book";
import { campaignMarkdown, download } from "@/lib/metrology/report";

export const Route = createFileRoute("/book")({ component: BookPage });

function BookPage() {
  return (
    <Shell>
      <BookBody />
    </Shell>
  );
}

function BookBody() {
  const c = useActive();
  const campaigns = useBook((s) => s.campaigns);
  const addLog = useBook((s) => s.addLog);
  const remove = useBook((s) => s.remove);
  const importBook = useBook((s) => s.importBook);
  const [note, setNote] = useState("");
  const [msg, setMsg] = useState("");
  const [confirm, setConfirm] = useState(false);

  return (
    <div className="space-y-4">
      <header>
        <p className="kicker">Archive</p>
        <h1 className="text-2xl font-semibold">Campaign book</h1>
        <p className="mt-1 text-sm text-muted">
          {campaigns.length} record{campaigns.length === 1 ? "" : "s"} on this handset. Export is the
          way out. Import appends; it does not overwrite.
        </p>
      </header>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="btn btn-ghost"
          onClick={() => {
            const payload = { app: "DSLV-ZPDI-Probing-The-Vacuum-Structure", rev: "3.4", campaigns };
            download(
              `dslv-zpdi-vacuum-book.json`,
              JSON.stringify(payload, null, 2),
              "application/json",
            );
          }}
        >
          Export the book
        </button>
        <label className="btn btn-ghost">
          Import JSON
          <input
            type="file"
            accept="application/json,.json"
            className="sr-only"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              e.target.value = "";
              if (!file) return;
              try {
                const parsed = JSON.parse(await file.text()) as unknown;
                const result = importBook(parsed);
                setMsg(result.ok ? `Imported ${result.n}.` : result.error);
              } catch {
                setMsg("That file did not parse.");
              }
            }}
          />
        </label>
      </div>
      {msg ? <p className="text-sm text-muted">{msg}</p> : null}

      {!c ? (
        <NeedCampaign />
      ) : (
        <>
          <section className="card space-y-3 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">{c.name}</h2>
                <p className="text-sm text-muted">
                  {c.operator || "Operator unset"} · {c.site || "Site unset"} · opened {c.createdAt}
                </p>
              </div>
              <Tag tone={c.frozen ? "ok" : "warn"}>{c.frozen ? "Frozen" : "Open"}</Tag>
            </div>
            {c.frozen ? <p className="break-all font-mono text-xs text-primary">{c.frozen.sha256}</p> : null}
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => download(`${slug(c.name)}.json`, JSON.stringify(c, null, 2), "application/json")}
              >
                Export this campaign
              </button>
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => download(`${slug(c.name)}.md`, campaignMarkdown(c), "text/markdown")}
              >
                Markdown
              </button>
            </div>
          </section>

          <section className="card space-y-3 p-4">
            <h2 className="font-semibold">Field note</h2>
            <Field label="Append only">
              <textarea className="field textarea" value={note} onChange={(e) => setNote(e.target.value)} />
            </Field>
            <button
              type="button"
              className="btn btn-ghost"
              disabled={!note.trim()}
              onClick={() => {
                addLog(c.id, { kind: "note", title: "Field note", body: note.trim() });
                setNote("");
              }}
            >
              Append note
            </button>
          </section>

          <section className="space-y-2">
            <h2 className="font-semibold">Log</h2>
            {!c.logs.length ? (
              <p className="text-sm text-muted">No entries. The walk appends calibrations, injections, and calls. This page does not invent them.</p>
            ) : (
              <ol className="space-y-2">
                {c.logs.map((log) => (
                  <li key={log.id} className="card p-3">
                    <div className="flex items-center justify-between gap-2">
                      <Tag>{log.kind}</Tag>
                      <time className="font-mono text-xs text-muted">{log.at}</time>
                    </div>
                    <h3 className="mt-1 text-sm font-semibold">{log.title}</h3>
                    <p className="mt-1 whitespace-pre-wrap text-sm text-muted">{log.body}</p>
                  </li>
                ))}
              </ol>
            )}
          </section>

          <section className="card space-y-3 p-4">
            <h2 className="font-semibold">Remove this campaign</h2>
            <p className="text-sm text-muted">
              Deletes one record from this handset. Export first if you want it. There is no cloud copy.
            </p>
            {confirm ? (
              <div className="flex gap-2">
                <button type="button" className="btn btn-hot flex-1" onClick={() => remove(c.id)}>
                  Delete {c.name}
                </button>
                <button type="button" className="btn btn-ghost flex-1" onClick={() => setConfirm(false)}>
                  Keep it
                </button>
              </div>
            ) : (
              <button type="button" className="btn btn-ghost" onClick={() => setConfirm(true)}>
                I want to delete this record
              </button>
            )}
          </section>
        </>
      )}
    </div>
  );
}

function slug(name: string): string {
  const s = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return s || "campaign";
}
