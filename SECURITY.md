# Security scope and private vulnerability reporting

**Selected route: GitHub private vulnerability reporting. Activation is pending.**
Target: [jeremylongworth-source/AgentAgriculture](https://github.com/jeremylongworth-source/AgentAgriculture).
Read-only verification on 2026-10-17 found a private, empty repository. The reporting
status API returned 404, which does not prove the feature enabled or disabled.
This SECURITY.md does not enable reporting or establish a monitored channel/SLA.
No remote/account/notification/credential setting was changed.

GitHub documents this feature for public repositories. Once the owner authorizes
the reviewed public source release, an eligible repository administrator must
separately enable it in Settings, Security and quality, Advanced Security,
Private vulnerability reporting. The owner must confirm responsible triage and
notifications; GitHub delivery depends on notification/watch settings. See the
[official configuration instructions](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository).

After activation is verified, use the repository's Security > Advisories >
Report a vulnerability button. The selected future
[private reporting form](https://github.com/jeremylongworth-source/AgentAgriculture/security/advisories/new)
is a prepared link, **not a verified working intake endpoint today**. If the button
is absent, do not post sensitive details in public issues. No alternate private
channel has been designated yet; hold sensitive details until an actual route is confirmed.

Use a minimal synthetic reproduction, affected version/host, expected and observed
behavior, and impact. Do not send secrets, farm/participant records or private logs.

The local core reads explicitly selected files and writes inspectable snapshots.
It makes no model/service call, stores no account credentials and sends no adviser
copy. Escaping, authority declarations, immutable evidence and tested recovery
reduce specific risks; they are not authentication, encryption, multiuser
authorization or a complete security audit. Input bounds do not establish
memory/time/disk guarantees; ignored folders are not access-control boundaries.

Technical checks cover finite synthetic Windows x64 / Python 3.14.3 / local NTFS
tasks. No production support SLA, regulated-use assurance, operational agronomy,
other-host qualification or participant-session isolation is claimed. The separate
post-launch study needs its own agreements/environment. Participant material does
not enter this repository or AI tools under the existing policy.
