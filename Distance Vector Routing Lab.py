#!/usr/bin/env python3
import GuiTextArea, RouterPacket, F
from copy import deepcopy

class RouterNode():
    myID = None
    myGUI = None
    sim = None
    costs = None

    # added members
    neighbors = None
    route = None
    table = None
    header = None

    # Access simulator variables with:
    # self.sim.POISONREVERSE, self.sim.NUM_NODES, etc.

    # --------------------------------------------------
    def __init__(self, ID, sim, costs):
        self.myID = ID
        self.sim = sim
        self.myGUI = GuiTextArea.GuiTextArea("  Output window for Router #" + str(ID) + "  ")
        self.costs = deepcopy(costs)

        # initialize list of neighbors
        self.neighbors = [x for x in range(self.sim.NUM_NODES) if x != self.myID and self.costs[x] != self.sim.INFINITY]

        # initialize the route list which will be self.neighbors at time 0
        self.route = [x if self.costs[x] != self.sim.INFINITY else '-' for x in range(self.sim.NUM_NODES)]

        # initialize routing table which will be just self.sim.INFINITY until we receive data from neighbors.
        self.table = [[self.costs[y] if x == self.myID else self.sim.INFINITY for y in range(self.sim.NUM_NODES)] for x in range(self.sim.NUM_NODES)]

        # initialize the header to be used for all output tables
        self.header = f'{"dst":>7} |' + ''.join([f'{x:>5}' for x in range(self.sim.NUM_NODES)])

        # now that the node is fully initialized we send updates to all neighbors
        for x in self.neighbors:
            self.sendUpdate(RouterPacket.RouterPacket(self.myID, x, self.costs))

        self.printDistanceTable()



    # --------------------------------------------------
    def recvUpdate(self, pkt):
        # update table and run Bellman-Ford algorithm if received data differs
        if pkt.mincost != self.table[pkt.sourceid]:
            self.table[pkt.sourceid] = pkt.mincost
            self.doBFA()


    # --------------------------------------------------
    def doBFA(self):
        # if the algorithm makes changes, update = True and we notify neighbo
        updated = False

        # for each router in the system try to find the neighbor that provides the shortest path to it
        for x in range(self.sim.NUM_NODES):     # for each router
            if x == self.myID:
                continue

            # start by assuming that nearest would be to the node directly
            lowcost = self.costs[x]
            nexthop = x

            for y in self.neighbors:            # for each neighbor
                if x == y:
                    continue

                # update lowcost/nexthop when a shorter path is found
                if (newcost := self.costs[y] + self.table[y][x]) < lowcost:
                    lowcost = newcost
                    nexthop = y

            # check that the newfound path cost differs from current one
            if (lowcost != self.table[self.myID][x]):
                print(f'Node {self.myID} has a new lowest cost: {self.myID} to {x} via {nexthop} with cost {lowcost} at time {str(self.sim.getClocktime())}')
                updated = True
                self.table[self.myID][x] = lowcost
                self.route[x] = nexthop

        if updated:
            # copy mincost so we can change it if POISONREVERSE is active
            mincost = deepcopy(self.table[self.myID])

            for x in self.neighbors:
                if self.sim.POISONREVERSE:
                    for y in range(self.sim.NUM_NODES):     # for each router
                        if x == self.route[y] and x != y:   # our shortest path is to Y via X
                            mincost[y] = self.sim.INFINITY  # tell neighbor X that our cost to Y is self.sim.INFINITY to avoid loop

                self.sendUpdate(RouterPacket.RouterPacket(self.myID, x, mincost))


    # --------------------------------------------------
    def sendUpdate(self, pkt):
        self.sim.toLayer2(pkt)


    # --------------------------------------------------
    def printDistanceTable(self):
        self.myGUI.println("Current table for " + str(self.myID) +
                           "  at time " + str(self.sim.getClocktime()))
        self.myGUI.println()

        # print out the table header for the routing table
        self.myGUI.println("Distance table:")
        self.myGUI.println(self.header)
        self.myGUI.println(''.ljust(len(self.header), '-'))     # horizontal line
        for x in self.neighbors:
            self.myGUI.println(f'{"nbr":^5}{x:>2} |' + ''.join([f'{y:>5}' for y in self.table[x]]))
        self.myGUI.println()

        # print out the distance vector and routes
        self.myGUI.println("Our distance vector and routes:")
        self.myGUI.println(self.header)
        self.myGUI.println(''.ljust(len(self.header), '-'))
        self.myGUI.println(f'{"cost":^7} |' + ''.join(f'{x:>5}' for x in self.table[self.myID]))
        self.myGUI.println(f'{"route":^7} |' + ''.join(f'{x:>5}' for x in self.route))
        self.myGUI.println()
        self.myGUI.println()


    # --------------------------------------------------
    def updateLinkCost(self, dest, newcost):
        # update cost vector and run Bellman-Ford algorithm
        self.costs[dest] = newcost
        self.doBFA()
