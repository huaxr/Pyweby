import abc
import six
import pymysql

import warnings
warnings.filterwarnings("ignore")

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
    DB = pymysql.connect("localhost", "root", "root", "test")
    cursor = DB.cursor()
    def __get__(self, instance, owner):
        return self.session()

    def __set__(self, instance, value):
        pass

    def session(self):
        return self.cursor

    def conn(self):
        raise NotImplementedError


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
                return "`{}` {} {} {},{}".format(self.name,self.type,"NOT NULL",
                                                 "AUTO_INCREMENT","PRIMARY KEY (`{}`)".format(self.name))
            elif self.not_null:
                return "`{}` {} {}".format(self.name, self.type, "NOT NULL")
            elif self.auto_increment:
                return "`{}` {} {},{}".format(self.name, self.type, "AUTO_INCREMENT",
                                              "PRIMARY KEY (`{}`)".format(self.name))
            else:
                return "`{}` {}".format(self.name, self.type)
        else:
            if self.not_null and self.auto_increment:
                return "`{}` {} {} {} {},{}".format(self.name,self.type,"NOT NULL","AUTO_INCREMENT",
                                                    "PRIMARY KEY (`{}`)".format(self.name),"DEFAULT '{}'".format(self.default))
            elif self.not_null:
                return "`{}` {} {} {}".format(self.name, self.type, "NOT NULL","DEFAULT '{}'".format(self.default))
            elif self.auto_increment:
                return "`{}` {} {} {},{}".format(self.name, self.type, "AUTO_INCREMENT",
                                                 "PRIMARY KEY (`{}`)".format(self.name),"DEFAULT '{}'".format(self.default))
            else:
                return "`{}` {} {}".format(self.name, self.type,"DEFAULT '{}'".format(self.default))


class IntegerField(Field):
    def __init__(self, name,not_null=False,auto_increment=False,default=None):
        super(IntegerField, self).__init__(name, "INT",not_null=not_null,
                                           auto_increment=auto_increment,default=default)


class StringField(Field):
    def __init__(self, name,not_null=False,auto_increment=False,default=None):
        super(StringField, self).__init__(name, "varchar(32)",
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
        attrs['db_session'] = DataBase()
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
                values.append(value)

        if fields or values:
            zip_pair = zip(fields, values)
            for i,j in zip_pair:
                tmp.append("{}='{}' and ".format(i,j))
            cond = ''.join(tmp).rstrip('and ')

            sql = "select * from `{}` where {}".format(cls.__table__,cond)

            create_table_sql = "create table if not exists {} {} {}"\
                .format(cls.__table__,tuple(cls.__mappings__.values()),"ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;")
            cls.db_session.execute(create_table_sql)

            cls.db_session.execute(sql)
            return cls.db_session.fetchone()



    def save(self):
        '''
        save method need an instance call.
        :return:
        '''
        fields,args = [],[]
        for k, v in self.__mappings__.items():
            fields.append(v.name)
            args.append(self.kw[v.name])
        sql = "insert into {}({}) values {}".format(self.__table__, ','.join(fields),tuple(args))
        self.db_session.execute(sql)



class Session(Model):
    id = IntegerField("id",auto_increment=True,not_null=True)
    session = StringField("session",not_null=True,default="null")
    content = StringField("content",not_null=True,default="null")
    PRIMARYKEY  = 'id'


if __name__ == '__main__':
    # mysql = "mysql://127.0.0.1:3306/framework?characterEncoding=utf8&useSSL=true"
    u = Session(id='',session=2333,content="logined")
    u.save()
    xx = Session.exists(session="2333")
    print(xx)

    # y = Session.updates(xx=22)
    # print(y)

