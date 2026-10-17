# Contribution and development guidance

Project-owned software and associated documentation use the [MIT licence](LICENSE).
Contribute only material you are entitled to provide under these terms and retain
third-party notices. See [licensing boundaries](docs/release/licensing.md).
The selected repository is currently private and empty; public contribution
infrastructure is not yet operating. No contributor agreement is introduced.

Use invented fixtures and a small reproducible case. Preserve identifiers, original
units/bytes, missing/suppressed/estimated/zero distinctions and the declared scope.
Keep arithmetic/validation deterministic. Do not replace source evidence to make a
total agree. Add tests for material failure modes rather than mirroring code.

Follow the [fresh-source setup and checks](docs/release/initial-preview.md). Runtime
dependencies and build tools are pinned separately. Keep network/account adapters
optional, and do not add paid services, credentials, remote writes or a new supported
domain claim as an incidental code change. Other platforms need their own evidence.

Include the concrete problem, resulting behavior, scope/limitations and checks in
a proposed change. Use only material you may contribute under the MIT
terms; retain third-party attribution. Do not submit farm records, participant
contacts, completed study forms, secrets or private logs. The study is separately
scoped after launch and does not block ordinary synthetic software improvements.

For a suspected vulnerability, read [reporting status](SECURITY.md) and avoid public
sensitive details. GitHub private vulnerability reporting is the selected route. Activation and
responsible triage/notification arrangements must be confirmed before launch; no
response SLA is promised.
