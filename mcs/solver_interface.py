from importlib import find_loader as module_exists
from numpy import inf, isinf, sign, nan, isnan, unique
from scipy import sparse
from typing import List, Tuple

class MILP_LP(object):
    def __init__(self, *args, **kwargs):
        allowed_keys = {'c', 'A_ineq','b_ineq','A_eq','b_eq','lb','ub','vtype',
                        'indic_constr','x0','options','solver','skip_checks','tlim'}
        # set all keys passed in kwargs
        for key,value in kwargs.items():
            if key in allowed_keys:
                setattr(self,key,value)
            else:
                raise Exception("Key "+key+" is not supported.")
        # set all remaining keys to None
        for key in allowed_keys:
            if key not in kwargs.keys():
                setattr(self,key,None)
        # Select solver (either by choice or automatically cplex > gurobi > glpk)
        avail_solvers = []
        if module_exists('swiglpk'):
            avail_solvers += ['glpk']
        if module_exists('cplex'):
            avail_solvers += ['cplex']
        if module_exists('gurobipy'):
            avail_solvers += ['gurobi']
        if module_exists('pyscipopt'):
            avail_solvers += ['scip']
        if self.solver is None:
            if 'cplex' in avail_solvers:
                self.solver = 'cplex'
            elif 'gurobi' in avail_solvers:
                self.solver = 'gurobi'
            elif 'scip' in avail_solvers:
                self.solver = 'scip'
            else:
                self.solver = 'glpk'
        elif not self.solver in avail_solvers:
            raise Exception("Selected solver is not installed / set up correctly.")
        # Copy parameters to object
        if self.A_ineq is not None:
            numvars = self.A_ineq.shape[1]
        elif self.A_eq is not None:
            numvars = self.A_eq.shape[1]
        elif self.ub is not None:
            numvars = len(self.ub)
        else:
            raise Exception("Number of variables could not be determined.")
        if self.c is None:
            self.c = [0.0]*numvars
        if self.A_eq is None:
            self.A_eq = sparse.csr_matrix((0,numvars))
        if self.b_eq is None:
            self.b_eq = []
        numineq = self.A_ineq.shape[0]
        # Remove unbounded constraints
        if self.A_eq == None:
            self.A_eq = sparse.csr_matrix((0,numvars))
        if self.b_eq == None:
            self.b_eq = []
        if self.lb == None:
            self.lb = [-inf()]*numvars
        if self.ub == None:
            self.ub = [ inf()]*numvars
        if self.vtype == None:
            self.vtype = 'C'*numvars
        # check dimensions
        if not self.skip_checks == True:
            if not (self.A_ineq.shape[0] == len(self.b_ineq)):
                raise Exception("A_ineq and b_ineq must have the same number of rows/elements")
            if not (self.A_eq.shape[0] == len(self.b_eq)):
                raise Exception("A_eq and b_eq must have the same number of rows/elements")
            if not (self.A_ineq.shape[1]==numvars and self.A_eq.shape[1]==numvars and len(self.c)==numvars and \
                    len(self.lb)==numvars and len(self.ub)==numvars and len(self.vtype)==numvars):
                raise Exception("A_eq, A_ineq, c, lb, ub, vtype must have the same number of columns/elements")
            # if (not self.indic_constr==None) and (not self.solver in ['cplex', 'gurobi', 'scip']):
            #     raise Exception("In order to use indicator constraints, you need to set up CPLEX, Gurobi or SCIP.")
            elif (not self.indic_constr==None): # check dimensions of indicator constraints
                num_ic = self.indic_constr.A.shape[0]
                if not (self.indic_constr.A.shape[1] == numvars and \
                        len(self.indic_constr.b)==num_ic and len(self.indic_constr.binv)==num_ic and \
                        len(self.indic_constr.sense)==num_ic and len(self.indic_constr.indicval)==num_ic):
                    raise Exception("Check dimensions of indicator constraints.")
        # Cast variables as float
        self.A_ineq = self.A_ineq.astype(float)
        self.A_eq    = self.A_eq.astype(float)
        self.c      = [float(v) for v in self.c]
        self.b_ineq = [float(v) for v in self.b_ineq]
        self.b_eq   = [float(v) for v in self.b_eq]
        self.lb     = [float(v) for v in self.lb]
        self.ub     = [float(v) for v in self.ub]
        if self.x0:
            self.x0 = [float(v) for v in self.x0]
        if self.indic_constr:
            self.indic_constr.A = self.indic_constr.A.astype(float)
            self.indic_constr.b = [float(v) for v in self.indic_constr.b]        
        # Create backend
        if self.solver == 'cplex':
            from mcs.cplex_interface import Cplex_MILP_LP
            self.backend = Cplex_MILP_LP(self.c,self.A_ineq,self.b_ineq,self.A_eq,self.b_eq,self.lb,self.ub,self.vtype,
                                            self.indic_constr,self.x0,self.options)
        elif self.solver == 'gurobi':
            from mcs.gurobi_interface import Gurobi_MILP_LP
            self.backend = Gurobi_MILP_LP(self.c,self.A_ineq,self.b_ineq,self.A_eq,self.b_eq,self.lb,self.ub,self.vtype,
                                            self.indic_constr,self.x0,self.options)
        elif self.solver == 'scip':
            from mcs.scip_interface import SCIP_MILP, SCIP_LP
            self.isLP = all(v=='C' for v in self.vtype)
            if self.isLP:
                self.backend = SCIP_LP(self.c,self.A_ineq,self.b_ineq,self.A_eq,self.b_eq,self.lb,self.ub,self.x0,self.options)
                return
            else:
                self.backend = SCIP_MILP(self.c,self.A_ineq,self.b_ineq,self.A_eq,self.b_eq,self.lb,self.ub,self.vtype,
                                self.indic_constr,self.x0,self.options)
        elif self.solver == 'glpk':
            from mcs.glpk_interface import GLPK_MILP_LP
            self.backend = GLPK_MILP_LP(self.c,self.A_ineq,self.b_ineq,self.A_eq,self.b_eq,self.lb,self.ub,self.vtype,
                                            self.indic_constr,self.x0,self.options)
        if self.tlim is None:
            self.set_time_limit(inf)
        else:
            self.set_time_limit(self.tlim)

    def solve(self) -> Tuple[List,float,float]:
        x, min_cx, status = self.backend.solve()
        if not isnan(x[0]): # if solution exists (is not nan), round integers
            x = [x[i] if self.vtype[i]=='C' else int(round(x[i])) for i in range(len(x))]
        return x, min_cx, status

    def slim_solve(self) -> float:
        a = self.backend.slim_solve()
        return a

    def populate(self,n) -> Tuple[List,float,float]:
        return self.backend.populate(n)

    def set_objective(self,c):
        self.c = c
        self.backend.set_objective(c)

    def set_objective_idx(self,C):
        # when indices occur multiple times, take first one
        C_idx = [C[i][0] for i in range (len(C))]
        C_idx = unique([C_idx.index(C_idx[i]) for i in range(len(C_idx))])
        C = [C[i] for i in C_idx]
        for i in range(len(C)):
            self.c[C[i][0]] = C[i][1]
        self.backend.set_objective_idx(C)

    def set_ub(self,ub):
        self.ub = ub
        self.backend.set_ub(ub)

    def add_eq_constraints(self,A_eq,b_eq):
        A_eq = sparse.csr_matrix(A_eq)
        A_eq.eliminate_zeros()
        b_eq = [float(b) for b in b_eq]
        self.A_eq = sparse.vstack((self.A_eq,A_eq))
        self.b_eq += b_eq
        self.backend.add_ineq_constraints(A_eq,b_eq)

    def add_ineq_constraints(self,A_ineq,b_ineq):
        A_ineq = sparse.csr_matrix(A_ineq)
        A_ineq.eliminate_zeros()
        b_ineq = [float(b) for b in b_ineq]
        self.A_ineq = sparse.vstack((self.A_ineq,A_ineq))
        self.b_ineq += b_ineq
        self.backend.add_ineq_constraints(A_ineq,b_ineq)

    def set_ineq_constraint(self,idx,a_ineq,b_ineq):
        self.A_ineq = self.A_ineq.tolil()
        self.A_ineq[idx] = sparse.lil_matrix(a_ineq)
        self.A_ineq = self.A_ineq.tocsr()
        self.b_ineq[idx] = b_ineq
        self.backend.set_ineq_constraint(idx,a_ineq,b_ineq)

    def clear_objective(self):
        self.set_objective([0]*len(self.c))

    def set_time_limit(self,t):
        self.tlim = t
        self.backend.set_time_limit(t)
