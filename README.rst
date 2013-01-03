==========================================
psendurance -- "Packet-switched endurance"
==========================================

Introduction
============

Peristent mobile data connection using ofono_. 

Mobile data connections, such as 3G and UTMS, break down every now and then. 
This poses a challenge for autonomous devices, small servers that connect to 
Internet using mobile data connections. There continous connection is desired.
This script tries to open such a connection and re-open it every time the
connection is lost.

This script is intended for autonomous devices that connect exclusively
to a mobile network. It is not intended to be a connman_ replacement.
Only one modem with one pre-defined internet context is currently supported. 

Currently this is developed and tested on a `Raspberry Pi`_ running Raspbian_, 
and a Huawei E367 USB dongle. 

At the present state it's quite experimental. Use it at your own risk. 
Ideas, improvements, patches and pull requests are welcome.

.. _ofono: http://www.ofono.org
.. _connman: http://www.connman.net
.. _`Raspberry Pi`: http://www.raspberrypi.org
.. _Raspbian: http://www.raspbian.org


License
=======

psendurance is released under the terms of GPLv2, see ``COPYING``.


Requirements
============

The following Raspbian packages should be installed:

- ``ofono``
- ``python``
- ``python-dbus``
- ``python-gobject``
- For convenience: ``usb-modeswitch``, ``usb-modeswitch-data``

You can install these in the usual way:

::

 $ apt-get install <package-name> 


Usage
=====

Plug in a 3G dongle with a SIM without a PIN. Make sure that the ZeroCD mode
is skipped by ``usb-modeswitch`` and ``ofonod`` sees the actual modem device.
(See ofono test scripts, ``./list-modems`` below.)

::

  $ python psendurance.py 

and hope it works.


Troubleshooting and debugging tips
==================================

ofono test scripts
------------------

Download the ofono package, untar it and go to ``/tests/`` directory.
There you can find many python scripts, which can be used to manually
command and test out your modem.

For example, this script executes roughly the same operations as:

::

 $ ./enable-modem
 $ ./online-modem
 $ ./set-roaming-allowed
 $ ./activate-context

List modems:

::

 $ ./list-modems

List contexts:

::

 $ ./list-contexts

Create an internet context:

::

 $ ./create-internet-context <APN> [username] [password]


Running ofono in debug mode 
---------------------------

Ofono's debug output is fairly verbose and informative. You can see it
by running the ofono daemon manually. Shut down the ofono system daemon first:

::

 $ sudo /etc/init.d/ofono stop
 $ sudo ofonod -nd
 (hit Ctrl-C to shutdown this, when done)

::

 $ sudo /etc/init.d/ofono start


Use dmesg
---------

Looking at kernel output is helpful for determining whether a 3G
dongle is in the right mode. If you're seeing just lines with "scsi",
the dongle is in ZeroCD mode. If the dongle gets into a modem mode, you should
see lines informing about creation ``/dev/tty*`` device nodes, 
such as ``/dev/ttyUSB0``.


"Missing support for TUN/TAP devices"
-------------------------------------

Seen in ofonod's debug output.

In Raspbian, ``tun`` module is not loaded by default. You can load it manually:

::

 $ sudo modprobe tun


"GPRS is not attached"
----------------------

Seen when trying to call ``./activate-context``.

One reason for this is that your ISP uses roaming network
of another ISP, and this is not allowed by ofono's default settings.
For example, Saunalahti in Finland uses Elisa's network.
RoamingAllowed must be enabled explicitly. In ofono test scripts (see above):

::

 $ ./set-roaming-allowed

You might want to be careful, if you're using this near your
country borders or a foreign country. Watch out those roaming fees,
and make sure you're registered to the correct network.
