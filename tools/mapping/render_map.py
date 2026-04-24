"""Render an interactive satellite map of DSLV-ZPDI events.

Reads primary HDF5 + secondary JSONL via tools.mapping.aggregate, then
emits a single self-contained HTML file using Folium.

Layers:
    * ESRI World Imagery (satellite) — default base layer, no API key required.
    * OpenStreetMap                  — fallback labeled base layer.
    * Primary events (red pins)      — labeled with r_smooth, timestamp.
    * Secondary events (blue pins)   — labeled with node_id, reason.
    * Anchor marker                  — sensor anchor + antenna heading cone.

Primary events are clustered to keep render time sane on large captures.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import sys
import webbrowser
from pathlib import Path

# Allow running as a module or as a script from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import folium
from folium.plugins import MarkerCluster

from mapping.aggregate import Anchor, MapEvent, collect_all


DEFAULT_OUT = Path.home() / ".local" / "share" / "dslv-zpdi" / "map.html"


def _fmt_ts(ts: float) -> str:
    if not ts or ts <= 0:
        return "—"
    try:
        return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    except (OverflowError, ValueError, OSError):
        return str(ts)


def _popup_html(e: MapEvent) -> str:
    rows = [
        ("Event", e.event_id),
        ("Source", e.source_file),
        ("Time (UTC)", _fmt_ts(e.timestamp_utc)),
        ("Lat", f"{e.latitude:.6f}"),
        ("Lon", f"{e.longitude:.6f}"),
    ]
    for k, v in e.metrics.items():
        if isinstance(v, float):
            rows.append((k, f"{v:.6f}"))
        elif v is not None:
            rows.append((k, str(v)))
    # Escape everything that came from a file — JSONL node_id / reason /
    # HDF5 payload UUIDs are operator-controlled but we still don't want
    # a stray < in a reason string to break the popup.
    body = "".join(
        f"<tr><td style='padding-right:8px;color:#888'>{html.escape(str(k))}</td>"
        f"<td style='font-family:monospace'>{html.escape(str(v))}</td></tr>"
        for k, v in rows
    )
    color = "#d7263d" if e.kind == "primary" else "#1f77b4"
    return (
        f"<div style='font-family:sans-serif;font-size:12px;min-width:280px'>"
        f"<div style='color:{color};font-weight:bold;margin-bottom:4px'>"
        f"{html.escape(e.kind.upper())} · {html.escape(e.label)}</div>"
        f"<table style='border-collapse:collapse'>{body}</table></div>"
    )


def build_map(anchor: Anchor, events: list[MapEvent]) -> folium.Map:
    center = (anchor.latitude, anchor.longitude)
    # Default to a high zoom if we have a real anchor, otherwise pull way
    # out so the "unconfigured" pin at 0,0 is obviously off.
    zoom = 17 if (anchor.latitude or anchor.longitude) else 2

    fmap = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles=None,
        control_scale=True,
    )

    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community",
        name="Satellite (ESRI)",
        overlay=False,
        control=True,
        max_zoom=19,
    ).add_to(fmap)
    folium.TileLayer(
        tiles="OpenStreetMap",
        name="Streets (OSM)",
        overlay=False,
        control=True,
    ).add_to(fmap)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
        attr="Labels © Esri",
        name="Labels overlay",
        overlay=True,
        control=True,
    ).add_to(fmap)

    # Anchor marker + antenna cone.
    # Default Bootstrap Glyphicons ship with Folium — no FontAwesome dep.
    node_id_esc = html.escape(anchor.node_id)
    site_esc = html.escape(anchor.site_name)
    folium.Marker(
        location=center,
        tooltip=f"{anchor.node_id} · {anchor.site_name}",
        popup=folium.Popup(
            f"<b>{node_id_esc}</b><br>{site_esc}<br>"
            f"Lat/Lon: {anchor.latitude:.6f}, {anchor.longitude:.6f}<br>"
            f"Alt: {anchor.altitude_m:.1f} m<br>"
            f"Antenna heading: {anchor.antenna_heading_deg:.1f}°",
            max_width=320,
        ),
        icon=folium.Icon(color="green", icon="signal"),
    ).add_to(fmap)

    if anchor.latitude or anchor.longitude:
        # Draw a small directional wedge. Just two rays 70° apart.
        from mapping.aggregate import _offset
        ray_len = 120.0  # metres
        lat_l, lon_l = _offset(anchor.latitude, anchor.longitude,
                               anchor.antenna_heading_deg - 35, ray_len)
        lat_r, lon_r = _offset(anchor.latitude, anchor.longitude,
                               anchor.antenna_heading_deg + 35, ray_len)
        folium.Polygon(
            locations=[center, (lat_l, lon_l), (lat_r, lon_r), center],
            color="#2ecc71", weight=1, fill=True, fill_color="#2ecc71", fill_opacity=0.12,
            tooltip="Antenna cone",
        ).add_to(fmap)

    # Split into primary/secondary clusters.
    primary = folium.FeatureGroup(name="Primary (tier 1)", show=True)
    secondary = folium.FeatureGroup(name="Secondary (tier 2)", show=True)

    primary_cluster = MarkerCluster(name="Primary cluster").add_to(primary)
    secondary_cluster = MarkerCluster(name="Secondary cluster").add_to(secondary)

    for e in events:
        color = "red" if e.kind == "primary" else "blue"
        marker = folium.Marker(
            location=(e.latitude, e.longitude),
            tooltip=e.label,
            popup=folium.Popup(_popup_html(e), max_width=360),
            icon=folium.Icon(color=color, icon="info-sign"),
        )
        if e.kind == "primary":
            marker.add_to(primary_cluster)
        else:
            marker.add_to(secondary_cluster)

    primary.add_to(fmap)
    secondary.add_to(fmap)
    folium.LayerControl(collapsed=False).add_to(fmap)

    # Legend
    n_primary = sum(1 for e in events if e.kind == "primary")
    n_secondary = sum(1 for e in events if e.kind == "secondary")
    legend = (
        "<div style='position:fixed;bottom:20px;left:20px;z-index:9999;"
        "background:rgba(0,0,0,0.80);color:#fff;padding:10px 14px;"
        "border-radius:6px;font:13px/1.4 sans-serif;"
        "box-shadow:0 2px 8px rgba(0,0,0,0.4)'>"
        "<div style='font-weight:bold;margin-bottom:4px'>DSLV-ZPDI Map</div>"
        f"<div>Anchor: {html.escape(anchor.node_id)} "
        f"({html.escape(anchor.site_name)})</div>"
        f"<div>Events: {len(events)} "
        f"(<span style='color:#ff5555'>{n_primary}</span> primary / "
        f"<span style='color:#5599ff'>{n_secondary}</span> secondary)</div>"
        "<div style='margin-top:4px'>"
        "<span style='color:#ff5555'>&#9679;</span> Primary (tier 1) &nbsp;"
        "<span style='color:#5599ff'>&#9679;</span> Secondary (tier 2) &nbsp;"
        "<span style='color:#2ecc71'>&#9679;</span> Anchor"
        "</div></div>"
    )
    fmap.get_root().html.add_child(folium.Element(legend))

    return fmap


def main():
    p = argparse.ArgumentParser(description="Render DSLV-ZPDI satellite map")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output HTML path")
    p.add_argument("--config", type=Path, help="sensor_location.yaml path (optional)")
    p.add_argument("--max-primary", type=int, default=2000)
    p.add_argument("--max-secondary", type=int, default=2000)
    p.add_argument("--open", action="store_true", help="open the map in a browser when done")
    args = p.parse_args()

    anchor, events = collect_all(
        config_path=args.config,
        max_primary=args.max_primary,
        max_secondary=args.max_secondary,
    )

    fmap = build_map(anchor, events)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fmap.save(str(args.out))

    n_primary = sum(1 for e in events if e.kind == "primary")
    n_secondary = sum(1 for e in events if e.kind == "secondary")
    print(f"[map] anchor: {anchor.node_id} @ {anchor.latitude:.6f},{anchor.longitude:.6f}")
    print(f"[map] events: primary={n_primary}  secondary={n_secondary}")
    print(f"[map] wrote: {args.out}")

    if args.open:
        webbrowser.open(f"file://{args.out}")


if __name__ == "__main__":
    main()
