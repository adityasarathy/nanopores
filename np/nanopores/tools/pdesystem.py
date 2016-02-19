""" General-purpose PDE System class """

from dolfin import *
from .illposed import *
from .errorest import *
from .utilities import _call
from collections import OrderedDict

parameters["refinement_algorithm"] = "plaza_with_parent_facets"

__all__ = ["PDESystem", "LinearPDE", "NonlinearPDE", "GoalAdaptivePDE",
           "GeneralLinearProblem", "GeneralNonlinearProblem", "CoupledProblem",
           "solve_pde"]

class PDESystem(object):
    imax = 100
    maxcells = 10000
    marking_fraction = 0.8

    def __init__(self, geo=None, solvers={}, functions={}, functionals={}):
        self.geo = geo
        self.functions = functions
        self.solvers = solvers
        self.functionals = functionals

    def solve(self, refinement=False, verbose=True):

        if verbose:
            print "Number of cells:",self.geo.mesh.num_cells()
        if self.geo.mesh.num_cells() > self.maxcells:
            refinement = False

        for i in range(self.imax):
            if verbose:
                print '\n- Loop ' +str(i+1) + ' of max.', self.imax

            self.single_solve()
            if verbose:
                self.print_functionals()
            #plot(self.solvers.values()[0].problem.solution(), interactive=True)
            if refinement:
                (ind,err) = self.estimate()
                self.save_estimate("est", err)
                if verbose:
                    print "Error estimate (H1):",err
                refined = self.refine(ind)
                if not refined:
                    if verbose:
                        print 'Maximal number of cells reached',  \
                               ' \n  ==> no more refinement \n'
                    break
                elif verbose:
                    print "New total number of cells:",self.geo.mesh.num_cells()
            else:
                break

    def save_estimate(self, string, err, N=None):
        if not hasattr(self, "estimators"):
            self.estimators = {}
        if not self.estimators.has_key(string):
            self.estimators[string] = Estimator(string)
        if N is None:
            N = self.geo.mesh.num_cells()
        self.estimators[string] += N, err

    def estimate(self):
        """ simple zz indicator, estimator """
        # just to have a basic estimation tool when nothing is defined
        u = self.solutions()[0]
        mesh = self.geo.mesh
        ind, err = zz_indicator(u)
        return ind, err

    def single_solve(self):
        for S in self.solvers.values(): S.solve()

    def refine(self,ind):
        mesh0 = self.geo.mesh
        mesh = self.refine_mesh(ind)
        #self.adapt(mesh)

        if mesh.num_cells() > self.maxcells:
            self.geo.mesh = mesh0
            return False

        self.adapt(mesh)
        return True

    def refine_mesh(self, ind):
        mesh = self.geo.mesh

        markers = CellFunction("bool",mesh)
        indicators = CellFunction("double",mesh)
        # TODO: parallel + efficient
        for c in cells(mesh):
            indicators[c] = ind(c.midpoint())

        # MARK
        dorfler_mark(markers, indicators, self.marking_fraction)

        # REFINE
        # TODO: use refine? adapt seems to crash more easily
        mesh = refine(mesh, markers)
        #mesh = adapt(mesh, markers)
        return mesh

    def adapt(self, mesh):
        self.geo.adapt(mesh)

        for S in self.solvers.values():
            S.adapt(mesh)

        functions = tuple(self.functions.values())
        for S in self.solvers.values():
            S.replace(functions,functions)

        for J in self.functionals.values():
            if isinstance(J,list):
                for j in J:
                    j.adapt(mesh)
                    j.replace(functions,functions)
            else:
                J.adapt(mesh)
                J.replace(functions,functions)

    def rebuild(self, mesh):
        """ Assumes geometry to have geo.rebuild """
        functionals = self.functionals

        self.geo.rebuild(mesh)
        self.__init__(self.geo)

        for Jstr,J in self.functionals.items():
            J.values = functionals[Jstr].values

    def visualize(self, subdomain=None):
        sol = {x: self.solutions(x, deepcopy=True) for x in self.functions}
        mesh = self.geo.mesh
        on = ""

        if subdomain:
            on = " on " + subdomain
            mesh = self.geo.submesh(subdomain)

        plot(mesh, title="final mesh"+on)
        for x in sol:
            for i, f in enumerate(sol[x]):
                if subdomain:
                    adaptfunction(f, mesh, assign=True)
                plot(f, title = ("%s-%i" % (x, i)) +on)
        interactive()

    def print_functionals(self):
        Jdir = self.functionals
        for Jstr in sorted(self.functionals):
            J = Jdir[Jstr]
            if isinstance(J,list):
                for ii in range(len(J)):
                    print ("%s[%i]: " %(Jstr,ii)) + str(J[ii].evaluate())
            else:
                print ("%s: " %Jstr) + str(J.evaluate())

    def get_functionals(self):
        Jdir = self.functionals
        functionals = {}
        for Jstr in sorted(self.functionals):
            J = Jdir[Jstr]
            if isinstance(J,list):
                for ii in range(len(J)):
                    functionals["%s[%i]" %(Jstr,ii)] = J[ii].evaluate()
            else:
                functionals[Jstr] = J.evaluate()
        return functionals

    def print_results(self, names=None):
        if not names:
            self.print_functionals()

    def solutions(self, string=None, deepcopy=False):
        if string:
            f = self.functions[string]
            if f.function_space().num_sub_spaces() > 0:
                return f.split(deepcopy=deepcopy)
            else:
                return (f,)
        t = ()
        for x in self.functions:
            t = t + self.solutions(x, deepcopy=deepcopy)
        return t

    def save_mesh(self, mesh_name=None):
        geo_name = self.geo.parameter("name")
        from nanopores import DATADIR
        DIR = "%s/%s/mesh" %(DATADIR, geo_name)
        if not mesh_name:
            mesh_name = "last_adapted_mesh"

        meshfile = File("%s/%s.xml" %(DIR, mesh_name))
        meshfile << self.geo.mesh
        N = str(self.geo.mesh.num_cells())
        meshfile = File("%s/adapted/mesh_%s.xml" %(DIR, N))
        meshfile << self.geo.mesh
        return DIR

class LinearPDE(PDESystem):
    ''' simple interface for single linear PDE '''
    def __init__(self, geo, ProblemClass, *problem_args, **problem_params):
        problem = ProblemClass(geo, *problem_args, **problem_params)
        solver = IllposedLinearSolver(problem)

        self.geo = geo
        self.functions = {ProblemClass.__name__: problem.solution()}
        self.solution = problem.solution()
        self.problem = problem
        self.solvers = {ProblemClass.__name__: solver}
        self.functionals = {}

class NonlinearPDE(PDESystem):
    ''' simple interface for single nonlinear PDE and Newton method '''
    tolnewton = 1e-4
    newtondamp = 1.

    def __init__(self, geo, ProblemClass, **problem_params):
        problem = ProblemClass(geo, **problem_params)
        solver = IllposedNonlinearSolver(problem)

        self.geo = geo
        self.functions = {ProblemClass.__name__: problem.solution()}
        self.solution = problem.solution()
        self.problem = problem
        self.solvers = {ProblemClass.__name__: solver}
        self.functionals = {}

    def single_solve(self, tol=None, damp=None, verbose=True):
        if not tol:
            tol = self.tolnewton
        if not damp:
            damp = self.newtondamp
        S = self.solvers.values()[0] 
        S.newtondamp = damp
        for i in range(self.imax):
            S.solve()
            #plot(self.solution) # for debugging
            if verbose:
                print 'Relative L2 Newton error:',S.relerror()
            if S.convergence(tol):
                if verbose:
                    print 'linf Norm of Newton update:', \
                            norm(S.problem.u.vector(),'linf'), \
                            '<=', tol ,' \n  ==> break loop \n'
                break
        print "Newton iterations:",i+1
        print 'Relative L2 Newton error:',S.relerror()
        return i+1
        
def solve_pde(Problem, geo=None, phys=None, refinement=False, imax = 20, maxcells=1e4,
        marking_fraction=0.8, tolnewton=1e-2, newtondamp=1., iterative=None, visualize=False, **params):
    """ very simple interface for quick tests """
    solverparams = dict(imax=imax, maxcells=maxcells, marking_fraction=marking_fraction,
        tolnewton=tolnewton, newtondamp=newtondamp)
    if iterative is not None:
        Problem.method["iterative"] = iterative # TODO shouldn't be necessary to change class attributes
        
    PDEClass = LinearPDE if Problem.is_linear else NonlinearPDE
    pde = PDEClass(geo, Problem, phys=phys, **params)
    for key in solverparams:
        setattr(pde, key, solverparams[key])
        
    t = Timer("solve")
    pde.solve(refinement=refinement)
    print "CPU time (solve): %s [s]" % (t.stop(),)
    
    if visualize:
        pde.visualize()
    return pde
    

class GoalAdaptivePDE(PDESystem):
    ''' simple interface for PDE solver with goal-oriented adaptivity '''
    def __init__(self, geo, phys, Problem, goal):
        # create two problems: the primal one with forms a, L and the *dual* one with
        # a_dual(u,v) := a(v,u)
        # L_dual(v) := goal(v)
        primal = Problem(geo, phys)
        dual = Problem(geo, phys)

        # now dual is just another instance of the primal problem, but we modify it:
        aT = adjoint(dual.a)
        dual.a = aT
        # now let v be the TestFunction of the adjoint problem
        v = aT.arguments()[0]
        # create new RHS, the goal
        L = goal(v)
        dual.L = L

        solver = IllposedLinearSolver(primal)
        dualsolver = IllposedLinearSolver(dual)

        # in the end, we are mainly interested in the goal functional
        # evaluated at the solution of the primal problem
        # so this should be a Functional as well
        u = primal.solution()
        goal_f = Functional(goal(u))

        self.geo = geo
        self.phys = phys
        self.functions = {"primal": u, "dual":dual.solution()}
        self.solution = u
        self.solvers = {"primal": solver, "dual":dualsolver}
        self.functionals = {"goal": goal_f}
        
    
class GeneralLinearProblem(AdaptableLinearProblem):
    is_linear = True

    def __init__(self, geo, phys=None, u=None, bcs=None, **params):
        
        mesh = geo.mesh
        V = self.space(mesh)
        params.update(geo=geo, phys=phys, V=V)
        
        if not u:
            if hasattr(self, "initial_u"):
                u = _call(self.initial_u, params)
            else:
                u = Function(V)
            
        params.update(u=u)
        self.params = params
        
        if not bcs:
            bcs = _call(self.bcs, params)
        
        a, L = _call(self.forms, params)
        AdaptableLinearProblem.__init__(self, a, L, u, bcs, geo.boundaries)
        
    def update_forms(self, **new_params):
        # useful to e.g. change timestep and reassemble matrix
    
        self.params.update(new_params)
        a, L = _call(self.forms, self.params)
        self.a = a
        self.L = L

        
class GeneralNonlinearProblem(AdaptableNonlinearProblem):
    is_linear = False

    def __init__(self, geo, phys=None, u=None, **params):
        
        mesh = geo.mesh
        V = self.space(mesh)
        params.update(geo=geo, phys=phys, V=V)
        
        if not u:
            if hasattr(self, "initial_u"):
                u = _call(self.initial_u, params)
            else:
                u = Function(V)
            
        params.update(u=u)
        self.params = params
        
        bcs = _call(self.bcs, params)
        for bc in bcs:
            bc.apply(u.vector())
            bc.homogenize()
        
        a, L = _call(self.forms, params)
        AdaptableNonlinearProblem.__init__(self, a, L, u, bcs, geo.boundaries)
        
        
        
class CoupledProblem(object):
    """ Automated creation of coupled problems out of single ones.
    Designed for problems that subclass General(Non)LinearProblem;
    will not immediately instantiate Problems but first use their static methods.
    TODO: One should also be able to make CoupledProblems out of CoupledProblems, to create nested
    fixed point loops automatically.
    
    Expected usage:
        problems = OrderedDict([
            ("pnp", PNPProblem),
            ("stokes", StokesProblem)])
        ])
        
        def couple_pnp(ustokes):
            return dict(u = ustokes.sub(0))
        
        def couple_stokes(upnp, phys):
            v, cp, cm = upnp.split()
            f = -phys.cFarad*(cp - cm)*grad(v)
            return dict(f = f)
        
        couplers = dict(
            pnp = couple_pnp
            stokes = couple_stokes
        )
        
        coupled = CoupledProblem(problems, couplers, geo, phys, **params)
        solver = CoupledSolver(coupled)
        for n in range(5):
            solver.solve()
    
    The CoupledProblem will use the given problem names to create internal names for the solutions, e.g.
    upnp, ustokes in this case, which will be fed through the couplers to provide arguments for the
    the problem's form definitions. Everything contained in the **params may be used in the couplers.
    E.g. in the above situation the StokesProblem forms must only expect a variable "f" (and thus not know
    anything about its coupling to PNP):
    
    class StokesProblem(GeneralLinearProblem)
        @staticmethod
        def forms(..., f):
            L = inner(f, v)
            ...
            
    and CoupledProblem will make sure that f actually becomes -cFarad*(cp - cm)*grad(v).
    The use of OrderedDict in the example makes sure that PNPProblem will be solved first in every
    iteration. If this is unimportant, problems may be simply a dict.
    """

    def __init__(self, problems, couplers, geo, phys=None, **params):
        # problems = dictionary of Problem classes
        # keys are important! (see class docstring)
        
        self.solutions = OrderedDict()
        self.problems = OrderedDict()
        
        params.update(geo=geo, phys=phys)
        self.params = params
        mesh = geo.mesh
        
        for name, Problem in problems.items():
            # get space
            V = Problem.space(mesh)
            
            # create solution function
            if hasattr(Problem, "initial_u"):
                u = _call(Problem.initial_u, dict(params, V=V))
            else:
                u = Function(V)
                
            self.solutions[name] = u
            params.update({"u" + name: u})
            
        # now we have all solutions in hand and can actually create the problems
        for name, Problem in problems.items():
            u = solutions[name]
            
            # obtain parameters coupled to other problems
            problem_specific_params = dict(params, u=u)
            problem_specific_params.update(_call(couplers[name], problem_specific_params))
            
            # actually instantiate the problem
            self.problems[name] = Problem(**problem_specific_params)
        
    def update_forms(self, **new_params):
        # useful to e.g. change timestep and reassemble matrices
        # this assumes that coupled parameters are *not* changed
        for name, problem in problems.items():
            problem.update_forms(**new_params)
        
