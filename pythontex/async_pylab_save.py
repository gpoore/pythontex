# -*- coding: utf-8 -*-
import time
import multiprocessing as mp
import numpy as np
import matplotlib
#matplotlib.use('Agg')
import matplotlib.pyplot as plt
"""
Asynchronous Plotting in Matplotlib: rather than call savefig directly, add plots to an asynchronous queue to avoid holding up the main program. Makes use of multiple processes to speed up the writing out.
original author: astrofrog, https://gist.github.com/1453933
minor modifications by: ob@cakebox.net
"""

class AsyncPylabSave():
    def __init__(self, processes=mp.cpu_count()):
        self.manager = mp.Manager()
        self.nc = self.manager.Value('i', 0)
        self.pids = []
        self.processes = processes

    def async_plotter(self, nc, fig, filename, processes, **kwargs):
        while nc.value >= processes:
            time.sleep(0.1)
        nc.value += 1
        fig.savefig(filename, **kwargs)
        plt.close(fig)
        nc.value -= 1

    def savefig(self, filename, fig=None, **kwargs):
        # Calls fig.savefig(filename) asynchronously, if fig is None (default) the current figure is saved.
        # kwargs are sent directly to savefig.
        if fig == None:
            fig = plt.gcf()
        p = mp.Process(target=self.async_plotter,
                       args=(self.nc, fig, filename, self.processes),
                       kwargs=kwargs)
        p.start()
        self.pids.append(p)

    def join(self):
        for p in self.pids:
            p.join()

"""
Example usage:
# Create instance of Asynchronous plotter
a = AsyncPylabSave()

for i in range(10):

    print 'Preparing %04i.png' % i

    # Generate random points
    x = np.random.random(10000)
    y = np.random.random(10000)

    # Generate figure
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.set_xscale('log')
    ax.set_yscale('log')
    ax.scatter(x, y)

    # Add figure to queue
    a.savefig('%04i.png' % i, fig=fig, facecolor='r')

# Wait for all plots to finish
a.join()
"""
