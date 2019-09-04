import tornado.ioloop
import tornado.web
import tornado.websocket
from datetime import datetime
import os
import cx_Oracle
import traceback
import json


port = os.getenv("EXHIBITION_PORT") or '8080'
username = os.getenv('ORCL_USERNAME') or 'username'
password = os.getenv('ORCL_PASSWORD') or 'password'
dbUrl = os.getenv('ORCL_DBURL') or '127.0.0.1:1521/orcl'
seconds = os.getenv('SCHED_SECONDS') or '5'
urlPrefix = os.getenv("EXHIBITION_CONTENT_PATH") or ''


def executeSql(sql, fetch=True, **kw):
    print("sql=", sql)
    con = cx_Oracle.connect(username, password, dbUrl)
    cursor = con.cursor()
    result = None
    try:
        cursor.prepare(sql)
        cursor.execute(None, kw)
        if fetch:
            result = cursor.fetchall()
        else:
            con.commit()
    except Exception:
        traceback.print_exc()
        con.rollback()
    finally:
        cursor.close()
        con.close()
    return result


def getTotalDeclareCount():
    now = datetime.now()
    sql = '''select count(1) from ceb2_invt_head t
        where t.sys_date >= to_date(:startTime, 'yyyy-MM-dd')
	'''
    startTime = now.strftime("%Y-%m-%d")
    result = executeSql(sql, startTime=startTime)
    if result is None:
        return 0
    else:
        return result[0][0]


def getTotalReleaseCount():
    now = datetime.now()
    sql = '''select count(1) from ceb2_invt_head t
        where t.sys_date >= to_date(:startTime, 'yyyy-MM-dd')
		and t.app_status = '800'
	'''
    startTime = now.strftime("%Y-%m-%d")
    result = executeSql(sql, startTime=startTime)
    if result is None:
        return 0
    else:
        return result[0][0]


def getCaiNiaoDeclareCount():
    now = datetime.now()
    sql = '''select count(1) from ceb2_invt_head t
        where t.sys_date >= to_date(:startTime, 'yyyy-MM-dd')
		and t.ebc_code in ('3301968FU0', '410166003B', '4403160SGR')
	'''
    startTime = now.strftime("%Y-%m-%d")
    result = executeSql(sql, startTime=startTime)
    if result is None:
        return 0
    else:
        return result[0][0]


def getCaiNiaoReleaseCount():
    now = datetime.now()
    sql = '''select count(1) from ceb2_invt_head t
        where t.sys_date >= to_date(:startTime, 'yyyy-MM-dd')
		and t.ebc_code in ('3301968FU0', '410166003B', '4403160SGR')
		and t.app_status = '800'
	'''
    startTime = now.strftime("%Y-%m-%d")
    result = executeSql(sql, startTime=startTime)
    if result is None:
        return 0
    else:
        return result[0][0]


def getVipDeclareCount():
    now = datetime.now()
    sql = '''select count(1) from ceb2_invt_head t
        where t.sys_date >= to_date(:startTime, 'yyyy-MM-dd')
		and t.ebc_code = '4401944972'
	'''
    startTime = now.strftime("%Y-%m-%d")
    result = executeSql(sql, startTime=startTime)
    if result is None:
        return 0
    else:
        return result[0][0]


def getVipReleaseCount():
    now = datetime.now()
    sql = '''select count(1) from ceb2_invt_head t
        where t.sys_date >= to_date(:startTime, 'yyyy-MM-dd')
		and t.ebc_code = '4401944972'
		and t.app_status = '800'
	'''
    startTime = now.strftime("%Y-%m-%d")
    result = executeSql(sql, startTime=startTime)
    if result is None:
        return 0
    else:
        return result[0][0]


def getRanking():
    now = datetime.now()
    sql = '''select * from (
	select min(t.ebc_name),count(1), sum(case t.app_status when '800' then 1 else 0 end)
    , sum(case t.cus_status when '26' then 1 else 0 end)
    , sum(case t.app_status when '2' then 1 else 0 end)
	, sum(case t.app_status when '03' then 1 else 0 end)
    , sum(case
        when t.app_status = '02' and not exists (select tt0.order_no from ceb2_invt_head tt0 where tt0.sys_date >= to_date('2019-09-04', 'yyyy-MM-dd')
            and tt0.app_status in ('800', '500', '899') and t.order_no = tt0.order_no and t.ebp_code = tt0.ebp_code)
        then 1 else 0 end)
    , sum(case t.app_status when '100' then 1 else 0 end)
    from ceb2_invt_head t
    where  t.sys_date >= to_date(:startTime, 'yyyy-MM-dd')
    group by t.ebc_code
    order by count(1) desc
	) where rownum <= 10
	'''
    startTime = now.strftime("%Y-%m-%d")
    result = executeSql(sql, startTime=startTime)
    if result is None:
        return []
    else:
        return result


def sendAllMessage():
    now = datetime.now()
    strnow = now.strftime("%Y-%m-%d %H:%M:%S.%f")
    data = {
        "time": strnow,
        "totalDeclareCount": 200,
        "totalReleaseCount": 100,
        "caiNiaoDeclareCount": 150,
        "caiNiaoReleaseCount": 140,
        "vipDeclareCount": 130,
        "vipReleaseCount": 120,
        "ranking": [['京东', 100, 90, 80, 2, 3, 4, 0], ['天猫', 110, 92, 90, 3, 4, 5, 0]]
    }

    if len(ExhibitionHandler.clients) > 0:
        data["totalDeclareCount"] = getTotalDeclareCount()
        data["totalReleaseCount"] = getTotalReleaseCount()
        data["caiNiaoDeclareCount"] = getCaiNiaoDeclareCount()
        data["caiNiaoReleaseCount"] = getCaiNiaoReleaseCount()
        data["vipDeclareCount"] = getVipDeclareCount()
        data["vipReleaseCount"] = getVipReleaseCount()
        data["ranking"] = getRanking()

        jsonStr = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        for c in ExhibitionHandler.clients:
            c.write_message(jsonStr)


class MainHandler(tornado.web.RequestHandler):

    def get(self):
        self.render("index.html")

class ExhibitionHandler(tornado.websocket.WebSocketHandler):

    clients = set()

    def check_origin(self, origin):
        return True

    def open(self):
        print("WebSocket opened")
        ExhibitionHandler.clients.add(self)

    def on_message(self, message):
        print(u"You said:" + message)

    def on_close(self):
        print("WebSOcket closed")
        ExhibitionHandler.clients.remove(self)

def make_app():
    return tornado.web.Application([
        (urlPrefix + r"/", MainHandler),
        (urlPrefix + r"/ws/exhibition", ExhibitionHandler),
    ])


app = make_app()
app.listen(int(port))
tornado.ioloop.PeriodicCallback(sendAllMessage, int(seconds) * 1000).start()
tornado.ioloop.IOLoop.current().start()
