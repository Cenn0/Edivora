# Third-party components and distribution notes

The application's own code is licensed under Apache-2.0; see `LICENSE`. That license does not replace the terms for Python, Qt, native codecs, inference libraries, model weights, or the compiler runtime.

## Components

| Component | Purpose | Source and applicable notices |
| --- | --- | --- |
| CPython | Bundled language runtime | [Python license](https://docs.python.org/3/license.html); PSF license and incorporated notices |
| PySide6, Shiboken and selected Qt libraries | Desktop widgets and Python bindings | [Qt for Python](https://doc.qt.io/qtforpython-6/licenses.html); LGPLv3/GPL/commercial terms depend on the component |
| Pillow and its native libraries | Decode, colour management, editing and export | [Pillow license](https://github.com/python-pillow/Pillow/blob/main/LICENSE); included codec notices remain applicable |
| NumPy and its native libraries | Tensor preparation and alpha composition | [NumPy license](https://github.com/numpy/numpy/blob/main/LICENSE.txt); BSD terms and bundled library notices |
| ONNX Runtime CPU | Neural network inference | [ONNX Runtime license](https://github.com/microsoft/onnxruntime/blob/main/LICENSE); MIT and third-party notices |
| U2NETP artifact | Foreground segmentation weights | [Original U-2-Net](https://github.com/xuebinqin/U-2-Net), [rembg adapter](https://github.com/danielgatis/rembg/blob/main/rembg/sessions/u2netp.py); see the provenance distinction below |
| Nuitka | Build tool and compiled runtime support | [Nuitka licensing](https://nuitka.net/doc/user-manual.html); the selected version's license and runtime exception apply |

The build copies available license, copying and notice files from installed distributions into `third-party-licenses/`, alongside an inventory of exact installed versions. The inventory also includes development/build tools; inclusion in that list does not mean all of those packages are shipped as executable application dependencies. The Nuitka compilation report records what is actually included.

## Qt and replacement of libraries

This application uses QtCore, QtGui and QtWidgets through PySide6, with dynamically loaded Qt libraries. It does not intentionally select GPL-only Qt add-on modules. Users' rights under the applicable LGPL terms, including modifying/replacing the library and reverse engineering for debugging such modifications, are not restricted by this project.

The standalone directory keeps dynamic libraries as separate files. Corresponding application source and build instructions are in this repository. Qt/PySide6 corresponding source for the exact distributed versions, the relevant library license texts, installation/replacement information and all incorporated notices must accompany an end-user release through a compliant delivery arrangement. A link to an upstream homepage alone is not claimed to discharge those obligations.

The generated notice inventory is a practical starting point for reviewing the actual binary contents. Review the selected modules and source availability before wider distribution. See [Qt's explanation of LGPL obligations](https://www.qt.io/development/open-source-lgpl-obligations).

## Model provenance

The original U-2-Net source repository carries Apache-2.0. The fixed `u2netp.onnx` file is an export hosted in rembg's `v0.0.0` release. A repository-level source license and the license for a separately converted weights asset are distinct evidence. This initial project has not obtained a separate redistribution statement from the weights/export publisher. Do not describe that as individually verified commercial licensing for the ONNX artifact.

The build verifies the artifact's exact size, its upstream MD5 compatibility value, and a pinned SHA-256. Hashes establish byte identity, not copyright permission, model quality or freedom from every security risk. Details and sources are in [docs/MODELS.md](docs/MODELS.md). Model binaries are not committed to Git history.

The initial Windows artifact is an unsigned development alpha. A wider end-user release requires completion of the model provenance and binary notice/source checks as well as the installation tests recorded in [docs/VERIFICATION.md](docs/VERIFICATION.md).
