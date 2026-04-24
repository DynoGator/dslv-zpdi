"""Simple tkinter GUI to edit ~/.config/dslv-zpdi/email.yaml.

Intentionally minimal — no dependencies beyond stdlib. Lets the user
paste in their Gmail App Password, add/remove recipients, and save a
chmod-600 config file without hunting through the filesystem.

Runs fine headless via ssh -X, or via the desktop icon under LXDE.
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path
from tkinter import Tk, StringVar, BooleanVar, Text, END, messagebox, ttk

try:
    import yaml  # optional but preferred
    _HAVE_YAML = True
except Exception:
    _HAVE_YAML = False


CONFIG_PATH = Path.home() / ".config" / "dslv-zpdi" / "email.yaml"
EXAMPLE_PATH = Path(__file__).resolve().parents[2] / "config" / "email.example.yaml"


DEFAULTS = {
    "backend": "gmail",
    "smtp_user": "",
    "smtp_password": "",
    "from_name": "DSLV-ZPDI Anchor",
    "recipients": [],
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "max_attachment_mb": 20,
    "include_primary": True,
    "include_secondary": True,
    "include_map": True,
    "subject_prefix": "[DSLV-ZPDI]",
}


def _load_current() -> dict:
    if not CONFIG_PATH.exists():
        return dict(DEFAULTS)
    try:
        if _HAVE_YAML:
            data = yaml.safe_load(CONFIG_PATH.read_text()) or {}
        else:
            data = {}
            for line in CONFIG_PATH.read_text().splitlines():
                line = line.split("#", 1)[0].rstrip()
                if ":" in line and not line.lstrip().startswith("- "):
                    k, _, v = line.partition(":")
                    data[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        data = {}
    merged = dict(DEFAULTS)
    merged.update(data)
    return merged


def _dump_yaml(data: dict) -> str:
    if _HAVE_YAML:
        return yaml.safe_dump(data, sort_keys=False)
    # Hand-rolled just enough to round-trip our shape.
    lines = []
    for k, v in data.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - \"{item}\"")
        elif isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, (int, float)):
            lines.append(f"{k}: {v}")
        else:
            s = str(v).replace('"', '\\"')
            lines.append(f'{k}: "{s}"')
    return "\n".join(lines) + "\n"


def run():
    cfg = _load_current()
    root = Tk()
    root.title("DSLV-ZPDI Email Setup")
    root.geometry("520x560")

    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True, padx=10, pady=10)

    # -- Account tab ---
    tab_acct = ttk.Frame(nb)
    nb.add(tab_acct, text="Account")

    backend = StringVar(value=cfg["backend"])
    smtp_user = StringVar(value=cfg["smtp_user"])
    smtp_password = StringVar(value=cfg["smtp_password"])
    from_name = StringVar(value=cfg["from_name"])
    smtp_host = StringVar(value=cfg["smtp_host"])
    smtp_port = StringVar(value=str(cfg["smtp_port"]))

    def row(frame, r, label, widget):
        ttk.Label(frame, text=label).grid(row=r, column=0, sticky="w", padx=6, pady=4)
        widget.grid(row=r, column=1, sticky="ew", padx=6, pady=4)

    tab_acct.columnconfigure(1, weight=1)
    row(tab_acct, 0, "Backend",
        ttk.Combobox(tab_acct, textvariable=backend, values=["gmail", "smtp"], state="readonly"))
    row(tab_acct, 1, "Sender address", ttk.Entry(tab_acct, textvariable=smtp_user))
    row(tab_acct, 2, "Sender display name", ttk.Entry(tab_acct, textvariable=from_name))
    row(tab_acct, 3, "Password (App Password)",
        ttk.Entry(tab_acct, textvariable=smtp_password, show="*"))
    row(tab_acct, 4, "SMTP host", ttk.Entry(tab_acct, textvariable=smtp_host))
    row(tab_acct, 5, "SMTP port", ttk.Entry(tab_acct, textvariable=smtp_port))

    hint = (
        "Gmail users: generate an App Password at\n"
        "https://myaccount.google.com/apppasswords\n"
        "(requires 2FA). Paste the 16-char code above."
    )
    ttk.Label(tab_acct, text=hint, foreground="#555", justify="left").grid(
        row=6, column=0, columnspan=2, sticky="w", padx=6, pady=(12, 4))

    # -- Recipients tab ---
    tab_rcp = ttk.Frame(nb)
    nb.add(tab_rcp, text="Recipients")
    ttk.Label(tab_rcp, text="One email per line:").pack(anchor="w", padx=8, pady=(8, 2))
    rcp_text = Text(tab_rcp, height=12)
    rcp_text.pack(fill="both", expand=True, padx=8, pady=4)
    rcp_text.insert("1.0", "\n".join(cfg["recipients"]))

    # -- Options tab ---
    tab_opt = ttk.Frame(nb)
    nb.add(tab_opt, text="Options")
    inc_p = BooleanVar(value=bool(cfg["include_primary"]))
    inc_s = BooleanVar(value=bool(cfg["include_secondary"]))
    inc_m = BooleanVar(value=bool(cfg["include_map"]))
    prefix = StringVar(value=cfg["subject_prefix"])
    max_mb = StringVar(value=str(cfg["max_attachment_mb"]))

    ttk.Checkbutton(tab_opt, text="Include tier 1 (primary HDF5)", variable=inc_p).pack(anchor="w", padx=8, pady=4)
    ttk.Checkbutton(tab_opt, text="Include tier 2 (secondary JSONL)", variable=inc_s).pack(anchor="w", padx=8, pady=4)
    ttk.Checkbutton(tab_opt, text="Include rendered satellite map", variable=inc_m).pack(anchor="w", padx=8, pady=4)

    f = ttk.Frame(tab_opt); f.pack(fill="x", padx=8, pady=8)
    ttk.Label(f, text="Subject prefix:").grid(row=0, column=0, sticky="w")
    ttk.Entry(f, textvariable=prefix).grid(row=0, column=1, sticky="ew", padx=6)
    ttk.Label(f, text="Max attachment MB:").grid(row=1, column=0, sticky="w", pady=(6, 0))
    ttk.Entry(f, textvariable=max_mb, width=8).grid(row=1, column=1, sticky="w", padx=6, pady=(6, 0))
    f.columnconfigure(1, weight=1)

    # -- Save/Test bar ---
    bar = ttk.Frame(root)
    bar.pack(fill="x", padx=10, pady=(0, 10))

    status = StringVar(value=f"Config: {CONFIG_PATH}")
    ttk.Label(bar, textvariable=status, foreground="#555").pack(side="left")

    def do_save():
        try:
            rcp_raw = rcp_text.get("1.0", END).strip().splitlines()
            recipients = [r.strip() for r in rcp_raw if r.strip()]
            data = {
                "backend": backend.get(),
                "smtp_user": smtp_user.get().strip(),
                "smtp_password": smtp_password.get(),
                "from_name": from_name.get(),
                "recipients": recipients,
                "smtp_host": smtp_host.get().strip() or "smtp.gmail.com",
                "smtp_port": int(smtp_port.get() or 587),
                "max_attachment_mb": float(max_mb.get() or 20),
                "include_primary": bool(inc_p.get()),
                "include_secondary": bool(inc_s.get()),
                "include_map": bool(inc_m.get()),
                "subject_prefix": prefix.get(),
            }
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_PATH.write_text(_dump_yaml(data))
            os.chmod(CONFIG_PATH, 0o600)
            status.set(f"Saved to {CONFIG_PATH} (mode 0600)")
            messagebox.showinfo("Saved", f"Wrote {CONFIG_PATH}")
        except Exception as e:
            messagebox.showerror("Save failed", f"{e}\n\n{traceback.format_exc()}")

    def do_test():
        do_save()
        messagebox.showinfo(
            "Test send",
            "Will build a bundle and send a real email using your saved config. "
            "Close this dialog, then run:\n\n"
            "  bash tools/mailer/send_now.sh\n\n"
            "or click the desktop icon 'DSLV-ZPDI Send Data'.",
        )

    ttk.Button(bar, text="Save", command=do_save).pack(side="right", padx=4)
    ttk.Button(bar, text="Save + how to test", command=do_test).pack(side="right", padx=4)

    root.mainloop()


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        print(f"GUI failed: {e}", file=sys.stderr)
        print("Tip: edit {} by hand (copy {} first).".format(
            CONFIG_PATH, EXAMPLE_PATH), file=sys.stderr)
        sys.exit(1)
