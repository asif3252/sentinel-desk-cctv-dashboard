# Contributing

Open a focused issue describing expected behavior, actual behavior, reproduction steps, Python/package versions and redacted environment details. Use synthetic or authorized non-identifying media. Do not submit secrets or site-specific security information.

For a source change:

1. Create a focused branch or fork.
2. Keep the dashboard and backend behavior consistent.
3. Add meaningful tests when alert rules, request validation or data handling change.
4. Run `python -m unittest discover -s . -p test_server.py`.
5. Run `node --check web/app.js` if JavaScript changed.
6. Explain what changed, why, how it was verified and any remaining limitations.

Useful areas include bounded frame buffering, graceful stream recovery, measurable performance, saved zones, event retention and accessibility. Report benchmarks with hardware, camera count, resolution, input FPS, measurement duration and end-to-end delay. Do not present estimates as observed results.
