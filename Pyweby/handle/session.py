#coding: utf-8

class Sess2dict(object):
    def __init__(self,sess):
        self.sess = sess

    @property
    def parse(self):
        res = {}
        tmp = self.sess.split('&')
        for i in tmp:
            k,v = i.split('|')
            res[k] = v
        return res