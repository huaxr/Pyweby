import abc
import json

import pymongo
import six
import pymysql
import contextlib
from ._compat import URLPARSE
from .logger import traceback,init_loger
from collections import namedtuple
from core.config import Configs
from  handle.auth import PRIVILIGE


Log = init_loger(__name__)
# import warnings
# warnings.filterwarnings("ignore")

class DBEngine(object):
    def __init__(self,db_uri=None):
        '''
        >>> a = URLPARSE("mysql://127.0.0.1:3306/test_db?user=root&passwd=root")
        >>> print(a)
        ParseResult(scheme='mysql', netloc='127.0.0.1:3306', path='/test_db', params='',query='user=root&pass=root', fragment='')
        '''
        self.db_uri = db_uri
        if self.db_uri:
            self.db_info = URLPARSE(db_uri)
            self.parse()


    @contextlib.contextmanager
    def sql(self):
        assert hasattr(self,'conn')
        yield self.conn

    def parse(self):
        '''
        parse the db's uri. through the scheme to select the branch.
        :return:
        '''
        scheme = self.db_info.scheme
        host,port = self.db_info.netloc.split(':',1)
        DB = self.db_info.path.lstrip('/')

        user,passwd = [i.split('=')[1] for i in self.db_info.query.split('&')]
        assert scheme in ['mysql','mongodb','redis'] and all([host,port,DB]),"DB URI ERROR"

        if scheme == 'mysql':
            conn = pymysql.connect(host, user, passwd, DB)
            # cursor = conn.cursor()
            self.conn =  conn
        elif scheme == 'mongodb':
            conn = pymongo.connection(host, port)
            db = conn[DB]
            self.conn = db
        elif scheme == 'redis':
            self.conn = None

        else:
            raise ValueError



@six.add_metaclass(abc.ABCMeta)
class BaseDB(object):
    @abc.abstractmethod
    def session(self):
        """
        keep database session alive
        """
    @abc.abstractmethod
    def conn(self):
        """
        another abstract method need to be implemented
        """

class DataBase(BaseDB):
    # Engine = DBEngine(Configs.Application.__subclasses__()[0]().settings.get('DATABASE',None))
    conn = pymysql.connect('localhost', 'root', 'root', 'test')
    cursor = conn.cursor()

    @property
    def db(self):
        return self.conn

    @property
    def session(self):
        return self.cursor



class Field(object):

    def __init__(self, name, column_type,not_null=False,auto_increment=False,default=None):
        self.name = name
        self.type = column_type
        self.not_null = not_null
        self.auto_increment = auto_increment
        self.default = default

    def __repr__(self):
        if not self.default:
            if self.not_null and self.auto_increment:
                return "`{}` {} {} {},{}".format(
                    self.name,self.type,"NOT NULL",
                                                 "AUTO_INCREMENT","PRIMARY KEY (`{}`)".format(self.name))
            elif self.not_null:
                return "`{}` {} {}".format(self.name, self.type, "NOT NULL")
            elif self.auto_increment:
                return "`{}` {} {},{}".format(
                    self.name, self.type, "AUTO_INCREMENT",
                                              "PRIMARY KEY (`{}`)".format(self.name))
            else:
                return "`{}` {}".format(self.name, self.type)
        else:
            if self.not_null and self.auto_increment:
                return "`{}` {} {} {} {},{}".format(
                    self.name,self.type,"NOT NULL","AUTO_INCREMENT",
                    "PRIMARY KEY (`{}`)".format(self.name),"DEFAULT '{}'".format(self.default))
            elif self.not_null:
                return "`{}` {} {} {}".format(
                    self.name, self.type, "NOT NULL","DEFAULT '{}'".format(self.default))
            elif self.auto_increment:
                return "`{}` {} {} {},{}".format(
                    self.name, self.type, "AUTO_INCREMENT",
                                                 "PRIMARY KEY (`{}`)".format(self.name),"DEFAULT '{}'".format(self.default))
            else:
                return "`{}` {} {}".format(
                    self.name, self.type,"DEFAULT '{}'".format(self.default))


class IntegerField(Field):
    def __init__(self, name,not_null=False,auto_increment=False,default=None):
        super(IntegerField, self).__init__(name, "INT",not_null=not_null,
                                           auto_increment=auto_increment,default=default)


class StringField(Field):
    def __init__(self, name,not_null=False,auto_increment=False,default=None):
        super(StringField, self).__init__(name, "varchar(180)",
                                          not_null=not_null,auto_increment=auto_increment,default=default)


class ModelMetaclass(type):

    def __new__(cls, name, bases, attrs):

        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)

        mappings = {}
        for k, v in attrs.items():
            if isinstance(v, Field):
                mappings[k] = v

        for k in mappings.keys():
            attrs.pop(k)

        attrs['__mappings__'] = mappings
        attrs['__table__'] = name
        attrs['DB'] = DataBase()
        return type.__new__(cls, name, bases, attrs)


@six.add_metaclass(ModelMetaclass)
class Model(dict):

    def __init__(self, **kw):

        self.kw = kw
        super(Model,self).__init__()

    @staticmethod
    def izip(*iterables):
        iterators = map(iter, iterables)
        while iterators:
            yield tuple(map(next, iterators))

    @classmethod
    def get(cls,**kw):
        # judge from the class object. by classmethod
        fields,values,tmp = [] ,[],[]

        allow_fileds = cls.__mappings__.keys()
        for field,value in kw.items():
            if field in allow_fileds:
                fields.append(field)
                # here json.dumps is need. cause we save
                #  the value into table using dumps too.
                values.append(json.dumps(value))

        if fields or values:

            zip_pair = zip(fields, values)

            for i,j in zip_pair:
                tmp.append("{}='{}' and ".format(i,j))

            cond = ''.join(tmp).rstrip('and ')

            sql = "select * from `{}` where {}".format(cls.__table__,cond)
            cls.DB.session.execute(sql)

            query_result = cls.DB.session.fetchone()
            if query_result:
                tuples = namedtuple('xx',list(allow_fileds))
                # now using json.loads make it right.
                namedTuple = tuples._make([json.loads(str(i)) for i in query_result])
                return namedTuple


    def create_table(self):
        create_table_sql = "create table if not exists {} {} {}" \
            .format(self.__table__, tuple(self.__mappings__.values()), "ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;")
        self.session.execute(create_table_sql)


    def save(self):
        '''
        save method need an instance call.
        :return:
        '''
        fields,args = [],[]
        for k, v in self.__mappings__.items():
            fields.append(v.name)
            value = self.kw[v.name]
            # args.append(value if not isinstance(value,dict) else json.dumps(value))
            # json makes it safe.
            # json can automatically transfer single quotes.
            args.append(json.dumps(value))
        sql = "insert into {}({}) values {}".format(self.__table__, ','.join(fields),tuple(args))
        try:
            self.session.execute(sql)
            self.conn.commit()
        except Exception as e:
            Log.info(traceback(e))
            self.create_table()
            self.save()

    @property
    def session(self):
        return self.DB.session

    @property
    def conn(self):
        return self.DB.db

    def __enter__(self):
        return self


    def __exit__(self, exc_type, exc_val, exc_tb):
        pass




class User(Model):
    id = IntegerField("id", auto_increment=True)
    user = StringField("user",not_null=True,default="null")
    passwd = StringField("passwd",not_null=True,default="null")
    privilege = StringField("privilege",not_null=True,default="R")
    information = StringField("information",not_null=True,default="R")
    # TODO not ok set here
    PRIMARYKEY = 'id'


