import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from nadi9 import __version__
from nadi9.engine import Engine
from nadi9.models import Correction, Limits, Pack, State
from nadi9.providers import ReplayProvider
from nadi9.storage import export, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Evidence-grounded Nadi-9 subtitle proposals")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Validate a structured evidence pack")
    validate.add_argument("pack", type=Path)
    schema = commands.add_parser("schema", help="Print the input JSON schema")
    schema.add_argument("kind", choices=["pack", "correction", "state"])
    run = commands.add_parser("run", help="Plan, propose, verify and export subtitles")
    run.add_argument("pack", type=Path)
    run.add_argument("--max-model-calls", type=int, default=25)
    run.add_argument("--max-tool-calls", type=int, default=50)
    resume = commands.add_parser("resume", help="Resume a partially processed episode")
    resume.add_argument("state", type=Path)
    correct = commands.add_parser("correct", help="Apply evidence corrections and replan")
    correct.add_argument("state", type=Path)
    correct.add_argument("correction", type=Path)
    for command in (run, resume, correct):
        command.add_argument("--out", type=Path, required=True)
        command.add_argument("--max-lines", type=int)
        command.add_argument("--simulate-failures", type=int, default=0)
    arguments = parser.parse_args()
    try:
        if arguments.command == "schema":
            model = {"pack": Pack, "correction": Correction, "state": State}[arguments.kind]
            print(json.dumps(model.model_json_schema(), indent=2))
            return
        if arguments.command == "validate":
            pack = Pack.model_validate_json(arguments.pack.read_text())
            print(json.dumps({"valid": True, "pack": pack.id, "synthetic": pack.synthetic}))
            return
        if arguments.max_lines is not None and arguments.max_lines < 0:
            raise ValueError("max-lines must be nonnegative")
        if arguments.simulate_failures < 0:
            raise ValueError("simulate-failures must be nonnegative")
        provider = ReplayProvider(arguments.simulate_failures)
        if arguments.command == "run":
            pack = Pack.model_validate_json(arguments.pack.read_text())
            limits = Limits(
                max_model_calls=arguments.max_model_calls, max_tool_calls=arguments.max_tool_calls
            )
            engine = Engine.start(pack, limits, provider)
        else:
            engine = Engine(State.model_validate_json(arguments.state.read_text()), provider)
        affected = None
        if arguments.command == "correct":
            correction = Correction.model_validate_json(arguments.correction.read_text())
            affected = engine.correct(correction)
        state = engine.run(arguments.max_lines)
        export(state, arguments.out)
        result = summary(state)
        if affected is not None:
            result["reprocessed"] = affected
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, ValidationError) as error:
        parser.exit(2, f"error: {error}\n")


if __name__ == "__main__":
    main()
