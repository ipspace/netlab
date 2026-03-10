---
name: release-notes
description: Create release notes for a new netlab release
---
# Creating release notes

* Use docs/release/release.template as a template
* Use other files in the docs/release folder as guidance
* Create release notes from commits after the last `release_xx.xx` tag
* Categorize commits without the explicit category (usually 'Doc' or 'Fix') in the title into one of the categories based on their content and impact.
* Try to identify breaking changes.
* Remove the PR references from everything but the bug and documentation fixes
* Remove the "Doc: " or "Fix: " part of the commit title
