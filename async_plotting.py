import time
import multiprocessing as mp

import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


class AsyncPlotter():

    def __init__(self, processes=mp.cpu_count()):

        self.manager = mp.Manager()
        self.nc = self.manager.Value('i', 0)
        self.pids = []
        self.processes = processes

    def async_plotter(self, nc, fig, filename, processes):
        while nc.value >= processes:
            time.sleep(0.1)
        nc.value += 1
        print "Plotting " + filename
        fig.savefig(filename)
        plt.close(fig)
        nc.value -= 1

    def save(self, fig, filename):
        p = mp.Process(target=self.async_plotter,
                       args=(self.nc, fig, filename, self.processes))
        p.start()
        self.pids.append(p)

    def join(self):
        for p in self.pids:
            p.join()

# Create instance of Asynchronous plotter
a = AsyncPlotter()

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
    a.save(fig, '%04i.png' % i)

# Wait for all plots to finish
a.join()
