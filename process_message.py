# coding=utf-8
from datetime import datetime
from redmine_project.user import db
from redmine_project.user import User
import redmine_project.create_bug
from redmine_project.component_ini import redis_handler as redis
from redmine_project.component_ini import redmine
from redmine_project.component_ini import config
from redmine_project.create_bug import process_begin_create_bug
from redmine_project.redmine_utils import priority_map, status_map
from redmine_project.redmine_utils import list_projects, list_possible_users


def check_user_context(request_body):
    wechat_user = request_body['user_id']
    user_state = redis.hgetall(redmine_project.create_bug.context_key(wechat_user))
    if len(user_state) > 0:
        if user_state['context'] == 'create_bug':
            success, response = redmine_project.create_bug.process_creating_bug(user_state, request_body)
            return True, success, response
        else:
            return True, False, 'unknown user context:{}'.format(user_state['context'])
    return False, None, None


def process_file(request_body):
    context_action, success, response = check_user_context(request_body)
    if context_action:
        return success, response
    else:
        return False, u'不要随便上传文件哟, 人家不会处理啦'


def process_text(request_body):
    text = request_body['content'].strip()
    wechat_user = request_body['user_id']
    print wechat_user
    context_action, success, response = check_user_context(request_body)
    if context_action:
        return success, response
    tokens = text.split()
    if tokens[0] == 'redmine':
        return process_redmine(tokens)
    elif tokens[0] == 'register' and len(tokens) >= 2 and tokens[1] == 'redmine':
        return process_register(wechat_user, tokens)
    elif tokens[0] == 'mybug':
        return process_mybug(wechat_user, tokens)
    elif tokens[0] == 'create' and len(tokens) >= 2 and tokens[1] == 'bug':
        existed_user = User.query.get(wechat_user)
        if existed_user is None:
            return False, u'请先注册\n{}'.format(register_redmine_usage())
        return process_begin_create_bug(wechat_user)
    else:
        print 'unsupported command'
        return False, usage()


def process_register(wechat_user, tokens):
    wechat_id = wechat_user
    if len(tokens) == 2:
        return False, register_redmine_usage()
    name = tokens[2]
    users = redmine.user.filter(name=name)
    if len(users) > 1:
        return False, u'{}\n亲,哪一个是你,请输入登录名'.format(list_possible_users(users))
    elif len(users) == 0:
        return False, u'亲,我们找不到你的账号'
    redmine_user = users[0]
    try:
        existed_user = User.query.get(wechat_id)
        if existed_user is not None:
            existed_user.redmine_id = redmine_user.id
        else:
            new_user = User(wechat_id=wechat_id, redmine_id=redmine_user.id)
            db.session.add(new_user)
        db.session.commit()
        return True, u'恭喜,你已成功和redmine用户{}{}绑定'.format(redmine_user.lastname, redmine_user.firstname)
    except:
        db.session.close()
        return False, u'很抱歉,服务出了点小问题,请重新尝试'


def process_redmine(tokens):
    if len(tokens) == 1:
        return True, list_projects()
    project_id = int(tokens[1])
    priority_id = None
    status_id = None
    create_time = None
    for token in tokens[2:]:
        kv = token.split('=')
        key, value = kv[0], kv[1]
        if key == 'p':
            priority_id = priority_map[value]
        elif key == 's':
            status_id = status_map[value]
        elif key == 't':
            create_time = '>={}'.format(value)
        else:
            print 'unrecognized key={}, value={}'.format(key, value)
            return False, redmine_usage()

    issues = []
    for issue in redmine.issue.filter(project_id=project_id, open_issues=True,
                                      priority_id=priority_id, status_id=status_id,
                                      created_on=create_time):
        issues.append(u'{} {}'.format(issue, issue.url))
    return True, u'{}\ntotal={}'.format('\n'.join(issues), len(issues))


def process_mybug(wechat_user, tokens):
    wechat_id = wechat_user
    time_now = datetime.now().strftime('%Y-%m-%d')
    create_time = '>=' + time_now
    priority_id = None
    status_id = None

    existed_user = User.query.get(wechat_id)
    if existed_user is None:
        return False, u'请先注册\n{}'.format(register_redmine_usage())

    for token in tokens[1:]:
        kv = token.split('=')
        key, value = kv[0], kv[1]
        if key == 'p':
            priority_id = priority_map[value]
        elif key == 's':
            status_id = status_map[value]
        elif key == 't':
            create_time = '>={}'.format(value)
        else:
            print 'unrecognized key={}, value={}'.format(key, value)
            return False, redmine_usage()

    issues = []
    for issue in redmine.issue.filter(open_issues=True, assigned_to_id=existed_user.redmine_id,
                                      priority_id=priority_id, status_id=status_id,
                                      created_on=create_time):
        issues.append(u'{} {}'.format(issue, issue.url))
    return True, u'{}\ntotal={}'.format('\n'.join(issues), len(issues))


def redmine_usage():
    return u'redmine project_id [p=普通] [s=新建] [t=2017-04-11]'


def register_redmine_usage():
    return u'register redmine your_username_in_redmine (支持模糊匹配)'


def usage():
    all_usage = [redmine_usage(), register_redmine_usage()]
    return u'\n'.join(all_usage)
