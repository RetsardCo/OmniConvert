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

- [ ] Implement a background job queue.
- [ ] Keep conversion work off the UI thread.
- [ ] Add per-job progress and status updates.
- [ ] Add a configurable limit for concurrent jobs.
- [ ] Implement cancellation where supported by the underlying engine.
- [ ] Ensure worker threads communicate with the UI safely.
- [ ] Implement safe subprocess execution with argument arrays.
- [ ] Capture engine output and errors.
- [ ] Add timeouts where appropriate.
- [ ] Create per-job temporary directories.
- [ ] Implement cleanup on success, failure, and cancellation.
- [ ] Prevent source-file overwrites by default.
- [ ] Validate destination paths.
- [ ] Add tests for cancellation, failure propagation, and output collisions.

**Acceptance criteria**
- [ ] Jobs execute in the background, failures are visible, and source files are not overwritten accidentally.

---

## Phase 4 — FFmpeg and Media Engine

### Dependency integration
- [ ] Detect FFmpeg.
- [ ] Detect FFprobe.
- [ ] Read and report installed versions.
- [ ] Detect missing executables and show actionable instructions.
- [ ] Check relevant codecs and capabilities rather than assuming every build supports every codec.

### Media inspection
- [ ] Inspect media containers and streams.
- [ ] Detect audio and video streams.
- [ ] Read duration, dimensions, sample rate, channel count, and available metadata when present.
- [ ] Handle files with no audio stream or no video stream.
- [ ] Handle malformed or unsupported media with useful errors.

### Initial audio/video operations
- [ ] Implement video-to-MP4 using a defined preset.
- [ ] Implement video-to-MKV where supported.
- [ ] Implement video-to-MP3.
- [ ] Implement video-to-WAV.
- [ ] Implement audio-to-MP3.
- [ ] Implement audio-to-WAV.
- [ ] Implement supported audio-to-FLAC.
- [ ] Implement supported video compression settings.
- [ ] Implement supported audio bitrate and sample-rate settings.
- [ ] Implement subtitle extraction where a suitable stream exists.
- [ ] Implement video-to-GIF or frame extraction as a defined operation.
- [ ] Report lossy conversion and stream-selection behavior.

### Media validation
- [ ] Verify output streams with FFprobe.
- [ ] Decode or inspect representative output files.
- [ ] Test missing-stream and corrupt-input cases.
- [ ] Test cancellation and large-file behavior.
- [ ] Verify progress reporting is honest when exact progress is unavailable.

**Acceptance criteria**
- [ ] Representative media operations pass automated integration tests and validate their outputs.

---

## Phase 5 — Image Engine

- [ ] Integrate Pillow.
- [ ] Detect supported image formats.
- [ ] Implement PNG-to-JPEG.
- [ ] Implement JPEG-to-PNG.
- [ ] Implement WEBP conversions where supported.
- [ ] Implement BMP and TIFF operations where supported.
- [ ] Implement image resizing.
- [ ] Implement image rotation and cropping.
- [ ] Implement image compression or quality settings where applicable.
- [ ] Implement GIF frame extraction where supported.
- [ ] Implement ICO generation.
- [ ] Handle transparency and warn when the target format cannot preserve it.
- [ ] Preserve or strip metadata according to explicit settings.
- [ ] Add output validation by reopening images and checking expected properties.
- [ ] Test corrupt images, unusual dimensions, and unsupported formats.

**Acceptance criteria**
- [ ] Each registered image operation has tests and handles transparency and output validation correctly.

---

## Phase 6 — Documents and PDFs

### Office conversion engine
- [ ] Detect LibreOffice.
- [ ] Verify headless conversion on the target Windows environment.
- [ ] Implement DOCX-to-PDF.
- [ ] Implement supported office-to-PDF operations.
- [ ] Implement supported office-to-text operations.
- [ ] Handle timeouts and failed document conversions.
- [ ] Document which formats and output filters are actually supported.

### PDF engine
- [ ] Choose and integrate PyMuPDF and/or pypdf for specific operations.
- [ ] Implement PDF metadata inspection.
- [ ] Implement text extraction.
- [ ] Implement page count and page metadata inspection.
- [ ] Implement supported page splitting or merging only with clear user controls.
- [ ] Implement PDF-to-JSON for a defined metadata/text schema.
- [ ] Implement image-to-PDF.
- [ ] Document limitations of PDF-to-editable-office conversions.
- [ ] Validate output PDFs by reopening them with a compatible library.
- [ ] Test encrypted, malformed, image-only, and large PDFs.

**Acceptance criteria**
- [ ] Document/PDF operations are tested and limitations are displayed to users.

---

## Phase 7 — Structured Data and Text

- [ ] Implement JSON parsing and serialization.
- [ ] Implement CSV parsing and serialization.
- [ ] Implement JSON-to-CSV with an explicit flattening/schema strategy.
- [ ] Implement CSV-to-JSON.
- [ ] Implement supported JSON-to-YAML and YAML-to-JSON routes.
- [ ] Add XML operations only with a suitable parser and safe parser configuration.
- [ ] Implement text encoding conversion where reliably detectable or user-selected.
- [ ] Implement line-ending conversion.
- [ ] Handle nested structures and incompatible schemas explicitly.
- [ ] Validate outputs by parsing them again.
- [ ] Test malformed input, empty files, unusual Unicode, and delimiter edge cases.

**Acceptance criteria**
- [ ] Structured-data outputs parse correctly and schema/flattening limitations are explained.

---

## Phase 8 — Archives and Compression

- [ ] Implement ZIP listing and extraction.
- [ ] Implement ZIP creation.
- [ ] Implement TAR operations.
- [ ] Implement GZ decompression and supported compression workflows.
- [ ] Integrate an additional archive tool for 7Z or other formats if needed.
- [ ] Inspect archive entries before extraction.
- [ ] Prevent archive path traversal.
- [ ] Apply decompressed-size and resource safeguards.
- [ ] Handle duplicate filenames and symbolic links safely.
- [ ] Validate created archives by listing or testing them.
- [ ] Add malicious and malformed archive test cases.

**Acceptance criteria**
- [ ] Archive operations pass safety tests and do not write outside the selected output directory.

---

## Phase 9 — Cross-Category Workflow Planner

- [ ] Define a workflow graph model.
- [ ] Define intermediate artifact ownership and cleanup rules.
- [ ] Implement bounded path search across registered operations.
- [ ] Prevent cycles and excessive workflow length.
- [ ] Display workflow steps before execution.
- [ ] Validate each intermediate output.
- [ ] Stop dependent steps when a previous step fails.
- [ ] Preserve useful error context for each step.
- [ ] Require confirmation for expensive or lossy operations when appropriate.
- [ ] Add a workflow history view.
- [ ] Test direct and multi-step workflows end-to-end.

### Initial workflow candidates
- [ ] Video-to-audio extraction.
- [ ] Image-to-text through OCR.
- [ ] Image-to-audio through OCR and local TTS.
- [ ] Document-to-audio through text extraction and local TTS.
- [ ] Video-to-text through subtitle extraction or optional speech recognition.
- [ ] Video metadata-to-JSON.
- [ ] PDF text/metadata-to-JSON.
- [ ] Archive-to-combined-PDF for eligible contents.
- [ ] CSV-to-video through a defined visualization template.
- [ ] Static executable metadata or strings-to-report operations.

**Acceptance criteria**
- [ ] A workflow can execute multiple operations in sequence, validate intermediates, and report exactly which step failed.

---

## Phase 10 — Optional Local OCR and Speech Engines

- [ ] Choose a local OCR engine and document its license.
- [ ] Implement OCR dependency detection.
- [ ] Make OCR operations unavailable when the engine is missing.
- [ ] Add OCR language selection where supported.
- [ ] Choose a local speech-recognition engine.
- [ ] Document model requirements, storage, and hardware expectations.
- [ ] Make speech-recognition models optional.
- [ ] Choose a local text-to-speech engine.
- [ ] Document voices, languages, model licenses, and output limits.
- [ ] Add explicit controls for model installation and storage.
- [ ] Ensure conversion jobs do not call cloud inference APIs.
- [ ] Test missing models and insufficient resources.
- [ ] Add integration tests using small permitted fixtures.

**Acceptance criteria**
- [ ] Optional models are clearly managed, operate locally, and do not block core conversion features when absent.

---

## Phase 11 — UI Completion and Usability

- [ ] Complete home screen.
- [ ] Complete conversion workspace.
- [ ] Complete job queue and status views.
- [ ] Complete history screen.
- [ ] Complete settings screen.
- [ ] Complete searchable format/operation explorer.
- [ ] Add context-sensitive settings.
- [ ] Add warnings for lossy conversion.
- [ ] Add clear dependency error messages.
- [ ] Add output folder opening.
- [ ] Add retry behavior where safe.
- [ ] Add keyboard accessibility and sensible tab order.
- [ ] Test long filenames and unusual Unicode paths.
- [ ] Test mixed-format batch input.
- [ ] Verify the UI does not show unavailable operations.

**Acceptance criteria**
- [ ] A user can add files, select a valid operation, configure it, run it, and locate the validated output without using a command line.

---

## Phase 12 — Privacy, Security, and Reliability

- [ ] Review every network-related dependency and code path.
- [ ] Ensure conversion engines receive local files only.
- [ ] Ensure no file upload or cloud conversion route exists.
- [ ] Ensure telemetry does not transmit file paths, contents, or history.
- [ ] Document any optional updater or model downloader.
- [ ] Test path traversal protections.
- [ ] Test subprocess argument handling.
- [ ] Test malformed inputs.
- [ ] Test archive-bomb and oversized-file safeguards.
- [ ] Test output collisions and source protection.
- [ ] Review logs for accidental sensitive content.
- [ ] Test temporary-file cleanup.
- [ ] Document that local processing does not make malicious inputs harmless.

**Acceptance criteria**
- [ ] Local-only behavior and core safety protections have been tested and documented.

---

## Phase 13 — Packaging and Release

- [ ] Choose installer, portable package, or split core/optional-engine distribution.
- [ ] Build with PyInstaller or the selected packaging tool.
- [ ] Confirm external tools and native libraries are available in the packaged environment.
- [ ] Confirm resources and configuration paths work outside the development directory.
- [ ] Add a startup dependency report.
- [ ] Test on a clean supported Windows machine or VM.
- [ ] Verify optional dependencies fail gracefully.
- [ ] Review third-party licenses and distribution obligations.
- [ ] Generate required license notices.
- [ ] Add application version and changelog.
- [ ] Test install, launch, conversion, upgrade, and uninstall behavior where applicable.
- [ ] Document known limitations.
- [ ] Publish the verified supported-format matrix.

**Acceptance criteria**
- [ ] The packaged application runs on a clean supported Windows environment and performs the documented operations.

---

## Phase 14 — Final Regression and Release Gate

- [ ] Run all unit tests.
- [ ] Run all integration tests.
- [ ] Run workflow tests.
- [ ] Run security tests.
- [ ] Run packaging tests.
- [ ] Verify that all advertised operations have tests.
- [ ] Verify that every registered operation has documented limitations.
- [ ] Verify that unsupported routes are explained.
- [ ] Verify that source files are not overwritten.
- [ ] Verify that UI work remains responsive during conversion.
- [ ] Verify local-only processing.
- [ ] Review README and installation instructions.
- [ ] Review `OmniConvertDoc.md`.
- [ ] Review and update `SUPPORTED_FORMATS.md`.
- [ ] Update `CHANGELOG.md`.
- [ ] Mark the release ready only after all required checks pass.

**Release acceptance criteria**
- [ ] The application launches and runs on a clean supported Windows environment.
- [ ] Representative conversions work and outputs are validated.
- [ ] Multi-step workflows report failures correctly.
- [ ] No known critical data-loss or path-safety issue remains open.
- [ ] The verified capability matrix matches the implementation.
- [ ] Dependencies and licensing are documented.

---

## Antigravity Working Rules

Use these instructions whenever continuing implementation:

- [ ] Read `OmniConvertDoc.md` and this checklist before starting a new milestone.
- [ ] Inspect current files before editing them.
- [ ] Preserve working code and user changes.
- [ ] State which milestone and checklist items are being addressed.
- [ ] Implement a small, coherent change.
- [ ] Run relevant tests and report actual results.
- [ ] Fix regressions before moving forward.
- [ ] Update checklist items only after verification.
- [ ] Update the supported-format matrix only after tests pass.
- [ ] Never claim an operation works merely because its UI control exists.
- [ ] Never silently rename an extension and call it conversion.
- [ ] Never claim tests passed unless they were actually run.
- [ ] Avoid unnecessary rewrites and giant monolithic files.
- [ ] Record new dependencies and license-review tasks.
- [ ] End each milestone with a concise summary of files changed, tests run, known issues, and next tasks.

## Recommended first task

Begin with Phase 0 and Phase 1 only. Inspect the repository, set up the environment, create the initial PySide6 application shell, implement basic file selection and detection, define the registry interface, and add smoke tests. Do not implement all format engines at once.

---

**End of checklist.**
