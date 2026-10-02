# Development and release

Source layout:

- `plugins/codex-native-stats`: marketplace plugin, MCP entry point, official-client adapter, renderer and statistics worker.
- `.agents/plugins/marketplace.json`: Codex GitHub/local marketplace descriptor.
- `installer/install.py`: per-user install, upgrade, uninstall and integrity checking.
- `build/Host.cs`: MCP launcher with a byte-preserving pipe relay and silent desktop launcher.
- `build/Cleanup.cs`: delayed removal of two owned installation targets, guarded by an ownership marker.
- `build/Setup.cs`: GUI setup with embedded ZIP; extraction and Python installer.
- `build/build.py`: pinned runtime download, wheel assembly, build and checksums.

Run on Windows x64. The build uses the .NET Framework compiler shipped with
Windows and Python 3.11+. It does not require pip or a .NET SDK. Python wheels
are downloaded through PyPI's versioned JSON API and checked against PyPI's
SHA256. Node ZIP bytes are checked against official SHASUMS256.txt. CPython
bytes are obtained over HTTPS from python.org and pinned to the checked-in lock.

`runtime/bin/CodexStatsHost.exe` is the small compiled launcher included in the
marketplace. Its source is `build/Host.cs`; a build regenerates it. Full runtimes
and release artifacts are excluded from Git. Artifact SHA256 is not a code
signature. This release has no Authenticode signature.

Validation commands:

```powershell
python build/build.py
python tests/test_distribution.py
build/payload/python/python.exe tests/test_installer_unit.py
build/payload/python/python.exe plugins/codex-native-stats/tests/test_startup.py
build/payload/node/node.exe plugins/codex-native-stats/tests/test_speed.cjs
```

The distribution test uses its own CODEX_HOME and installation root, validates
the real setup executable, portable host's MCP handshake, repeated install,
upgrade, corruption rejection, uninstall and preservation of unrelated config
and data. It does not register production shortcuts or open the user's App.

Optional official-runtime fixture tests (require the Store App):

```powershell
$env:CODEX_STATS_NODE = "$PWD/build/payload/node/node.exe"
build/payload/python/python.exe plugins/codex-native-stats/tests/test_startup_official.py
build/payload/python/python.exe plugins/codex-native-stats/tests/test_official_plugin.py
```

These tests launch a separate profile with synthetic records. Fixture layout
tests do not certify all real account-backed client layouts. Never distribute
test reports, user data, credentials, logs or backup scripts with a release.

After publishing the repository, `python tests/test_remote_marketplace.py`
checks the real GitHub download, plugin installation, bundled MCP runtime and
uninstall in an isolated home. This optional test requires Git and the Codex CLI.

For a release, update VERSION, plugin manifest/server versions and release
documentation together. Build, run the tests, then publish the setup EXE,
runtime ZIP and SHA256SUMS.txt under a matching tag.
