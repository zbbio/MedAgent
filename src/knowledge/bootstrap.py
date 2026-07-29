"""Download and verify the pinned MedRAG Textbooks corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from huggingface_hub import snapshot_download

from ..config import config


logger = logging.getLogger(__name__)
DEFAULT_MANIFEST_PATH = (
    Path(__file__).resolve().parent
    / "manifests"
    / "medrag_textbooks.json"
)


class CorpusBootstrapError(RuntimeError):
    """Base class for actionable corpus initialization failures."""


class CorpusUnavailableError(CorpusBootstrapError):
    """The required corpus is missing and downloading is disabled."""


class CorpusTermsNotAcceptedError(CorpusBootstrapError):
    """Third-party data acknowledgement was not explicitly accepted."""


class CorpusVerificationError(CorpusBootstrapError):
    """Downloaded or existing corpus content does not match its manifest."""


@dataclass(frozen=True)
class CorpusReport:
    name: str
    repo_id: str
    revision: str
    sources: int
    chunks: int
    bytes: int
    target_dir: str


def load_manifest(path: Path | str = DEFAULT_MANIFEST_PATH) -> dict[str, Any]:
    manifest_path = Path(path)
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    required = {
        "name",
        "repo_id",
        "repo_type",
        "revision",
        "expected_chunks",
        "expected_sources",
        "files",
    }
    missing = sorted(required - manifest.keys())
    if missing:
        raise CorpusVerificationError(
            f"Corpus manifest is missing fields: {', '.join(missing)}"
        )
    return manifest


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_corpus(
    target_dir: Path | str,
    manifest: dict[str, Any] | None = None,
) -> CorpusReport:
    """Verify files, byte sizes, hashes, JSONL schema, IDs, and total rows."""
    target = Path(target_dir)
    corpus_manifest = manifest or load_manifest()
    expected_files = corpus_manifest["files"]
    if len(expected_files) != int(corpus_manifest["expected_sources"]):
        raise CorpusVerificationError(
            "Manifest source count does not match its file list"
        )
    expected_paths = {
        Path(entry["path"]).as_posix()
        for entry in expected_files
    }
    actual_paths = {
        path.relative_to(target).as_posix()
        for path in target.glob("chunk/*.jsonl")
    }
    if actual_paths != expected_paths:
        missing = sorted(expected_paths - actual_paths)
        unexpected = sorted(actual_paths - expected_paths)
        details = []
        if missing:
            details.append(f"missing={','.join(missing)}")
        if unexpected:
            details.append(f"unexpected={','.join(unexpected)}")
        raise CorpusVerificationError(
            "Corpus file set mismatch: " + "; ".join(details)
        )

    seen_ids: set[str] = set()
    chunks = 0
    total_bytes = 0
    for entry in expected_files:
        relative_path = Path(entry["path"])
        file_path = target / relative_path
        if not file_path.is_file():
            raise CorpusVerificationError(
                f"Corpus file is missing: {relative_path.as_posix()}"
            )
        size = file_path.stat().st_size
        if size != int(entry["size"]):
            raise CorpusVerificationError(
                f"Corpus file size mismatch: {relative_path.as_posix()}"
            )
        if _sha256(file_path) != entry["sha256"]:
            raise CorpusVerificationError(
                f"Corpus file hash mismatch: {relative_path.as_posix()}"
            )
        total_bytes += size

        with file_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    document = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise CorpusVerificationError(
                        f"Invalid JSONL at {relative_path.as_posix()}:{line_number}"
                    ) from exc
                for field in ("id", "title", "content"):
                    if not isinstance(document.get(field), str) or not document[field]:
                        raise CorpusVerificationError(
                            f"Missing {field} at "
                            f"{relative_path.as_posix()}:{line_number}"
                        )
                document_id = document["id"]
                if document_id in seen_ids:
                    raise CorpusVerificationError(
                        f"Duplicate corpus id: {document_id}"
                    )
                seen_ids.add(document_id)
                chunks += 1

    if chunks != int(corpus_manifest["expected_chunks"]):
        raise CorpusVerificationError(
            "Corpus chunk count mismatch: "
            f"expected {corpus_manifest['expected_chunks']}, got {chunks}"
        )

    return CorpusReport(
        name=corpus_manifest["name"],
        repo_id=corpus_manifest["repo_id"],
        revision=corpus_manifest["revision"],
        sources=len(expected_files),
        chunks=chunks,
        bytes=total_bytes,
        target_dir=str(target.resolve()),
    )


def bootstrap_textbooks(
    *,
    target_dir: Path | str | None = None,
    manifest_path: Path | str = DEFAULT_MANIFEST_PATH,
    auto_download: bool | None = None,
    terms_accepted: bool | None = None,
    downloader: Callable[..., str] = snapshot_download,
) -> CorpusReport:
    """Reuse a verified corpus or atomically download the pinned snapshot."""
    target = Path(target_dir or config.TEXTBOOKS_CORPUS_DIR)
    manifest = load_manifest(manifest_path)

    if target.exists():
        report = verify_corpus(target, manifest)
        logger.info(
            "Textbooks corpus already verified: sources=%s chunks=%s",
            report.sources,
            report.chunks,
        )
        return report

    should_download = (
        config.TEXTBOOKS_AUTO_DOWNLOAD
        if auto_download is None
        else auto_download
    )
    accepted = (
        config.MEDRAG_TEXTBOOKS_ACCEPT_TERMS
        if terms_accepted is None
        else terms_accepted
    )
    if not should_download:
        raise CorpusUnavailableError(
            "Textbooks corpus is missing and TEXTBOOKS_AUTO_DOWNLOAD is false"
        )
    if not accepted:
        raise CorpusTermsNotAcceptedError(
            "Set MEDRAG_TEXTBOOKS_ACCEPT_TERMS=true after reviewing "
            "docs/corpus-licensing.md"
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=".medrag-textbooks-",
            dir=target.parent,
        )
    )
    try:
        logger.info(
            "Downloading %s at revision %s",
            manifest["repo_id"],
            manifest["revision"],
        )
        downloader(
            repo_id=manifest["repo_id"],
            repo_type=manifest["repo_type"],
            revision=manifest["revision"],
            allow_patterns=["chunk/*.jsonl"],
            local_dir=str(staging),
        )
        report = verify_corpus(staging, manifest)
        final_report = CorpusReport(
            **{
                **asdict(report),
                "target_dir": str(target.resolve()),
            }
        )
        marker = {
            **asdict(final_report),
            "verified_at": datetime.now(UTC).isoformat(),
            "license_status": manifest.get("license_status", "unknown"),
            "upstream_url": manifest.get("upstream_url", ""),
        }
        with (staging / ".medagent-corpus.json").open(
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(marker, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(staging, target)
        return final_report
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download and verify the pinned MedRAG Textbooks corpus"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only verify an existing corpus; never download",
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=Path(config.TEXTBOOKS_CORPUS_DIR),
    )
    parser.add_argument(
        "--optional",
        action="store_true",
        help="Exit successfully when downloading is disabled and no corpus exists",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    try:
        if args.check:
            report = verify_corpus(args.target_dir)
        elif args.optional and not config.TEXTBOOKS_ENABLED:
            logger.warning(
                "Local textbook retrieval is disabled; "
                "continuing in pubmed_only mode"
            )
            return 0
        elif args.optional and not config.TEXTBOOKS_AUTO_DOWNLOAD:
            logger.warning(
                "Automatic textbook download is disabled; "
                "continuing without initialization"
            )
            return 0
        else:
            report = bootstrap_textbooks(target_dir=args.target_dir)
    except CorpusUnavailableError as exc:
        if args.optional:
            logger.warning("%s; continuing in pubmed_only mode", exc)
            return 0
        logger.error("%s", exc)
        return 1
    except CorpusBootstrapError as exc:
        logger.error("%s", exc)
        return 1

    print(json.dumps(asdict(report), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
