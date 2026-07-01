# Voice audio boundary audit

Date: 2026-07-01

This note records the Gateway-facing boundary for the maintained postmarketOS
Kukui satellite. It replaces the older long-form audio topology dump in this
repository.

Current satellite audio/AEC runtime facts are owned by `phosh-ha-status`:

- native Phosh UI and display agent;
- PipeWire/WebRTC AEC graph;
- `wyoming-satellite` mic/speaker wrapper scripts;
- day/night playback gain;
- local fixed feedback clips;
- playback stop and barge-in endpoints;
- `DiagnosticSnapshot` host probes and repair hints.

Gateway documents should not duplicate full PipeWire topology, environment
variable tables, target repair procedures, or native UI acceptance criteria.
When Gateway needs current satellite state, it consumes the diagnostic snapshot
instead.

## Maintained assumptions

The deployed satellite is expected to expose:

- `sensor.kukui_diagnostic_snapshot`;
- `sensor.kukui_asr_metrics`;
- display-agent `GET /diagnostic-snapshot`;
- display-agent `POST /voice/barge-in`;
- display-agent `POST /voice/playback/stop`;
- PipeWire/AEC evidence through snapshot fields such as `pipewire_graph`;
- native Phosh deployment evidence through `native_ui`;
- ASR endpoint progress through `asr.endpoint`.

TTS-time microphone gating is not current behavior. Do not rely on or
regenerate:

- `KUKUI_TTS_MUTE_GATE`;
- `set-microphone-mute.sh`;
- `--tts-start-command`;
- `--tts-played-command`.

## What LLM Gateway owns

LLM Gateway owns:

- semantic routing and prompt policy;
- Home Assistant tool policy and confirmation state;
- provider fallback and stale-result suppression;
- voice-run timelines;
- trace-safe summaries of satellite diagnostics;
- calls to satellite interruption services when a newer turn supersedes an old
  turn.

LLM Gateway does not own:

- raw microphone capture;
- VAD implementation;
- AEC graph construction;
- satellite speaker gain;
- local OPUS/WAV fallback playback;
- native lock-screen rendering.

## Diagnostic contract

Voice Harness and stored traces should treat these fields as the Gateway-facing
contract:

- first failing diagnostic prerequisite from `checks[].depends_on`;
- `pipewire_graph.aec_enabled`;
- `pipewire_graph.kukui_aec_source_visible`;
- `pipewire_graph.kukui_voice_sink_visible`;
- `pipewire_graph.mic_open_during_tts`;
- `native_ui.enabled`;
- `asr.endpoint.source`;
- ASR progress metrics such as phase, frame counts, upstream VAD state,
  interim/final result counts, and latency fields;
- acoustic report fields when present, including
  `false_vad_during_earcon`, `false_vad_during_tts`,
  `echo_suppression_db`, and `barge_in_detected_during_tts`.

Gateway tests should validate ingestion and rendering of these summaries, not
the target device's audio graph itself.

## Remaining verification

The live full-duplex path still needs measured acoustic evidence:

1. Capture real recordings from the deployed satellite.
2. Generate the compact acoustic report with `lab/audio-glitch-analysis`.
3. Copy it to the configured `KUKUI_ACOUSTIC_REPORT` path.
4. Run `lab/voice-pipeline-smoke` for a real wake -> ASR -> Gateway -> TTS ->
   playback turn.
5. Confirm Voice Harness traces show the same diagnostic snapshot and endpoint
   progress seen by the display agent.
