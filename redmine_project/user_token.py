from component_ini import db


class Tokens(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.BigInteger)
    action = db.Column(db.String(100))
    value = db.Column(db.String(200))
    created_on = db.Column(db.DateTime)
    updated_on = db.Column(db.DateTime)

    def __init__(self, user_id, action, value):
        self.user_id = user_id
        self.action = action
        self.value = value

    def __repr__(self):
        return 'Token(user_id={}, value={}, value={})'.format(self.user_id, self.action, self.value)