# (c) 2016 Gregor Mitscha-Baude
import numpy as np
import matplotlib.pyplot as plt
import nanopores.models.pughpore as pugh
import folders

# IV curve
@pugh.solvers.cache_forcefield("pugh_IV", pugh.defaultp)
def IV(V, **params):
    params["x0"] = None
    J = []
    for bV in V:
        params["bV"] = bV
        setup = pugh.Setup(**params)
        pb, pnps = pugh.solve(setup)
        J.append(pnps.evaluate(setup.phys.CurrentPNPS)["J"])
    return dict(J=J)

# I for different surface charges
@pugh.solvers.cache_forcefield("pugh_Irho", pugh.defaultp)
def Irho(Rho, **params):
    params["x0"] = None
    bV = params["bV"]
    J = []
    for rho in Rho:
        params["dnaqsdamp"] = rho
        setup = pugh.Setup(**params)
        pb, pnps = pugh.solve(setup, visualize=True)
        J.append(pnps.evaluate(setup.phys.CurrentPNPS)["J"])
    cond = [abs(j/bV) for j in J]
    return dict(J=J, cond=cond)


ddata = {2: dict(name="Dpugh", Nmax=1e5, dim=2, r=0.11, h=1.0),
         3: dict(name="Dpugh", Nmax=2e6, dim=3, r=0.11, h=2.0)}

params = {2: dict(dim=2, diamPore=None, dnaqsdamp=0.5, h=1., Nmax=2e4, rDPore=0.95088702818),
          3: dict(dim=3, diamPore=None, dnaqsdamp=0.5, h=2., Nmax=2e5, rDPore=0.95173, stokesiter=False,
                  cheapest=True)}

Rho = np.linspace(.1, .8, 8)
Rho = list(-Rho)[::-1] + [0.001] + list(Rho)

colors = {True: "violet", False: "blue"}
dnaqs = {3: -0.7353, 2: -0.7353}
figsize = (4, 2.8)

for dim in 2, 3:
    plt.figure("%dD" % dim, figsize=figsize)
    for data in None, ddata[dim]:
        result = Irho(Rho, nproc=2, calc=False,
                      diffusivity_data=data, **params[dim])
        #Rho = map(lambda x: -x, Rho)
        J = [1e12*j for j in result["J"][::-1]]
        label = "constant D in pore" if data is None else "position-dep. D"
        plt.plot(Rho, J, "s-", label=label, color=colors[data is None])

    plt.plot([-1, 1], [2.29*1e3*0.1]*2, "--b", label="Pugh et al.")
    plt.fill_between([-1, 1], [(2.29 - 0.26)*0.1*1e3]*2,
                     [(2.29 + 0.26)*0.1*1e3]*2, color="#ccccff")

    plt.xlabel(r"DNA surface charge [q/nm$^2$]")

    plt.axvline(x=dnaqs[dim], linestyle="--", color="#666666")
    hann = 100
    plt.annotate("est. surface charge", (dnaqs[dim], hann),
             xytext=(dnaqs[dim] + 0.15, hann-20), color="#666666",
             arrowprops=dict(arrowstyle="->", color="#666666"))
    plt.ylabel("Current [pA]")

    plt.xlim(-.82, .82)
    plt.ylim(0, 1500)
    plt.yticks([0, 500, 1000])
    plt.xticks([-0.5, 0, 0.5])

    #plt.title("influence of surf. charge on current (%dD)" %dim)
    if dim==2:
        plt.legend(bbox_to_anchor=(.35, .6), loc="upper left") #, frameon=False)
    if dim==3:
        plt.legend(bbox_to_anchor=(.35, .55), loc="upper left") #, frameon=False)
        #plt.legend(loc="center")

pugh.nano.savefigs("Irho/", folders.FIGDIR, figsize)
plt.show()