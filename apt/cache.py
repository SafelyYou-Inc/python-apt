import apt_pkg
from apt import Package
from apt.progress import OpTextProgress
from UserDict import UserDict

class Cache(object):
    def __init__(self, progress=None):
        self.Open(progress)

    def Open(self, progress):
        self._cache = apt_pkg.GetCache(progress)
        self._depcache = apt_pkg.GetDepCache(self._cache)
        self._records = apt_pkg.GetPkgRecords(self._cache)
        self._dict = {}
        self._callbacks = {}

        # build the packages dict
        if progress != None:
            progress.Op = "Building data structures"
        i=last=0
        size=len(self._cache.Packages)
        for pkg in self._cache.Packages:
            if progress != None and last+100 < i:
                progress.Update(i/float(size)*100)
                last=i
            # drop stuff with no versions (cruft)
            if len(pkg.VersionList) > 0:
                self._dict[pkg.Name] = Package(self._cache, self._depcache,
                                               self._records, self, pkg)
            i += 1
        if progress != None:
            progress.Done()
        
    def __getitem__(self, key):
        return self._dict[key]

    def has_key(self, key):
        try:
            self._dict[key]
        except KeyError:
            return False
        return True

    def __len__(self):
        return len(self._dict)

    def keys(self):
        return self._dict.keys()

    def GetChanges(self):
        changes = [] 
        for name in self._dict.keys():
            p = self._dict[name]
            if p.MarkedUpgrade() or p.MarkedInstall() or p.MarkedDelete() or \
               p.MarkedDowngrade() or p.MarkedReinstall():
                changes.append(p)
        return changes

    def Upgrade(self, DistUpgrade=False):
        self.CachePreChange()
        self._depcache.Upgrade(DistUpgrade)
        self.CachePostChange()

    def Commit(self, fprogress, iprogress):
        self._depcache.Commit(fprogress, iprogress)

    # cache changes
    def CachePostChange(self):
        " called internally if the cache has changed, emit a signal then "
        if not self._callbacks.has_key("cache_post_change"):
            return
        for callback in self._callbacks["cache_post_change"]:
            apply(callback)

    def CachePreChange(self):
        """ called internally if the cache is about to change, emit
            a signal then """
        if not self._callbacks.has_key("cache_pre_change"):
            return
        for callback in self._callbacks["cache_pre_change"]:
            apply(callback)

    def connect(self, name, callback):
        """ connect to a signal, currently only used for
            cache_{post,pre}_changed """
        if not self._callbacks.has_key(name):
            self._callbacks[name] = []
        self._callbacks[name].append(callback)

# ----------------------------- experimental interface
class Filter(object):
    def apply(self, pkg):
        return True

class MarkedChangesFilter(Filter):
    def apply(self, pkg):
        if pkg.MarkedInstall() or pkg.MarkedDelete() or pkg.MarkedUpgrade():
            return True
        else:
            return False

class FilteredCache(Cache):
    def __init__(self, progress=None):
        Cache.__init__(self, progress)
        self._filtered = {}
        self._filters = []
    def __len__(self):
        return len(self._filtered)
    
    def __getitem__(self, key):
        return self._dict[key]

    def keys(self):
        return self._filtered.keys()

    def has_key(self, key):
        try:
            self._filtered[key]
        except KeyError:
            return False
        return True

    def _reapplyFilter(self):
        for pkg in self._dict.keys():
            for f in self._filters:
                if f.apply(self._dict[pkg]):
                    self._filtered[pkg] = 1
                    break
    
    def SetFilter(self, filter):
        self._filters = []
        self._filters.append(filter)
        self._reapplyFilter() 

    def CachePostChange(self):
        Cache.CachePostChange(self)
        " called internally if the cache changes, emit a signal then "
        self._reapplyFilter()

def cache_pre_changed():
    print "cache pre changed"

def cache_post_changed():
    print "cache post changed"
                
if __name__ == "__main__":
    print "Cache self test"
    apt_pkg.init()
    c = Cache(OpTextProgress())
    c.connect("cache_pre_change", cache_pre_changed)
    c.connect("cache_post_change", cache_post_changed)
    print c.has_key("aptitude")
    p = c["aptitude"]
    print p.Name()
    print len(c)

    for pkg in c.keys():
        x= c[pkg].Name()

    c.Upgrade()
    changes = c.GetChanges()
    print len(changes)
    for p in changes:
        #print p.Name()
        x = p.Name()

    print "Testing filtered cache"
    c = FilteredCache()
    c.Upgrade()
    c.SetFilter(MarkedChangesFilter())
    print len(c)
    for pkg in c.keys():
        #print c[pkg].Name()
        x = c[pkg].Name()
    
    print len(c)
