from component_ini import db


class User(db.Model):
    wechat_id = db.Column(db.String(100), primary_key=True)
    redmine_id = db.Column(db.BigInteger)

    def __init__(self, wechat_id, redmine_id):
        self.wechat_id = wechat_id
        self.redmine_id = redmine_id

    def __repr__(self):
        return 'User(wechat_id={}, redmine_id={})'.format(self.wechat_id, self.redmine_id)

