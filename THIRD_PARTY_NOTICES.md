# Third-party components

The plugin and installer source are MIT licensed. Bundled runtimes and libraries
retain their respective licenses; the MIT license does not relicense them.

| Component | Version | License / location in Windows payload |
|---|---|---|
| CPython embedded x64 | 3.13.16 | Python Software Foundation license, `python/LICENSE.txt` |
| Node.js x64 | 22.23.3 | MIT and bundled third-party licenses, `node/LICENSE` |
| psutil | 7.2.2 | BSD-3-Clause, `python/Lib/site-packages/psutil-*.dist-info` |
| websocket-client | 1.9.2 | Apache-2.0, `python/Lib/site-packages/websocket_client-*.dist-info` |
| pywin32 | 312 | PSF, `python/Lib/site-packages/pywin32-*.dist-info` |

All wheel contents, including license/metadata files, are retained. Exact
download URLs and SHA256 values are recorded in `DEPENDENCIES.json` in the
distribution and `build/dependencies.lock.json` in the source repository.
