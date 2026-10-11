# OmniConvert — Full Project Documentation

**Document:** `OmniConvertDoc.md`  
**Project:** OmniConvert  
**Document type:** Product requirements, technical design, implementation guide  
**Status:** Planning baseline  
**Target platform:** Windows desktop  
**Processing model:** Local-first / offline-capable after dependencies are installed  
**Primary implementation language:** Python  
**UI framework:** PySide6

---

## 1. Project Overview

OmniConvert is a Windows desktop application designed to convert, transform, extract, package, and inspect a broad range of file types from one unified interface.

The target categories include:

- Documents and office files
- PDFs and text formats
- Raster and vector images
- Audio
- Video
- Archives and compressed files
- Structured data
- Source code and logs
- Metadata and selected binary-file representations
- Multi-step workflows that combine operations across categories

OmniConvert is intended to be a practical universal file-processing workspace. It should support broad useful coverage without claiming that every file extension can be meaningfully converted into every other extension.

### 1.1 Core product principle

**An operation must transform or represent the file's contents; changing the extension alone is never a conversion.**

Some operations are direct format conversions. Others require extraction, rendering, recognition, transcription, serialization, or a sequence of transformations. The application must make the selected operation and its limitations clear.

### 1.2 Product direction

- Windows-only desktop application.
- No website as the product interface.
- No cloud conversion APIs.
- No mandatory user account.
- Local processing of user-selected files.
- Offline conversion after all required dependencies and optional models are installed.
- Broad format coverage expanded incrementally through independent conversion engines.
- A capability registry drives the UI and conversion planner.
- Source files must not be overwritten by default.

---

## 2. Goals and Non-Goals

### 2.1 Goals

1. Provide a single interface for a broad set of file-processing operations.
2. Support meaningful cross-category workflows.
3. Support batch jobs and per-file settings.
4. Identify file types using content inspection where feasible, not extensions alone.
5. Discover which operations are available with the currently installed engines.
6. Keep conversion work off the UI thread.
7. Validate output files after operations.
8. Provide understandable errors and logs.
9. Keep processing local and avoid sending file contents to remote services.
10. Package the application for Windows installation or portable distribution.
11. Keep the architecture modular so new engines and operations can be added without rewriting the UI.
12. Maintain automated tests and an explicit support matrix.

### 2.2 Non-goals for the first release

- Guaranteeing every possible format pair.
- Perfect reconstruction of complex PDF layouts into editable office documents.
- Executing or emulating EXE files to infer their behavior.
- Building a website or remote conversion service.
- Bundling every possible codec, model, and external tool into the first installer.
- Guaranteeing lossless conversion between inherently incompatible or lossy formats.
- Replacing specialized professional applications for every proprietary format.
- Claiming that a format is supported solely because its extension appears in a dropdown.

---

## 3. Users and Primary Workflows

### 3.1 Typical user

A Windows user who needs one application for common file conversion, media extraction, batch processing, document handling, and selected cross-category transformations.

### 3.2 Core workflows

1. Add one or more files by browsing or drag-and-drop.
2. Inspect detected type, size, metadata, and available operations.
3. Choose a direct conversion or a defined multi-step workflow.
4. Configure relevant output options.
5. Choose an output folder and filename policy.
6. Start the job and monitor progress.
7. Review warnings, errors, and validation results.
8. Open the output location or review conversion history.

### 3.3 Cross-category examples

These are examples of possible workflows, subject to implementation and dependency availability:

| Input | Output | Defined operation |
|---|---|---|
| MP4 | MP3 | Extract and encode the audio stream |
| MP4 | WAV | Extract audio and encode PCM audio |
| Video with subtitles | TXT | Extract a subtitle stream, if present |
| Video | TXT | Local speech recognition, if configured |
| Video | JSON | Export metadata, stream details, or a structured transcript |
| JPG | TXT | OCR recognition |
| JPG | PDF | Place the image into a PDF page |
| JPG | WAV | OCR text, then local text-to-speech |
| DOCX | MP3 | Extract document text, then local text-to-speech |
| PDF | JSON | Extract text, tables, or metadata into a defined schema |
| ZIP | PDF | Extract eligible contents and combine supported documents into PDF, subject to explicit workflow settings |
| EXE | TXT | Extract eligible printable strings without executing the file |
| EXE | JSON | Export static file metadata or analysis results |
| CSV | MP4 | Generate a video using a user-selected visualization or slideshow template |

These are not all first-release commitments. Each route must be added to the capability registry only after its engine, dependencies, validation, and tests exist.

---

## 4. Supported Format Strategy

Format support is a matrix of operations, not a single yes/no property for an extension. The actual capability depends on the file's container, codecs, structure, installed engines, and selected operation.

### 4.1 Documents and office files

Initial candidates:

- DOCX, DOC, ODT, RTF
- PDF
- TXT, Markdown, HTML
- XLSX, XLS, CSV, TSV
- PPTX, ODP
- Additional office formats where tested

Potential operations:

- Office document to PDF
- Supported office formats to text
- Markdown to HTML
- HTML to PDF using a suitable local renderer
- CSV to JSON
- JSON to CSV when a compatible schema is defined
- PDF text and metadata extraction
- PDF page/image extraction where supported
- PDF-to-editable-document conversion only with explicit quality caveats

### 4.2 Images and graphics

Initial candidates:

- PNG, JPG/JPEG, WEBP, BMP, TIFF, GIF, ICO
- AVIF and SVG where compatible libraries are installed

Potential operations:

- Raster image format conversion
- Resize, rotate, crop, and compression
- GIF frame extraction
- Image metadata extraction or removal
- Image-to-PDF
- OCR to text
- SVG rasterization where supported
- ICO generation
- Transparency-aware conversion

The UI must warn when converting an image with transparency to a format that does not support transparency.

### 4.3 Audio

Initial candidates:

- WAV, MP3, FLAC, AAC, M4A, OGG, Opus, AIFF
- Other formats supported by the selected FFmpeg build

Potential operations:

- Audio transcoding
- Bitrate and quality settings
- Sample-rate and channel conversion
- Audio extraction from video
- Metadata inspection and supported metadata editing
- Audio-to-text through an optional local speech-recognition engine
- Text-to-audio through an optional local TTS engine

### 4.4 Video

Initial candidates:

- MP4, MKV, MOV, AVI, WEBM, WMV, MPEG
- Additional containers and codecs when verified

Potential operations:

- Video transcoding
- Resolution, bitrate, frame-rate, and quality controls where supported
- Audio extraction
- Subtitle extraction where a compatible stream exists
- Frame extraction
- Metadata and stream inspection
- Video-to-GIF
- Video-to-text through subtitle extraction or optional local speech recognition
- Video-to-JSON metadata/transcript export
- Video generation from a supported slideshow or visualization template

### 4.5 Archives

Initial candidates:

- ZIP, TAR, GZ
- 7Z and other formats through compatible external tools

Potential operations:

- Extract archives
- Repack extracted contents into another supported archive format
- Compress files
- Inspect archive entries before extraction

Security requirements include path traversal protection, archive-bomb safeguards, resource limits, and safe handling of symbolic links and unusual file entries.

### 4.6 Structured data and text

Initial candidates:

- JSON, XML, YAML, CSV, TSV, SQL
- TXT, Markdown, HTML, source-code text, and logs

Potential operations:

- Parse and serialize between compatible data representations
- Text encoding conversion
- Line-ending conversion
- JSON/YAML/XML transformations when data structures are compatible
- CSV-to-JSON and JSON-to-CSV with explicit handling of arrays, nested values, and schemas
- Static text and metadata extraction from selected file types

Do not promise semantics-preserving conversion where the source and destination models differ. Provide warnings or ask for a schema or flattening strategy.

### 4.7 Other and binary files

For selected binary formats, the application may provide defined operations such as:

- File signature and metadata inspection
- Hexadecimal dump
- Printable-string extraction
- Hash calculation
- Static metadata reports
- Safe extraction of known embedded resources when a dedicated parser exists

These operations are representations or analyses, not generic semantic conversions. Never execute a selected file to inspect it.

---

## 5. Technology Stack

### 5.1 Core application

- **Python:** application logic and engine orchestration.
- **PySide6:** desktop UI.
- **pytest:** automated tests.
- **PyInstaller:** packaging baseline for Windows.

### 5.2 Conversion engines

- **FFmpeg / FFprobe:** media inspection, decoding, encoding, extraction, and transcoding.
- **Pillow:** common raster-image operations.
- **LibreOffice:** supported office document conversions, including headless workflows.
- **PyMuPDF and/or pypdf:** selected PDF operations.
- **Tesseract or another local OCR engine:** OCR workflows.
- **Optional local speech recognition:** for example, a compatible faster-whisper setup.
- **Optional local text-to-speech:** choose a maintained engine that can run locally.
- **Python standard library:** selected archive and structured-data operations.
- **Additional external tools:** only after their capabilities, distribution model, compatibility, and licensing are reviewed.

### 5.3 Dependency policy

The core application must detect dependencies at startup and explain missing components. It must not crash merely because an optional engine is unavailable.

Separate dependencies into:

1. Required application dependencies.
2. Required dependencies for a specific operation.
3. Optional engines.
4. Optional model files.
5. Build-time packaging tools.

Optional OCR, speech-recognition, and TTS models should not be mandatory for basic media, image, and document conversion.

### 5.4 Licensing

Before redistributing any dependency, review its license, version-specific terms, codec implications, and bundling requirements. Do not assume that a Python package license covers an external executable, codec, model, or model weights. Record third-party components and their licenses in a dependency inventory.

---

## 6. High-Level Architecture

### 6.1 Logical pipeline

1. **Input selection:** receive paths from the user.
2. **File inspection:** inspect extension, signature, metadata, streams, size, and relevant properties.
3. **Operation discovery:** query the capability registry.
4. **Planning:** select a direct operation or compatible workflow graph.
5. **Execution:** run the selected engine in a worker.
6. **Progress reporting:** send progress and log events to the UI.
7. **Output validation:** verify output existence, parseability, streams, schema, or expected properties.
8. **Delivery:** move or retain the output safely in the destination folder.
9. **History:** record operation, status, timing, and non-sensitive metadata.

### 6.2 Suggested repository structure

```text
OmniConvert/
├── app.py
├── requirements.txt
├── pyproject.toml
├── README.md
├── OmniConvertDoc.md
├── OmniToDo.md
├── src/
│   └── omniconvert/
│       ├── __init__.py
│       ├── application.py
│       ├── config/
│       │   ├── settings.py
│       │   └── paths.py
│       ├── ui/
│       │   ├── main_window.py
│       │   ├── home_view.py
│       │   ├── conversion_view.py
│       │   ├── queue_view.py
│       │   ├── history_view.py
│       │   ├── settings_view.py
│       │   └── format_explorer.py
│       ├── core/
│       │   ├── file_detector.py
│       │   ├── metadata.py
│       │   ├── registry.py
│       │   ├── planner.py
│       │   ├── job_manager.py
│       │   ├── validation.py
│       │   ├── temp_files.py
│       │   └── errors.py
│       ├── models/
│       │   ├── capability.py
│       │   ├── conversion_job.py
│       │   └── workflow.py
│       ├── engines/
│       │   ├── base.py
│       │   ├── ffmpeg_engine.py
│       │   ├── image_engine.py
│       │   ├── document_engine.py
│       │   ├── pdf_engine.py
│       │   ├── archive_engine.py
│       │   ├── data_engine.py
│       │   ├── ocr_engine.py
│       │   └── speech_engine.py
│       └── resources/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── fixtures/
│   └── security/
├── scripts/
│   ├── check_dependencies.py
│   └── build_windows.py
└── packaging/
    ├── pyinstaller/
    └── licenses/
```

This is a proposed layout. It may be adjusted to match an existing repository after inspection. Avoid creating unused modules solely to match the diagram.

---

## 7. Conversion Capability Registry

The registry is the source of truth for what the application advertises.

### 7.1 Example capability

```json
{
  "id": "video.extract_mp3",
  "display_name": "Extract audio to MP3",
  "input_categories": ["video"],
  "output_category": "audio",
  "input_formats": ["mp4", "mkv", "mov", "avi"],
  "output_formats": ["mp3"],
  "engine": "ffmpeg",
  "operation": "extract_audio",
  "settings_schema": {
    "bitrate": {
      "type": "choice",
      "values": ["128k", "192k", "256k", "320k"],
      "default": "192k"
    }
  },
  "lossy": true,
  "requires_user_choice": false,
  "optional_dependencies": [],
  "validation": "probe_and_decode_audio",
  "limitations": [
    "Source must contain a readable audio stream",
    "MP3 encoding is lossy"
  ]
}
```

This is an illustrative registry entry. Production validation must verify the actual installed FFmpeg build and the source file's streams and codecs.

### 7.2 Registry rules

- Each operation has a stable unique identifier.
- Input and output constraints must be explicit.
- Container support must not be confused with codec support.
- Required and optional dependencies must be distinguished.
- Settings must be validated before execution.
- The UI must derive available options from registered capabilities.
- An operation is not advertised if its required engine is unavailable.
- Runtime inspection can further restrict capabilities for a particular input.
- Validation must be defined for each operation or engine family.
- Unsupported routes must produce an actionable explanation.

---

## 8. Workflow Planner

### 8.1 Purpose

The planner finds a valid sequence of registered operations from the detected source to the requested output or representation.

### 8.2 Workflow examples

**Image to spoken audio**

1. Validate and decode image.
2. Run OCR.
3. Let the user review or edit recognized text where appropriate.
4. Run local text-to-speech.
5. Encode or save the selected audio format.
6. Validate the audio output.

**Document to audio**

1. Read document using a compatible parser or conversion engine.
2. Extract text.
3. Apply text cleanup if selected.
4. Generate speech using a local TTS engine.
5. Save and validate audio.

**Video to transcript**

1. Inspect streams and subtitles.
2. If suitable subtitles exist, extract them.
3. Otherwise, offer local speech recognition if installed.
4. Export transcript to TXT, SRT, VTT, or JSON as supported.
5. Validate output structure.

**CSV to video**

1. Parse CSV.
2. Ask for a chart, animation, or slideshow template.
3. Validate columns and visualization settings.
4. Render visual frames.
5. Encode video through a compatible engine.
6. Validate the resulting video.

### 8.3 Planning constraints

- Avoid cycles and unbounded workflow search.
- Set a maximum number of workflow steps.
- Require user confirmation for expensive or lossy operations where appropriate.
- Use temporary intermediate files with clear ownership and cleanup rules.
- Do not pass malformed or failed intermediate outputs to subsequent steps.
- Record each step's status and error.
- Do not silently substitute a different operation.
- Do not claim that all possible source/destination pairs have a path.

---

## 9. User Interface Requirements

### 9.1 Home

- Drag-and-drop zone.
- Browse button.
- Recent files or jobs, without exposing file contents.
- Quick access to common operations.
- Clear local-processing status.

### 9.2 Conversion workspace

- Input list and detected type.
- File details and available streams.
- Searchable operation list.
- Destination format or output representation.
- Contextual settings.
- Output directory and naming rules.
- Warnings about lossiness or limitations.
- Start action and preflight validation.

### 9.3 Job manager

Suggested states:

- Queued
- Inspecting
- Waiting for dependency
- Running
- Validating
- Completed
- Completed with warnings
- Failed
- Cancelled

Progress should be reported only when the engine provides meaningful progress information. Do not invent precise percentages for engines that cannot report them.

### 9.4 History

- Operation name.
- Input and output filenames.
- Completion status.
- Start time and duration.
- Error summary when relevant.
- Open output folder action.
- Retry action where the source remains available.

History must not store file contents. Users should be able to clear history and configure retention.

### 9.5 Settings

- Default output folder.
- Filename collision policy.
- Temporary directory.
- Maximum concurrent jobs.
- Resource limits.
- Dependency status.
- Optional model status and location.
- Theme and UI preferences.
- History retention.
- Logging level.
- Privacy and network behavior.

### 9.6 Format explorer

- Search by extension, category, or operation.
- Show supported inputs and outputs.
- Explain required engines.
- Show limitations and lossy behavior.
- Distinguish installed capabilities from unavailable optional capabilities.

---

## 10. Job Execution and Concurrency

- Never perform long-running conversion work on the UI thread.
- Use worker objects or a controlled thread pool.
- Limit concurrent resource-intensive jobs.
- Use subprocess argument arrays rather than shell-interpolated command strings.
- Capture standard output and standard error safely.
- Handle process startup failure and abnormal termination.
- Support cancellation where the engine permits it.
- Ensure cancellation terminates child processes appropriately.
- Distinguish job cancellation from application shutdown.
- Avoid updating UI widgets directly from worker threads.
- Persist only the job metadata needed for history and recovery.
- Do not automatically resume a partially written output without validation.

---

## 11. Output Naming, Temporary Files, and Validation

### 11.1 Source protection

- Never overwrite the source by default.
- Use a temporary output and finalize it only after successful validation where feasible.
- Apply a collision policy such as rename, ask, or replace with explicit user confirmation.
- Normalize and validate output paths.
- Prevent path traversal.

### 11.2 Temporary files

- Use a dedicated application-controlled temporary directory.
- Create unique per-job workspaces.
- Track ownership of intermediate files.
- Clean up on success, failure, and cancellation.
- Do not delete user-selected source files.
- If cleanup fails, report the location and provide safe manual cleanup guidance.

### 11.3 Validation

Validation should be specific to the operation:

- Media: inspect streams and attempt decoding.
- Images: reopen the output and verify dimensions and mode.
- Documents: open or parse the output with a compatible tool.
- JSON/XML/YAML: parse the output.
- CSV: parse rows and verify expected columns where known.
- Archives: list entries and validate archive readability.
- Text: verify encoding and non-empty content when expected.
- Multi-step workflows: validate every intermediate output before proceeding.

A successful process exit code alone is not sufficient evidence that the output is valid.

---

## 12. Security and Reliability

Input files must be treated as untrusted.

Requirements:

- Do not execute input files.
- Validate file paths and destination paths.
- Use safe subprocess invocation.
- Avoid shell injection.
- Apply limits for very large inputs and decompression ratios.
- Prevent archive path traversal.
- Avoid unbounded memory loading of large files.
- Apply timeouts to engines that can hang.
- Isolate temporary output paths.
- Handle malformed media and documents without crashing the whole app.
- Do not display raw, unescaped file contents as UI markup.
- Keep logs useful but avoid logging sensitive document contents.
- Review third-party parser and engine security advisories during maintenance.
- Do not disable Windows security features as part of installation.

The application should clearly state that local processing does not make malicious files harmless; it simply avoids sending the file to a remote conversion service.

---

## 13. Privacy and Network Policy

### 13.1 Required behavior

- File contents remain on the local machine during conversion.
- No cloud conversion APIs.
- No account requirement.
- No telemetry that transmits file paths, contents, or conversion history.
- Optional model downloads must be explicit.
- Network use for updates or downloads must be separate from conversion jobs.
- The app must function offline for operations whose dependencies are installed.

### 13.2 Verification

Test local-only behavior by:

- Reviewing network-related dependencies and code paths.
- Ensuring conversion engines receive local paths or local data only.
- Checking that no remote service is called by a conversion operation.
- Inspecting network activity during representative conversions.
- Documenting any optional update or download behavior.

Do not claim that the application never uses the network under every circumstance if its updater or optional model downloader can access the internet.

---

## 14. Testing Strategy

### 14.1 Unit tests

Test file detection, registry filtering, settings validation, path handling, naming policy, planner constraints, and error mapping.

### 14.2 Integration tests

Test representative conversions with small known fixtures. Verify content and output properties, not just filenames.

### 14.3 Workflow tests

Test multi-step chains, intermediate validation, failure propagation, cleanup, and retry behavior.

### 14.4 Security tests

Test path traversal attempts, malformed files, archive traversal, filename collisions, unusual Unicode names, large files, and subprocess argument safety.

### 14.5 Packaging tests

Test installation and launch on a clean supported Windows environment. Verify dependency detection and ensure that bundled executables and resources resolve correctly.

### 14.6 Test fixture policy

Use legally redistributable or internally generated fixtures. Avoid including copyrighted sample media or sensitive personal documents without permission.

### 14.7 Definition of done for an operation

An operation is complete only when:

1. It is registered.
2. Required dependencies are declared.
3. Input and settings validation exist.
4. Execution is implemented.
5. Errors are handled.
6. Output validation exists.
7. Unit or integration tests pass.
8. UI capability discovery works.
9. Limitations are documented.
10. The operation appears in the support matrix.

---

## 15. Packaging and Release

### 15.1 Packaging approach

Use PyInstaller as the initial packaging approach, but verify all external dependencies separately.

Potential distribution models:

- **Installer:** installs the application and approved dependencies.
- **Portable package:** keeps application files and supported bundled tools in a local directory.
- **Core installer plus optional engines:** keeps the base installer smaller and lets users install additional capabilities.

Choose the model after measuring package size, reviewing licenses, and testing on clean Windows systems.

### 15.2 External dependency handling

FFmpeg, LibreOffice, OCR tools, speech models, and other external components may have independent installation and distribution requirements. A PyInstaller build does not automatically guarantee that they are available.

At startup, report:

- Found dependency and version.
- Missing dependency.
- Available operations affected.
- Installation or configuration instructions.
- Whether the dependency is mandatory or optional.

### 15.3 Release checklist

- Version number and changelog.
- Dependency inventory.
- License notices.
- Clean-machine tests.
- Windows Defender and packaging false-positive review where relevant.
- Installer or portable-package verification.
- Crash and error logging review.
- User documentation.
- Known limitations.
- Backup and recovery guidance for settings and history.

---

## 16. Documentation Deliverables

Maintain:

- `OmniConvertDoc.md`: product and technical specification.
- `OmniToDo.md`: phased implementation checklist.
- `README.md`: installation, usage, build, and troubleshooting.
- `SUPPORTED_FORMATS.md`: verified operation matrix.
- `ARCHITECTURE.md`: module responsibilities and data flow.
- `THIRD_PARTY_LICENSES.md`: bundled component and license inventory.
- `CHANGELOG.md`: release history.
- `CONTRIBUTING.md`: optional development conventions if collaboration begins.

The support matrix must distinguish planned, implemented, tested, and unavailable operations.

---

## 17. Antigravity Development Instructions

Use Antigravity as an incremental implementation assistant.

1. Inspect the repository before changing files.
2. Preserve existing working code and user changes.
3. Read the project documentation and checklist before implementation.
4. Propose a short plan for the next milestone.
5. Implement one cohesive milestone at a time.
6. Run relevant tests after each change.
7. Fix regressions before expanding scope.
8. Update `OmniToDo.md` only when work is verified.
9. Update the support matrix only when tests pass.
10. Do not claim tests passed unless they were actually run.
11. Do not invent conversion support.
12. Keep source modules reasonably sized and focused.
13. Use clear types, interfaces, and structured error handling.
14. Document new dependencies and their licensing implications.
15. Never remove project files or rewrite major modules without checking their current purpose.

### First implementation task

Build only the initial foundation:

- Inspect the repository.
- Create the project structure as needed.
- Establish the Python environment and dependency checks.
- Create a working PySide6 window.
- Implement safe file selection and basic file identification.
- Define the capability registry interface.
- Add a minimal job model and logging.
- Write initial tests.
- Verify that the application launches.

Do not attempt to implement all conversion engines in the first pass.

---

## 18. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Scope becomes too broad | Use milestones and operation-level acceptance criteria |
| Missing external dependencies | Dependency checker and clear per-operation availability |
| Incorrect format assumptions | Inspect signatures, containers, codecs, and content |
| Loss of document layout | Report conversion limitations and validate output |
| Large installer | Optional engines and models; review bundle strategy |
| Unsafe malformed files | Resource limits, safe subprocesses, validation, and security tests |
| UI freezes | Background workers and bounded concurrency |
| Fake conversion support | Registry entries require implementation and tests |
| Local privacy claims become inaccurate | Audit network behavior and document updater/model downloads |
| License incompatibility | Maintain a third-party dependency and license inventory |
| Model storage consumes disk space | Make models optional and show size requirements |
| Incomplete cleanup | Per-job temporary workspaces and cleanup tests |

---

## 19. Initial Release Acceptance Criteria

The initial release is ready for broader testing when:

- The Windows desktop application launches reliably.
- Files can be added and inspected.
- The registry drives operation availability.
- At least a representative set of image and media conversions works end-to-end.
- A background job queue keeps the UI responsive.
- Errors and unsupported operations are explained.
- Outputs are validated.
- Source files are protected.
- Local-only processing behavior has been checked.
- Tests run successfully in the development environment.
- Packaging and dependency requirements are documented.
- The verified support matrix is available.
- Known limitations are explicit.

The exact list of supported formats for the initial release must be determined by tested implementation, not by the aspirational list in this document.

---

## 20. Reference Documentation

Consult current official documentation before selecting versions or implementing specific operations:

- FFmpeg: https://ffmpeg.org/documentation.html
- Pillow: https://pillow.readthedocs.io/en/stable/
- PySide6: https://doc.qt.io/qtforpython-6/
- LibreOffice: https://www.libreoffice.org/
- PyMuPDF: https://pymupdf.readthedocs.io/
- pypdf: https://pypdf.readthedocs.io/
- pytest: https://docs.pytest.org/
- PyInstaller: https://pyinstaller.org/
- Tesseract OCR: https://tesseract-ocr.github.io/
- faster-whisper: https://github.com/SYSTRAN/faster-whisper

Documentation and licenses can change by version. Verify the actual versions selected for the project.

---

**End of document.**
