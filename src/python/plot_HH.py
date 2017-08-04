import pyap_setup as ps
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
import numpy as np

model_number = 1
expt_name = "synthetic_HH"
trace_name = "synthetic_HH"

cmaes_best_fits_file, best_fit_png, best_fit_svg = ps.cmaes_and_figs_files(model_number, expt_name, trace_name)

all_points = np.loadtxt(cmaes_best_fits_file)

data = all_points[:,:-1]
data_mean = np.mean(data, axis=0)

# Do an SVD on the mean-centered data.
uu, dd, vv = np.linalg.svd(data - data_mean)

p = np.polyfit(data[:,0], data[:,1:], deg=1)
print p

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

ax.scatter(*data.T)

ax.set_title("Hodgkin Huxley 1952 CMA-ES best fits")
ax.set_xlabel('$G_{Na}$')
ax.set_ylabel('$G_K$')
ax.set_zlabel('$G_l$')

plt.show()

