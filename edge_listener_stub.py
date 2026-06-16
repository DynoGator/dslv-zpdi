"""Edge listener stub for dslv-zpdi.

Listens on localhost:8443 for sensor payloads, verifies their SHA-256
provenance, and prints the results.
"""

import asyncio
import hashlib
import json
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s EdgeStub: %(message)s",
)
log = logging.getLogger("edge-stub")

async def handle_connection(websocket):
    addr = websocket.remote_address
    log.info("Connection from %s", addr)
    try:
        async for message in websocket:
            if not isinstance(message, (str, bytes)):
                log.warning("Received message of unknown type: %s", type(message))
                continue
            try:
                # 1. Parse JSON
                if isinstance(message, bytes):
                    raw_received = message
                    data = json.loads(message.decode("utf-8"))
                else:
                    raw_received = message.encode("utf-8")
                    data = json.loads(message)

                # 2. Extract provided digest
                provided_digest = data.pop("sha256", None)
                if not provided_digest:
                    log.warning("Received payload without 'sha256' field")
                    continue

                # 3. Recompute hash of the remaining fields
                # We must use the same canonical serialization as the node.
                canonical_raw = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
                actual_digest = hashlib.sha256(canonical_raw).hexdigest()

                # 4. Verify
                if actual_digest == provided_digest:
                    log.info("VERIFIED: node=%s wall=%s digest=%s...", 
                             data.get("node"), 
                             data.get("timestamps", {}).get("wall_ns"),
                             actual_digest[:12])
                else:
                    log.error("INTEGRITY FAILURE!")
                    log.error("  Provided: %s", provided_digest)
                    log.error("  Actual:   %s", actual_digest)

            except json.JSONDecodeError:
                log.error("Failed to decode JSON message")
            except Exception as e:
                log.exception("Error processing message: %s", e)
    except Exception as e:
        log.debug("Connection closed with error: %s", e)
    finally:
        log.info("Disconnected from %s", addr)

async def main():
    import websockets
    server = await websockets.serve(handle_connection, "localhost", 8443)
    log.info("Edge listener stub running on ws://localhost:8443")
    async with server:
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
