#!/usr/bin/python
#-*- coding:utf-8 -*-  
import tool
from http import Http
import time
import json
from python_sqlite import Database
from auto163 import Auto163

# @singlton
class Robot:
    """机器人智能语义应答""" 

    id = ""
    name = ""

    def __init__(self):
        self.id = "test id"
        self.name = "test name"
        self.http = Http()
        self.auto163 = Auto163("Music")
        self.apiKey = "bfbf6432b655493b9e861b470bca9921"
        self.userId = "WalkerDust"
        
        self.db = Database()
        self.db.execute(
        ''' 
        create table if not exists music(
            url         text primary key,
            name        text,
            fromName    text,
            count       text
        )
        ''' )
        self.db.execute(
            ''' 
            create table if not exists user(
                name        text primary key,
                id          text,
                icon        text,
                flag        text
            )
            ''' )
        self.db.execute(
            ''' 
            create table if not exists msg(
                id            text primary key, 
                userName      text,
                data          text,
                time          text
            )
            ''' )
        self.initMusic()
        self.palyHistoryMusic = []
        return
# 音乐模块
    def initMusic(self):
        li = ""

        count = self.db.getCount("select * from music ")
        if(count <= 0): #毫无数据 则 加入默认数据
            li = []
            with open('music.txt', 'r') as f:  
                data = f.readlines()  
                for item in data:
                    name = item.strip()
                    url = "http://39.107.26.100:8088/file/" + name
                    fromName = ""
                    self.db.execute('insert into music values(?,?,?,?)', url, name, fromName,"5")                        
        return    

    # 内部点播 若有名字则按照名字本地搜索和云搜索 否则 按照type切歌
    def getMusic(self, musicName="", fromName="", playType=0):
        music = {}

        if(musicName != ""):
            res = self.db.executeQueryOne("select * from music where name=? ", musicName)
            if(res.get("url", "") != ""):
                music = res
            else:
                res=self.auto163.getMusic(musicName, fromName) # [music,music]
                for item in res:
                    self.addMusic(item)
                if(len(res) > 0):
                    music = res[0]

        else:
            if(playType == -1): #上一曲
                if(len(self.palyHistoryMusic) > 1):
                    music = self.palyHistoryMusic.pop()
                    music = self.palyHistoryMusic.pop()
            # elif(playType == 1):
            else:
                size = self.db.getCount("select * from music ")
                num = 5
                page = int(1.0 * size / num)
                page = tool.getRandom(0, page)
                (size, listRes) = self.db.executeQueryPage("select * from music", page, num)
                getSize = len(listRes)
                count = tool.getRandom(0, getSize)
                music = listRes[count]

                tool.line()
                print("size:" + str(size) + "  page:" + str(page) + " num:" + str(num) + " listResSize:" + str(getSize) )
                for item in listRes:
                    print(item.get("url"), item.get("fromName"))
                print("选中了" + str(count))
                print(music)
                tool.line()
        if(music.get("url", "") != ""):
            self.palyHistoryMusic.append(music)
            if(len(self.palyHistoryMusic) > 10):
                self.palyHistoryMusic.pop(0)

        return music
    # 外部点播音乐记录
    def addMusic(self, music):
        self.palyHistoryMusic.append(music)
        if(len(self.palyHistoryMusic) > 10):
            self.palyHistoryMusic.pop(0)
        url = music.get("url", "")
        name = music.get("name", "")
        fromName = music.get("fromName", "")
        oldMusic = self.db.executeQueryOne("select * from music where url = ? " , url) 
        if(oldMusic == None):
            print("添加音乐")
            print(music)
            self.db.execute('insert into music values(?,?,?,?)', url, name, fromName, "1")                        
        else: #更新该音乐数据
            print("更新音乐")
            count = int(oldMusic.get("count", 0))
            count = str(count + 1)
            music["count"] = count
            print(music)
            self.db.execute('update music set name=?, fromName=?, count=? where url=?', name, fromName, count, url)                        
        return 
    def removeMusic(self, url=""):
        index = 0
        print("移除音乐" + url)
        self.db.execute('delete from music where url = ? ', url)
        return 
# 人员信息管理 权限 状态
#     name        text primary key,
#     id        text,
#     icon    text,
#     flag    text
    def addUser(self, user={}):
        name = user.get("name", "")
        id = user.get("id", "")
        icon = user.get("icon", "")
        flag = user.get("flag", "0")
        if(self.db.getCount("select * from user where name=?", name) > 0):
            self.db.execute("update user set id=?,icon=?,flag=? where name=?", id, icon, flag, name)
        else:
            self.db.execute("insert into user(name,id,icon,flag) values(?,?,?,?)",name,id,icon,flag)
    def turnUser(self, name, flag):
        if(self.db.getCount("select * from user where name=?", name) > 0):
            self.db.execute("update user set flag=? where name=?", flag, name)
        else:
            self.db.execute("insert into user(name,flag) values(?,?)",name,flag)
    def getUser(self, name=""):
        res = self.db.executeQueryOne("select * from user where name=?", name)
        if(res == None):
            res = {}
        return res


# 消息监控
    def addMsg(self, id, userName, data, msgTime):
        self.db.execute('insert into msg values(?,?,?,?)', id, userName, data, msgTime)

# 智能应答 
    def do(self, msg, userId="CC"):
        res = "" 
        response = self.http.doPost('http://www.tuling123.com/openapi/api', {
                "key":self.apiKey,
                "info":msg,
                "userid":userId,
                # "userInfo":{
                #     "apiKey":self.apiKey,
                #     "userId":self.userId,
                # },
                # "reqType":0,
                # "perception":{
                #     "inputText":{
                #         "text":msg,
                #     }
                # },
            }
        )
        jsonStr = response.read()

        if(jsonStr != ""):
            res = tool.makeObj(json.loads(jsonStr))
            code = res.get("code", "")
            print("Robot. " + str(msg) + " -> " + jsonStr)
        else:
            print("Robot. " + str(msg) + " -> error !!!!!!!!! ")
        return res

    def test(self):
        while(True):
            cmd=raw_input("")
            if(cmd != ""):
                res = self.do(cmd)
                print(res)
                time.sleep(1)

        return





if __name__ == '__main__':
    r = Robot()
    r.test()