---
name: release
description: Prepare all files needed to cut a new netlab release
---
# Preparing a New netlab Release

## Identify the release version

* Use user input or determine the new version number (e.g. `26.03`) using calendar versioning (`YY.MM` for the first release in a month or `YY.MM.NN` for subsequent releases)
* Find the previous release tag with `git tag | grep release | sort -V | tail -5`.

## Check what is already done

Some steps are done incrementally during development and must **not** be repeated:

* `docs/release/XX.YY.md` — may already exist (created mid-cycle via a separate PR)
* `docs/release.md` — may already have the new release entry
* `docs/caveats.md` — updated alongside feature commits; do **not** rewrite
* `docs/platforms.md` — updated alongside feature commits; do **not** rewrite

## Files that always need updating

| File | What to change |
|------|----------------|
| `netsim/__init__.py` | `__version__` string |
| `legacy/setup.py` | `version` string |
| `README.md` | `## Releases` blurb — latest release link + fallback link |

## Check release notes completeness

* List all commits since the previous tag: `git log release_XX.YY..HEAD --oneline`
* Compare each commit against the existing `docs/release/XX.YY.md` to find missing items.
* Focus on user-facing commits; skip internal items (integration test cleanups, timing fixes, skill/tooling updates).
* When the release notes file does **not** yet exist, use `docs/release/release.template` as a base and the `release-notes` skill to write it.

## Update docs/release.md if needed

* If the new release entry is missing, add it at the top (above the previous release), following the style of recent entries.
* Include the release date (today) in the heading.
* Include the toctree entry for `release/XX.YY.md`.

## README.md wording pattern

```
The latest release is [release XX.YY](https://github.com/ipspace/netlab/releases/tag/release_XX.YY).
It should be pretty stable, but if you encounter bugs, please report them as
[GitHub issues](https://github.com/ipspace/netlab/issues/new/choose) and use
[release XX.ZZ](https://github.com/ipspace/netlab/releases/tag/release_XX.ZZ).
```

where `XX.ZZ` is the **previous** stable release.

## Commit message convention

The release commit is titled `Release XX.YY (#NNNN)` and is submitted as a PR.
