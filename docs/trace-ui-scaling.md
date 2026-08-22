# Trace UI scaling decision

Measured on the target Home Assistant host on 2026-08-22:

- stored Turns: 9;
- events per Turn: 11–15, median 13;
- largest Turn: 15 events;
- trace storage: 506,577 bytes;
- bundled panel: about 208 KiB;
- bundled Replay Diff module: about 12 KiB.

The current ledger renders tens of rows, not hundreds or thousands. Adding a
virtual-scrolling Adapter now would increase state and measurement complexity
without removing an observed failure. Keep `@tanstack/virtual-core` out of the
bundle until either one query reaches 200 Turns or one Turn reaches 1,000
events. `shouldVirtualizeTrace()` keeps this threshold explicit and tested.

When either threshold is reached, measure scripting/render time on the target
device and introduce the framework-neutral core behind a ledger Adapter. Do not
use the React binding. The Adapter must retain stable row keys, selection, and
accessible row indexes across prepend and filtering, following the useful
parts of DeepSeek Harness's trajectory window rather than copying its entire
frontend runtime.
