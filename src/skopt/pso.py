"""
Particle Swarm Optimizer (PSO)


## Particles

In PSO, a particle represents a set of parameters to be optimised. 
Each parameter is therefore a degree of freedom of the particle.  
Each particle is represented by its coordinate value. Additionally it needs several attributes:
    
    * fitness (the quality of the set of parameters) -- e.g. RMS deviation
    * speed -- how much the position of the particle changes from one generation to the next
    * smin/smax -- speed limits
    * best -- particles own best position (i.e. with highest fitness)


## Particle normalisaton/re-normalisation

Additionally to the above generic PSO-related attributes, we need to introduce position normalisation as follows.  
The parameters giving the particle coordinates are with different meaning, magnitudes and units.
However, to keep the PSO generic, it is best to impose identical scale in each dimension,
so that particle range is the same in each direction.  
This is achieved by normalising the parameters so that the particle position in each dimension is between -1 and +1.  
However, when evaluating the fitness of the particle, we need the renormalised values 
(i.e. the true values of the parameters).  

Hence we introduce three additional attributes:
    
* norm -- a list with the scaling factors for each dimension ($\eta$),
* shift -- offset of the parameter range from 0 ($\sigma$),
* renormalized -- the true value of the parameters ($\lambda$) represented by the particle.

The user must supply only the true range of the particle in the form of a tuple, 
per dimension ($\lambda_{min}$,$\lambda_{max}$).  
Then $(\lambda_{max}-\lambda_{min})\eta = 2.0$, or, 
$\eta = 2.0/(\lambda_2-\lambda_1)$, and 
$\sigma = 0.5*(\lambda_{max}+\lambda_{min})$.

So, the true particle position (for evaluations) is 
$\lambda = P/\eta + \sigma$, 
where $P$ is the normalised position of the particle.


## Using particles

Below, we have the declaration of the particle class and a couple of methods for creation and evolution of the particle based on the PSO algorithm.   

__Note that the evaluation of the fitness of the particle is problem specific and the user must supply its own evaluation function and register it under the name ``'evaluate' `` with the toolbox.__


## Particle Swarm

The swarm is a a list of particles, with a couple of additional attributes:
    
    * ``gbest `` -- globally the best particle (position) ever (i.e. accross any generation so far)
    * ``gbestfit `` -- globally the best fitness (i.e. the quality value of gbest)   

The swarm is declared, created and let to evolve with the help of the ``PSO`` class.
"""
import random
import operator
import sys
import logging
import numpy as np

from deap import base
from deap import creator
from deap import tools

def declareTypes(weights):
    """
    Declare Particle class with fitting objectives (-1: minimization; +1 maximization).
    Each particle consists of a set of normalised coordinates, returned by the
    particle's instance itself. The true (physical) coordinates of the particle
    are stored in the field 'renormalized'. The field 'best' contains the best 
    fitness-wise position that the particle has ever had (in normalized coords).
    Declare also Swarm class; inherit from list + PSO specific attributes
    gbest and gbestfit.
    Arguments:
        weights -- tupple, e.g. (-1,) for single objective minimization, or
                   (+1,+0.5) for two objective maximization, etc.
    """
    creator.create("pFitness", base.Fitness, weights=weights)
    creator.create("Particle", list, fitness=creator.pFitness, speed=list, past=list,
                   smin=None, smax=None, best=None, norm=list, shift=list, renormalized=list,
                   worstErr=None)
    creator.create("Swarm", list, gbest=None, gbestfit=creator.pFitness,
                   gbest_iteration=None)


def createParticle(prange):
    """
    Create particle of dimensionality len(prange), assigning initial particle
    coordinate in the i-th dimension within the prange[i] tuple.
    Note that the range is normalised and shifted, so that the result is a coordinate
    within -1 to 1 for each dimension, and initial speed between -.5 and +.5.
    To get the true (i.e. physical) coordinates of the particle, 
    one must use part.renormalized field.
    Arguments:
        prange -- list of tuples. each tuple is a range of _initial_ coord.
    Return:
        particle -- an instance of the Particle class, with initialized coordinates both
                    normalized (the instance itself) and true, physical coords (self.renormalized).
    """
    # size is the dimensionality (degrees of freedom) of the particle
    # prange is a list of tuples containing the _initial_ range of particle coordinates
    # prange is normalised, to [-1:+1], and the speedlimit is set to 0.5 the range
    size = len(prange)
    pmin, pmax, smin, smax = -1.0, 1.0, -1.0, 1.0
    part = creator.Particle(random.uniform(pmin, pmax) for _ in range(size))
    part.past = [random.uniform(pmin, pmax) for _ in range(size)]
    part.speed = [random.uniform(smin, smax) for _ in range(size)]
    part.smin = smin
    part.smax = smax
    part.norm = [(pmax - pmin) / (r[1] - r[0]) for r in prange]
    part.shift = [0.5 * (r[1] + r[0]) for r in prange]
    try:
        part.renormalized = list(map(operator.add, list(map(operator.div, part, part.norm)), part.shift))
    except AttributeError:
        part.renormalized = list(map(operator.add, list(map(operator.truediv, part, part.norm)), part.shift))
    return part


def evolveParticle_0(part, best, phi1=2, phi2=2):
    """
    _NOTA__BENE_
    This is the implementation shown in the examples of the DEAP library.
    The inertial factor is 1.0 (implicit) and seems to be too big.
    Phi1/2 are also somewhat bigger than the Psi/Ki resulting from the optimal
    Psi = 2.9922
    A method to update the position and speed of a particle (part), according to the
    original PSO algorithm of Ricardo Poli, James Kennedy and Tim Blackwell, 
    'Particle swarm optimization: an overview'. Swarm Intelligence. 2007; 1: 33-57.
    Arguments:
        part -- instance of the particle class, the particle to be updated
        best -- the best known particle ever (within the life of the swarm)
        phi1,phi2 -- connectivity coefficients
    """
    u1 = (random.uniform(0, phi1) for _ in range(len(part)))
    u2 = (random.uniform(0, phi2) for _ in range(len(part)))
    v_u1 = list(map(operator.mul, u1, list(map(operator.sub, part.best, part))))
    v_u2 = list(map(operator.mul, u2, list(map(operator.sub, best, part))))
    part.speed = list(map(operator.add, part.speed, list(map(operator.add, v_u1, v_u2))))
    for i, speed in enumerate(part.speed):
        if speed < part.smin:
            part.speed[i] = part.smin
        elif speed > part.smax:
            part.speed[i] = part.smax
    part[:] = list(map(operator.add, part, part.speed))
    try:
        part.renormalized = list(map(operator.add, list(map(operator.div, part, part.norm)), part.shift))
    except AttributeError:
        part.renormalized = list(map(operator.add, list(map(operator.truediv, part, part.norm)), part.shift))


def evolveParticle(part, best, inertia=0.7298, acceleration=2.9922, degree=2):
    """
    A method to update the position and speed of a particle (part), according to the
    generalized formula of Eq(3) in J.Kennedy, "Particle Swarm Optimization" in
    "Encyclopedia of Machine Learning" (2010), which is equivalent to Eqs(3-4) of
    'Particle swarm optimization: an overview'. Swarm Intelligence. 2007; 1: 33-57.
    Arguments:
        part -- instance of the particle class, the particle to be updated
        best -- the best known particle ever (within the life of the swarm)
        inertia -- factor scaling the persistence of the particle
        acceleration -- factor scaling the influence of particle connection
        degree -- unused right now. should serve for a fully informed particle swarm (FIPS),
                  but this requires best to become a list of neighbours best;
                    also u1,u2 and v_u1, v_u2 should be transformed into a Sum over neighbours
    Returns the updated particle
    """
    if degree != 2:
        sys.exit("ERROR: degree!=2 is not supported (no support for FIPS yet). Cannot continue.")
    # calculate persistence and influence terms
    u1 = (random.uniform(0, acceleration / degree) for _ in range(len(part)))
    u2 = (random.uniform(0, acceleration / degree) for _ in range(len(part)))
    v_u1 = list(map(operator.mul, u1, list(map(operator.sub, part.best, part))))
    v_u2 = list(map(operator.mul, u2, list(map(operator.sub, best, part))))
    persistence = list(map(operator.mul, [inertia] * len(part), list(map(operator.sub, part, part.past))))
    influence = list(map(operator.add, v_u1, v_u2))
    part.speed = list(map(operator.add, persistence, influence))
    # assign current position to the old one
    for i, p in enumerate(part):
        part.past[i] = p
    # apply speed limit per dimension!
    for i, s in enumerate(part.speed):
        if s < part.smin:
            part.speed[i] = part.smin
        elif s > part.smax:
            part.speed[i] = part.smax
    # update current position in both normalized and physical coordinates
    part[:] = list(map(operator.add, part, part.speed))
    try:
        part.renormalized = list(map(operator.add, list(map(operator.div, part, part.norm)), part.shift))
    except AttributeError:
        part.renormalized = list(map(operator.add, list(map(operator.truediv, part, part.norm)), part.shift))


# init arguments: 
pso_init_args = ["npart", "objectives", "parrange", "evaluate"]
pso_optinit_args   = ["logger", 'ngen', 'ErrTol'] 

# call arguments
pso_call_args      = []
pso_optcall_args   = ['ngen', "ErrTol", ] 

pso_dflts = {'npart': 10, 'ngen': 200, 'ErrTol': 0.001, 
                'objective_weights': (-1,)}


def pso_args(**kwargs):
    """
    """
    pso_obligatory_args = pso_init_args + pso_call_args
    args = {}
    optargs = {}
    for arg in pso_obligatory_args:
        try: 
            args[arg] = kwargs[arg]
        except KeyError:
            errormsg = "PSO missing obligatory argument {0}\n".format(arg)+\
                "Please define at least:\n{0}\n".format(pso_obligatory_args)+\
                "PSO supports also:\n{0}\n".format(pso_optional_args)
            try:
                kwargs['logger'].critical(errormsg)
            except KeyError:
                print (errormsg)
            sys.exit(1)
    for arg in list(set(pso_optinit_args + pso_optcall_args)):
        try: 
            optargs[arg] = kwargs[arg]
        except KeyError:
            pass

    init_args = [args[key] for key in pso_init_args]
    call_args = [args[key] for key in pso_call_args]
    init_optional_args = dict([(key, optargs[key]) for key in optargs if key in pso_optinit_args])
    call_optional_args = dict([(key, optargs[key]) for key in optargs if key in pso_optcall_args])

    return init_args, call_args, init_optional_args, call_optional_args


def report_stats(stats, logger=logging.getLogger(__name__)):
    """
    """
    statsHeader = "".join([
    '{0:>5s}'.format('Gen.'),
    '{0:>10s}'.format('Min.'),
    '{0:>10s}'.format('Max.'),
    '{0:>10s}'.format('Avg.'),
    '{0:>10s}'.format('Std.'),
    '{0:>12s}'.format('WorstErr(%)'),
    ])
    logger.info('')
    logger.info("PSO statistics follow:")
    logger.info(statsHeader)
    logger.info('============================================================')
    ngen = len(stats)
    for gen in range(ngen):
        s = stats[gen]
        logger.info("".join([
        '{0:>5d}'.format(gen),
        '{0:>10.4f}'.format(s['Fitness']['Min']),
        '{0:>10.4f}'.format(s['Fitness']['Max']),
        '{0:>10.4f}'.format(s['Fitness']['Avg']),
        '{0:>10.4f}'.format(s['Fitness']['Std']),
        '{0:>12.2f}'.format(s['WRE']['Min']*100),
            ]))
    logger.info('============================================================')


#def minabs(swarm):
#    return np.min(np.abs([part.worstErr for part in swarm]))


class PSO(object):
    """
    Class defining Particle-Swarm Optimizer.
    """
    toolbox = base.Toolbox()
    nBestKept = 10
    halloffame = tools.HallOfFame(nBestKept)

    # see J. Kennedy "Particle Swarm Optimization" in "Encyclopedia of machine learning" (2010).
    pInertia = 0.7298
    pAcceleration = 2.9922

    def __init__(self, parameters, evaluate, npart=10, ngen=100, 
                 objective_weights=(-1,), ErrTol=0.001):
        """
        Create a particle swarm
        """
        try:
            parrange = [(p.minv, p.maxv) for p in parameters]
        except AttributeError:
            assert isinstance(parameters, list) and len(parameters[0]) == 2,\
                ("NOTABENE: `parameters` argument PSO.__init__() should be a list,\n"
                "every element of which is either a tuple (min_value, max_value)\n"
                "or a class with attributes minv and maxv!")
            parrange = parameters
        # define the particle and the methods associated with its creation, evolution and fitness evaluation
        declareTypes(objective_weights)
        self.toolbox.register("create", createParticle, prange=parrange)
        self.toolbox.register("evolve", evolveParticle, inertia=self.pInertia, acceleration=self.pAcceleration)
        self.toolbox.register("evaluate", evaluate)
        # create a swarm from particles with the above defined properties
        self.toolbox.register("swarm", tools.initRepeat, creator.Swarm, self.toolbox.create)
        self.swarm = self.toolbox.swarm(npart)
        self.ngen = ngen
        self.ErrTol = ErrTol
        # Provide with statistics collector and evolution logger
        #  - fitness statistics
        fit_stats = tools.Statistics(key=lambda ind: ind.fitness.values)
        fit_stats.register("Avg", np.mean)
        fit_stats.register("Std", np.std)
        fit_stats.register("Min", np.min)
        fit_stats.register("Max", np.max)
        #  - Worst Relative Error statistics
        wre_stats = tools.Statistics(key=lambda ind: ind.worstErr)
        wre_stats.register("Min", np.min)
        # All statistics will be compiled for each generation and added to the record
        self.mstats = tools.MultiStatistics(Fitness=fit_stats, WRE=wre_stats)
        self.stats_record = []


    def optimise(self, ngen=None, ErrTol=None):
        """
        Let the swarm evolve for ngen (or self.ngen) generations.
        """
        # ngen and ErrTol would typically be set during initialization
        if ngen is None:
            ngen = self.ngen
        if ErrTol is None:
            ErrTol = self.ErrTol
        #
        self.stats_record = []
        for g in range(ngen):
            for i, part in enumerate(self.swarm):
                iteration = (g, i)
#                try:
#                    # assume that the evaluator makes use of iteration
                part.fitness.values, part.worstErr = self.toolbox.evaluate(part.renormalized, iteration)
#                except:
#                    # omit iteration from the arguments otherwise
#                    part.fitness.values, part.worstErr = self.toolbox.evaluate(part.renormalized)
                if not part.best or part.best.fitness < part.fitness:
                    part.best = creator.Particle(part)
                    part.best.fitness.values = part.fitness.values

                if not self.swarm.gbest or self.swarm.gbest.fitness < part.fitness:
                    self.swarm.gbest_iteration = iteration
                    self.swarm.gbest = creator.Particle(part)
                    self.swarm.gbest.fitness.values = part.fitness.values
                    self.swarm.gbest.renormalized = part.renormalized
                    self.swarm.gbest.worstErr = part.worstErr
                    self.halloffame.update(self.swarm)

            # Update particles only after full evaluation of the swarm,
            # so that gbest possibly arise from the last generation.
            for part in self.swarm:
                self.toolbox.evolve(part, self.swarm.gbest)

            # Gather all the fitnesses and worst errors and update the stats
            self.stats_record.append(self.mstats.compile(self.swarm))

            # Try an alternative exit criterion
            if ErrTol is not None:
                if (np.abs(self.swarm.gbest.worstErr) <= ErrTol):
                    break

        return self.swarm, self.stats_record


    def __call__(self, *args, **kwargs):
        return self.optimise(*args, **kwargs)
