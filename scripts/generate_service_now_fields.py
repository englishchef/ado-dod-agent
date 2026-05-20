"""CLI entrypoint for Phase 5B ServiceNow field draft generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from backend.app.models.llm_outputs import CombinedLlmOutputs
    from backend.app.services.llm.azure_foundry_client import AzureFoundryChatClient, LlmClientError
    from backend.app.services.llm.generator import generate_all_buckets
    from backend.app.services.storage.local_store import LocalJsonStore
    from backend.app.utils.config import get_settings
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.app.models.llm_outputs import CombinedLlmOutputs
    from backend.app.services.llm.azure_foundry_client import AzureFoundryChatClient, LlmClientError
    from backend.app.services.llm.generator import generate_all_buckets
    from backend.app.services.storage.local_store import LocalJsonStore
    from backend.app.utils.config import get_settings


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate ServiceNow field drafts from Phase 4 evidence buckets."
    )
    parser.add_argument("--build-id", type=int, required=True)
    parser.add_argument("--evidence-bundle", type=str, default=None)
    parser.add_argument("--bucket-1", type=str, default=None)
    parser.add_argument("--bucket-2", type=str, default=None)
    parser.add_argument("--bucket-3", type=str, default=None)
    return parser


def run_generation(args: argparse.Namespace) -> dict[str, Any]:
    """Load evidence, invoke the generator, persist outputs, and return a safe summary."""

    settings = get_settings()
    store = LocalJsonStore(settings)
    evidence_bundle, source_path = _load_evidence_inputs(args, store)

    client = AzureFoundryChatClient(settings=settings)
    outputs = generate_all_buckets(
        build_id=args.build_id,
        evidence_bundle=evidence_bundle,
        client=client,
        source_path=source_path,
    )
    output_paths = persist_outputs(store=store, build_id=args.build_id, outputs=outputs)
    return build_summary(outputs=outputs, output_paths=output_paths)


def persist_outputs(
    *,
    store: LocalJsonStore,
    build_id: int,
    outputs: CombinedLlmOutputs,
) -> dict[str, str]:
    """Persist per-bucket and combined LLM output artifacts."""

    return {
        "bucket_1_output_path": store.save_output_json(
            build_id, "bucket_1_output.json", outputs.bucket_1.model_dump(mode="json")
        ),
        "bucket_2_output_path": store.save_output_json(
            build_id, "bucket_2_output.json", outputs.bucket_2.model_dump(mode="json")
        ),
        "bucket_3_output_path": store.save_output_json(
            build_id, "bucket_3_output.json", outputs.bucket_3.model_dump(mode="json")
        ),
        "llm_outputs_path": store.save_output_json(
            build_id, "llm_outputs.json", outputs.model_dump(mode="json")
        ),
    }


def build_summary(
    *,
    outputs: CombinedLlmOutputs,
    output_paths: dict[str, str],
) -> dict[str, Any]:
    """Build a compact, non-sensitive generation summary."""

    return {
        "build_id": outputs.build_id,
        "deployment": outputs.model_metadata.deployment,
        "prompt_versions": outputs.model_metadata.prompt_versions,
        "target_fields": {
            "bucket_1": outputs.bucket_1.target_fields,
            "bucket_2": outputs.bucket_2.target_fields,
            "bucket_3": outputs.bucket_3.target_fields,
        },
        "model_confidence": {
            "bucket_1": outputs.bucket_1.model_confidence,
            "bucket_2": outputs.bucket_2.model_confidence,
            "bucket_3": outputs.bucket_3.model_confidence,
        },
        "missing_information_count": {
            "bucket_1": len(outputs.bucket_1.missing_information),
            "bucket_2": len(outputs.bucket_2.missing_information),
            "bucket_3": len(outputs.bucket_3.missing_information),
        },
        "output_paths": output_paths,
    }


def format_summary(summary: dict[str, Any]) -> str:
    """Render a safe CLI summary without full evidence or generated field text."""

    paths = summary["output_paths"]
    return "\n".join(
        [
            "ServiceNow field draft generation summary",
            f"- build_id: {summary['build_id']}",
            f"- deployment: {summary['deployment']}",
            f"- prompt_versions: {summary['prompt_versions']}",
            f"- target_fields: {summary['target_fields']}",
            f"- model_confidence: {summary['model_confidence']}",
            f"- missing_information_count: {summary['missing_information_count']}",
            f"- bucket_1_output_path: {paths['bucket_1_output_path']}",
            f"- bucket_2_output_path: {paths['bucket_2_output_path']}",
            f"- bucket_3_output_path: {paths['bucket_3_output_path']}",
            f"- llm_outputs_path: {paths['llm_outputs_path']}",
        ]
    )


def _load_evidence_inputs(
    args: argparse.Namespace,
    store: LocalJsonStore,
) -> tuple[dict[str, Any], str | None]:
    if args.evidence_bundle:
        source_path = args.evidence_bundle
        bundle = _read_json_object(Path(args.evidence_bundle))
    else:
        source_path = store.evidence_path(args.build_id, "evidence_bundle.json")
        bundle = store.load_evidence_bundle(args.build_id)

    if args.bucket_1:
        bundle["bucket_1"] = _read_json_object(Path(args.bucket_1))
    if args.bucket_2:
        bundle["bucket_2"] = _read_json_object(Path(args.bucket_2))
    if args.bucket_3:
        bundle["bucket_3"] = _read_json_object(Path(args.bucket_3))

    return bundle, source_path


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Input JSON must be an object: {path}")
    return payload


def main() -> int:
    args = _build_parser().parse_args()
    try:
        summary = run_generation(args)
    except FileNotFoundError as exc:
        print(f"ServiceNow field generation failed: input file not found. {exc}")
        return 2
    except json.JSONDecodeError as exc:
        print(f"ServiceNow field generation failed: input file is invalid JSON. {exc}")
        return 3
    except (ValueError, LlmClientError) as exc:
        print(f"ServiceNow field generation failed: {exc}")
        return 4

    print(format_summary(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
