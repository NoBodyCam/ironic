Ironic - The Real Java driver
======

Ironic is an Incubated OpenStack project which aims to provision
bare metal machines instead of virtual machines, forked from the
Nova Baremetal driver. This fork is intended to ease the life of
system administrators and cloud develpoers by enabling a X10
Driver for Ironic, using this Ironic driver and X10 enabled
hardware you will be able to deploy a cup of coffee, as easily
as you can deploy a vm. With the proper orchestration (heat,
salt, chef) it would be possible to deploy a entire meal.

-----------------
Project Resources
-----------------
After a little looking I found my x10 hardware is way out of date.
It looks like there is now Inste0n: So I've reworked the driver to
use Inste0n hardware.

Here are a couple of links to some cheap hardware that can be picked
up at your local Home Depot. (you know its a real hack if you get to go to Home Depot)

 http://www.homedepot.com/p/Insteon-PowerLine-Modem-2413S/204380605?N=arcd#.UlyE-Xgkt38
 http://www.homedepot.com/p/Smarthome-ApplianceLinc-INSTEON-Plug-in-Appliance-On-Off-3-Pin-Module-2456s3/100530075?N=arcd#.UlyFiXgkt38

I use plmpower from this ubuntu package: https://launchpad.net/ubuntu/raring/+package/powerman
to issue the actual commands to the devices.

When creating a Inste0n node the Inste0n ID must be entered as a valid MAC address.
This places a restriction on Inste0n ID's. The plm module only uses the first two characters
of the nodes Mac address. As example, a node using the plm driver with mac address
of A1:00:00:00:00 would act on Inste0n device A1.

