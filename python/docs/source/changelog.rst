Changelog
=========

Version 0.1.6 (2026-07-25)
--------------------------
- Breaking change. Big one. All caching data catchers have been renamed to queueing, and inbound data catchers now cache.

Version 0.1.5 (2026-07-13)
--------------------------
- Added passthrough ``requests`` verify parameter for DataFlows.

Version 0.1.4 (2026-07-13)
--------------------------
- Breaking DataFlow API change: renamed ``DataLink.local_type`` / ``remote_type`` to
  ``local_datacatcher_type`` / ``remote_datacatcher_type``.
- Breaking DataFlow API change: renamed ``Heartbeat.remote_type`` to
  ``Heartbeat.remote_flowmodel_type``

Version 0.1.3 (2026-06-01)
--------------------------
- Added runtime hook.

Version 0.1.2 (2026-05-22)
--------------------------
- Additional hook for top level `joop` context overrides.

Version 0.1.1 (2026-05-22)
--------------------------
- Add hook for `joop` context overrides.

Version 0.1.0 (2026-05-12)
--------------------------
- Add the DataFlow module.
- Add functionality to `joop.sql`.
- Add JSON web component initial implementation.
- Move `joop.http` to `joop.net`; a breaking change that is acceptable at this point in the project.
- Minor change to general subcomponent rendering.

Version 0.0.5 (2026-02-11)
--------------------------
- Fix a typo and move an implementation check to a separate method.

Version 0.0.4 (2026-02-05)
--------------------------
- Add ORM config dataclass.

Version 0.0.3 (2026-02-05)
--------------------------
- Add SQLConfig dataclass.

Version 0.0.2 (2026-02-03)
--------------------------
- Var bug fixes.

Version 0.0.1 (2026-02-02)
--------------------------
- Initial version. Features AlpineJS-powered table.
