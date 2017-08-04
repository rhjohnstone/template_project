import pyap_setup as ps
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
import numpy as np

model_number = 1
expt_name = "synthetic_HH"
trace_name = "synthetic_HH"

cmaes_best_fits_file, best_fit_png, best_fit_svg = ps.cmaes_and_figs_files(model_number, expt_name, trace_name)

X, Y, Z, l = np.loadtxt(cmaes_best_fits_file).T

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

ax.scatter(X, Y, Z)

ax.set_title("Hodgkin Huxley 1952 CMA-ES best fits")
ax.set_xlabel('$G_{Na}$')
ax.set_ylabel('$G_K$')
ax.set_zlabel('$G_l$')

plt.show()

