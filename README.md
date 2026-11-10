<div align="center">

![Banner](https://github.com/user-attachments/assets/669348c4-343f-4c6b-9d05-1588ef194b6d)

<h2>Broadcast video production software and a media asset management for ffplayout</h2>

Elmuth aims to manage a television playout system capable of scheduling a broadcast lineup. It is designed to work with ffplayout.

![](https://img.shields.io/badge/Recommended%20platform%20-Linux-red?style=flat)
![](https://img.shields.io/badge/Language-Python-blue?style=flat)
![](https://img.shields.io/badge/License-GPL--3.0-green?style=flat)
![](https://img.shields.io/badge/PRs-Accepted-yellow?style=flat)

</div>

## Informations

> [!CAUTION]
> elmuth is still under heavy development; use it with the understanding that the product is not yet ready for production.

Originally conceived for a French WebTV project, the project aims to follow a roadmap that will enable it to serve a wider variety of projects while making the technology accessible to as many people as possible.

![Screenshot](https://github.com/user-attachments/assets/f8a30aa8-3277-4d82-be4a-701ee87e83ee)

## What is the current status of elmuth's development?

The project is approaching the first alpha releases. It should be released within a few months. However, you can test it as development progresses by running it on your machine using ffplayout.

Any help will be welcome once the project is a little further along. Since I’m not a professional developer, the first versions will be based on amateur Python 3.14, HTML, Tailwind, HTMX and Javascript code.

## Is AI accepted in code ?

Currently, the use of AI is not permitted for designing critical parts of the code. These tools are only allowed during the debugging phase. This measure has been taken to avoid any issues related to code that is not understood or is copyrighted, as well as security concerns.

If you need to use it to fix bugs or resolve an issue, we recommend using local AI whenever possible in this context.

## Install

To install **elmuth** follow the instructions in the wiki :

> [!CAUTION]
> The nightly versions of elmuth may cause issues during installation and use. Please test the software in a controlled virtual environment. You are solely responsible for any bugs, crashes, or other issues that arise from using elmuth’s nightly versions on a production machine.

* [Installation steps](https://github.com/HIATUS-FILMS/elmuth/wiki/Install-instructions)

## License

elmuth is distributed under the GNU General Public License GPLv3, see LICENSE file for details.

elmuth uses the following third party libraries :

* Tailwind CSS                   (MIT License)
* Flask               3.1.3      (BSD-3-Clause)
* Flask-Login         0.6.3      (MIT License)
* Jinja2              3.1.6      (BSD License)
* MarkupSafe          3.0.3      (BSD-3-Clause)
* Werkzeug            3.1.8      (BSD-3-Clause)
* blinker             1.9.0      (MIT License)
* certifi             2026.7.22  (Mozilla Public License 2.0 (MPL 2.0))
* cffi                2.1.1      (MIT-0)
* charset-normalizer  3.5.1      (MIT)
* click               8.5.0      (BSD-3-Clause)
* cryptography        50.0.1     (Apache-2.0 OR BSD-3-Clause)
* idna                3.20       (BSD-3-Clause)
* itsdangerous        2.2.0      (BSD License)
* pycparser           3.0        (BSD-3-Clause)
* requests            2.34.2     (Apache Software License)
* urllib3             2.8.0      (MIT)
  
*Software license list by pip-licenses 5.5.5 (MIT License)*

## Roadmap (For v1.0)

### Software base
- [x] Config file & database support
- [x] Media scan
- [x] Playlist generator **(Use with caution)**

### WebUI
- [x] Setup wizard
- [x] Playlist editor
- [x] Playout control
- [ ] Settings section
- [x] Media asset management

### ffplayout
- [x] ffplayout connexion
- [x] ffplayout control
