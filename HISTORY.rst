=======
History
=======

0.8.0 (2021-05-18)
------------------
* Support for Zocalo configuration files

0.7.4 (2021-03-17)
------------------
* Documentation improvements

0.7.3 (2021-01-19)
------------------
* Ignore error when logserver hostname can't be looked up immediately

0.7.2 (2021-01-18)
------------------
* Add a symbolic link handling library function
* Cache the logserver hostname by default

0.7.1 (2020-11-13)
------------------
* Add a --dry-run option to zocalo.go

0.7.0 (2020-11-02)
------------------
* Drop support for Python 3.5
* Update language constructs for Python 3.6+

0.6.4 (2020-11-02)
------------------
* Add support for Python 3.9

0.6.3 (2020-05-25)
------------------
* Remove stomp.py requirement - this is pulled in via workflows only

0.6.2 (2019-07-16)
------------------
* Set live flag in service environment if service started with '--live'

0.6.0 (2019-06-17)
------------------
* Start moving dlstbx scripts to zocalo package:
  * zocalo.go
  * zocalo.wrap
* Entry point 'dlstbx.wrappers' has been renamed 'zocalo.wrappers'
* Dropped Python 3.4 support


0.5.4 (2019-03-22)
------------------
* Compatibility fixes for graypy >= 1.0

0.5.2 (2018-12-11)
------------------
* Don't attempt to load non-existing file


0.5.1 (2018-12-04)
------------------
* Fix packaging bug which meant files were missing from the release


0.5.0 (2018-12-04)
------------------
* Add zocalo.service command to start services


0.4.0 (2018-12-04)
------------------
* Add status notification thread logic


0.3.0 (2018-12-04)
------------------
* Add schlockmeister service and base wrapper class


0.2.0 (2018-11-28)
------------------
* Add function to enable logging to graylog


0.1.0 (2018-10-19)
------------------
* First release on PyPI.
