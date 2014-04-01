Gonewilder
==========

Content downloader.


Installing
==========

Requires:
* Python
* Python Imaging Library (PIL)
* SQLite3

Optional:
* Apache (for web interface only)
** Files in root (`.`) and `py` directories need to be CGI Executable in Apache

Install dependencies on Debian: 7 (wheezy)
==========================================

```bash
apt-get install python2.7-dev python-tk python-setuptools python-pip python-dev libjpeg8-dev libjpeg tcl8.5-dev tcl8.5 zlib1g-dev zlib1g libsnack2-dev tk8.5-dev libwebp-dev libwebp2 vflib3-dev libfreetype6-dev libtiff5-dev libjbig-dev
pip install pillow
```

Executing
=========

Execute `Gonewild.py` in the `./py/` directory. Include no arguments to start infinite loop which checks for and downloads new content. Other options available, see:

```bash
python Gonewild.py --help
```
