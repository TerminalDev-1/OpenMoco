# Comparable client distribution approaches

Checked on 2026-10-12. Source files, release assets, and externally linked
client downloads are distinct. These observations describe current published
trees and documentation, not every historical version or a distribution rule.

| Project | Observation |
| --- | --- |
| [OpenSquad](https://github.com/8-bitHacc/OpenSquad) | Its README links a pre-patched client hosted externally on MEGA. No APK/APKM/XAPK paths were found in its current Git tree, and its GitHub release list was empty when checked. |
| [20Clash](https://github.com/NotHuza/20Clash) | Its README links a pre-made client hosted externally on GoFile. No APK/APKM/XAPK paths were found in its current Git tree, and its GitHub release list was empty when checked. |
| [magic-rs](https://github.com/thexeondev/magic-rs) | Its README directs users to externally hosted releases to download server and client APKs. Its GitHub release list was empty when checked; the README's release link points to the developer's separate Git service. |

An exact repository called “OpenScord” was not identified in the searches.
OpenSquad is a relevant comparison, without assuming it is the project the
user meant.

OpenMoco's chosen approach is to keep source code in Git and provide its
verified test-client APKs as GitHub Release downloads. GitHub documents a
per-asset limit below 2 GiB in [About releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).
The client's larger asset split is therefore published as numbered parts
with a checksum manifest and reassembly tool.
