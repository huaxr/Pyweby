#coding:utf-8
from apscheduler.schedulers.blocking import BlockingScheduler
import subprocess, os, signal, pymongo, pymysql

db = pymysql.connect("10.12.40.235", "sec_crawler", "8o2euPBuBce9", "sec_crawler")
cursor = db.cursor()

def handle_file(content):
    with open("tmp.txt", mode="w+") as f:
        f.truncate()
        f.write(content)


def read_file():
    with open("tmp.txt", mode="w+") as f:
        return f.read()


def job():
    file_content = read_file()
    print("starting job.")
    p = subprocess.Popen("node puppeteer.js", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    pid = p.pid
    for i in iter(p.stdout.readline, str):
        print(i)
        if i.startswith('index'):
            continue

        else:
            handle_file(i)

        if i.strip() == file_content:
            print("shut down job, define is:", file_content)
            os.kill(pid, signal.SIGTERM)
            break

    print("over.. next loop")


def db_mongo():
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["vluns"]
    mycol = mydb["seebug2"]
    collections = mycol.find()
    for i in collections:
        db_mysql(i)


def db_mysql(set):
    """
    create table seebug(id int not null auto_increment, title varchar(100),
    serial varchar(100), time varchar(100), component varchar(100), cve varchar(100),
    type varchar(100), affect_version varchar(100), level varchar(100),PRIMARY KEY(id))engine=InnoDB;
    :return:
    """
    title = set.get('title', '').strip().encode('utf-8').replace("'", ' ').replace('"', ' ')
    serial = set.get('serial', '').strip().encode('utf-8').replace("'", ' ').replace('"', ' ')
    time = set.get('time', '').strip().encode('utf-8').replace("'", ' ').replace('"', ' ')
    component = set.get('component', '').strip().encode('utf-8').replace("'", ' ').replace('"', ' ')
    cve = set.get('cve', '').strip().encode('utf-8').replace("'", ' ').replace('"', ' ')
    type = set.get('type', '').strip().encode('utf-8').replace("'", ' ').replace('"', ' ')
    affect_version = set.get('affect_version', '').strip().encode('utf-8').replace("'", ' ').replace('"', ' ')
    level = set.get('level', '').strip().encode('utf-8').replace("'", ' ').replace('"', ' ')
    try:
        cursor.execute("insert into seebug values (NULL, '%s','%s','%s','%s','%s','%s','%s','%s')" %(title,serial,time,component,cve,type,affect_version,level))
        db.commit()
    except pymysql.err.Error as e:
        print(e)



if __name__ == '__main__':
    # sched = BlockingScheduler()
    # sched.add_job(job, "interval", seconds=10)
    # sched.start()
    db_mongo()


