(dev-ai-tools)=
# Using AI Tools in netlab Development

Yes, we use AI tools. No, the robots are not running the project (yet). This document describes how we use AI coding assistants when developing _netlab_, what we expect from AI-assisted contributions, and why a human still has to press the **Merge** button. And yes, while Ivan edited it, most of this document was written by Claude ;)

```eval_rst
.. contents:: Table of Contents
   :depth: 1
   :local:
   :backlinks: none
```

## The Short Version

* AI tools are welcome. Unreviewed AI output is not. See also [No AI Slop Manifesto](https://www.slopmanifesto.com/).
* Whoever submits a pull request owns it, regardless of who (or what) typed it.
* The [quality gates](dev-ai-quality-gates) apply to everyone: carbon-based and silicon-based contributors alike.
* If an AI tool wrote a significant part of a commit, say so with a `Co-Authored-By` trailer.

## Why We Use AI Tools

_netlab_ supports dozens of devices, each with its own configuration syntax, quirks, and creative interpretation of the relevant RFCs. Writing yet another Jinja2 template that turns the same data structure into yet another dialect of `router ospf` is exactly the kind of work that AI tools are surprisingly good at.

Claude and GitHub Copilot also turned out to be surprisingly good at:

* Porting device features from one platform to another
* Writing developer documentation (and keeping it in sync with the code)
* Chasing bugs through the topology transformation code
* Drafting release notes from a pile of merged pull requests

## The Tools We Use

* All pull requests are reviewed with **GitHub Copilot**[^GHC] in Lite or Balanced mode. The comments are reviewed by the maintainer(s) and acted upon.
* Ivan figured out he prefers creating stuff over writing code, and is using **Claude CLI** to take over the boring stuff. He's also using Grammarly while trying to fake that he knows the rules of the English language.
* Browse through the [list of contributors](https://github.com/ipspace/netlab/graphs/contributors) to see other tools contributors use when creating the pull requests.

[^GHC]: Which may or may not be the same as Office Copilot or Microsoft Copilot, depending on how the Microsoft branding team feels this week.

Most important: you're free to use whatever tool you like, as long as you review what you submit in your PRs. We care about the results and the quality of your work, not about the brand of your autocomplete.

## How We Tell the AI Tools What We Want

AI coding agents are like enthusiastic new team members: they know a lot about everything and nothing about _netlab_. We keep the project-specific instructions in the repository:

* `AGENTS.md` (in the repository root) -- build, lint, and test commands, coding style, Box and Jinja2 idioms, documentation rules, and the all-important **NO NITPICKING** rule
* `.github/copilot-instructions.md` -- the development philosophy (warning: contains traces of a reality distortion field), heavily "borrowed" from smarter people.

When an AI tool repeatedly makes the same mistake, we don't just fix the code; we add a rule to `AGENTS.md`, so the next session (or the next contributor's AI tool) doesn't have to learn the same lesson the hard way.

Additionally, Ivan occasionally asks his Claude pair-programmer to dump its memories into `AGENTS.md` rules. Feel free to do the same.

## Rules of Engagement

**You are responsible for the code you submit.** "The AI wrote it" is not an acceptable answer to "why does this break IS-IS on Junos?"

**Read the diff before you submit it.** AI tools love to "improve" code they were not asked to touch: reformatting lines, swapping quotes, renaming variables, adding defensive checks for conditions that can never happen. We don't want any of that in a pull request (see the **NO NITPICKING** section of `AGENTS.md`).

**Don't post AI slop.** If we have to ask an AI tool to summarize your wall-of-text, be it an issue, comment, commit message, or a PR description, you failed, and will be told so in no uncertain words[^NFL]. Post stuff that you'd be OK reading by yourself at 7 AM while having your first coffee.

[^NFL]: Although I promise I won't go full Linus on you 😜

**Test on real devices.** AI tools are great at producing configurations that look plausible. Network devices are great at rejecting plausible configurations. Run the relevant [integration tests](dev-testing-integration) before claiming a device feature works.

**Do not invent features.** If the tool claims that a device supports a feature, check the vendor documentation (or better, the device CLI).

**Keep the humans in the loop.** Explain the *why* in the pull request description, and mention the questions the AI tool could not answer. Flag semantic changes explicitly instead of hiding them in a "minor cleanup".

(dev-ai-quality-gates)=
## Quality Gates

The AI-generated code has to pass the same checks as any other code:

* `mypy` type checking
* `ruff` linting
* `yamllint`
* The transformation and error-case tests (`tests/run-tests.sh`)

For device features, also run the relevant [integration tests](dev-testing-integration) on the affected devices. See [](dev-testing) for more details.

## Attribution

When an AI tool wrote a significant part of a commit, add a `Co-Authored-By` trailer to the commit message (most tools do that automatically if you ask them to create the commit message). For example:

```
Co-Authored-By: <AI tool and model> <noreply@vendor.com>
```

I usually remove the `Co-Authored-By` trailer for small GitHub Copilot autofixes. Who cares who fixed a typo?

Curious how much of _netlab_ was co-authored by machines? Ask git:

```
git log --format='%b' | grep -i 'co-authored-by' | sed 's/<.*//' | sort | uniq -c | sort -rn
```

## What the AI Tools Are (Still) Bad At

* Knowing which device quirks are real and which ones they just made up
* Understanding why a seemingly redundant check exists (hint: there was a bug report)
* Looking at the bigger picture
* Reinventing the functionality of the existing utility functions (although at least Claude CLI remembers what I tell it, and doesn't make the same mistake twice)
* Resisting the urge to refactor everything in sight
* Admitting they don't know the answer

## Frequently Asked Questions

**Will you accept my AI-generated pull request?**
: If it's correct, tested, focused, and you understand it -- yes. If it's 3000 lines of "enhancements" nobody asked for -- no.

**Can I use AI tools to write documentation?**
: Yes, but read it first. The documentation must describe how _netlab_ works, not how an AI tool thinks it should work.

**Did an AI tool write this document?**
: Of course, but then Ivan read it before committing it. What else did you expect?

