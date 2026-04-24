#!/usr/bin/env bash
# DSLV-ZPDI HDF5 data browser.
#
# Opens a terminal sized for the DSI screen and lets the user pick an
# HDF5 file to inspect with h5ls / h5dump. Not fancy — it's an escape
# hatch into the raw telemetry when the dashboard isn't enough.
set -Eeuo pipefail

REPO="/home/dynogator/dslv-zpdi"
PRIMARY="$REPO/output/primary"

# Build a menu of the 20 most recent HDF5 captures.
mapfile -t FILES < <(ls -t "$PRIMARY"/*.h5 2>/dev/null | head -20)

if [ ${#FILES[@]} -eq 0 ]; then
    echo "No HDF5 captures found under $PRIMARY"
    read -rp "Press enter to close..."
    exit 1
fi

echo "==============================================================="
echo "          DSLV-ZPDI :: HDF5 Data Browser"
echo "==============================================================="
echo
for i in "${!FILES[@]}"; do
    f="${FILES[$i]}"
    sz=$(du -h "$f" | cut -f1)
    printf "  %2d) %-52s %s\n" "$i" "$(basename "$f")" "$sz"
done
echo
read -rp "Pick a file number (or q to quit): " pick
case "$pick" in
    q|Q|"") exit 0 ;;
esac

if ! [[ "$pick" =~ ^[0-9]+$ ]] || [ "$pick" -ge "${#FILES[@]}" ]; then
    echo "invalid selection"
    read -rp "Press enter to close..."
    exit 1
fi

FILE="${FILES[$pick]}"
echo
echo "=== h5stat: $(basename "$FILE") ==="
h5stat "$FILE" | sed -n '1,15p'

echo
echo "=== h5ls (first 30 entries) ==="
h5ls "$FILE" | head -30

echo
echo "=== commands ==="
echo "  d = full h5dump (paged)"
echo "  s = stats only"
echo "  l = h5ls -r (recursive)"
echo "  q = quit"
while :; do
    read -rp "action> " a
    case "$a" in
        d) h5dump "$FILE" | less -R ;;
        s) h5stat "$FILE" | less -R ;;
        l) h5ls -r "$FILE" | less -R ;;
        q|Q|"") break ;;
        *) echo "unknown action" ;;
    esac
done
