![Logo](static/img/logo.png)

elmuth - for ffplayout
===============

Elmuth aims to manage a television playout system capable of scheduling a broadcast lineup. It is designed to work with ffplayout.

Originally conceived for a French WebTV project, the project aims to follow a roadmap that will enable it to serve a wider variety of projects while making the technology accessible to as many people as possible.

![Project](http://www.image-heberg.fr/files/1790018688165833045.png)

Is AI accepted in code ?
-------------------

Currently, the use of AI is not permitted for designing critical parts of the code. These tools are only allowed during the debugging phase. This measure has been taken to avoid any issues related to code that is not understood or is copyrighted, as well as security concerns.

What is the current status of elmuth's development?
-------------------

The project is still in its early stages, and the first pre-alpha versions should be released within a few weeks or months.

Any help will be welcome once the project is a little further along. Since I’m not a professional developer, the first versions will be based on amateur Python 3.14, HTML, CSS and Javascript code.


License
-------------------
elmuth is distributed under the GNU General Public License GPLv3, see LICENSE file for details.

elmuth uses the following third party libraries :

* Tailwind CSS                   (MIT License)
* Flask               3.1.3      (BSD-3-Clause)
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
  
*Software license list by pip-licenses 5.5.5*

Roadmap (For v1.0)
-------------------

* Software base
- [x] Config file & database support
- [ ] Media scan
- [ ] Playlist generator

* WebUI
- [x] Setup wizard
- [ ] Playlist editor
- [ ] Playout control
- [ ] Settings section
- [ ] Media asset management

* ffplayout
- [x] ffplayout connexion
- [x] ffplayout control (Work in progress)
