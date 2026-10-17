"""Explicit local file operations with English/French help and human messages."""

import argparse
import json
from pathlib import Path
import sys
from yaml import YAMLError

from .capture import prepare
from .contracts import load_document
from .errors import PipelineError
from .handoff import prepare_handoff
from .language import error_text, text
from .pipeline import ENGINE_VERSION, run
from .storage import verify_snapshot


def _language(argv):
    for index, argument in enumerate(argv):
        if argument == "--language" and index + 1 < len(argv):
            return argv[index + 1] if argv[index + 1] in {"en", "fr"} else "en"
        if argument.startswith("--language="):
            return argument.split("=", 1)[1] if argument.split("=", 1)[1] in {"en", "fr"} else "en"
    if "--task" in argv:
        try:
            language = load_document(Path(argv[argv.index("--task") + 1]))["language"]
            return language if language in {"en", "fr"} else "en"
        except (OSError, ValueError, KeyError, TypeError, IndexError, YAMLError):
            pass
    if "--run" in argv:
        try:
            language = load_document(Path(argv[argv.index("--run") + 1]) / "review-package.json")["language"]
            return language if language in {"en", "fr"} else "en"
        except (OSError, ValueError, KeyError, TypeError, IndexError, YAMLError):
            pass
    return "en"


class _Parser(argparse.ArgumentParser):
    def __init__(self, *args, language="en", **kwargs):
        self.language = language
        kwargs["add_help"] = False
        super().__init__(*args, **kwargs)
        self._positionals.title = "commandes" if language == "fr" else "commands"
        self._optionals.title = "options"
        self.add_argument("-h", "--help", action="help", help=text(language, "cli.help"))

    def format_help(self):
        value = super().format_help()
        return value.replace("usage:", "utilisation :", 1) if self.language == "fr" else value

    def error(self, message):
        prefix = "the following arguments are required: "
        translated = text(self.language, "cli.required", arguments=message.removeprefix(prefix)) if message.startswith(prefix) else text(self.language, "cli.usage_error")
        self.exit(2, json.dumps({"error": "cli.usage", "message": translated}, ensure_ascii=False) + "\n")


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    argv = list(sys.argv[1:] if argv is None else argv)
    language = _language(argv)
    t = lambda key: text(language, key)
    parser = _Parser(prog="agent-agriculture", language=language, description=t("cli.description"))
    parser.add_argument("--version", action="version", version=ENGINE_VERSION, help=t("cli.version"))
    parser.add_argument("--language", choices=("en", "fr"), default=language, help=t("cli.language"))
    commands = parser.add_subparsers(dest="command", required=True, parser_class=lambda **kwargs: _Parser(language=language, **kwargs))

    def command(name):
        child = commands.add_parser(name, help=t("cli." + name), description=t("cli." + name))
        child.add_argument("--language", choices=("en", "fr"), default=argparse.SUPPRESS, help=t("cli.language"))
        return child

    reconcile = command("reconcile")
    for flag in ("task", "manifest", "output", "corrections"):
        reconcile.add_argument("--" + flag, type=Path, required=flag != "corrections", help=t("cli." + flag))
    verify = command("verify")
    verify.add_argument("path", type=Path, help=t("cli.path"))
    handoff = command("handoff")
    handoff.add_argument("--run", type=Path, required=True, help=t("cli.run_path"))
    handoff.add_argument("--output", type=Path, required=True, help=t("cli.output"))
    capture = command("capture")
    capture.add_argument("--purchase", type=Path, required=True, help=t("cli.purchase_file"))
    capture.add_argument("--receiving", type=Path, help=t("cli.receiving_file"))
    capture.add_argument("--output", type=Path, required=True, help=t("cli.output"))
    for flag in ("task-id", "enterprise", "jurisdiction", "start", "end", "currency", "question", "recipient", "current-tool"):
        capture.add_argument("--" + flag, required=True, help=t("cli." + flag.replace("-", "_")))
    capture.add_argument("--coverage", choices=("complete", "partial", "unknown"), required=True, help=t("cli.coverage"))
    capture.add_argument("--omission", action="append", default=[], help=t("cli.omission"))
    for flag in ("authority", "mapping", "transcription"):
        capture.add_argument("--confirm-" + flag, action="store_true", help=t("cli.confirm_" + flag))
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            marker = verify_snapshot(args.path)
            result = {"run_id": marker["run_id"], "integrity": "verified", "message": t("cli.verified")}
        elif args.command == "handoff":
            result = prepare_handoff(args.run, args.output)
        elif args.command == "capture":
            result = prepare(purchase=args.purchase, receiving=args.receiving, output=args.output, task_id=args.task_id,
                             enterprise=args.enterprise, jurisdiction=args.jurisdiction, start=args.start, end=args.end,
                             currency=args.currency, language=args.language, question=args.question, recipient=args.recipient,
                             current_tool=args.current_tool, coverage=args.coverage, omissions=args.omission,
                             confirm_authority=args.confirm_authority, confirm_mapping=args.confirm_mapping, confirm_transcription=args.confirm_transcription)
            result["message"] = t("capture.saved")
        else:
            result = run(args.task, args.manifest, args.output, args.corrections, language=args.language)
            result["message"] = t("cli.saved")
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except PipelineError as exc:
        error = {"error": exc.code, "message": error_text(language, exc.code)}
        if exc.code.startswith("contract."):
            constraint, _, location = str(exc).partition(" at ")
            error.update(constraint=constraint, location=location or "/")
        print(json.dumps(error, ensure_ascii=False), file=sys.stderr)
    except (OSError, ValueError, KeyError, TypeError, YAMLError):
        print(json.dumps({"error": "input_or_output.unavailable", "message": error_text(language, "input_or_output.unavailable")}, ensure_ascii=False), file=sys.stderr)
    return 2
