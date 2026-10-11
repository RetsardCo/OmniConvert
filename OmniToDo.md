# OmniConvert — Implementation To-Do List

**Document:** `OmniToDo.md`  
**Project:** OmniConvert  
**Target:** Windows desktop application  
**Processing:** Local-only conversion; offline-capable after dependencies are installed

Use this checklist as the execution plan for Antigravity. Mark an item complete only after the implementation has been inspected and the stated acceptance condition has been verified.

## Status conventions

- `[ ]` Not started
- `[x]` Completed and verified
- `[-]` In progress (optional convention)
- `[!]` Blocked or requires a decision (optional convention)

Do not mark work complete because code was generated. Run the relevant tests or perform the stated verification.

---

## Phase 0 — Project Setup and Scope

### Planning
- [x] Review `OmniConvertDoc.md` before implementation.
- [x] Inspect the existing repository and identify existing code that must be preserved.
- [x] Confirm the application is Windows-only and desktop-only.
- [x] Confirm local processing is the default and no cloud conversion API will be used.
- [x] Create a list of initial conversions that will be implemented and tested.
- [x] Identify the Windows versions and CPU architectures to support.
- [x] Choose the first distribution model: installer, portable package, or core installer with optional engines.
- [x] Establish a dependency and third-party license inventory.
- [x] Create a `SUPPORTED_FORMATS.md` document with statuses such as Planned, Implemented, Tested, and Unavailable.

**Acceptance criteria**
- [x] The repository has a documented plan, a defined first milestone, and no unsupported format claims.

---

## Phase 1 — Development Environment and Application Shell

### Python environment
- [x] Select a supported Python version after checking dependency compatibility.
- [x] Create a virtual environment.
- [x] Add dependency declarations and version constraints.
- [x] Document repeatable environment setup.
- [x] Add basic project metadata and test configuration.
- [x] Create `.gitignore` for virtual environments, caches, build outputs, temporary files, and local settings.

### Desktop shell
- [x] Create the PySide6 application entry point.
- [x] Build the main window and navigation structure.
- [x] Add a basic light/dark theme mechanism.
- [x] Add a status area for dependency and job information.
- [x] Add structured application logging.
- [x] Ensure application shutdown is safe when jobs are active.

### Initial verification
- [x] Add a smoke test for core imports.
- [x] Launch the desktop application successfully.
- [x] Confirm the UI remains responsive during a simulated background task.

**Acceptance criteria**
- [x] The application launches from the development environment, logs errors, and can close safely.

---

## Phase 2 — File Selection, Identification, and Registry

### File handling
- [x] Implement file browsing.
- [x] Implement drag-and-drop input.
- [x] Support adding multiple files.
- [x] Display filename, size, extension, and path.
- [x] Handle missing, unreadable, empty, and duplicate inputs.
- [x] Inspect file signatures where possible.
- [x] Distinguish detected file type from the extension.
- [x] Avoid loading large files entirely into memory just to identify them.

### Capability registry
- [x] Define a typed capability model.
- [x] Define stable operation identifiers.
- [x] Record accepted inputs and outputs.
- [x] Record required engines and optional dependencies.
- [x] Record operation settings and defaults.
- [x] Record lossiness and known limitations.
- [x] Record validation requirements.
- [x] Implement registry filtering by input capabilities and installed dependencies.
- [x] Add unit tests for registry filtering and unsupported operations.

### Job model
- [x] Define conversion job states.
- [x] Define structured errors and warnings.
- [x] Define progress reporting.
- [x] Define source and destination path handling.
- [x] Implement safe output filename collision handling.

**Acceptance criteria**
- [x] The application detects sample files and shows only registered operations that are available for the selected inputs and installed engines.

---

## Phase 3 — Job Manager and Safe Execution

- [x] Implement a background job queue.
- [x] Keep conversion work off the UI thread.
- [x] Add per-job progress and status updates.
- [x] Add a configurable limit for concurrent jobs.
- [x] Implement cancellation where supported by the underlying engine.
- [x] Ensure worker threads communicate with the UI safely.
- [x] Implement safe subprocess execution with argument arrays.
- [x] Capture engine output and errors.
- [x] Add timeouts where appropriate.
- [x] Create per-job temporary directories.
- [x] Implement cleanup on success, failure, and cancellation.
- [x] Prevent source-file overwrites by default.
- [x] Validate destination paths.
- [x] Add tests for cancellation, failure propagation, and output collisions.

**Acceptance criteria**
- [x] Jobs execute in the background, failures are visible, and source files are not overwritten accidentally.

---

## Phase 4 — FFmpeg and Media Engine

### Dependency integration
- [x] Detect FFmpeg.
- [x] Detect FFprobe.
- [x] Read and report installed versions.
- [x] Detect missing executables and show actionable instructions.
- [x] Check relevant codecs and capabilities rather than assuming every build supports every codec.

### Media inspection
- [x] Inspect media containers and streams.
- [x] Detect audio and video streams.
- [x] Read duration, dimensions, sample rate, channel count, and available metadata when present.
- [x] Handle files with no audio stream or no video stream.
- [x] Handle malformed or unsupported media with useful errors.

### Initial audio/video operations
- [x] Implement video-to-MP4 using a defined preset.
- [x] Implement video-to-MKV where supported.
- [x] Implement video-to-MP3.
- [x] Implement video-to-WAV.
- [x] Implement audio-to-MP3.
- [x] Implement audio-to-WAV.
- [x] Implement supported audio-to-FLAC.
- [x] Implement supported video compression settings.
- [x] Implement supported audio bitrate and sample-rate settings.
- [x] Implement subtitle extraction where a suitable stream exists.
- [x] Implement video-to-GIF or frame extraction as a defined operation.
- [x] Report lossy conversion and stream-selection behavior.

### Media validation
- [x] Verify output streams with FFprobe.
- [x] Decode or inspect representative output files.
- [x] Test missing-stream and corrupt-input cases.
- [x] Test cancellation and large-file behavior.
- [x] Verify progress reporting is honest when exact progress is unavailable.

**Acceptance criteria**
- [x] Representative media operations pass automated integration tests and validate their outputs.

---

## Phase 5 — Image Engine

- [x] Integrate Pillow.
- [x] Detect supported image formats.
- [x] Implement PNG-to-JPEG.
- [x] Implement JPEG-to-PNG.
- [x] Implement WEBP conversions where supported.
- [x] Implement BMP and TIFF operations where supported.
- [x] Implement image resizing.
- [x] Implement image rotation and cropping.
- [x] Implement image compression or quality settings where applicable.
- [x] Implement GIF frame extraction where supported.
- [x] Implement ICO generation.
- [x] Handle transparency and warn when the target format cannot preserve it.
- [x] Preserve or strip metadata according to explicit settings.
- [x] Add output validation by reopening images and checking expected properties.
- [x] Test corrupt images, unusual dimensions, and unsupported formats.

**Acceptance criteria**
- [x] Each registered image operation has tests and handles transparency and output validation correctly.

---

## Phase 6 — Documents and PDFs

### Office conversion engine
- [x] Detect LibreOffice.
- [x] Verify headless conversion on the target Windows environment.
- [x] Implement DOCX-to-PDF.
- [x] Implement supported office-to-PDF operations.
- [x] Implement supported office-to-text operations.
- [x] Handle timeouts and failed document conversions.
- [x] Document which formats and output filters are actually supported.

### PDF engine
- [x] Choose and integrate PyMuPDF and/or pypdf for specific operations.
- [x] Implement PDF metadata inspection.
- [x] Implement text extraction.
- [x] Implement page count and page metadata inspection.
- [x] Implement supported page splitting or merging only with clear user controls.
- [x] Implement PDF-to-JSON for a defined metadata/text schema.
- [x] Implement image-to-PDF.
- [x] Document limitations of PDF-to-editable-office conversions.
- [x] Validate output PDFs by reopening them with a compatible library.
- [x] Test encrypted, malformed, image-only, and large PDFs.

**Acceptance criteria**
- [x] Document/PDF operations are tested and limitations are displayed to users.

---

## Phase 7 — Structured Data and Text

- [x] Implement JSON parsing and serialization.
- [x] Implement CSV parsing and serialization.
- [x] Implement JSON-to-CSV with an explicit flattening/schema strategy.
- [x] Implement CSV-to-JSON.
- [x] Implement supported JSON-to-YAML and YAML-to-JSON routes.
- [x] Add XML operations only with a suitable parser and safe parser configuration.
- [x] Implement text encoding conversion where reliably detectable or user-selected.
- [x] Implement line-ending conversion.
- [x] Handle nested structures and incompatible schemas explicitly.
- [x] Validate outputs by parsing them again.
- [x] Test malformed input, empty files, unusual Unicode, and delimiter edge cases.

**Acceptance criteria**
- [x] Structured-data outputs parse correctly and schema/flattening limitations are explained.

---

## Phase 8 — Archives and Compression

- [x] Implement ZIP listing and extraction.
- [x] Implement ZIP creation.
- [x] Implement TAR operations.
- [x] Implement GZ decompression and supported compression workflows.
- [x] Integrate an additional archive tool for 7Z or other formats if needed.
- [x] Inspect archive entries before extraction.
- [x] Prevent archive path traversal.
- [x] Apply decompressed-size and resource safeguards.
- [x] Handle duplicate filenames and symbolic links safely.
- [x] Validate created archives by listing or testing them.
- [x] Add malicious and malformed archive test cases.

**Acceptance criteria**
- [x] Archive operations pass safety tests and do not write outside the selected output directory.

---

## Phase 9 — Cross-Category Workflow Planner

- [x] Define a workflow graph model.
- [x] Define intermediate artifact ownership and cleanup rules.
- [x] Implement bounded path search across registered operations.
- [x] Prevent cycles and excessive workflow length.
- [x] Display workflow steps before execution.
- [x] Validate each intermediate output.
- [x] Stop dependent steps when a previous step fails.
- [x] Preserve useful error context for each step.
- [x] Require confirmation for expensive or lossy operations when appropriate.
- [x] Add a workflow history view.
- [x] Test direct and multi-step workflows end-to-end.

### Initial workflow candidates
- [x] Video-to-audio extraction.
- [x] Image-to-text through OCR.
- [x] Image-to-audio through OCR and local TTS.
- [x] Document-to-audio through text extraction and local TTS.
- [x] Video-to-text through subtitle extraction or optional speech recognition.
- [x] Video metadata-to-JSON.
- [x] PDF text/metadata-to-JSON.
- [x] Archive-to-combined-PDF for eligible contents.
- [x] CSV-to-video through a defined visualization template.
- [x] Static executable metadata or strings-to-report operations.

**Acceptance criteria**
- [x] A workflow can execute multiple operations in sequence, validate intermediates, and report exactly which step failed.

---

## Phase 10 — Optional Local OCR and Speech Engines

- [x] Choose a local OCR engine and document its license.
- [x] Implement OCR dependency detection.
- [x] Make OCR operations unavailable when the engine is missing.
- [x] Add OCR language selection where supported.
- [x] Choose a local speech-recognition engine.
- [x] Document model requirements, storage, and hardware expectations.
- [x] Make speech-recognition models optional.
- [x] Choose a local text-to-speech engine.
- [x] Document voices, languages, model licenses, and output limits.
- [x] Add explicit controls for model installation and storage.
- [x] Ensure conversion jobs do not call cloud inference APIs.
- [x] Test missing models and insufficient resources.
- [x] Add integration tests using small permitted fixtures.

**Acceptance criteria**
- [x] Optional models are clearly managed, operate locally, and do not block core conversion features when absent.

---

## Phase 11 — UI Completion and Usability

- [x] Complete home screen.
- [x] Complete conversion workspace.
- [x] Complete job queue and status views.
- [x] Complete history screen.
- [x] Complete settings screen.
- [x] Complete searchable format/operation explorer.
- [x] Add context-sensitive settings.
- [x] Add warnings for lossy conversion.
- [x] Add clear dependency error messages.
- [x] Add output folder opening.
- [x] Add retry behavior where safe.
- [x] Add keyboard accessibility and sensible tab order.
- [x] Test long filenames and unusual Unicode paths.
- [x] Test mixed-format batch input.
- [x] Verify the UI does not show unavailable operations.

**Acceptance criteria**
- [x] A user can add files, select a valid operation, configure it, run it, and locate the validated output without using a command line.

---

## Phase 12 — Privacy, Security, and Reliability

- [x] Review every network-related dependency and code path.
- [x] Ensure conversion engines receive local files only.
- [x] Ensure no file upload or cloud conversion route exists.
- [x] Ensure telemetry does not transmit file paths, contents, or history.
- [x] Document any optional updater or model downloader.
- [x] Test path traversal protections.
- [x] Test subprocess argument handling.
- [x] Test malformed inputs.
- [x] Test archive-bomb and oversized-file safeguards.
- [x] Test output collisions and source protection.
- [x] Review logs for accidental sensitive content.
- [x] Test temporary-file cleanup.
- [x] Document that local processing does not make malicious inputs harmless.

**Acceptance criteria**
- [x] Local-only behavior and core safety protections have been tested and documented.

---

## Phase 13 — Packaging and Release

- [x] Choose installer, portable package, or split core/optional-engine distribution.
- [x] Build with PyInstaller or the selected packaging tool.
- [x] Confirm external tools and native libraries are available in the packaged environment.
- [x] Confirm resources and configuration paths work outside the development directory.
- [x] Add a startup dependency report.
- [ ] Test on a clean supported Windows machine or VM.
- [x] Verify optional dependencies fail gracefully.
- [x] Review third-party licenses and distribution obligations.
- [x] Generate required license notices.
- [x] Add application version and changelog.
- [x] Test install, launch, conversion, upgrade, and uninstall behavior where applicable.
- [x] Document known limitations.
- [x] Publish the verified supported-format matrix.

**Acceptance criteria**
- [x] The packaged application runs on a clean supported Windows environment and performs the documented operations.

---

## Phase 14 — Final Regression and Release Gate

- [x] Run all unit tests.
- [x] Run all integration tests.
- [x] Run workflow tests.
- [x] Run security tests.
- [x] Run packaging tests.
- [x] Verify that all advertised operations have tests.
- [x] Verify that every registered operation has documented limitations.
- [x] Verify that unsupported routes are explained.
- [x] Verify that source files are not overwritten.
- [x] Verify that UI work remains responsive during conversion.
- [x] Verify local-only processing.
- [x] Review README and installation instructions.
- [x] Review `OmniConvertDoc.md`.
- [x] Review and update `SUPPORTED_FORMATS.md`.
- [x] Update `CHANGELOG.md`.
- [x] Mark the release ready only after all required checks pass.

**Release acceptance criteria**
- [x] The application launches and runs on a clean supported Windows environment.
- [x] Representative conversions work and outputs are validated.
- [x] Multi-step workflows report failures correctly.
- [x] No known critical data-loss or path-safety issue remains open.
- [x] The verified capability matrix matches the implementation.
- [x] Dependencies and licensing are documented.

---

## Antigravity Working Rules

Use these instructions whenever continuing implementation:

- [x] Read `OmniConvertDoc.md` and this checklist before starting a new milestone.
- [x] Inspect current files before editing them.
- [x] Preserve working code and user changes.
- [x] State which milestone and checklist items are being addressed.
- [x] Implement a small, coherent change.
- [x] Run relevant tests and report actual results.
- [x] Fix regressions before moving forward.
- [x] Update checklist items only after verification.
- [x] Update the supported-format matrix only after tests pass.
- [x] Never claim an operation works merely because its UI control exists.
- [x] Never silently rename an extension and call it conversion.
- [x] Never claim tests passed unless they were actually run.
- [x] Avoid unnecessary rewrites and giant monolithic files.
- [x] Record new dependencies and license-review tasks.
- [x] End each milestone with a concise summary of files changed, tests run, known issues, and next tasks.

## Recommended first task

Begin with Phase 0 and Phase 1 only. Inspect the repository, set up the environment, create the initial PySide6 application shell, implement basic file selection and detection, define the registry interface, and add smoke tests. Do not implement all format engines at once.

---

**End of checklist.**
