'''
python class to handle n-dimensional rectangular boxes and unions of them

note: very naive implementation of union, suitable for a couple 100 boxes
'''

# TODO: customizable length scales
# TODO: reduce number of boxes in disjoint union when there is no intersection
# TODO: it would be nice to have some sort of "interactive mode" where you add
#       domains and boundaries in order and they are plotted immediately -- for showing off.

from itertools import izip, product, combinations
from .. import py4gmsh
import dolfin

__all__ = ["BoxCollection", "Box", "Interval"]
MESHDIR = "/tmp/nanopores"
        
class BoxCollection(object):
    " collection of disjoint boxes, and their vertices, edges, facets "
    
    def __init__(self, *boxes):
        self.boxes = list(boxes)
        self.subdomains = []
        self.boundaries = []
        self.facets = []
        self.indexset = set()
        self.params = {}
        #self.csg = union(map(csgExpression, boxes))

    def __str__(self):
        return str(self.csg)
        
    # two methods to unify Boxes and BoxCollections
    def _csg(self):
        return self.csg
    def _boxes(self):
        return self.boxes
    def _indexset(self):
        return self.indexset
                
    def compute_entities(self):
        dic = multi_box_union(self.boxes, self.facets)
        self.__dict__.update(dic)
        self.indexset = self._csg().eval()
        self.indexsets = self._csg().evalsets()
        for sub in self.subdomains:
            sub.indexset = sub._csg().eval() & self.indexset
        for sub in self.boundaries:
            sub.indexset = sub._csg().eval()
        # make sure that subdomains cover all of domain:
        if self.subdomains:
            rest = self - union(self.subdomains)
            rest.indexset = rest.csg.eval()
            if rest.indexset:
                self.addsubdomain(rest, "rest")
        
    def compute_boundaries(self):
        # call after compute_entities
        # TODO
        pass
        
    def create_geometry(self, lc=.5):
        self.compute_entities()
        entities_to_gmsh(self.entities, self.indexsets, lc=lc)
        physical_to_gmsh(self.subdomains, self.boundaries)
        self.geo = to_mesh()
        self.geo.params = self.params
        if hasattr(self, "synonymes"):
            self.geo.import_synonymes(self.synonymes)
        return self.geo
        
    def recreate_geometry(self):
        self.geo = geo_from_meshdir()
        self.geo.params = self.params
        if hasattr(self, "synonymes"):
            self.geo.import_synonymes(self.synonymes)
        return self.geo
        
    def plot(self, sub=False):
        geo = self.create_geometry() if not hasattr(self, "geo") else self.geo
        if hasattr(geo, "subdomains"):
            dolfin.plot(geo.subdomains)
            dolfin.plot(geo.boundaries)
        else:
            dolfin.plot(geo.mesh)
        dolfin.interactive()
        
    def addsubdomain(self, sub, name):
        assert isinstance(sub, BoxCollection) or isinstance(sub, Box)
        sub.name = name
        self.subdomains.append(sub)
        self.boxes = list(set(self.boxes + sub._boxes()))
        #self.boxes = _unique(self.boxes + sub._boxes())
        
    def addsubdomains(self, **subdomains):
        for name, sub in subdomains.items():
            self.addsubdomain(sub, name)
    
    def addboundary(self, sub, name):
        assert isinstance(sub, BoxCollection) or isinstance(sub, Box)
        sub.name = name
        self.boundaries.append(sub)
        self.facets = list(set(self.facets + sub._boxes()))
        #self.facets = _unique(self.facets + sub._boxes())
        
    def addboundaries(self, **boundaries):
        for name, sub in boundaries.items():
            self.addboundary(sub, name)
        
    def boundary(self):
        # TODO
        pass
        
    def __or__(self, other):
        boxes = list(set(self._boxes() + other._boxes()))
        coll = BoxCollection(*boxes)
        coll.csg = self._csg() | other._csg()
        return coll
        
    def __and__(self, other):
        boxes = list(set(self._boxes() + other._boxes()))
        coll = BoxCollection(*boxes)
        coll.csg = self._csg() & other._csg()
        return coll
        
    def __sub__(self, other):
        boxes = list(set(self._boxes() + other._boxes()))
        coll = BoxCollection(*boxes)
        coll.csg = self._csg() - other._csg()
        return coll
        
    def __repr__(self):
        return str(self._csg())
        
def Interval(a, b):
    # simple wrapper for Box
    return Box(intervals=[(a, b)])
        
class Box(BoxCollection):
    
    def __init__(self, a=None, b=None, intervals=None, center=None, l=None, w=None, h=None):
        if intervals is not None:
            self.intervals = intervals
            self.dim = len(intervals)
            self.a = tuple(x for x,y in intervals)
            self.b = tuple(y for x,y in intervals)
        else:
            if center is not None:
                a = [c - x*.5 for c,x in zip(center, [l,w,h])]
                b = [c + x*.5 for c,x in zip(center, [l,w,h])]
            # a, b should be tuples
            assert len(a) == len(b)
            a, b = _sort(a, b)
            a = tuple(Float(x) for x in a)
            b = tuple(Float(x) for x in b)
            self.intervals = zip(a, b)
            self.dim = len(a)
            self.a = a
            self.b = b
            
        # determine topological dimension
        self.dimt = 0
        for i in self.intervals:
            if not i[0] == i[1]:
                self.dimt += 1
        
        BoxCollection.__init__(self, self)

    def __str__(self):
        return "Box(%s)" %("x".join(["[%s, %s]" %i for i in self.intervals]),)
        
    def __repr__(self):
        return "Box(%s, %s)" %(self.a, self.b)
        
    def __cmp__(self, other):
        return cmp(self.intervals, other.intervals)
        
    def __iter__(self):
        return iter(self.intervals)
        
    def __getitem__(self, i):
        return self.intervals[i]
        
    # two methods to unify Boxes and BoxCollections
    def _csg(self):
        return csgExpression(self)
    def _boxes(self):
        return [self]
    def _indexset(self):
        return self.indexset
        
    def __or__(self, other):
        # return union of two Boxes as a BoxCollection
        coll = BoxCollection(self, *(other._boxes()))
        coll.csg = self._csg() | other._csg()
        return coll
        
    def __and__(self, other):
        # return intersection of two Boxes as a BoxCollection
        coll = BoxCollection(self, *(other._boxes()))
        coll.csg = self._csg() & other._csg()
        return coll
        
    def __sub__(self, other):
        # return difference of two Boxes as a BoxCollection
        coll = BoxCollection(self, *(other._boxes()))
        coll.csg = self._csg() - other._csg()
        return coll
        
    def boundary(self, *strings):
        facets = _facets(self.intervals)
        if strings:
            ind = [_boundaries[self.dim][s] for s in strings]
            facets = [facets[i] for i in ind]
        boxes = []
        for facet in facets:
            intervals = [(f if isinstance(f, tuple) else (f,f)) for f in facet]
            boxes.append(Box(intervals=intervals))
        return union(boxes)
        
_boundaries = {
1 : dict(
    left = 0,
    right = 1,
),
2 : dict(
    left = 0,
    right = 1,
    top = 3,
    bottom = 2,
),
3 : dict(
    left = 0,
    right = 1,
    front = 2,
    back = 3,
    top = 5,
    bottom = 4,
)}
        
class csgExpression(object):
    # either singleton (box) or made up of two csgExpressions via set operations

    def __init__(self, *args):
        if len(args) == 1:
            self.sginit(*args)
        else:
            self.opinit(*args)
    
    def sginit(self, A):
        self.A = A
        #self.string = repr(A)
        self.singleton = True
    
    def opinit(self, op, A, B):
        self.op = op
        self.A = A
        self.B = B
        #self.string = "(%s %s %s)" %(repr(A), op, repr(B))
        #self.string = "(%s %s %s)" %("%s", op, "%s")
        self.singleton = False
        
    def __repr__(self):
        if self.singleton:
            return repr(self.A)
        else:
            return "(%s %s %s)" %(repr(self.A), self.op, repr(self.B))
        #return self.string
        
    def eval(self): # is designed to return a set
        if self.singleton:
            return self.A._indexset()
        if self.op == "|":
            return self.A.eval() | self.B.eval()
        elif self.op == "&":
            return self.A.eval() & self.B.eval()
        elif self.op == "-":
            return self.A.eval() - self.B.eval()
    
    # TODO: get rid of eval(). having an indexset for every dimension is better
    def evalsets(self): # indexset for every dimension
        if self.singleton:
            return self.A.indexsets
        if self.op == "|":
            return [a | b for a, b in zip(self.A.evalsets(), self.B.evalsets())]
        elif self.op == "&":
            return [a & b for a, b in zip(self.A.evalsets(), self.B.evalsets())]
        elif self.op == "-":
            return [a - b for a, b in zip(self.A.evalsets(), self.B.evalsets())]
            
    # boolean operations    
    def __or__(self, other):
        return csgExpression("|", self, other)
    def __and__(self, other):
        return csgExpression("&", self, other)
    def __sub__(self, other):
        return csgExpression("-", self, other)

class Float(float):
    tol = 1e-10
    
    def __cmp__(self, other):
        return _cmp(self, other, self.tol)
    
    # TODO: this is performance-critical, so minimize function calls    
    def __eq__(self, other):
        if isinstance(other, Float):
            return cmp(self, other) == 0
        else:
            return False

    def __ne__(self, other):
        return not self == other
        
def union(seq):
    return reduce(lambda x, y: x | y, seq)
    
def intersection(seq):
    return reduce(lambda x, y: x & y, seq)
        
def _sort(a, b):
    a_ = tuple(map(min, izip(a,b)))
    b_ = tuple(map(max, izip(a,b)))
    return a_, b_
        
def _cmp(s, t, tol):
    " test floats for approximate equality "
    if s > t+tol:
        return 1
    elif s < t-tol:
        return -1
    else:
        return 0    
        
def _unique(seq):
    # version of list(set(seq)) but using list membership test
    # (weaker than set membership test, for approximate Float equality)
    unique = []
    [unique.append(x) for x in seq if not unique.count(x)]
    return unique
        
def multi_interval_union(intvs):
    " return disjoint subintervals with same union as intervals, plus parent information "
    # input: list of intervals
    # output: for lists:
    #   1) sorted list of N (unique) endpoints
    #   2) equivalent to 4) for the endpoints
    #   3) corresponding list of N-1 subintervals
    #   4) list of N-1 sets denoting to which of the original intervals a subinterval belongs
    # (number of intervals is expected to be smallish, like < 10000)
    # interval := tuple (a,b) with a <= b, a,b are Floats
    # in the case of a == b the interval will be ignored in the final output
    points = sorted(_unique([x for intv in intvs for x in intv]))
    subs = zip(points[:-1], points[1:])
    psets = [set() for i in points]
    ssets = [set() for i in subs]
    for i, intv in enumerate(intvs):
        a, b = intv
        for j in range(points.index(a), points.index(b)):
            psets[j].add(i)
            ssets[j].add(i)
        psets[points.index(b)].add(i)
    #print points, psets, subs, ssets    
    return points, psets, subs, ssets
    
    
def _map(f, seq):
    """ version of map() for function with multiple return values.
    instead of a list of tuples (like map), return a tuple of lists. """
    return tuple(map(list, zip(*map(f, seq))))
        
def multi_box_union(boxes, facets=[]):
    " return union of boxes as collection of disjoint boxes "
    # TODO: atm this modifies the boxes with an "indexset" attribute
    #       which doesn't seem perfectly clean
    allboxes = boxes + facets
    
    # get dimension; all boxes must have the same
    dim = boxes[0].dim
    assert all([dim == box.dim for box in boxes])
    
    # get list of disjoint intervals for every dimension
    nodes, nsets, intvs, isets = _map(multi_interval_union, izip(*allboxes))
        
    D = range(dim) # [0,...,dim-1]
    D1 = range(dim+1) # [0,..,dim]
    entities = [[] for k in D1] # entity := d-tuple of tuples/floats <=> box
    esets = [[] for k in D1] # eset := {indices of the parent boxes of an entity}
    for box in allboxes:
        box.indexsets = [set() for i in D1]
        #box.indexset = set()
    
    # collect all admissible k-entities for k = 1,...,d
    # 0-entity = vertex, 1-entity = edge, ...
    for k in D1:
        j = 0
        for tup in combinations(D, k):
            k_entities = product(*[(intvs[i] if i in tup else nodes[i]) for i in D])
            k_esets1D = product(*[(isets[i] if i in tup else nsets[i]) for i in D])
            for entity, eset1D in izip(k_entities, k_esets1D):
                eset = set.intersection(*eset1D)
                if eset:
                    entities[k].append(entity)
                    esets[k].append(eset)
                    for ii in eset:
                        allboxes[ii].indexsets[k].add(j)
                    """
                    if k == (dim-1):
                        for ii in eset:
                            if allboxes[ii] in facets: # TODO: bad hack
                                allboxes[ii].indexset.add(j)
                    if k == dim:
                        for ii in eset:
                            if allboxes[ii] in boxes:
                                allboxes[ii].indexset.add(j)
                    """
                    j += 1
                               
        #print "k=%s:"%k, entities[k]
        #print
    # choose correct indexset for every box
    for box in allboxes:
        box.indexset = box.indexsets[box.dimt]
    
    return dict(nodes=nodes, entities=entities, esets=esets)
    
def _facets(box): # get facets from d-dimensional box, d >= 1
    facets = []
    d = len(box)
    for i, x in enumerate(box): # iterate through intervals/floats
        if isinstance(x, tuple):
            facets.append(tuple((x[0] if i==j else box[j]) for j in range(d)))
            facets.append(tuple((x[1] if i==j else box[j]) for j in range(d)))
    return tuple(facets)
    
def _orientations(k): # facet orientations
    return ["-","","","-","-",""][:(2*(k+1))] # valid for 0-, 1- and 2-dim. facets
    
FacetLoop = {
    0: lambda x:x,
    1: py4gmsh.LineLoop,
    2: py4gmsh.SurfaceLoop
    }
    
Entity = {
    1: lambda x: py4gmsh.Line(*x),
    2: py4gmsh.PlaneSurface,
    3: py4gmsh.Volume
    }

def entities_to_gmsh(entities, indexsets, lc=.5):

    global gmsh_entities
    global dim
    global dimt
    
    dim = len(entities)-1
    dimt = -1
    for en in entities:
        if en:
            dimt += 1
    
    gmsh_entities = [[None for e in k] for k in entities]
    
    # a shortcut
    _gmsh = lambda entity, k: gmsh_entities[k][entities[k].index(entity)]
    
    # add points
    for i, e in enumerate(entities[0]):
        # py4gmsh.Point expects three values x,y,z
        e = e + tuple(0. for i in range(3 - dim))
        # create point
        gmsh_entities[0][i] = py4gmsh.Point(e, lc)
        
    # add entities of dimension > 0
    for k in range(1, dim+1):
        for i, e in enumerate(entities[k]):
            # TODO preliminary hack
            #if k == dim:
            if i not in indexsets[k]:
                continue
                    
            # get surrounding facets (x,y,z in this order)
            facets = _facets(e)
            
            # find corresponding gmsh facets
            facets = [_gmsh(l, k-1) for l in facets]
            
            # create facet loop with correct orientations
            orient = _orientations(k-1)
            loop = FacetLoop[k-1]([o+s for o, s in izip(orient, facets)])
            
            # add entity
            gmsh_entities[k][i] = Entity[k](loop)
            
    return gmsh_entities
            
def physical_to_gmsh(subdomains, boundaries):
    # call only after entities_to_gmsh
    for sub in subdomains:
        vols = [gmsh_entities[dimt][i] for i in sub.indexset]
        py4gmsh.PhysicalVolume(vols, sub.name, dimt)
    for sub in boundaries:
        surfs = [gmsh_entities[dimt-1][i] for i in sub.indexset]
        py4gmsh.PhysicalSurface(surfs, sub.name, dimt)
    
def to_mesh(clscale=1., pid=""):
    py4gmsh.raw_code(['General.ExpertMode = 1;'])
    code = py4gmsh.get_code()
    meta = py4gmsh.get_meta()

    import os, subprocess
    import nanopores
    inputfile = "input%s.geo" %pid
    outfile = "out%s.msh" %pid
    meshfile = "mesh%s.xml" %pid

    # create path/to/nanoporesdata/gid/mesh if not already there
    meshdir = MESHDIR
    if not os.path.exists(meshdir):
        os.makedirs(meshdir)

    fid_dict = {"fid_geo": os.path.join(meshdir, inputfile),
                "fid_msh": os.path.join(meshdir, outfile)}

    # save code to .geo file
    fobj = open(fid_dict["fid_geo"], "w")
    fobj.write(code)
    fobj.close()

    # after writing the geo file, call gmsh
    gmsh_out = subprocess.call(["gmsh", "-3", "-v", "1","-clscale", "%f" %clscale,
                     fid_dict["fid_geo"], "-o", fid_dict["fid_msh"]])

    if gmsh_out != 0:
        raise RuntimeError('Gmsh failed in generating this geometry')
    
    fid_dict["fid_xml"] = os.path.join(meshdir, meshfile)
    subprocess.check_output(["dolfin-convert", fid_dict["fid_msh"], fid_dict["fid_xml"]])
    # for debugging:
    # convert2xml(fid_dict["fid_msh"], fid_dict["fid_xml"])
    mesh = dolfin.Mesh(fid_dict["fid_xml"])
    
    if meta:
        subdomains = dolfin.MeshFunction("size_t", mesh, meshdir+"/mesh%s_physical_region.xml"%pid)
        boundaries = dolfin.MeshFunction("size_t", mesh, meshdir+"/mesh%s_facet_region.xml"%pid)
        with open('%s/%s.txt' % (meshdir, "meta%s" %pid), 'w') as f:
            f.write(repr(meta))
        physdom = meta.pop("physical_domain")
        physbou = meta.pop("physical_boundary")
        # TODO: no interface for synonymes yet. maybe isn't needed if geo.import_synonymes() works well.
        return nanopores.Geometry(None, mesh, subdomains, boundaries, physdom, physbou)
        
    return nanopores.Geometry(None, mesh)   
    
def geo_from_meshdir(DIR=MESHDIR):
    import nanopores
    mesh = dolfin.Mesh(DIR+"/mesh.xml")
    subdomains = dolfin.MeshFunction("size_t", mesh, DIR+"/mesh_physical_region.xml")
    boundaries = dolfin.MeshFunction("size_t", mesh, DIR+"/mesh_facet_region.xml")
    
    with open(DIR+"/meta.txt", "r") as f:
        meta = eval(f.read())
    
    physdom = meta.pop("physical_domain")
    physbou = meta.pop("physical_boundary")
    
    return nanopores.Geometry(None, mesh, subdomains, boundaries, physdom, physbou)
 