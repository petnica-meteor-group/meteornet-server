from django.db.models import Model, CharField, FloatField, TextField, ManyToManyField, \
                             DateTimeField, BooleanField, ForeignKey, CASCADE, SET_DEFAULT

class Status(Model):
    name = CharField(max_length=64, default='Test Status')
    color = CharField(max_length=16, default='#00CC00')

class State(Model):
    name = CharField(max_length=64, default='Test Status')

class StateRuleCombiner(Model):

class StateRuleOperator(Model):


class StateRule(Model):
    key = CharField(max_length=64)
    ForeignKey(Status, on_delete=CASCADE)
