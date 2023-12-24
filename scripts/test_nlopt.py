import nlopt
import numpy as np
import matplotlib.pyplot as plt

def myfunc(x, grad):
    if(grad.size > 0):
        # modify in place, not used for gadient-free algorithms
        grad[0] = 0.0
        grad[1] = 0.5 / np.sqrt(x[1])
    return np.sqrt(x[1])


def myconstraint(x, grad, a, b):
    if(grad.size > 0):
        # modify in place, not used for gadient-free algorithms
        grad[0] = 3 * a * (a*x[0] + b)**2
        grad[1] = -1.0
    return (a*x[0] + b)**3 - x[1]


if __name__=="__main__":

    # gradient-based optimization
    opt = nlopt.opt(nlopt.LD_MMA, 2)

    # minimse between (\infty, o]
    opt.set_lower_bounds([-float('inf'), 0])

    # the function we want to minimise
    opt.set_min_objective(myfunc)
    
    # constaint added as lambda functions
    opt.add_inequality_constraint(lambda x,grad: myconstraint(x,grad,2,0), 1e-8)
    opt.add_inequality_constraint(lambda x,grad: myconstraint(x,grad,-1,1), 1e-8)
    
    # set solver tolerance
    opt.set_xtol_rel(1e-6)
    
    # solve
    x = opt.optimize([1.234, 5.678])
    minf = opt.last_optimum_value()
    
    # print results
    print("optimum at ", x[0], x[1])
    print("minimum value = ", minf)
    print("result code = ", opt.last_optimize_result())

    # figure
    x1 = np.linspace(-0.5, 1, 256)
    x2_1 = (2.*x1)**3
    x2_2 = (-x1+1.)**3
    plt.plot(x1, x2_1, label=r"$x_2\ge(2x_1+0)^3$")
    plt.plot(x1, x2_2, label=r"$x_2\ge(-x_1+1)^3$")
    plt.fill_between(x1, np.maximum(x2_1, x2_2), 8.0,
    color='gray', alpha=0.2, label="feasible region")
    plt.plot(x[0], x[1], 'o', label="Optimum")
    plt.xlim(-0.5, 1)
    plt.ylim(-1, 8)
    plt.xlabel(r"$x_1$")
    plt.ylabel(r"$x_2$")
    plt.legend()
    plt.savefig("nlopt.png", dpi=300)
    plt.show()
