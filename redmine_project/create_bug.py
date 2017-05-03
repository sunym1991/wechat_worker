# coding=utf-8
from component_ini import redis_handler as redis
from component_ini import redmine, REDMINE_ROOT
from functools import partial
from redmine_utils import list_projects, priority_map, list_possible_users
import base64
import os
import ConfigParser
from redminelib import Redmine
from user import User
from user_token import Tokens
from redmine_utils import priority_map


class BugCreationItem:
    def __init__(self, required, next_state, back, commit, usage_func, process_func):
        self.required = required
        self.next_state = next_state
        self.back = back
        self.commit = commit
        self.usage_func = usage_func
        self.process_func = process_func


def usage_project_id():
    return u'{}\n请输入project id:\n{}'.format(list_projects(), usage_common('project_id'))


def usage_subject():
    return u'请输入Bug主题:\n{}'.format(usage_common('subject'))


def usage_description():
    return u'请输入Bug描述:\n{}'.format(usage_common('description'))


def usage_priority_id():
    return u'请输入优先级: {}\n{}'.format(','.join(priority_map.keys()), usage_common('priority_id'))


def usage_assigned_to_id():
    return u'将此Bug指派给哪位攻城狮呢?支持模糊匹配用户名:如ymsun,ym,ms,sun\n{}'.format(usage_common('assigned_to_id'))


def usage_uploads():
    return u'请上传附件:\n{}'.format(usage_common('uploads'))


def usage_common(state):
    result = []
    if bug_creation_map[state].back is not None:
        result.append(u'back: 返回输入{}'.format(bug_creation_map[state].back))
    if not bug_creation_map[state].required and bug_creation_map[state].next_state != state:
        result.append(u'pass: 跳过')
    if bug_creation_map[state].commit:
        result.append(u'commit: 提交')
    result.append(u'cancel: 取消Bug提交')
    return '\n'.join(result)


def process_common_state(current_state, user_state, request_body):
    content = request_body['content']
    if request_body['content'] is str:
        content = content.strip()
    wechat_user = request_body['user_id']
    user_state[current_state] = content
    user_state['state'] = bug_creation_map[current_state].next_state
    save_state(wechat_user, user_state)
    return True, bug_creation_map[user_state['state']].usage_func()


def process_priority_id(user_state, request_body):
    content = request_body['content'].strip()
    if content in priority_map:
        request_body['content'] = priority_map[content]
        return process_common_state('priority_id', user_state, request_body)
    else:
        return False, usage_priority_id()


def process_assigned_to_id(user_state, request_body):
    content = request_body['content'].strip()
    users = redmine.user.filter(name=content)
    if len(users) > 1:
        return True, u'{}\n找到以上可能的用户, 请选择\n{}'.format(list_possible_users(users), usage_assigned_to_id())
    elif len(users) == 0:
        return False, u'找不到匹配的用户, 请重新输入\n{}'.format(usage_assigned_to_id())
    request_body['content'] = str(users[0].id)
    return process_common_state('assigned_to_id', user_state, request_body)


def process_uploads(user_state, request_body):
    content = request_body['content'].strip()
    if 'file_name' not in request_body:
        return False, u'命令输错了呦,重新提交吧\n{}'.format(usage_uploads())
    file_name = u'{}/{}'.format(os.path.abspath('.'), request_body['file_name'])
    with open(file_name, 'wb') as write:
        write.write(base64.b64decode(content))
    current_uploaded_file = int(user_state['uploaded_file'])
    user_state['uploaded_file_{}'.format(current_uploaded_file)] = file_name
    user_state['uploaded_file_{}_name'.format(current_uploaded_file)] = request_body['file_name']
    user_state['uploaded_file'] = current_uploaded_file + 1
    request_body['content'] = generate_uploads(user_state)
    return process_common_state('uploads', user_state, request_body)


bug_creation_map = {
    'project_id': BugCreationItem(True, 'subject', None, False,
                                  usage_project_id, partial(process_common_state, 'project_id')),
    'subject': BugCreationItem(True, 'description', 'project_id', False,
                               usage_subject, partial(process_common_state, 'subject')),
    'description': BugCreationItem(False, 'priority_id', 'subject', True,
                                   usage_description, partial(process_common_state, 'description')),
    'priority_id': BugCreationItem(False, 'assigned_to_id', 'description', True,
                                   usage_priority_id, process_priority_id),
    'assigned_to_id': BugCreationItem(False, 'uploads', 'priority_id', True,
                                      usage_assigned_to_id, process_assigned_to_id),
    'uploads': BugCreationItem(False, 'uploads', 'assigned_to_id', True,
                               usage_uploads, process_uploads)
}

action_set = {'back', 'pass', 'commit', 'cancel'}


def process_creating_bug(user_state, request_body):
    content = request_body['content'].strip()
    wechat_user = request_body['user_id']
    if content in action_set:
        if content == 'back':
            return back_create_bug(wechat_user=wechat_user, user_state=user_state)
        elif content == 'pass':
            return pass_create_bug(wechat_user=wechat_user, user_state=user_state)
        elif content == 'commit':
            return commit_create_bug(wechat_user, user_state)
        elif content == 'cancel':
            return cancel_create_bug(wechat_user)
        else:
            return False, u'我们内部出了一点点小错误哟, 再试一下吧'
    else:
        return bug_creation_map[user_state['state']].process_func(user_state, request_body)


def generate_uploads(user_state):
    file_list = []
    for i in range(int(user_state['uploaded_file'])):
        file_list.append({
            'path': user_state['uploaded_file_{}'.format(i)],
            'filename': user_state['uploaded_file_{}_name'.format(i)]
        })
    return file_list


def pass_create_bug(wechat_user, user_state):
    if bug_creation_map[user_state['state']].required:
        return False, u'当前状态不允许跳过\n{}'.format(bug_creation_map[user_state['state']].usage_func())
    user_state['state'] = bug_creation_map[user_state['state']].next_state
    save_state(wechat_user, user_state)
    return True, bug_creation_map[user_state['state']].usage_func()


def back_create_bug(wechat_user, user_state):
    if bug_creation_map[user_state['state']].back is None:
        return False, u'当前状态不允许后退\n{}'.format(bug_creation_map[user_state['state']].usage_func())
    # todo 是否需要删除当前状态下已经设置好的内容
    user_state['state'] = bug_creation_map[user_state['state']].back
    save_state(wechat_user, user_state)
    return True, bug_creation_map[user_state['state']].usage_func()


def cancel_create_bug(wechat_user):
    delete_state(wechat_user)
    return True, u'您已取消提交bug'


def commit_create_bug(wechat_user, user_state):
    if bug_creation_map[user_state['state']].commit:
        user_state['uploads'] = generate_uploads(user_state)
        print user_state
        existed_user = User.query.get(wechat_user)
        if existed_user is not None:
            existed_key = Tokens.query.filter_by(user_id=existed_user.redmine_id, action='api').first()
            redmine_key = existed_key.value
        else:
            delete_state(wechat_user)
            return False, u'没能找到你的注册信息呦,请先注册后重新create bug啦~'
        config = ConfigParser.RawConfigParser()
        config.read('{}{}'.format(REDMINE_ROOT, '/config.ini'))
        redmine = Redmine(url=config.get('redmine', 'url'),
                          key=redmine_key,
                          version=config.get('redmine', 'version'))
        new_issue = redmine.issue.create(**user_state)
        if new_issue is not None:
            delete_state(wechat_user)
            return True, u'您已成功提交了bug哟'
        else:
            return False, u'人家没有能够成功创建bug呢'
    else:
        return False, u'当前状态不可以commit bug\n{}'.format(bug_creation_map[user_state['state']].usage_func())


def save_state(wechat_user, user_state):
    redis.hmset(context_key(wechat_user), user_state)
    redis.expire(context_key(wechat_user), 20 * 60)


def delete_state(wechat_user):
    redis.delete(context_key(wechat_user))


def context_key(user_id):
    return 'chatops.context.{}'.format(user_id)


def process_begin_create_bug(wechat_user):
    user_state = {'context': 'create_bug', 'state': 'project_id', 'uploaded_file': 0}
    redis.hmset(context_key(wechat_user), user_state)
    return True, bug_creation_map[user_state['state']].usage_func()


