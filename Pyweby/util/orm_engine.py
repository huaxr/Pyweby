import abc
import json
import six
import pymysql
import contextlib

from common.compat import URLPARSE
from common.logger import traceback, init_loger
from collections import namedtuple
from common.exception import ORMError
from config.config import Global

__all__ = ('User')

Log = init_loger(__name__)


# import warnings
# warnings.filterwarnings("ignore")

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


class DBEngine(object):
    def __init__(self, db_uri=None):
        '''
        ParseResult(scheme='mysql', netloc='127.0.0.1:3306', path='/test_db', params='',query='user=root&pass=root', fragment='')
        '''
        self.db_uri = db_uri
        if self.db_uri:
            self.db_info = URLPARSE(db_uri)
            self.parse()

    @contextlib.contextmanager
    def sql(self):
        assert hasattr(self, 'conn')
        yield self.conn

    def parse(self):
        '''
        parse the db's uri. through the scheme to select the branch.
        :return:
        '''
        scheme = self.db_info.scheme
        host, port = self.db_info.netloc.split(':', 1)
        DB = self.db_info.path.lstrip('/')
        try:
            user, passwd = [i.split('=')[1] for i in self.db_info.query.split('&')]
        except (IndexError, Exception):
            raise AttributeError(
                "Error db uri: %s fromat e.g.:[mysql://localhost/database?user=x&passwd=x]" % self.db_uri)
        assert scheme in ['mysql', 'mongodb', 'redis'] and all([host, port, DB]), "DB URI ERROR"

        if scheme == 'mysql':
            conn = pymysql.connect(host, user, passwd, DB)
            self.conn = conn
        elif scheme == 'mongodb':
            self.conn = None
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
    '''
    DBEngine Class parse the db-uri to the specific result.

    Engine = DBEngine(Configs.Application.__subclasses__()[0]().settings.get('DATABASE',None))
    conn = pymysql.connect('localhost', 'root', 'root', 'test')
    cursor = conn.cursor()
    '''

    Engine = DBEngine(db_uri=Global.DATABASE)

    with Engine.sql() as conn:
        conn = conn
        cursor = conn.cursor()

    @property
    def db(self):
        return self.conn

    @property
    def session(self):
        return self.cursor


class Field(object):

    def __init__(self, name, column_type, not_null=False, auto_increment=False, default=None):
        self.name = name
        self.type = column_type
        self.not_null = not_null
        self.auto_increment = auto_increment
        self.default = default

    def __repr__(self):
        if not self.default:
            if self.not_null and self.auto_increment:
                return "`{}` {} {} {},{}".format(
                    self.name, self.type, "NOT NULL",
                    "AUTO_INCREMENT", "PRIMARY KEY (`{}`)".format(self.name))
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
                    self.name, self.type, "NOT NULL", "AUTO_INCREMENT",
                    "PRIMARY KEY (`{}`)".format(self.name), "DEFAULT '{}'".format(self.default))
            elif self.not_null:
                return "`{}` {} {} {}".format(
                    self.name, self.type, "NOT NULL", "DEFAULT '{}'".format(self.default))
            elif self.auto_increment:
                return "`{}` {} {} {},{}".format(
                    self.name, self.type, "AUTO_INCREMENT",
                    "PRIMARY KEY (`{}`)".format(self.name), "DEFAULT '{}'".format(self.default))
            else:
                return "`{}` {} {}".format(
                    self.name, self.type, "DEFAULT '{}'".format(self.default))


class IntegerField(Field):
    def __init__(self, name, not_null=False, auto_increment=False, default=None):
        super(IntegerField, self).__init__(name, "INT", not_null=not_null,
                                           auto_increment=auto_increment, default=default)


class StringField(Field):
    def __init__(self, name, not_null=False, auto_increment=False, default=None):
        super(StringField, self).__init__(name, "varchar(180)",
                                          not_null=not_null, auto_increment=auto_increment, default=default)


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


OP = MGdict(
    AND='AND',
    OR='OR',
    NOT='!=',
    WHERE='WHERE',
    ALL='*',
)

OP += {'EQUAL': '=', 'GT': '>', 'LT': '<'}


@six.add_metaclass(ModelMetaclass)
class Model(dict):

    def __init__(self, sql=None, **kw):
        self.sql = sql
        self.kw = kw
        super(Model, self).__init__()

    @staticmethod
    def izip(*iterables):
        iterators = map(iter, iterables)
        while iterators:
            yield tuple(map(next, iterators))

    @classmethod
    def get(cls, **kw):
        limit_fields = kw.pop('limit_fields', [])

        limits = ','.join(limit_fields) if limit_fields else OP.ALL
        fields, values, tmp = [], [], []

        allow_fileds = cls.__mappings__.keys()
        for field, value in kw.items():
            if field in allow_fileds:
                fields.append(field)
                # here json.dumps is need. cause we save
                #  the value into table using dumps too.
                values.append(json.dumps(value))

        if not values:
            sql = "select {} from `{}`".format(limits, cls.__table__)
            setattr(cls, 'sql', sql)
            return cls

        if fields or values:

            zip_pair = zip(fields, values)

            for i, j in zip_pair:
                tmp.append("{}='{}' and ".format(i, j))

            cond = ''.join(tmp).rstrip('and ')

            sql = "select {} from `{}` where {}".format(limits, cls.__table__, cond)
            setattr(cls, 'sql', sql)
            return cls

    @classmethod
    def exclude(cls, **kwargs):

        if not hasattr(cls, 'sql'):
            raise ORMError("Must call Model.get() before exclude.")

        fields, values, tmp = [], [], []

        allow_fileds = cls.__mappings__.keys()
        for field, value in kwargs.items():
            if field in allow_fileds:
                fields.append(field)
                values.append(json.dumps(value))

        if fields or values:
            if cls.sql.__contains__('where'):
                tmp.append(OP.AND)
            else:
                tmp.append(OP.WHERE)

            zip_pair = zip(fields, values)
            for i, j in zip_pair:
                tmp.append("{} {} '{}'".format(i, OP.NOT, j))

        excluder = ' ' + ' '.join(tmp)
        setattr(cls, 'sql', cls.sql + excluder)
        # print(cls.sql)
        return cls

    def create_table(self):
        try:
            create_table_sql = "create table if not exists {} {} {}" \
                .format(self.__table__, tuple(self.__mappings__.values()), "ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;")
            self.session.execute(create_table_sql)
        except pymysql.err.NotSupportedError:
            create_table_sql = "create table if not exists {} {} {}" \
                .format(self.__table__, tuple(self.__mappings__.values()), "DEFAULT CHARSET=utf8mb4;")
            self.session.execute(create_table_sql)

    @classmethod
    def cls_create_table(cls):

        create_table_sql = "create table if not exists {} {} {}" \
            .format(cls.__table__, tuple(cls.__mappings__.values()), "DEFAULT CHARSET=utf8mb4;")  # ENGINE=InnoDB
        cls.DB.session.execute(create_table_sql)

    def save(self):
        '''
        save method need an instance call.
        :return:
        '''
        fields, args = [], []
        for k, v in self.__mappings__.items():
            fields.append(v.name)
            value = self.kw[v.name]
            # args.append(value if not isinstance(value,dict) else json.dumps(value))
            # json makes it safe.
            # json can automatically transfer single quotes.
            args.append(json.dumps(value))
        sql = "insert into {}({}) values {}".format(self.__table__, ','.join(fields), tuple(args))
        try:
            self.session.execute(sql)
            self.conn.commit()
        except Exception as e:
            Log.info(traceback(e))
            self.create_table()
            self.save()

    @classmethod
    def fetchone(cls, named='Default'):
        '''
        >>> c = User.get(user='hua').exclude(passwd='123').fetchone()
        >>>     for i in c:
        >>>     print(i)
        '''
        try:
            cls.DB.session.execute(cls.sql)
            cls.DB.db.commit()
        except pymysql.err.ProgrammingError:
            cls.cls_create_table()
            cls.commit()

        tuples = namedtuple(named, list(cls.allow_fileds()))
        '''
        If only fetchone gets a result, it will return directly to the data,
        otherwise it will use generator.
        '''
        query_result = cls.DB.session.fetchone()
        if query_result:
            namedTuple = tuples._make([json.loads(str(i)) for i in list(query_result)])
            return namedTuple

    @classmethod
    def fetchall(cls, named='Default'):
        '''
        generator result.
        call next(result) until raise Stop.
        '''
        tuples = namedtuple(named, list(cls.allow_fileds()))
        query_result = cls.DB.session.fetchall()
        if query_result:
            for j in query_result:
                namedTuple = tuples._make([json.loads(str(i)) for i in j])
                yield namedTuple

    @classmethod
    def order_by(cls, *args, **kwargs):
        '''
        order by the field from the fetch result.
        >>> cls.order_by('id',desc=True)
        return cls with sql parameter.
        '''
        if not hasattr(cls, 'sql'):
            raise ORMError("Must call Model.get() before order_by.")

        DESC = kwargs.pop('desc', False)
        allow_fileds = cls.allow_fileds()
        field = args[0]
        if field in allow_fileds:
            # /** order by id desc **/
            cls.sql += ' ORDER BY {} {}'.format(field, OP.DESC if DESC else '')
        return cls

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

    def __repr__(self):
        return self.__class__.__name__

    @classmethod
    def allow_fileds(cls):
        return cls.__mappings__.keys()


class User(Model):
    id = IntegerField("id", auto_increment=True)
    user = StringField("user", not_null=True, default="null")
    passwd = StringField("passwd", not_null=True, default="null")
    privilege = StringField("privilege", not_null=True, default="R")
    information = StringField("information", not_null=True, default="R")
    # TODO not ok set here
    PRIMARYKEY = 'id'


class sessions(Model):
    session = StringField("session", not_null=True)
    value = StringField("value", not_null=True)
