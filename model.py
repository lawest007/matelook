#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'Changxun Fan'

from orm import *
from db import *
import pickle, operator
from collections import defaultdict
from math import ceil
from config_default import configs

_LIMIT_ = configs['LIMIT']

class User(Model):
    __table__ = 'user_info'
    zid = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    full_name = StringField(ddl='varchar(50)')
    password = StringField(ddl='varchar(50)')
    email = StringField(ddl='varchar(50)')
    mates = StringField(ddl='varchar(50)')
    birthday = StringField(ddl='varchar(50)')
    home_longitude = StringField(ddl='varchar(20)')
    home_latitude = StringField(ddl='varchar(20)')
    home_suburb = StringField(ddl='varchar(20)')
    program = StringField(ddl='varchar(20)')
    courses = StringField(ddl='varchar(200)')
    mates = StringField(ddl='varchar(1000)')
    image = StringField(ddl='varchar(50)')
    public = BooleanField(default=1)
    suspending = BooleanField(default=0)
    notifications = StringField(default=pickle.dumps([0]), ddl='varchar(500)')
    request = StringField(default=pickle.dumps([]), ddl='varchar(100)')
    description = StringField(default='', ddl='varchar(500)')

    @classmethod
    def findByName(cls, name):
        sql = "select zid, full_name, image, mates from user_info where full_name like '%{}%'".format(name)
        results = select(sql, ())
        users = []
        columns = ['zid', 'full_name', 'image', 'mates']
        for r in results:
            u = dict(zip(columns, r))
            users.append(cls(**u))
        return users

    @classmethod
    def findPosts(cls, content):
        sql = "select `pid` from user_post where message like '%{}%'".format(content)
        results = select(sql, ())
        posts = [Post.findByKey(r[0]) for r in results]
        return sorted(posts, key=operator.itemgetter('time'), reverse=True)

    def getPosts(self):
        sql = "select `pid` from `user_post` where `{}` like '%{}%'".format(self.__primary_key__, self.zid)
        results = select(sql, ())
        posts = [Post.findByKey(r[0]) for r in results]
        return sorted(posts, key=operator.itemgetter('time'), reverse=True)

    def getMates(self):
        mates = pickle.loads(self.mates)
        mates.sort(reverse=True)
        return [m for m in mates if self.findByKey(m)]

    def getMatesWithInfo(self):
        mates = pickle.loads(self.mates)
        mates.sort(reverse=True)
        return [self.findByKey(m) for m in mates if self.findByKey(m)]

    def mate(self, u_zid):
        mates = self.getMates()
        if u_zid not in mates:
            mates.append(u_zid)
        self.mates = pickle.dumps(mates)
        self.update()
        u_user = User.findByKey(u_zid)
        # double mate
        if u_user:
            u_mates = u_user.getMates()
            if self.zid not in u_mates:
                u_mates.append(self.zid)
                u_user.mates = pickle.dumps(u_mates)
                u_user.update()

    def unmate(self, u_zid):
        mates = self.getMates()
        if u_zid in mates:
            mates.remove(u_zid)
            self.mates = pickle.dumps(mates)
            self.update()
        u_user = User.findByKey(u_zid)
        # double unmate
        if u_user:
            u_mates = u_user.getMates()
            if self.zid in u_mates:
                u_mates.remove(self.zid)
                u_user.mates = pickle.dumps(u_mates)
                u_user.update()

    def mateSuggestions(self):
        """
            name zid image common friends
        """
        mates = self.getMates()
        potential = []
        for mate in mates:
            user = self.findByKey(mate)
            if user:
                potential.extend(pickle.loads(user.mates))
        mates.extend(self.getRequests())
        mates.append(self.zid)
        for mate in mates:
            while mate in potential:
                potential.remove(mate)
        count = defaultdict(int)
        for mate in potential:
            count[mate] += 1
        common = sorted(count.items(), reverse=True, key=lambda i: i[1])
        results = []
        cols = ['zid', 'name', 'image', 'common' ]
        for m in common:
            u = self.findByKey(m[0])
            if u:
                results.append(dict(zip(cols, [u.zid, u.full_name, u.image, m[1]])))
        return results[:10]

    def getCourses(self):
        courses = pickle.loads(self.courses)
        courses.sort(reverse=True)
        return courses

    def getRequests(self):
        sql = "select `to_zid` from requests where `from_zid`=?"
        results = select(sql, (self.zid,))
        requests = []
        for r in results:
            requests.append(r[0])
        return requests

    def getRecentPosts(self):
        mates = self.getMates()
        recentPosts = self.getPosts()
        for mate in mates:
            user = self.findByKey(mate)
            if user:
                posts = user.getPosts()
                recentPosts.extend(posts)
        # recentPostsOrderByTime = []
        # for post in sorted(recentPosts, key=operator.itemgetter('time'), reverse=True):
        #     recentPostsOrderByTime.append(post)
        # return recentPostsOrderByTime
        return sorted(recentPosts, key=operator.itemgetter('time'), reverse=True)

    def getNotifications(self):
        cur_notifications = pickle.loads(self.notifications)
        new_notifications = self.dumpNotifications()
        cur_notifications.extend(new_notifications)
        # add the length
        cur_notifications[0] += len(new_notifications)
        self.notifications = pickle.dumps(cur_notifications)
        self.update()
        notifications = [Notifications(**n) for n in cur_notifications[1:]]
        notifications.insert(0, cur_notifications[0])
        return notifications

    def getNotificationById(self, nid):
        notifications = pickle.loads(self.notifications)
        notifications[0] = 0
        for n in notifications[1:]:
            if nid == n.nid:
                return n
        return {}

    def removeNotificationById(self, nid):
        notifications = pickle.loads(self.notifications)
        notifications[0] = 0
        n = 0
        for n in notifications[1:]:
            if nid == n.nid:
                break
        if n in notifications:
            notifications.remove(n)
        self.notifications = pickle.dumps(notifications)
        self.update()

    def clearNotice(self):
        notifications = pickle.loads(self.notifications)
        notifications[0] = 0
        self.notifications = pickle.dumps(notifications)
        self.update()

    def dumpNotifications(self):
        sql = 'select `nid` from notifications where `to_zid`=?'
        results = select(sql, (self.zid,))
        notifications = []
        for r in results:
            notification = Notifications.findByKey(r[0])
            notifications.append(notification)
            notification.remove()
        return notifications


class Post(Model):
    __table__ = 'user_post'
    pid = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    zid = StringField(ddl='varchar(50)')
    time = StringField(default=time_stamp, ddl='varchar(50)')
    message = StringField(ddl='varchar(500)')

    @property
    def commentsSize(self):
        return len(self.getComments())

    @classmethod
    def findPosts(cls, col, value):
        sql = "select `pid` from `user_post` where `{}` like '%{}%'".format(col, value)
        results = select(sql, ())
        posts = []
        for r in results:
            post = Post.findByKey(r[0])
            if post:
                posts.append(post)
        return sorted(posts, key=operator.itemgetter('time'), reverse=True)

    def getComments(self):
        # # # # # # # # 
        sql = "select `cid`, `zid` from `user_comment` where `{}`=?".format(self.__primary_key__)
        results = select(sql, (self.pid,))
        # return [Comment.findByKey(r[0]) for r in results]
        # comments = [Comment.findByKey(r[0]) for r in results]
        comments = []
        for r in results:
            comment = Comment.findByKey(r[0])
            poster = User.findByKey(r[1])
            comment.image = poster.image
            comment.name = poster.full_name
            comments.append(comment)
        # return comments
        return sorted(comments, key=operator.itemgetter('time'), reverse=True)

    def removeComments(self):
        sql = "select `cid` from `user_comment` where `{}`=?".format(self.__primary_key__)
        results = select(sql, (self.pid,))
        for r in results:
            comment = Comment.findByKey(r[0])
            comment.remove()

    def getPosterName(self):
        sql = "select `full_name`, `image` from `user_info` where `zid`=?"
        results = select(sql, (self.zid,))
        return results[0]


class Notifications(Model):
    __table__ = 'notifications'
    nid = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    from_zid = StringField(ddl='varchar(50)')
    to_zid = StringField(ddl='varchar(50)')
    noti_type = StringField(ddl='varchar(10)')
    time = StringField(default=time_stamp, ddl='varchar(10)')
    from_name = StringField(default='Anonymous', ddl='varchar(10)')
    from_img = StringField(default='no_image.png', ddl='varchar(10)')
    # state = BooleanField(default=0)
    pid = StringField(default='', ddl='varchar(50)')


class Requests(Model):
    __table__ = 'requests'
    rid = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    from_zid = StringField(ddl='varchar(50)')
    to_zid = StringField(ddl='varchar(50)')

    @classmethod
    def getRequest(cls, from_zid, to_zid):
        sql = 'select rid from requests where from_zid=? and to_zid=?'
        results = select(sql, (from_zid, to_zid,))
        if results:
            request = Requests.findByKey(results[0][0])
            return request
        return None


class Comment(Model):
    __table__ = 'user_Comment'
    cid = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    pid = StringField(ddl='varchar(50)')
    zid = StringField(ddl='varchar(50)')
    time = StringField(default=time_stamp, ddl='varchar(50)')
    message = TextField()
    image = ''
    name= ''


class Pagination(object):
    def __init__(self, page, total_count, limit=_LIMIT_):
        self.page = page
        self.limit = limit
        self.total_count = total_count

    @property
    def pages(self):
        return int(ceil(self.total_count / float(self.limit)))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def begin(self):
        return (self.page - 1) * self.limit

    @property
    def end(self):
        # if self.page * self.limit >  self.total_count:
        #     return self.total_count
        return  self.page * self.limit


    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=5, right_edge=2):
        last = 0
        for num in range(1, self.pages + 1):
            if num <= left_edge or \
               (num > self.page - left_current - 1 and \
                num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num


if __name__ == '__main__':
    test = True
    # print('test_model')





