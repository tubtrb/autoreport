from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable

import yaml

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]


class HandoffError(Exception):
    """Raised when the autorelease handoff cannot be completed."""


LIVE_SERVICE_SECTION_PATTERN = re.compile(
    r"(?ms)^## Live service\r?\n.*?(?=^## |\Z)"
)
FRONT_MATTER_BODY_PATTERN = re.compile(
    r"^(---\s*\r?\n.*?\r?\n---\s*\r?\n?)(.*)$",
    re.DOTALL,
)


@dataclass(frozen=True)
class PublicServiceInfo:
    as_of: str
    release_home: str
    release_guide: str
    release_updates: str
    hosted_demo_primary: str
    hosted_demo_alternate: str | None = None
    hosted_demo_healthcheck: str | None = None
    hosted_demo_healthcheck_expected: str | None = None


@dataclass(frozen=True)
class PostSpec:
    key: str
    section: str
    source_path: Path
    target_path: Path
    slug: str
    title: str
    summary: str
    tags: tuple[str, ...]
    transform_body: Callable[[str, "PostSpec", argparse.Namespace], str]
    source_asset_dir: Path | None = None
    cover_image: str | None = None


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[4]
    parser = argparse.ArgumentParser(
        description=(
            "Sync versioned autoreport posts into the private autorelease repo."
        )
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=repo_root,
        help="Path to the autoreport repository root.",
    )
    parser.add_argument(
        "--autorelease-root",
        type=Path,
        default=repo_root.parent / "autorelease",
        help="Path to the private autorelease repository root.",
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Version to hand off. Defaults to the version in pyproject.toml.",
    )
    parser.add_argument(
        "--source-ref",
        default=None,
        help="Branch, tag, or commit to record in the handoff front matter.",
    )
    parser.add_argument(
        "--date",
        dest="date_value",
        default=date.today().isoformat(),
        help="Front matter date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--status",
        default="draft",
        choices=("draft", "publish"),
        help="Target publish status for the handoff items.",
    )
    parser.add_argument(
        "--source-repo",
        default="tubtrb/autoreport",
        help="Source repository name written into the front matter.",
    )
    return parser.parse_args()


def read_project_version(repo_root: Path) -> str:
    pyproject_path = repo_root / "pyproject.toml"
    with pyproject_path.open("rb") as handle:
        data = tomllib.load(handle)
    version = data.get("project", {}).get("version")
    if not version:
        raise HandoffError(f"Could not find project.version in {pyproject_path}.")
    return str(version)


def detect_source_ref(repo_root: Path) -> str:
    exact_tag = run_git(
        repo_root,
        ["describe", "--tags", "--exact-match"],
        allow_failure=True,
    )
    if exact_tag:
        return exact_tag

    branch_name = run_git(
        repo_root,
        ["rev-parse", "--abbrev-ref", "HEAD"],
        allow_failure=True,
    )
    if branch_name and branch_name != "HEAD":
        return branch_name

    commit_sha = run_git(
        repo_root,
        ["rev-parse", "--short", "HEAD"],
        allow_failure=False,
    )
    return commit_sha


def run_git(repo_root: Path, args: list[str], *, allow_failure: bool) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        if allow_failure:
            return ""
        raise HandoffError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def slug_version(version: str) -> str:
    return version.replace(".", "-")


def load_public_service_info(repo_root: Path) -> PublicServiceInfo:
    info_path = repo_root / "docs" / "deployment" / "public-service-info.yaml"
    if not info_path.exists():
        raise HandoffError(f"Public service info file not found: {info_path}")

    raw = yaml.safe_load(info_path.read_text(encoding="utf-8")) or {}
    release_site = raw.get("release_site") or {}
    hosted_demo = raw.get("hosted_demo") or {}

    def required(section: dict[str, object], key: str) -> str:
        value = str(section.get(key, "")).strip()
        if not value:
            raise HandoffError(
                f"Missing '{key}' in public service info file: {info_path}"
            )
        return value

    return PublicServiceInfo(
        as_of=required(raw, "as_of"),
        release_home=required(release_site, "home"),
        release_guide=required(release_site, "guide"),
        release_updates=required(release_site, "updates"),
        hosted_demo_primary=required(hosted_demo, "primary"),
        hosted_demo_alternate=str(
            hosted_demo.get("alternate_hostname", "")
        ).strip()
        or None,
        hosted_demo_healthcheck=str(hosted_demo.get("healthcheck", "")).strip() or None,
        hosted_demo_healthcheck_expected=str(
            hosted_demo.get("healthcheck_expected", "")
        ).strip()
        or None,
    )


def build_specs(args: argparse.Namespace) -> list[PostSpec]:
    repo_root = args.repo_root.resolve()
    autorelease_root = args.autorelease_root.resolve()
    version = args.version
    slugged_version = slug_version(version)
    posts_root = repo_root / "docs" / "posts"
    devlog_asset_dir = optional_asset_dir(posts_root / f"devlog-image-v{version}")
    guide_asset_dir = optional_asset_dir(posts_root / f"guide-image-v{version}")
    guide_cover_image = None
    if guide_asset_dir is not None and (guide_asset_dir / "image.png").exists():
        guide_cover_image = "../assets/guide/image.png"

    devlog_slug = f"autoreport-v{slugged_version}-devlog"
    guide_slug = "guide"
    release_slug = f"autoreport-v{slugged_version}-release-notes"
    return [
        PostSpec(
            key="devlog",
            section="devlog",
            source_path=posts_root / f"autoreport-v{version}-development-log.md",
            target_path=autorelease_root / "content" / "devlogs" / f"{devlog_slug}.md",
            slug=devlog_slug,
            title=f"Autoreport v{version} 개발 일지",
            summary=(
                f"Autoreport v{version} 작업 기록으로, 구현 메모와 릴리즈 준비 흐름을 담았습니다."
            ),
            tags=("development-log", "autoreport", f"v{version}"),
            transform_body=transform_devlog_body,
            source_asset_dir=devlog_asset_dir,
        ),
        PostSpec(
            key="guide",
            section="guide",
            source_path=posts_root / f"autoreport-guide-v{version}.md",
            target_path=autorelease_root / "content" / "guides" / f"{guide_slug}.md",
            slug=guide_slug,
            title="User Guide",
            summary=(
                "Current guide to the contract-first Autoreport workflow across the CLI, starter-manual web app, and updates pages."
            ),
            tags=("user-guide", "autoreport", "contract-first", f"v{version}"),
            transform_body=transform_guide_body,
            source_asset_dir=guide_asset_dir,
            cover_image=guide_cover_image,
        ),
        PostSpec(
            key="release-note",
            section="release-note",
            source_path=posts_root / f"autoreport-v{version}-release-notes.md",
            target_path=(
                autorelease_root
                / "content"
                / "release-notes"
                / f"{release_slug}.md"
            ),
            slug=release_slug,
            title=f"Autoreport v{version} Release Notes",
            summary=(
                f"Release summary for Autoreport v{version}, including current capabilities and verification notes."
            ),
            tags=("release", "autoreport", f"v{version}"),
            transform_body=transform_release_notes_body,
        ),
    ]


def optional_asset_dir(path: Path) -> Path | None:
    if not path.exists():
        return None
    return path


def ensure_source_exists(spec: PostSpec) -> None:
    if not spec.source_path.exists():
        raise HandoffError(f"Source post not found: {spec.source_path}")


def read_source_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        match = re.match(r"^---\s*\r?\n.*?\r?\n---\s*\r?\n?(.*)$", text, re.DOTALL)
        if match is not None:
            return match.group(1).strip() + "\n"
    return text.strip() + "\n"


def transform_devlog_body(body: str, spec: PostSpec, _: argparse.Namespace) -> str:
    source_prefix = spec.source_asset_dir.name if spec.source_asset_dir else ""
    if source_prefix:
        body = body.replace(
            f"]({source_prefix}/",
            f"](../assets/{spec.slug}/",
        )
    return body


def render_live_service_section(info: PublicServiceInfo) -> str:
    lines = [
        "## Live service",
        "",
        f"As of `{info.as_of}`, the public release pages and the hosted demo app are available at:",
        "",
        f"- Release-facing site home: `{info.release_home}`",
        f"- Release-facing user guide: `{info.release_guide}`",
        f"- Release-facing updates hub: `{info.release_updates}`",
        f"- Hosted demo app: `{info.hosted_demo_primary}`",
    ]
    if info.hosted_demo_alternate:
        lines.append(f"- Alternate EC2 hostname: `{info.hosted_demo_alternate}`")
    if info.hosted_demo_healthcheck:
        healthcheck_line = f"- Hosted demo health check: `{info.hosted_demo_healthcheck}`"
        if info.hosted_demo_healthcheck_expected:
            healthcheck_line += f" returns `{info.hosted_demo_healthcheck_expected}`"
        lines.append(healthcheck_line)
    return "\n".join(lines)


def upsert_live_service_section(
    body: str,
    info: PublicServiceInfo,
    *,
    insert_before_heading: str,
) -> str:
    normalized = LIVE_SERVICE_SECTION_PATTERN.sub("", body).strip()
    section = render_live_service_section(info)
    if insert_before_heading in normalized:
        return normalized.replace(
            insert_before_heading,
            section + "\n\n" + insert_before_heading,
            1,
        )
    return normalized + "\n\n" + section


def transform_guide_body(body: str, spec: PostSpec, args: argparse.Namespace) -> str:
    source_prefix = spec.source_asset_dir.name if spec.source_asset_dir else ""
    if source_prefix:
        body = body.replace(
            f"]({source_prefix}/",
            f"](../assets/{spec.slug}/",
        )
    body = re.sub(
        r"(?m)^This guide reflects .*?active branch\.",
        f"This guide reflects the Autoreport implementation at `{args.source_ref}`.",
        body,
        count=1,
    )
    body = re.sub(
        r"\bOn the current branch,",
        "In this handoff build,",
        body,
        count=1,
    )
    body = re.sub(
        r"(?m)^The current branch was verified with (.+?)\.$",
        rf"The `{args.source_ref}` build was verified with \1.",
        body,
        count=1,
    )
    body = body.replace(
        "## Verification on the current branch",
        "## Verification for this handoff build",
    )
    body = body.replace(
        "REPLACE_WITH_PUBLIC_IMAGE_URL",
        f"../assets/{spec.slug}/image.png",
    )
    body = re.sub(
        r"<!-- Local working screenshot asset: .*? -->\r?\n?",
        "",
        body,
    )
    body = upsert_live_service_section(
        body,
        args.public_service_info,
        insert_before_heading="## What is Autoreport?",
    )
    return body


def transform_release_notes_body(
    body: str,
    _: PostSpec,
    args: argparse.Namespace,
) -> str:
    body = re.sub(
        r"\bThe current branch now exposes\b",
        "This release now exposes",
        body,
        count=1,
    )
    body = body.replace(
        "Clearer current-branch release verification using focused tests and browser smoke checks",
        "Clearer release verification using focused tests and browser smoke checks",
    )
    body = body.replace(
        "## Verification on the current branch",
        "## Verification for this release",
    )
    current_branch_sentence = (
        "This release note is based on the current workspace state rather than a tagged public deployment."
    )
    if args.source_ref.startswith("v"):
        replacement = (
            f"This release note reflects the `{args.source_ref}` tag and the verification run used for release signoff."
        )
    else:
        replacement = (
            f"This release note reflects the `{args.source_ref}` branch and its verification run."
        )
    body = body.replace(current_branch_sentence, replacement)
    body = upsert_live_service_section(
        body,
        args.public_service_info,
        insert_before_heading="## What's included in this release",
    )
    return body


def transform_homepage_body(body: str, args: argparse.Namespace) -> str:
    return upsert_live_service_section(
        body,
        args.public_service_info,
        insert_before_heading="## Product overview",
    )


def render_front_matter(spec: PostSpec, args: argparse.Namespace) -> str:
    lines = [
        "---",
        f"title: {json.dumps(spec.title, ensure_ascii=False)}",
        f"slug: {spec.slug}",
        f"section: {spec.section}",
        f"summary: {json.dumps(spec.summary, ensure_ascii=False)}",
        f"date: {args.date_value}",
        f"status: {args.status}",
        "tags:",
    ]
    for tag in spec.tags:
        lines.append(f"  - {tag}")
    lines.extend(
        [
            f"source_repo: {json.dumps(args.source_repo, ensure_ascii=False)}",
            f"source_ref: {json.dumps(args.source_ref, ensure_ascii=False)}",
        ]
    )
    if spec.cover_image:
        lines.append(f"cover_image: {json.dumps(spec.cover_image, ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines)


def write_target_post(spec: PostSpec, args: argparse.Namespace) -> None:
    ensure_source_exists(spec)
    body = read_source_body(spec.source_path)
    body = spec.transform_body(body, spec, args).strip() + "\n"
    front_matter = render_front_matter(spec, args)
    spec.target_path.parent.mkdir(parents=True, exist_ok=True)
    spec.target_path.write_text(
        front_matter + "\n\n" + body,
        encoding="utf-8",
    )


def sync_assets(spec: PostSpec) -> None:
    if spec.source_asset_dir is None or not spec.source_asset_dir.exists():
        return

    target_root = spec.target_path.parents[1] / "assets" / spec.slug
    target_root.mkdir(parents=True, exist_ok=True)
    for source in spec.source_asset_dir.rglob("*"):
        if not source.is_file():
            continue
        relative = source.relative_to(spec.source_asset_dir)
        destination = target_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def replace_markdown_body(text: str, body: str) -> str:
    match = FRONT_MATTER_BODY_PATTERN.match(text)
    if match is None:
        raise HandoffError("Target Markdown file is missing valid front matter.")
    return match.group(1).rstrip() + "\n\n" + body.strip() + "\n"


def sync_homepage_live_service(args: argparse.Namespace) -> Path:
    homepage_path = args.autorelease_root / "content" / "pages" / "main.md"
    if not homepage_path.exists():
        raise HandoffError(f"Autorelease homepage not found: {homepage_path}")
    raw_text = homepage_path.read_text(encoding="utf-8")
    _, body = parse_front_matter(raw_text)
    transformed_body = transform_homepage_body(body, args)
    homepage_path.write_text(
        replace_markdown_body(raw_text, transformed_body),
        encoding="utf-8",
    )
    return homepage_path


def validate_touched_posts(
    args: argparse.Namespace,
    specs: list[PostSpec],
    *,
    extra_paths: list[Path] | None = None,
) -> None:
    autorelease_src = args.autorelease_root / "src"
    sys.path.insert(0, str(autorelease_src))
    try:
        from autorelease.content import load_post
        from autorelease.validate import validate_post
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise HandoffError(
            "Could not import autorelease validation helpers. "
            "Run this script in an environment with PyYAML available."
        ) from exc

    errors: list[str] = []
    for spec in specs:
        post = load_post(spec.target_path, args.autorelease_root)
        errors.extend(validate_post(post))
    for path in extra_paths or []:
        post = load_post(path, args.autorelease_root)
        errors.extend(validate_post(post))

    if errors:
        raise HandoffError("\n".join(errors))


def main() -> int:
    args = parse_args()
    args.repo_root = args.repo_root.resolve()
    args.autorelease_root = args.autorelease_root.resolve()
    args.version = args.version or read_project_version(args.repo_root)
    args.source_ref = args.source_ref or detect_source_ref(args.repo_root)
    args.public_service_info = load_public_service_info(args.repo_root)

    specs = build_specs(args)
    for spec in specs:
        write_target_post(spec, args)
        sync_assets(spec)

    homepage_path = sync_homepage_live_service(args)
    validate_touched_posts(args, specs, extra_paths=[homepage_path])

    print(
        "HANDOFF_OK "
        f"version={args.version} "
        f"source_ref={args.source_ref} "
        f"posts={len(specs)}"
    )
    for spec in specs:
        print(spec.target_path)
    print(homepage_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
