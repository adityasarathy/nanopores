import matplotlib
from matplotlib import gridspec
from matplotlib import cm
from math import sqrt,exp
import matplotlib.pyplot as plt
import matplotlib.path as mplPath
import numpy as np
from aHem_array_2d import *
from calculateforce import loadforces2
F, Fel, Fdrag = loadforces2()
#plt.ion()
#fig1=plt.figure(figsize=(18,12))
#fig=fig1.add_subplot()
#bar=fig1.add_subplot()
bar, ax0 = plt.subplots(figsize=(7.5,6.5))
#ax=plt.axes()


def fmt(x, pos):
    a, b = '{:.1e}'.format(10**x).split('e')
    b = int(b)
    return r'${}\cdot10^{{{}}}$N'.format(a,b)
formt = matplotlib.ticker.FuncFormatter(fmt)




def argument(x,y,z):
    return np.array([float(x),float(y),float(z)])
#def F(vec):
#    return [0.,0.,-2e-13]
def radius(x,y):
    return sqrt(x**2+y**2)
def sgn(x):
    if x<0:
        return -1
    elif x>0:
        return 1
    else:
        return 0

leftend=15.
x_mem=np.linspace(X_aHem_2d[18][0],leftend,100)
y_mem=np.zeros(x_mem.shape[0])+X_aHem_2d[18][1]
x_mem_2=-x_mem
size=X_aHem_2d.shape[0]
X_=np.zeros(size+1)
Y_=np.zeros(size+1)
for index in range(size):
	X_[index]=X_aHem_2d[index][0]
	Y_[index]=X_aHem_2d[index][1]
X_[size]=X_[0]
Y_[size]=Y_[0]
X_2=-X_

axes=plt.gca()
axes.set_ylim([-10,2])
axes.set_xlim([-5,5])
axes.set_xlabel('X coordinate [nm]')
axes.set_ylabel('Z coordinate [nm]')

bbPath=mplPath.Path(X_aHem_2d)
Ny = 40
Nx = 50
ax0.plot(X_,Y_,linewidth=3,color='black')
ax0.plot(X_2,Y_,linewidth=3,color='black')
ax0.plot(x_mem,y_mem,color='black',linewidth=2)
ax0.plot(x_mem_2,y_mem,color='black',linewidth=2)
plt.title(r'$F_{drag}$',fontsize=25)

Y, X = np.mgrid[-10:2:Ny*1j, -5:5:Nx*1j] #-5:30 and -30:30
U = np.zeros((Ny,Nx))
V = np.zeros((Ny,Nx))
for y in range(Ny):
    for x in range(Nx):
        if bbPath.contains_point((X[y][x],Y[y][x])) or bbPath.contains_point((-X[y][x],Y[y][x])):
            U[y][x] = 0
            V[y][x] = 0
        else:
            if Y[y][x]<-5.41 and (X[y][x]<-1.2 or X[y][x]>1.2):
                U[y][x] = 0.
                V[y][x] = 0.
            else:
                F_=Fdrag(argument(X[y][x],0,Y[y][x]))
                U[y][x] = F_[0]
                V[y][x] = F_[2]
#for y in range(Ny):
#    for x in range(Nx):
#        if bbPath.contains_point((X[y][x],Y[y][x])) or bbPath.contains_point((-X[y][x],Y[y][x])):
#            U[y][x] = 0
#            V[y][x] = 0
#        else:
#            if Y[y][x]<-5.5 and (X[y][x]<-1.2 or X[y][x]>1.2):
#                U[y][x] = 0
#                V[y][x] = 0
#            else:
#                F=Fdrag(argument(X[y][x],0,Y[y][x]))
#                U[y][x] = F[0]
#                V[y][x] = F[2]

strm = ax0.streamplot(X,Y,U,V,arrowsize=3, linewidth=1.5, density=3, cmap=cm.viridis, color=np.log10(np.sqrt(U*U+V*V)))
bar.colorbar(strm.lines,format=formt)


plt.tight_layout()
#plt.show()
plt.savefig('force_drag.eps')
