# Troubleshooting

## Detection packages: Install required

Stop the server with Ctrl+C. Run `powershell -ExecutionPolicy Bypass -File .\Install-Detection.ps1`, then restart with `powershell -ExecutionPolicy Bypass -File .\Start.ps1`. Re-enter the recorder login because restart clears memory. Verify imports with the command in [COMMANDS.md](COMMANDS.md).

## Package installation or Python compatibility errors

Use Python 3.11 or 3.12 with a dedicated `.venv`. Newer interpreter versions may not have compatible binary wheels for every inference dependency. Inspect the first installation error. For DNS/proxy/network failures, restore normal access to package registries and retry. Do not disable security controls or use unknown package mirrors.

## The dashboard does not open

Confirm the server window shows `http://127.0.0.1:8765`. Keep that window open and enter the URL in the browser address bar. Opening `web/index.html` directly does not start the backend. If port 8765 is occupied, close the older Sentinel Desk process normally. The server deliberately rejects unexpected Host headers.

## TCP port test fails

Check the recorder IP, the actual RTSP port, and local network reachability. SmartPSS's device service may use port 37777; do not confuse it with the RTSP service. This application does not alter NVR network settings.

## TCP test succeeds but no picture appears

Reachability only proves a TCP port accepted a connection. Verify credentials, account permissions, connected channel, stream choice and enabled substream. Select main stream if your configuration has no usable substream, while monitoring resource usage. First start may still be downloading model weights. Check local output-folder permissions if detection stops after an event.

## The camera is loading slowly

First launch may download weights. CPU inference and high-resolution decoding also take time. Begin with one camera and a lower-bandwidth substream. Preview refresh is approximately every 1.5 seconds, and displayed FPS is processing throughput rather than end-to-end video delay.

## Zone or rule changes do not affect the current session

The worker reads these settings when monitoring starts. Stop the camera, wait for it to finish, then restart. Draw the zone on an available camera frame. The default zone covers the central 70% of the image.

## Repeated or missed events

Missing detections reset dwell. Tracker ID changes can split a person into new tracks, and re-entry starts new rule state. Review lighting, occlusion, camera angle, thresholds and annotated evidence. Cooldown applies per event type and active track, not globally to a person's real identity.

## Events disappear after restart

The dashboard event list and acknowledgements live in memory. JPEG evidence and `events/events.csv` remain on disk; automatic reloading is not implemented. The dashboard CSV export includes up to 200 recent in-memory events, not necessarily the complete on-disk history.

## Stream disconnects or stop is delayed

There is no automatic reconnection in this version. Restart monitoring after connectivity recovers. Stop waits for the current operation; a model download or blocking decoder operation can delay it. Ctrl+C shuts down the server.

## How to report a problem

Include OS and Python/package versions, selected stream type, reproducible steps and redacted error text. Do not include passwords, authenticated RTSP URLs, actual recorder addresses, identifiable footage or security-sensitive site information.
