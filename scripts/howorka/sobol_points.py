from mpl_toolkits.mplot3d import Axes3D
import numpy as np
from numpy.random import random
import matplotlib.pyplot as plt

#........................R.............................
#                                                     .
#                                                     . 
#              .........l0..........                  .
#              .                   .                  .
#              ._ _______________ _...............    .
#              |D|               |D|     .   .   .    .
#              |D|......l1.......|D|    h1   .   .    .
#              |D|_ ____l2_____ _|D|......   h2  .    .
#              |DDD|_ _______ _|DDD|..........   .    .
#              |DDDDD|       |DDDDD|             .    .
#              |DDDDD|       |DDDDD|             .    .
#       DNA--->|DDDDD|       |DDDDD|           hpore  .
#              |DDDDD|       |DDDDD|             .    .
#              |DDDDD|..l3...|DDDDD|             .    .
#   MEMBRANE   |DDDDD|       |DDDDD|             .    H
#      |       |DDDDD|       |DDDDD|             .    .
#      |       |DDDDD|       |DDDDD|....h4       .    .
#______V_________|DDD|       |DDD|_____.________ .___ .......
#MMMMMMMMMMMMMMMM|DDD|       |DDD|MMMMM.MMMMMMMMM.MMMM.    hmem
#MMMMMMMMMMMMMMMM|DDD|_______|DDD|MMMMM.MMMMMMMMM.MMMM.......
#                .               .                    .
#                .......l4........                    .
#                                                     .
#                                                     .
#                                                     .
#......................................................

R = 40
H = 70
l0 = 22.5
l1 = 17.5
l2 = 12.5
l3 = 7.5
l4 = 17.5
hpore = 46
hmem = 2.2
h2 = hpore-35. 
h1 = h2-2.5
h4 = 10.
rMolecule=1.


####################################################
################# GENERATE ARRAY ###################
####################################################

from sobol import i4_sobol_generate as sobol

# array of factors for pore width
fac = np.array([.5*l0*1.2,.5*l0,.5*l1-rMolecule,.5*l1-rMolecule,.5*l2-rMolecule,.5*l3-rMolecule,.5*l3-rMolecule,.5*l3-rMolecule,.5*l3-rMolecule,.5*l3-rMolecule])
#array of z values in pore
z = np.array([.5*hpore+5.,.5*hpore+rMolecule,.5*hpore,.5*(hpore-h1),.5*hpore-h1,.5*hpore-h2,-.5*hpore+.75*(hpore-h2),-.5*hpore+.5*(hpore-h2),-.5*hpore+.25*(hpore-h2),-.5*hpore])

k0=3 #start exponent 2^k0
k=3 #increase number of points to 2^(k0+k)

#if k0=3 :      k |  k=1  |  k=2  |  k=3  |  k=4  |  k=5  |  k=6 
#          points |   21  |   37  |   73  |  137  |  273  |  529
#    total points |   210 |   370 |   730 |  1370 |  2730 |  5290

XY = sobol(2,2**k0,0)
X_points,Y_points = XY[0],XY[1]
for i in range(k+1): # additional points
    XY = sobol(2,2**(i+k0),2**(i+k0))
    X_points = np.append(X_points,XY[0])
    Y_points = np.append(Y_points,XY[1])

for i in list(reversed(range(X_points.shape[0]))): # cut off other triangle
    if Y_points[i]>X_points[i]:
        X_points = np.delete(X_points,i)
        Y_points = np.delete(Y_points,i)

print '# points = %d\n# z-values =%d\n# totals points= %d'%(X_points.shape[0],z.shape[0],X_points.shape[0]*z.shape[0])

X, Y, Z = np.array([]), np.array([]), np.array([]) # concatenate all arrays
for j in range(z.shape[0]):
    Z_p=np.zeros(X_points.shape[0])+z[j]
    X_p = X_points*fac[j]
    Y_p = Y_points*fac[j]
    X = np.append(X,X_p)
    Y = np.append(Y,Y_p)
    Z = np.append(Z,Z_p)
array=[[X[i],Y[i],Z[i]] for i in range(X.shape[0])]

####################################################
############### GENERATE ARRAY END #################
####################################################

def surfx(y1,y2,z1,z2,d,size,rs,cs):
    Y = np.linspace(y1,y2,size)
    Z = np.linspace(z1,z2,size)
    Y, Z = np.meshgrid(Y,Z)
    X = np.zeros(size)+d
    surf = ax.plot_surface(X,Y,Z, rstride=rs, cstride=cs, alpha=alpha,color=color)

def surfy(x1,x2,z1,z2,d,size,rs,cs):
    X = np.linspace(x1,x2,size)
    Z = np.linspace(z1,z2,size)
    X, Z = np.meshgrid(X,Z)
    Y = np.zeros(size)+d
    surf = ax.plot_surface(X,Y,Z, rstride=rs, cstride=cs, alpha=alpha,color=color)

def surfz(x1,x2,y1,y2,d,size,rs,cs):
    X = np.linspace(x1,x2,size)
    Y = np.linspace(y1,y2,size)
    X, Y = np.meshgrid(X,Y)
    Z = np.zeros(size)+d
    surf = ax.plot_surface(X,Y,Z, rstride=rs, cstride=cs, alpha=alpha,color=color)

fig = plt.figure()
ax = fig.gca(projection='3d')
ax.view_init(elev=0,azim=270)
ax.set_xlim([-.5*R,.5*R])
ax.set_ylim([-.5*R,.5*R])
ax.set_zlim([-.5*H,.5*H])
ax.set_aspect(1)

size=10
alpha=.1
rs, cs = 1, 1
color='blue'

#front
surfy(-.5*l3,.5*l3,-.5*hpore,.5*hpore-h2,.5*l3,size,1,1)
surfy(-.5*l2,.5*l2,.5*hpore-h2,.5*hpore-h1,.5*l2,size,5,1)
surfy(-.5*l1,.5*l1,.5*hpore-h1,.5*hpore,.5*l1,size,10,1)
surfy(.5*l0,-.5*l0,-.5*hpore+hmem,.5*hpore,.5*l0,size,5,5)
#front-right
surfy(.5*l3,.5*l2,-.5*hpore,.5*hpore-h2,0.,size,5,5)
surfy(.5*l2,.5*l1,-.5*hpore,.5*hpore-h1,0.,size,5,5)
surfy(.5*l1,.5*l0,-.5*hpore+hmem,.5*hpore,0.,size,5,5)
surfy(.5*l4,.5*R,-.5*hpore,-.5*hpore+hmem,0.,size,5,5)
#front-left
surfy(-.5*l3,-.5*l2,-.5*hpore,.5*hpore-h2,0.,size,5,5)
surfy(-.5*l2,-.5*l1,-.5*hpore,.5*hpore-h1,0.,size,5,5)
surfy(-.5*l1,-.5*l0,-.5*hpore+hmem,.5*hpore,0.,size,5,5)
surfy(-.5*l4,-.5*R,-.5*hpore,-.5*hpore+hmem,0.,size,5,5)

#top-front
surfz(-.5*l0,.5*l0,.5*l1,.5*l0,.5*hpore,size,10,1)
surfz(-.5*l1,.5*l1,.5*l2,.5*l1,.5*hpore-h1,size,10,1)
surfz(-.5*l2,.5*l2,.5*l3,.5*l2,.5*hpore-h2,size,10,1)
surfz(-.5*R,.5*R,.5*l0,.5*R,-.5*hpore+hmem,size,5,5)
surfz(-.5*R,.5*R,.5*l0,.5*R,-.5*hpore,size,5,5)
#top-right
surfz(.5*l1,.5*l0,0.,.5*l1,.5*hpore,size,5,5)
surfz(.5*l2,.5*l1,0.,.5*l2,.5*hpore-h1,size,5,5)
surfz(.5*l3,.5*l2,0.,.5*l3,.5*hpore-h2,size,5,5)
surfz(.5*l0,.5*R,0.,.5*l0,-.5*hpore+hmem,size,5,5)
surfz(.5*l0,.5*R,0.,.5*l0,-.5*hpore,size,5,5)
#top-left
surfz(-.5*l1,-.5*l0,0.,.5*l1,.5*hpore,size,5,5)
surfz(-.5*l2,-.5*l1,0.,.5*l2,.5*hpore-h1,size,5,5)
surfz(-.5*l3,-.5*l2,0.,.5*l3,.5*hpore-h2,size,5,5)
surfz(-.5*l0,-.5*R,0.,.5*l0,-.5*hpore+hmem,size,5,5)
surfz(-.5*l0,-.5*R,0.,.5*l0,-.5*hpore,size,5,5)
#right
surfx(0.,.5*l1,.5*hpore-h1,.5*hpore,.5*l1,size,5,5)
surfx(0.,.5*l2,.5*hpore-h2,.5*hpore-h1,.5*l2,size,5,5)
surfx(0.,.5*l3,-.5*hpore,.5*hpore-h2,.5*l3,size,5,5)
surfx(0.,.5*l0,-.5*hpore+hmem,.5*hpore,.5*l0,size,5,5)
#left
surfx(0.,.5*l1,.5*hpore-h1,.5*hpore,-.5*l1,size,5,5)
surfx(0.,.5*l2,.5*hpore-h2,.5*hpore-h1,-.5*l2,size,5,5)
surfx(0.,.5*l3,-.5*hpore,.5*hpore-h2,-.5*l3,size,5,5)
surfx(0.,.5*l0,-.5*hpore+hmem,.5*hpore,-.5*l0,size,5,5)


ax.scatter(X,Y,Z)
#ax.scatter(X,-Y,Z)
#ax.scatter(-X,Y,Z)
#ax.scatter(-X,-Y,Z)
#ax.scatter(Y,X,Z)
#ax.scatter(Y,-X,Z)
#ax.scatter(-Y,X,Z)
#ax.scatter(-Y,-X,Z)
plt.tight_layout()
plt.show()


plt.scatter(X_points,Y_points)
plt.plot([0.,1.,1.,0.,0.,1.],[0.,0.,1.,1.,0.,1.],color='blue')
ax=plt.gca()
ax.set_aspect(1)
plt.tight_layout()
plt.show()
