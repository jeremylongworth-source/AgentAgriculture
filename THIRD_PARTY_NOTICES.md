# Third-party notices and distribution boundaries

The MIT licence in LICENSE covers project-owned software and associated
documentation. It does not relicense third-party components, external datasets,
provider pages, supplied research snapshots or attachments. Existing notices and
source-specific rights remain applicable. See [licensing scope](docs/release/licensing.md).

This source draft vendors no dependency wheels, provider payloads or raw research.
The pinned runtime dependency set is attrs 26.1.0, jsonschema 4.26.0,
jsonschema-specifications 2025.9.1, PyYAML 6.0.3, referencing 0.37.0 and rpds-py
2026.9.1. Their inspected wheel metadata declares MIT; their own copyright and
licence files must be retained when those components are redistributed. A shared
licence identifier does not transfer their copyright to this project. Build tools
also retain their own terms. Lockfiles identify exact acquired artifacts.

Prior local binary bundles preserve original dependency wheels and notices.
They are separate historical artifacts, not relabelled or relicensed by this file.
A future bundled distribution needs an inventory of its actual components and
applicable notice/redistribution obligations. No third-party notice was removed.

Source registry URLs, provider names and historical access labels identify research
leads. Null permitted-use/attribution/redistribution fields remain unresolved for
provider content. Shipping an authored non-fetching catalogue neither grants rights
to provider payloads nor requires pretending that payloads are bundled. Historical
assertions are explained in the [public provenance index](docs/release/public-provenance.md).
