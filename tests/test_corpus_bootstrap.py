import hashlib
import json
import shutil
from pathlib import Path

import pytest

from src.knowledge.bootstrap import (
    CorpusTermsNotAcceptedError,
    CorpusUnavailableError,
    CorpusVerificationError,
    bootstrap_textbooks,
    verify_corpus,
)


def _write_jsonl(path: Path, documents: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for document in documents:
            handle.write(json.dumps(document, ensure_ascii=False) + "\n")


def _manifest_for(root: Path) -> dict:
    files = []
    chunks = 0
    for path in sorted((root / "chunk").glob("*.jsonl")):
        content = path.read_bytes()
        files.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
        chunks += sum(
            1
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    return {
        "schema_version": 1,
        "name": "Test Textbooks",
        "repo_id": "example/test-textbooks",
        "repo_type": "dataset",
        "revision": "test-revision",
        "expected_chunks": chunks,
        "expected_sources": len(files),
        "files": files,
    }


def _write_manifest(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest), encoding="utf-8")


def _sample_source(root: Path) -> dict:
    _write_jsonl(
        root / "chunk" / "anatomy.jsonl",
        [
            {"id": "anatomy_0", "title": "Anatomy", "content": "First chunk"},
            {"id": "anatomy_1", "title": "Anatomy", "content": "Second chunk"},
        ],
    )
    _write_jsonl(
        root / "chunk" / "medicine.jsonl",
        [
            {
                "id": "medicine_0",
                "title": "Medicine",
                "content": "Third chunk",
            }
        ],
    )
    return _manifest_for(root)


def test_verify_corpus_checks_schema_hashes_and_counts(tmp_path):
    corpus = tmp_path / "corpus"
    manifest = _sample_source(corpus)

    report = verify_corpus(corpus, manifest)

    assert report.sources == 2
    assert report.chunks == 3
    assert report.bytes > 0


def test_verify_corpus_rejects_modified_content(tmp_path):
    corpus = tmp_path / "corpus"
    manifest = _sample_source(corpus)
    with (corpus / "chunk" / "anatomy.jsonl").open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(
            json.dumps(
                {"id": "extra", "title": "Extra", "content": "Unexpected"}
            )
            + "\n"
        )

    with pytest.raises(CorpusVerificationError, match="size mismatch"):
        verify_corpus(corpus, manifest)


def test_verify_corpus_rejects_unexpected_jsonl(tmp_path):
    corpus = tmp_path / "corpus"
    manifest = _sample_source(corpus)
    _write_jsonl(
        corpus / "chunk" / "unexpected.jsonl",
        [{"id": "extra", "title": "Extra", "content": "Unexpected"}],
    )

    with pytest.raises(CorpusVerificationError, match="unexpected"):
        verify_corpus(corpus, manifest)


def test_bootstrap_downloads_to_staging_then_publishes(tmp_path):
    source = tmp_path / "source"
    manifest = _sample_source(source)
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(manifest_path, manifest)
    target = tmp_path / "data" / "textbooks"

    def fake_download(**kwargs):
        local_dir = Path(kwargs["local_dir"])
        shutil.copytree(source / "chunk", local_dir / "chunk")
        assert kwargs["revision"] == "test-revision"
        return str(local_dir)

    report = bootstrap_textbooks(
        target_dir=target,
        manifest_path=manifest_path,
        auto_download=True,
        terms_accepted=True,
        downloader=fake_download,
    )

    assert report.chunks == 3
    assert (target / ".medagent-corpus.json").is_file()
    marker = json.loads(
        (target / ".medagent-corpus.json").read_text(encoding="utf-8")
    )
    assert marker["target_dir"] == str(target.resolve())
    assert not list(target.parent.glob(".medrag-textbooks-*"))


def test_bootstrap_requires_download_and_terms_flags(tmp_path):
    source = tmp_path / "source"
    manifest = _sample_source(source)
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(manifest_path, manifest)
    target = tmp_path / "missing"

    with pytest.raises(CorpusUnavailableError):
        bootstrap_textbooks(
            target_dir=target,
            manifest_path=manifest_path,
            auto_download=False,
            terms_accepted=True,
        )

    with pytest.raises(CorpusTermsNotAcceptedError):
        bootstrap_textbooks(
            target_dir=target,
            manifest_path=manifest_path,
            auto_download=True,
            terms_accepted=False,
        )
