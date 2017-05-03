# coding=utf-8
from component_ini import redmine

priority_map = {u'低': 1, u'普通': 2, u'高': 3, u'紧急': 4, u'立刻': 5}
status_map = {
    u'新建': 1,
    u'进行中': 2,
    u'已解决': 3,
    u'反馈': 4,
    u'已关闭': 5,
    u'已拒绝': 6,
    u'重新打开': 7,
    u'重复的问题': 8,
    u'无法重现': 9,
    u'需求如此': 10
}


def list_projects():
    projects = []
    for project in redmine.project.all():
        projects.append(u'{} id={}'.format(project.name, project.id))
    return u'\n'.join(projects)


def list_possible_users(users):
    result = []
    for user in users:
        result.append(u'登录名:{}, 全名:{}{}'.format(user.login, user.lastname, user.firstname))
    return '\n'.join(result)
