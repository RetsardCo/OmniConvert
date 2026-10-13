"""OmniConvert main executable launcher script."""

import sys
from pathlib import Path

# Add src to sys.path
src_dir = Path(__file__).resolve().parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

import multiprocessing
from omniconvert.application import run_app

if __name__ == "__main__":
    multiprocessing.freeze_support()

    # CLI / Worker mode dispatch (prevents spawning extra GUI instances when subprocesses are executed)
    if len(sys.argv) > 1:
        if sys.argv[1] == "-c":
            code = sys.argv[2]
            sys.argv = [sys.argv[0]] + sys.argv[3:]
            exec(code, {"__name__": "__main__"})
            sys.exit(0)
        elif sys.argv[1] == "--tts-worker":
            from omniconvert.engines.speech_engine import run_tts_worker
            sys.exit(run_tts_worker(sys.argv[2:]))

    sys.exit(run_app())
