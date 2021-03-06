import ap_simulator  
import pyap_setup as ps
import argparse
import numpy as np
import sys
import numpy.random as npr
import time
import multiprocessing as mp
import argparse

parser = argparse.ArgumentParser()
requiredNamed = parser.add_argument_group('required arguments')
requiredNamed.add_argument("--data-file", type=str, help="csv file from which to read in data", required=True)
requiredNamed.add_argument("--seed", type=int, help="python random seed for initial position", required=True)
parser.add_argument("-i", "--iterations", type=int, help="total MCMC iterations", default=500000)
parser.add_argument("--unscaled", action="store_true", help="perform MCMC sampling in unscaled 'conductance space'", default=False)
parser.add_argument("--non-adaptive", action="store_true", help="do not adapt proposal covariance matrix", default=False)
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

npr.seed(args.seed)

def exponential_scaling(unscaled_params):
    return original_gs ** unscaled_params


def solve_for_voltage_trace(temp_g_params, ap_model):
    ap_model.SetToModelInitialConditions()
    return ap_model.SolveForVoltageTraceWithParams(temp_g_params)


def log_target_exp_scaled(temp_unscaled_params, ap_model, expt_trace):
    temp_unscaled_gs, temp_sigma = temp_unscaled_params[:-1], temp_unscaled_params[-1]
    if (temp_sigma <= 0):
        return -np.inf
    else:
        temp_gs = exponential_scaling(temp_unscaled_gs)
        try:
            test_trace = solve_for_voltage_trace(temp_gs, ap_model)
        except:
            print "Failed to solve"
            print temp_gs
            sys.exit()
        return -len(expt_trace)*np.log(temp_sigma) - np.sum((test_trace-expt_trace)**2)/(2.*temp_sigma**2) + np.dot(temp_unscaled_gs, log_gs)


def log_target_unscaled(temp_params, ap_model, expt_trace):
    """Log target distribution with improper semi-infinite prior"""
    if np.any(temp_params < 0):
        return -np.inf
    else:
        temp_gs, temp_sigma = temp_params[:-1], temp_params[-1]
        try:
            test_trace = solve_for_voltage_trace(temp_gs, ap_model)
        except:
            print "Failed to solve"
            print temp_gs
            sys.exit()
        return -len(expt_trace)*np.log(temp_sigma) - np.sum((test_trace-expt_trace)**2)/(2.*temp_sigma**2)

    
def compute_initial_sigma(temp_unscaled_gs, ap_model, expt_trace):
    temp_gs = exponential_scaling(temp_unscaled_gs)
    test_trace = solve_for_voltage_trace(temp_gs, ap_model)
    return np.sqrt(np.sum((test_trace-expt_trace)**2)/len(expt_trace))
    
    
if args.unscaled:
    log_target = log_target_unscaled
else:
    log_target = log_target_exp_scaled


def do_mcmc_adaptive(ap_model, expt_trace, temperature):#, theta0):
    global loga, acceptance
    #npr.seed(trace_number)
    print "Starting chain"
    start = time.time()
    cmaes_best_fits_file, best_fit_png, best_fit_svg = ps.cmaes_and_figs_files(pyap_options["model_number"], expt_name, trace_name)
    try:
        cmaes_results = np.loadtxt(cmaes_best_fits_file)
        ndim = cmaes_results.ndim
        if ndim == 1:
            best_gs = cmaes_results[:-1]
        else:
            best_index = np.argmin(cmaes_results[:,-1])
            best_gs = cmaes_results[best_index,:-1]
        initial_unscaled_gs = np.log(best_gs) / log_gs
    except Exception, e:
        print "\n",e,"\n"
        initial_unscaled_gs = np.ones(num_params-1)
    if args.unscaled:
        #theta_cur = np.concatenate((exponential_scaling(initial_unscaled_gs),[compute_initial_sigma(initial_unscaled_gs, ap_model, expt_trace)]))
        theta_cur = true_params * npr.rand(4) * 10.
    else:
        sys.exit("\nOnly doing unscaled in this script\n")
    mean_estimate = np.abs(theta_cur)
    cov_estimate = 0.01*np.diag(mean_estimate)
    print "\ntheta_cur:", theta_cur, "\n"
    log_target_cur = log_target(theta_cur, ap_model, expt_trace)

    total_iterations = args.iterations
    thinning = 5
    num_saved = total_iterations / thinning + 1
    burn = num_saved / 4

    chain = np.zeros((num_saved, num_params+1))
    chain[0, :] = np.concatenate((theta_cur, [log_target_cur]))

    loga = 0.
    acceptance = 0.    

    status_when = total_iterations / 100
    adapt_when = 500*num_params

    t = 1
    s = 1
    while t <= total_iterations:
        theta_star = npr.multivariate_normal(theta_cur, np.exp(loga)*cov_estimate)
        """try:
            theta_star = npr.multivariate_normal(theta_cur, np.exp(loga)*cov_estimate)
        except Warning as e:
            print str(e)
            print "Iteration:", t
            print "temperature:", temperature
            print "theta_cur:", theta_cur
            print "loga:", loga
            print "cov_estimate:", cov_estimate
            sys.exit()"""
        log_target_star = log_target(theta_star, ap_model, expt_trace)
        u = npr.rand()
        if np.log(u) < log_target_star - log_target_cur:
            accepted = 1
            theta_cur = theta_star
            log_target_cur = log_target_star
        else:
            accepted = 0
        acceptance = (t-1.)/t * acceptance + 1./t * accepted
        if t % thinning == 0:
            chain[t/thinning,:] = np.concatenate((theta_cur, [log_target_cur]))
        if t % status_when == 0:
            #pass
            print t/status_when, "/", total_iterations/status_when
            print "acceptance =", acceptance
            time_taken_so_far = time.time()-start
            estimated_time_left = int(total_iterations*time_taken_so_far/t - time_taken_so_far)
            print "\n\nEstimated time remaining: {} s = {}-ish min\n\n".format(estimated_time_left, estimated_time_left/60)
        if t == adapt_when:
            mean_estimate = np.copy(theta_cur)
        if t > adapt_when:
            gamma_s = 1./(s+1.)**0.6
            temp_covariance_bit = np.array([theta_cur-mean_estimate])
            cov_estimate = (1-gamma_s) * cov_estimate + gamma_s * np.dot(np.transpose(temp_covariance_bit),temp_covariance_bit)
            mean_estimate = (1-gamma_s) * mean_estimate + gamma_s * theta_cur
            loga += gamma_s*(accepted-0.25)
            s += 1
        t += 1
    # discard burn-in before saving chain, just to save space mostly
    time_taken = int(time.time() - start)
    print "\n\nTime taken: {} s = {} min\n\n".format(time_taken,time_taken/60)
    #chain = chain[burn:, :]
    if not args.unscaled:
        chain[:,:-2] = original_gs**chain[:,:-2]  # return params scaled back into G-space
    return chain


def do_mcmc_non_adaptive(ap_model, expt_trace, temperature):#, theta0):
    global loga, acceptance
    #npr.seed(trace_number)
    print "Starting chain"
    start = time.time()
    cmaes_best_fits_file, best_fit_png, best_fit_svg = ps.cmaes_and_figs_files(pyap_options["model_number"], expt_name, trace_name)
    try:
        cmaes_results = np.loadtxt(cmaes_best_fits_file)
        ndim = cmaes_results.ndim
        if ndim == 1:
            best_gs = cmaes_results[:-1]
        else:
            best_index = np.argmin(cmaes_results[:,-1])
            best_gs = cmaes_results[best_index,:-1]
        initial_unscaled_gs = np.log(best_gs) / log_gs
    except Exception, e:
        print "\n",e,"\n"
        #initial_unscaled_gs = np.ones(num_params-1)
    if args.unscaled:
        #theta_cur = np.concatenate((exponential_scaling(initial_unscaled_gs),[compute_initial_sigma(initial_unscaled_gs, ap_model, expt_trace)]))
        theta_cur = true_params * npr.rand(4) * 10.
    else:
        sys.exit("\nOnly doing unscaled in this script\n")
    cov_estimate = 0.01*np.diag(np.abs(theta_cur))
    print "\ntheta_cur:", theta_cur, "\n"
    log_target_cur = log_target(theta_cur, ap_model, expt_trace)

    total_iterations = args.iterations
    thinning = 5
    num_saved = total_iterations / thinning + 1
    burn = num_saved / 4

    chain = np.zeros((num_saved, num_params+1))
    chain[0, :] = np.concatenate((theta_cur, [log_target_cur]))

    loga = 0.
    acceptance = 0.    

    status_when = total_iterations / 100
    adapt_when = 500*num_params

    t = 1
    s = 1
    while t <= total_iterations:
        theta_star = npr.multivariate_normal(theta_cur, np.exp(loga)*cov_estimate)
        """try:
            theta_star = npr.multivariate_normal(theta_cur, np.exp(loga)*cov_estimate)
        except Warning as e:
            print str(e)
            print "Iteration:", t
            print "temperature:", temperature
            print "theta_cur:", theta_cur
            print "loga:", loga
            print "cov_estimate:", cov_estimate
            sys.exit()"""
        log_target_star = log_target(theta_star, ap_model, expt_trace)
        u = npr.rand()
        if np.log(u) < log_target_star - log_target_cur:
            accepted = 1
            theta_cur = theta_star
            log_target_cur = log_target_star
        else:
            accepted = 0
        acceptance = (t-1.)/t * acceptance + 1./t * accepted
        if t % thinning == 0:
            chain[t/thinning,:] = np.concatenate((theta_cur, [log_target_cur]))
        if t % status_when == 0:
            #pass
            print t/status_when, "/", total_iterations/status_when
            print "acceptance =", acceptance
            time_taken_so_far = time.time()-start
            estimated_time_left = int(total_iterations*time_taken_so_far/t - time_taken_so_far)
            print "\n\nEstimated time remaining: {} s = {}-ish min\n\n".format(estimated_time_left, estimated_time_left/60)
        if t > adapt_when:
            gamma_s = 1./(s+1.)**0.6
            loga += gamma_s*(accepted-0.25)
            s += 1
        t += 1
    # discard burn-in before saving chain, just to save space mostly
    time_taken = int(time.time() - start)
    print "\n\nTime taken: {} s = {} min\n\n".format(time_taken,time_taken/60)
    #chain = chain[burn:, :]
    if not args.unscaled:
        chain[:,:-2] = original_gs**chain[:,:-2]  # return params scaled back into G-space
    return chain


if args.non_adaptive:
    do_mcmc = do_mcmc_non_adaptive
else:
    do_mcmc = do_mcmc_adaptive

protocol = 1
solve_start, solve_end, solve_timestep, stimulus_magnitude, stimulus_duration, stimulus_period, stimulus_start_time = ps.get_protocol_details(protocol)
solve_end = 100  # just for HH
original_gs, g_parameters, model_name = ps.get_original_params(pyap_options["model_number"])
log_gs = np.log(original_gs)
num_params = len(original_gs)+1  # include sigma

true_params = np.concatenate((original_gs, [0.25]))

def do_everything():
    try:
        expt_times, expt_trace = np.loadtxt(trace_path,delimiter=',').T
    except:
        sys.exit( "\n\nCan't find (or load) {}\n\n".format(trace_path) )
    
    solve_start, solve_end = expt_times[[0,-1]]
    solve_timestep = expt_times[1] - expt_times[0]

    ap_model = ap_simulator.APSimulator()
    ap_model.DefineStimulus(stimulus_magnitude, stimulus_duration, pyap_options["stimulus_period"], stimulus_start_time)
    ap_model.DefineSolveTimes(solve_start, solve_end, solve_timestep)
    ap_model.DefineModel(pyap_options["model_number"])
    ap_model.SetExtracellularPotassiumConc(pyap_options["extra_K_conc"])
    ap_model.SetIntracellularPotassiumConc(pyap_options["intra_K_conc"])
    ap_model.SetExtracellularSodiumConc(pyap_options["extra_Na_conc"])
    ap_model.SetIntracellularSodiumConc(pyap_options["intra_Na_conc"])
    ap_model.SetNumberOfSolves(pyap_options["num_solves"])
    if (data_clamp_on < data_clamp_off):
        ap_model.UseDataClamp(data_clamp_on, data_clamp_off)
        ap_model.SetExperimentalTraceAndTimesForDataClamp(expt_times, expt_trace)

    temperature = 1
    mcmc_file, log_file, png_dir = ps.mcmc_file_log_file_and_figs_dirs(pyap_options["model_number"], expt_name, trace_name, args.unscaled, args.non_adaptive)
    spl = mcmc_file.split('.')
    mcmc_file = "{}_seed_{}.{}".format(spl[0], args.seed, spl[1])
    spl = log_file.split('.')
    log_file = "{}_seed_{}.{}".format(spl[0], args.seed, spl[1])
    log_start_time = time.time()
    chain = do_mcmc(ap_model, expt_trace, temperature)
    log_time_taken = time.time() - log_start_time
    np.savetxt(mcmc_file, chain)
    with open(log_file, "w") as outfile:
        outfile.write("Expt: {}\n".format(expt_name))
        outfile.write("Trace: {}\n".format(trace_name))
        outfile.write("Time taken: {} s = {} min = {} hr\n".format(int(log_time_taken), round(log_time_taken/60.,1), round(log_time_taken/3600.,1)))
        outfile.write("Final loga: {}\n".format(loga))
        outfile.write("Final acceptance rate: {}\n".format(acceptance))
    print "\nSaved MCMC output at {}\n".format(mcmc_file)
    return None

do_everything()


