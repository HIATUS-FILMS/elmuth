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

* Flask (BSD License)
* Werzeug (BSD License)
* cryptography | Fernet (Apache 2.0 / BSD License)
* requests (BSD license)
* Jinja2 (BSD License)
* Tailwind CSS (MIT License)


Roadmap (For v1.0)
-------------------

* Software base
- [x] Config file & database support
- [ ] Media scan
- [ ] Playlist generator

* WebUI
- [x] Setup wizard (Not working yet)
- [ ] Playlist editor
- [ ] Playout control
- [ ] Settings section
- [ ] Media asset management

* ffplayout
- [ ] ffplayout connexion
- [ ] ffplayout control
