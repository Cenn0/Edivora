# Qt for Python license texts and source provenance

Recorded on 2026-10-12 for the Windows development alpha.

## What these files contain

The six files in [qt-licenses/](qt-licenses/) are unchanged copies of the common license texts in the official Qt for Python 6.12.0 source release. They supplement the notices copied from installed wheels into `third-party-licenses/`. The application build copies this `docs/` directory into the portable package.

The inspected 6.12.0 PySide6, Essentials, Addons and Shiboken wheel inventories contained only `LicenseRef-Qt-Commercial.txt`. The official, version-specific [PySide6](https://pypi.org/project/PySide6/6.12.0/), [Essentials](https://pypi.org/project/PySide6-Essentials/6.12.0/) and [Shiboken](https://pypi.org/project/shiboken6/6.12.0/) release metadata also identifies LGPL-3.0-only, GPL-2.0-only and GPL-3.0-only as alternatives. PySide6's release description explicitly states that its PyPI wheels serve both open-source and commercial use. The presence of the commercial notice alone is therefore not treated as evidence of a change to a commercial-only license.

In the exact source revision below, [create_wheels.py](https://github.com/pyside/pyside-setup/blob/f50facb83fc3dc5f3240c854668c7a6dd93871b2/create_wheels.py) lists all six texts in `base_files` and copies them into the wheel build root. Its [pyproject template](https://github.com/pyside/pyside-setup/blob/f50facb83fc3dc5f3240c854668c7a6dd93871b2/wheel_artifacts/pyproject.toml.base) declares the LGPL/GPL alternatives, but neither it nor the [setup template](https://github.com/pyside/pyside-setup/blob/f50facb83fc3dc5f3240c854668c7a6dd93871b2/wheel_artifacts/setup.py.base) explicitly selects `license-files`. Setuptools' [documented automatic license-file patterns](https://setuptools.pypa.io/en/latest/userguide/miscellaneous.html) match the commercial notice's filename and do not match the other five filenames. This explains a plausible packaging mechanism for the missing texts; it is an inference from the recipe and inventory, not a statement from the wheel publisher.

## Exact origin of the copied texts

Repository: [official PySide mirror](https://github.com/pyside/pyside-setup), also mirrored by [qtproject/pyside-pyside-setup](https://github.com/qtproject/pyside-pyside-setup).

Release tag: `v6.12.0`. Both mirrors resolved the tag to annotated tag object `6aefae25747a8d860d201f3ab2b2e199b9e8e006`, whose target is commit `f50facb83fc3dc5f3240c854668c7a6dd93871b2`. The [immutable tag object](https://api.github.com/repos/pyside/pyside-setup/git/tags/6aefae25747a8d860d201f3ab2b2e199b9e8e006) records the Qt for Python 6.12.0 release and its 2026-10-08 tag date.

Each source link below uses that commit rather than a moving branch or tag. The local files preserve the upstream UTF-8 bytes and LF line endings.

| Local file | Immutable upstream file | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| [LGPL-3.0-only.txt](qt-licenses/LGPL-3.0-only.txt) | [Source](https://raw.githubusercontent.com/pyside/pyside-setup/f50facb83fc3dc5f3240c854668c7a6dd93871b2/LICENSES/LGPL-3.0-only.txt) | 7651 | `da7eabb7bafdf7d3ae5e9f223aa5bdc1eece45ac569dc21b3b037520b4464768` |
| [GPL-2.0-only.txt](qt-licenses/GPL-2.0-only.txt) | [Source](https://raw.githubusercontent.com/pyside/pyside-setup/f50facb83fc3dc5f3240c854668c7a6dd93871b2/LICENSES/GPL-2.0-only.txt) | 18092 | `8177f97513213526df2cf6184d8ff986c675afb514d4e68a404010521b880643` |
| [GPL-3.0-only.txt](qt-licenses/GPL-3.0-only.txt) | [Source](https://raw.githubusercontent.com/pyside/pyside-setup/f50facb83fc3dc5f3240c854668c7a6dd93871b2/LICENSES/GPL-3.0-only.txt) | 35147 | `8ceb4b9ee5adedde47b31e975c1d90c73ad27b6b165a1dcd80c7c545eb65b903` |
| [Qt-GPL-exception-1.0.txt](qt-licenses/Qt-GPL-exception-1.0.txt) | [Source](https://raw.githubusercontent.com/pyside/pyside-setup/f50facb83fc3dc5f3240c854668c7a6dd93871b2/LICENSES/Qt-GPL-exception-1.0.txt) | 965 | `40678d338ce53cd93f8b22b281a2ecbcaa3ee65ce60b25ffb0c462b0530846b2` |
| [GFDL-1.3-no-invariants-only.txt](qt-licenses/GFDL-1.3-no-invariants-only.txt) | [Source](https://raw.githubusercontent.com/pyside/pyside-setup/f50facb83fc3dc5f3240c854668c7a6dd93871b2/LICENSES/GFDL-1.3-no-invariants-only.txt) | 22955 | `110535522396708cea37c72a802c5e7e81391139f5f7985631c93ef242b206a4` |
| [LicenseRef-Qt-Commercial.txt](qt-licenses/LicenseRef-Qt-Commercial.txt) | [Source](https://raw.githubusercontent.com/pyside/pyside-setup/f50facb83fc3dc5f3240c854668c7a6dd93871b2/LICENSES/LicenseRef-Qt-Commercial.txt) | 462 | `9b1f50aae6267f9d5e0ceb6775ee86450262c25ec7c0573e151fe5d3f18a4700` |

The common set retains the upstream alternatives and the documentation/tool exception texts. Including that set does not select every alternative license for the application's own code or imply that all upstream tools, examples or documentation are executable parts of this application.

The official release source archive is also listed in [Qt's 6.12.0 source download directory](https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.12.0-src/). The commit-specific links above are the provenance used to copy and verify these text files.

## Qt components in the inspected standalone build

The inclusion evidence is the Nuitka report from [Windows alpha run 38303734085](https://github.com/Cenn0/localAiPhotoEditor/actions/runs/38303734085), built from application commit `121d702f89885c9803a2dcc930ef02340607295f`. It identifies the following copied native Qt libraries and plugins. An entry in the separate installed-package inventory is not by itself evidence that a module executes in the editor.

| Reported component | Upstream source |
| --- | --- |
| Qt6Core, Qt6Gui, Qt6Widgets, Qt6Network | [qtbase at 6.12.0](https://github.com/qt/qtbase/tree/025bdad181de241e81bf853c8a2d7bf3d19261a9) |
| Windows, Direct2D, minimal and offscreen platform plugins; modern Windows style; GIF, ICO and JPEG image plugins; certificate, OpenSSL and Schannel TLS plugins | [qtbase plugin sources](https://github.com/qt/qtbase/tree/025bdad181de241e81bf853c8a2d7bf3d19261a9/src/plugins) |
| Qt6Svg, SVG image plugin and SVG icon engine | [qtsvg at 6.12.0](https://github.com/qt/qtsvg/tree/883a58532078d003cefef0a549bfe9f885ce41f5) |
| ICNS, TGA, TIFF, WBMP and WebP image plugins | [qtimageformats at 6.12.0](https://github.com/qt/qtimageformats/tree/dc13f2fbff1d579cfb2eb2d9092e3563b4d05b8e) |
| Qt6Pdf and the PDF image plugin | The installed Python wheel is `PySide6_Pdf==6.12.0.140`. Qt PDF belongs to the [qtwebengine source repository](https://github.com/qt/qtwebengine); see the version boundary below. |

For the three Qt 6.12.0 source modules, the official annotated release tags resolve as follows:

| Repository | Tag object | Immutable release commit |
| --- | --- | --- |
| qt/qtbase | [fcef5b2c755492753eb8f7424dd2bc7337832068](https://api.github.com/repos/qt/qtbase/git/tags/fcef5b2c755492753eb8f7424dd2bc7337832068) | `025bdad181de241e81bf853c8a2d7bf3d19261a9` |
| qt/qtsvg | [0a753f450c4b4671cc97ef1c566512b9ab322382](https://api.github.com/repos/qt/qtsvg/git/tags/0a753f450c4b4671cc97ef1c566512b9ab322382) | `883a58532078d003cefef0a549bfe9f885ce41f5` |
| qt/qtimageformats | [a55b747c08b9ecf55a89ce3f0b191bbd246fcb1d](https://api.github.com/repos/qt/qtimageformats/git/tags/a55b747c08b9ecf55a89ce3f0b191bbd246fcb1d) | `dc13f2fbff1d579cfb2eb2d9092e3563b4d05b8e` |

The `LICENSES/LGPL-3.0-only.txt` files in all three pinned Qt repositories were compared to the copied PySide text and are byte-identical (Git blob `65c5ca88a67c30becee01c5a8816d964b03862f9`). Their source trees also retain per-file SPDX declarations and incorporated third-party attribution files.

### Qt PDF version boundary

Qt PDF's [official documentation](https://doc.qt.io/qt-6/qtpdf-index.html) describes its PDFium-based PDF image plugin and its LGPLv3/GPLv2/commercial licensing alternatives. Its separately versioned source line is now 6.140.x; the installed Python distribution version is 6.12.0.140. On the recording date, the public qtwebengine mirror exposed 6.140.0 prerelease tags but no final `v6.140.0` tag. An exact source commit for the particular packaged PDF binary has not been established here. A moving branch or prerelease commit is not substituted as though that mapping were verified.

The presence of `PySide6_WebEngine` in the build environment's inventory does not establish use of the WebEngine browser API. The report above specifically establishes the PDF image plugin and its native PDF library.

## Source and notice scope

These are upstream release references and unchanged primary license texts, not a claim of a byte-for-byte reproduction of the upstream wheels. The six common texts do not replace notices belonging to embedded native dependencies. The source trees, [Qt's third-party license index](https://doc.qt.io/qt-6/licenses-used-in-qt.html), and [Qt for Python's incorporated-code notices](https://doc.qt.io/qtforpython-6/licenses.html) identify those components. Their relevance depends on the final binary contents and build options.

The project's existing [third-party component notes](../THIRD_PARTY_NOTICES.md) describe library replacement and source-delivery considerations. No new application or binary compatibility guarantee is made by this provenance record.
