import pyap_setup as ps
import argparse
import numpy as np
import sys
import numpy.random as npr
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import itertools as it


#python_seed = 1
#npr.seed(python_seed)

parser = argparse.ArgumentParser()
requiredNamed = parser.add_argument_group('required arguments')
requiredNamed.add_argument("--data-file", type=str, help="first csv file from which to read in data", required=True)
requiredNamed.add_argument("-n", "--num-traces", type=int, help="which hMCMC to use", required=True)
parser.add_argument("-s", "--series", action="store_true", help="plot serially-run hMCMC", default=False)

args, unknown = parser.parse_known_args()
if len(sys.argv)==1:
    parser.print_help()
    sys.exit(1)
args, unknown = parser.parse_known_args()
trace_path = args.data_file
split_trace_path = trace_path.split('/')
expt_name = split_trace_path[4]
trace_name = split_trace_path[-1][:-4]
options_file = '/'.join( split_trace_path[:5] ) + "/PyAP_options.txt"
expt_params_file = '/'.join( split_trace_path[:5] ) + "/expt_params.txt"

split_trace_name = trace_name.split("_")
first_trace_number = int(split_trace_name[-1])

pyap_options = {}
with open(options_file, 'r') as infile:
    for line in infile:
        (key, val) = line.split()
        if (key == "model_number") or (key == "num_solves"):
            val = int(val)
        else:
            val = float(val)
        pyap_options[key] = val
        
data_clamp_on = pyap_options["data_clamp_on"]
data_clamp_off = pyap_options["data_clamp_off"]
        
original_gs, g_parameters, model_name = ps.get_original_params(pyap_options["model_number"])
num_gs = len(original_gs)

g_labels = ["${}$".format(g) for g in g_parameters]

parallel = not args.series
print parallel


"""for n, i in it.product(range(2), range(num_gs)):
    print n, i
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.grid()
    if n == 0:
        xlabel = r"\hat{" + g_parameters[i] +"}$"
        figname = "trace_{}_top_{}.png".format(n, g_parameters[i])
    elif n == 1:
        xlabel = r"\sigma_{" + g_parameters[i] +"}^2$"  # need to check if this squared is correct
        figname = "trace_{}_sigma_{}_squared.png".format(n, g_parameters[i])
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Normalised frequency")
    idx = (2+n)*num_gs + i
    ax.hist(chain[burn:, idx], bins=40, color='blue', edgecolor='blue')"""
    #fig.savefig(png_dir+figname)
    #plt.close()

    
N_e = args.num_traces

expt_params = np.loadtxt(expt_params_file)[:N_e,:]

i = 4

colours = ['#1b9e77','#d95f02','#7570b3']

fig, ax = plt.subplots()
fig.set_tight_layout(True)


def update(n):
    label = 'timestep {0}'.format(n)
    print(label)
    ax.cla()
    ax.grid()
    ax.set_xlabel(g_labels[i])
    
    ax.set_title('Trace {}'.format(n))
    
    single_trace_name = trace_name[:-1]+str(n)
    mcmc_file, log_file, png_dir = ps.mcmc_file_log_file_and_figs_dirs(pyap_options["model_number"], expt_name, single_trace_name, unscaled=True, non_adaptive=False, temperature=1)
    single_chain = np.loadtxt(mcmc_file, usecols=[i, -1])
    
    best_ll_idx = np.argmax(single_chain[:,-1])
    best_ll_param = single_chain[best_ll_idx, 0]
    ax.hist(single_chain[:, 0], normed=True, bins=40, color=colours[0], edgecolor=colours[0])
    ax.axvline(best_ll_param, color=colours[1], lw=3, label='MPD')

    ax.axvline(expt_params[n, i], color=colours[2], lw=3, label='True')

    ax.legend()
    
    #return ax
    
anim = FuncAnimation(fig, update, frames=np.arange(1, 32), interval=1000)
try:
    anim.save('GKr.gif', dpi=80, writer='imagemagick')
except:
    pass
plt.show(block=True)

