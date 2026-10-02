# Compatibility and troubleshooting

Supported target: Windows 10/11 x64, Microsoft Store Codex package
`OpenAI.Codex_2p2nqsd0c76g0`, .NET Framework 4.5+ (normally included).
Other platforms and ARM64-native builds are not included.

The default official package is discovered dynamically; no fixed client version
is embedded in the launcher. MSIX logical Roaming and physical LocalCache
endpoint files are both supported. A stale logical port does not suppress the
physical candidate. Each listener must belong to the official package and the
matching browser profile, and bind only to loopback.

If statistics are missing:

1. Check the plugin is enabled and the Windows runtime is installed.
2. Save tasks and exit the official App normally once, then use the generated
   **Codex 官方版（输入栏统计）** shortcut.
3. In an existing local chat, ask Codex to check `statistics_status`. An active
   adapter is insufficient evidence: inspect actual `ui.visibleControls`,
   `missingControls` and `insideInputBar`.
4. `waiting_for_exit` means the current App has no renderer launch endpoint;
   waiting longer will not help. `waiting_for_renderer` means it has the flags
   and the adapter is waiting for a validated endpoint.
5. New empty chats and remote/cloud chats may have no usable local records.
6. If an official client update changes input-bar selectors or internal routing,
   install a compatible plugin release or open an issue with client/plugin
   versions and redacted status. Do not submit keys, logs or full config files.

Plugin management and official App updates remain available because the
official package and update files are not modified. Updating a GitHub marketplace
does not install runtime dependencies; update the Windows package too.
