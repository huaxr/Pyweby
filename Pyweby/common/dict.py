#coding: utf-8

class MagicDict(dict):
    """
    an dict support self-defined operator

    """
    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            raise AttributeError(attr)

    def __setattr__(self, attr, value):
        self[attr] = value

    def __iadd__(self, rhs):
        self.update(rhs)
        return self

    def __add__(self, rhs):
        d = MagicDict(self)
        d.update(rhs)
        return d

    def truncate(self):
        self.clear()
        return

    def __contains__(self, item):
        return item in self.keys()


class Globals(dict):
    def __init__(self):
        self.context = []
        super(Globals, self).__init__()

    def register(self, item):
        self.context.append(item)

    def __getattr__(self, item):
        return self.get(item, None)

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, item):
        self.pop(item, None)

    def __iadd__(self, other):
        assert isinstance(other, dict), "instance must be dict"
        self.update(other)
        return self

    def __add__(self, other):

        self.update(other)
        return self

    def __repr__(self):
        return "Globals with context env"


class MGdict(dict):
    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            raise AttributeError(attr)

    def __setattr__(self, attr, value):
        self[attr] = value

    def __iadd__(self, rhs):
        self.update(rhs); return self

    def __add__(self, rhs):
        d = MGdict(self); d.update(rhs); return d