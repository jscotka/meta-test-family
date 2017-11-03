import yaml
import os
import glob

MFILENAME = "metadata.yaml"
DESC = "description"
SOURCE = "source"
TESTE = "tests"
TESTC = "tests_coverage"
DOCUMENT = ["document", "metadata"]
SUBTYPE = "subtype"
SUBTYPE_G = "general"
SUBTYPE_T = "test"
BACKEND = "backend"
BACKEND_DEFAULT = "mtf"

class MetadataLoader(object):
    base_element = {}
    parent_backend = BACKEND_DEFAULT
    def __init__(self, localtion=".", linters=False, backend=BACKEND_DEFAULT):
        self.location = localtion
        self.backend = backend
        self.__load_recursive()
        self.parent_backend = self.base_element.get(BACKEND) or BACKEND_DEFAULT
        if linters:
            self._import_linters()

    def _import_tests(self,testglob, pathlenght=0):
        for testfile in glob.glob(testglob):
            self.__insert_to_test_tree(os.path.dirname(testglob.strip(os.sep).split(os.sep))[pathlenght:],
                                       testfile)

    def _import_linters(self):
        raise NotImplementedError

    def get_metadata(self):
        return self.base_element

    def load_yaml(self, location):
        with open(location, 'r') as ymlfile:
            xcfg = yaml.load(ymlfile.read())
        if xcfg.get(DOCUMENT[0]) not in DOCUMENT[1]:
            raise BaseException("bad yaml file: item (%s)", xcfg.get(DOCUMENT[0]))
        else:
            return xcfg

    def __insert_to_coverage(self, path_list, test):
        if not self.base_element.get(TESTC):
            self.base_element[TESTC] = dict()
        coverage_key = "/".join(path_list)
        # add test coverage key
        # add backend key if does not exist
        if not self.base_element[TESTC].get(BACKEND):
            self.base_element[TESTC][BACKEND] = self.parent_backend

    def __parse_base_coverage(self,base=None, path=[]):
        base = base or self.base_element.get(TESTE,{})
        if base.get(DESC):
            if path:
                self.__insert_to_coverage(path,base)
        else:
            for key, value in base.iteritems():
                self.__parse_base_coverage(base=value, path=path+[key])

    def __insert_to_test_tree(self, path_list, test):
        actualelem = self.base_element
        if not actualelem.get(TESTE):
            actualelem[TESTE] = dict()
        actualelem = actualelem[TESTE]
        previous_item = None
        link_previous = None
        for item in path_list:
            if actualelem.get(item) == None:
                actualelem[item] = dict()
            link_previous = actualelem
            previous_item = item
        link_previous[previous_item] = test
        self.__insert_to_coverage(path_list, test)
        return self.base_element

    def __load_recursive(self):
        allfiles = []
        location = self.location
        for root, sub_folders, files in os.walk(location):
            if MFILENAME in files:
                allfiles.append(os.path.join(root,MFILENAME))
        base_element = self.load_yaml(allfiles[0])
        if base_element.get(SUBTYPE) == SUBTYPE_G:
            allfiles=allfiles[1:]
        else:
            base_element={}
        self.base_element = base_element
        self.__parse_base_coverage()
        for item in allfiles:
            self.__insert_to_test_tree(os.path.dirname(item)[len(location):].split("/")[1:],
                                       self.load_yaml(item))

    def get_coverage(self):
        return self.base_element.get(TESTC)

    def backend_test_set(self):
        return set([x.get(SOURCE) for x in self.get_coverage() if x.get(BACKEND)==self.backend and x.get(SOURCE)])

    def get_backends(self):
        return set([x.get(BACKEND) for x in self.get_coverage()])

    def filter_relevancy(self,envrion_description):
        raise NotImplementedError

    def filter_tags(self,tag_list):
        raise NotImplementedError

    def filter(self, relevancy={}, tags=[]):
        raise NotImplementedError


class MetadataLoaderMTF(MetadataLoader):
    import moduleframework.tools
    MTF_LINTER_PATH = os.path.dirname(moduleframework.tools.__file__)

    def __init__(self, *args, **kwargs):
        super(MetadataLoader, self).__init__(*args,**kwargs)

    def _import_linters(self):
        self._import_tests(os.path.join(self.MTF_LINTER_PATH,"*.py"), pathlenght=-2)




def test_loader():
    mt = MetadataLoader(localtion="example-component/tests")
    #print yaml.dump(mt.get_metadata())

#test_loader()