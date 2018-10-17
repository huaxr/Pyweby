#coding:utf-8
from apscheduler.schedulers.blocking import BlockingScheduler
import subprocess, os, signal, pymongo, pymysql, logging
import requests
import datetime
import json
import difflib

db = pymysql.connect("", "", "8o2euPBuBce9", "")
cursor = db.cursor()


def reconnect():
    """
    consider timeout socket result in pipe error.
    fix bugs only.
    :return:
    """
    global db, cursor
    try:
        cursor.close()
        db.close()
    except Exception:
        pass
    db = pymysql.connect("10.12.40.235", "sec_crawler", "8o2euPBuBce9", "sec_crawler")
    cursor = db.cursor()


def handle_file(content):
    with open("/home/huaxinrui/js/tmp.txt", mode="w+") as f:
        f.truncate()
        f.write(content)


def read_file():
    with open("/home/huaxinrui/js/tmp.txt", mode="r+") as f:
        return f.read()


def kill(p, pid):
    os.kill(pid, signal.SIGTERM)
    print("shutdown process")
    p.stdout.close()
    p.wait()


def job():
    try:
        file_content = read_file().strip()
        flag = True  # writeable
        p = subprocess.Popen(["node", "puppeteer.js"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        pid = p.pid  # 在*nix下，当shell=True时，如果arg是nohup python个字符串，就使用shell来解释执行这个字符串。如果args是个列表，则第一项被视为命令
        print("starting, content [%s], pid [%s]" %(file_content, str(pid)))
        for i in iter(p.stdout.readline, b''):
            if i:
                xx = i.strip().split('---')
                print(xx)
                if len(xx) == 7:
                    if xx[0] <= file_content:
                        kill(p, pid)
                        return

                    else:
                        ssv, title, com, level, version, type, cve = xx[0], xx[1], xx[2], xx[3], xx[4].replace('\r', '').replace('\n', ''), xx[5], xx[6]

                        if flag and ssv.startswith("SSV") and ssv > file_content:
                            handle_file(ssv)
                            flag = False

                        like = sql(com)

                        if like:
                            affect_list = query(like)
                            print(affect_list)
                            if affect_list:
                                if ssv > file_content:  # if <= match , kill process directly
                                    times = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                                    chate_lark(ssv=ssv, title=title, com=com, level=level, version=version, type=type, urls='\n'.join(affect_list), cve=cve)
                                    insert(title, ssv, times, com, cve, type, version, level, '\n'.join(affect_list), times)
                                else:
                                    kill(p, pid)
                                    return

                else:
                    continue

    except KeyboardInterrupt:
        print("exit..")
        kill(p, pid)

    print("over.. next loop")


def sql(rlike):
    try:
        rlike = rlike.lower()
        cursor.execute("select distinct(app_name) from webfp, app_name where webfp.app_id = app_name.id")
        result = cursor.fetchall()
        for i in result:
            if similarity(rlike.lower(), i[0].lower()):
                if rlike in i[0].lower():
                    return rlike

                if i[0].lower() in rlike:
                    return i[0]
        return 0

    except pymysql.err.Error as e:
        print(e)
        reconnect()
        return sql(rlike)


def query(rlike):
    tmp = set()
    cursor.execute("select craw_url,app_name from dataview where app_name like '%{}%'".format(rlike))
    result = cursor.fetchall()
    for i in result:
        tmp.add(i[0] + " (" + i[1] + ")")
    return tmp


def insert(title, serial, time, component, cve, type, affect_version, level, urls, up_time):
    try:
        cursor.execute("insert into alert values (NULL, '%s','%s','%s','%s','%s','%s','%s','%s','%s','%s')" % (title, serial, time, component, cve, type, affect_version, level, urls, up_time))
        db.commit()
    except pymysql.err.Error as e:
        print("err happends", e)


# def db_mongo():
#     myclient = pymongo.MongoClient("mongodb://localhost:27017/")
#     mydb = myclient["vluns"]
#     mycol = mydb["test"]
#     collections = mycol.find()
#     for i in collections:
#         db_mysql(i)
#
#
# def db_mysql(set):
#     """
#     create table seebug(id int not null auto_increment, title varchar(100),
#     serial varchar(100), time varchar(100), component varchar(100), cve varchar(100),
#     type varchar(100), affect_version varchar(100), level varchar(100),PRIMARY KEY(id))engine=InnoDB;
#     :return:
#     """i
#     title = set.get('title', '').strip().encode('utf-8').replace("'", ' ').replace('"', ' ')
#     serial = set.get('serial', '').strip().encode('utf-8').replace("'", ' ').replace('"', ' ')
#     time = set.get('time', '').strip().encode('utf-8').replace("'", ' ').replace('"', ' ')
#     component = set.get('component', '').strip().encode('utf-8').replace("'", ' ').replace('"', ' ')
#     cve = set.get('cve', '').strip().encode('utf-8').replace("'", ' ').replace('"', ' ')
#     type = set.get('type', '').strip().encode('utf-8').replace("'", ' ').replace('"', ' ')
#     affect_version = set.get('affect_version', '').strip().encode('utf-8').replace("'", ' ').replace('"', ' ').replace("\n", '')
#     level = set.get('level', '').strip().encode('utf-8').replace("'", ' ').replace('"', ' ')
#     try:
#         cursor.execute("insert into seebugs values (NULL, '%s','%s','%s','%s','%s','%s','%s','%s')" %(title,serial,time,component,cve,type,affect_version,level))
#         db.commit()
#         print("ok")
#     except pymysql.err.Error as e:
#         print(e)

def similarity(v1, v2):
    return 1 if difflib.SequenceMatcher(None, v1, v2).quick_ratio() > 0.65 else 0


def chate_lark(ssv,title, com,level,version, type, urls,cve, chat_id="6570483341189972231"):

    BASE_URL = "https://oapi.zjurl.cn/open-apis/api/v2/message"  # 开放平台接口地址
    ROBOT_TOKEN = "b-adfca7ce-070f-4105-a995-99d479ab1a35"
    MSG_TYPE = "post"
    data = {
                "token": ROBOT_TOKEN,
                "chat_id": chat_id,
                "msg_type": MSG_TYPE,
                "content": {
                    "title": "漏洞告警",
                    "text": "漏洞编号: %s\n"
                            "漏洞详情: %s\n"
                            "影响组件: %s l:[%s] v:[%s]\n"
                            "漏洞类型: %s\n"
                            "可能受影响的资产列表如下:\n%s\n" 
                            "%s" %(ssv,title, com,level, version or 'unknown', type, urls, "CVE详情:\n"+cve+"\n" if cve else "null")
                }
            }
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    r = requests.post(
        url=BASE_URL,
        data=json.dumps(data),
        headers=headers,
    )
    # print(r.content)
    if r.status_code > 200:
        return False
    return True


if __name__ == '__main__':
    log = logging.getLogger('apscheduler.executors.default')
    log.setLevel(logging.INFO)  # DEBUG

    fmt = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    h = logging.StreamHandler()
    h.setFormatter(fmt)

    log.addHandler(h)
    sched = BlockingScheduler()
    sched.add_job(job, "interval", seconds=1800)
    sched.start()

    # print(sql("Joomla!"))
    # db_mongo()
    # insert('','','','','','','','哈哈哈','a\nb')
    # chate_lark(ssv="xxx", chat_id='6605845550731132928')
    # print(query('nginx'))

    #test: 6605845550731132928
    #soc : 6570483341189972231


