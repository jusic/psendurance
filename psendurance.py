#!/usr/bin/env python

#    psendurance -- persistent mobile data connection using ofono
#    Copyright (C) 2013  Jussi Sainio
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import dbus, sys
import gobject
import dbus.mainloop.glib

class OfonoModem:
    """
    Handles one ofono modem instance.

    By default, it:
        - brings the modem online, 
        - allows modem to attach roaming networks,
        - activates the first internet context.

    If a connection or network is lost, it will activate the context again
    when the network gets up.
    """

    def __init__(self, dbusconn, path):
        self.dbusconn = dbusconn
        self.path = path
        self.modem = dbus.Interface(self.dbusconn.get_object('org.ofono', self.path), 'org.ofono.Modem')

        self.sim_changed_handler = None

        self.has_powered = False
        self.has_online = False
        self.has_sim = False

        self.has_connmgr = False

        self.context = None

        self.sim_changed_handler = self.dbusconn.add_signal_receiver(self.sim_changed,
                    bus_name="org.ofono",
                    dbus_interface="org.ofono.SimManager",
                    signal_name="PropertyChanged",
                    path=self.path,
                    path_keyword="path",
                    interface_keyword="interface")

        self.modem_property_changed_handler = self.dbusconn.add_signal_receiver(self.modem_property_changed,
                    bus_name="org.ofono",
                    dbus_interface="org.ofono.Modem",
                    signal_name="PropertyChanged",
                    path=self.path,
                    path_keyword="path",
                    interface_keyword="interface")

        self.connmgr_property_changed_handler = self.dbusconn.add_signal_receiver(self.connmgr_property_changed,
                    bus_name="org.ofono",
                    dbus_interface="org.ofono.ConnectionManager",
                    signal_name="PropertyChanged",
                    path=self.path,
                    path_keyword="path",
                    interface_keyword="interface")

        self.connctx_property_changed_handler = None

    def destruct(self):
        """
        Disconnect all signal handlers.
        """

        if self.sim_changed_handler != None:
            self.sim_changed_handler.remove()
        self.sim_changed_handler = None

        if self.modem_property_changed_handler != None:
            self.modem_property_changed_handler.remove()
        self.modem_property_changed_handler = None

        if self.connmgr_property_changed_handler != None:
            self.connmgr_property_changed_handler.remove()
        self.connmgr_property_changed_handler = None

        if self.connctx_property_changed_handler != None:
            self.connctx_property_changed_handler.remove()
        self.connctx_property_changed_handler = None

    def connctx_property_changed(self, name, value, path, interface):
        print "in connctx_property_changed (%s)" % path
        if name == "Active":
            self.check_context(value)

    def connmgr_property_changed(self, name, value, path, interface):
        """
        Connection Manager property change handler
        """
        print "in connmgr_property_changed (%s)" % path

        if name == "Attached":
            self.check_network(value)

    def modem_property_changed(self, name, value, path, interface):
        """
        Check if modem has ConnectionManager, set roaming
        """
        #print "in modem_property_changed (%s)" % path
        if name == "Interfaces":
            self.check_interfaces(value)


    def sim_changed(self, name, value, path, interface):
        """
        Turn the modem online if we have SubscriberIdentity
        """
        print "in sim_changed (%s)" % path

        if name != "SubscriberIdentity":
            return True

        if self.has_online == False:
            self.modem.SetProperty("Online", dbus.Boolean(1), timeout = 120)

        return True

    def check_context(self, value):
        """
        Check if connection context is activated.
        """

        if value == False:
            print "Mobile data connection lost (%s)" % self.contextpath

            # retry
            self.activate_context()

        if value == True:
            print "Mobile data connection established (%s)" % self.contextpath

    def activate_context(self):
        """
        Activates a connection context (connects to internet).
        """
        
        try:
            self.context.SetProperty("Active", dbus.Boolean(1), timeout = 100)
            print "context activated (%s)" % self.contextpath
        except dbus.DBusException, e:
            print "context activation failed (%s)" % self.contextpath

    def check_network(self, value):
        """
        Check if mobile network is available.
        """
        if value == False:
            print "Connection to mobile network lost (%s)" % self.path
        elif value == True:
            print "Connection to mobile network established (%s)" % self.path
            self.check_context(self.context.GetProperties()["Active"])

    def check_interfaces(self, value):
        """
        Check if SimManager or ConnectionManager interfaces are available.
        """
        if "org.ofono.SimManager" in value:
            self.has_sim = True

        if "org.ofono.ConnectionManager" in value:
            if self.has_connmgr == False:
                
                #
                # Connection manager has appeared for the first time.
                #

                connman = dbus.Interface(self.dbusconn.get_object('org.ofono', self.path), 
                    'org.ofono.ConnectionManager')

                # Set roaming allowed, power up the connmgr to attach network.

                connman.SetProperty("RoamingAllowed", dbus.Boolean(1))    
                print "Set roaming allowed (%s)" % self.path
                connman.SetProperty("Powered", dbus.Boolean(1))
                print "Connection manager powered (%s)" % self.path
               

                # Re-power up modem (for some reason needed).

                self.modem.SetProperty("Powered", dbus.Boolean(1), timeout = 120)
                print "Modem powered (%s)" % self.path
                self.modem.SetProperty("Online", dbus.Boolean(1), timeout = 120)
                print "Modem online (%s)" % self.path

               

                # Get all contexts and select the first one.

                contexts = connman.GetContexts()
                self.contextpath = contexts[0][0]

                print "Context path: %s" % self.contextpath

                self.connctx_property_changed_handler = self.dbusconn.add_signal_receiver(self.connctx_property_changed,
                            bus_name="org.ofono",
                            dbus_interface="org.ofono.ConnectionContext",
                            signal_name="PropertyChanged",
                            path=self.contextpath,
                            path_keyword="path",
                            interface_keyword="interface")


                self.context = dbus.Interface(bus.get_object('org.ofono', self.contextpath),
                    'org.ofono.ConnectionContext')


                self.check_network(connman.GetProperties()["Attached"])
                
                self.has_connmgr = True


    def check_property(self, key, value):
        """
        Check modem properties.
        """

        if key == "Interfaces":
            self.check_interfaces(value)

        elif key == "Powered":
            if value == True:
                print "Modem enabled (%s)" % self.path
                self.has_powered = True

            else:
                print "Modem disabled (%s)" % self.path
                try:
                    self.modem.SetProperty("Powered", dbus.Boolean(1), timeout = 120)
                except:
                    print "error"
                    pass

        elif key == "Online":
            if value == True:
                print "Modem online (%s)" % self.path
                self.has_online = True
            else:
                print "Modem offline (%s)" % self.path

        elif key == "Lockdown":
            if value == True:
                print "Modem locked (%s)" % self.path
            else:
                print "Modem unlocked (%s)" % self.path

class OfonoHandler:
    """
    Handles adding and removal of ofono modems.
    """

    def __init__(self, dbusconn):
        self.dbusconn = dbusconn
        self.manager = dbus.Interface(bus.get_object('org.ofono', '/'), 'org.ofono.Manager')
        self.modems = {}

        self.dbusconn.add_signal_receiver(self.modem_added,
                        bus_name="org.ofono",
                        signal_name = "ModemAdded",
                        member_keyword="member",
                        path_keyword="path",
                        interface_keyword="interface")

        self.dbusconn.add_signal_receiver(self.modem_removed,
                        bus_name="org.ofono",
                        signal_name = "ModemRemoved",
                        member_keyword="member",
                        path_keyword="path",
                        interface_keyword="interface")


    def ofono_connect():
        pass

    def ofono_disconnect():
        pass

    def get_modems(self):
        """
        Fetch all modems currently in system.
        """

        modems = self.manager.GetModems()

        for path, properties in modems:
            self.create_modem(path, properties)


    def modem_added(self, name, value, member, path, interface):
        print "modem added (%s)" % name
        self.create_modem(name, value)


    def modem_removed(self, name, member, path, interface):
        print "modem removed (%s)" % name
        self.destroy_modem(name)


    def create_modem(self, path, properties):
        """
        Create and add modem to the modem dict.
        """
        
        modemdata = OfonoModem(self.dbusconn, path)

        for key, value in properties.items():
            modemdata.check_property(key, value)

        self.modems[path] = modemdata

    def destroy_modem(self, path):
        """
        Remove and destroy modem from the modem dict.
        """
        self.modems[path].destruct()

        del self.modems[path]


if __name__ == "__main__":
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)    

    # get the dbus
    bus = dbus.SystemBus()

    # setup ofono handler
    oh = OfonoHandler(bus)
    
    # check current modems
    oh.get_modems()

    # enter the event loop
    mainloop = gobject.MainLoop()
    mainloop.run()
