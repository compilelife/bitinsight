from bitstream import *
from copy import copy

class Field:
    def __init__(self, name, bs):
        self.bs = bs
        self.name = name
        self.begin = BitPos(-1,-1)
        self.end = BitPos(-1,-1)
        self.value = None

    def __str__(self):
        return "%s\t%s=>%s"%(self.name, str(self.begin), str(self.end))

class Table(Field):
    def __init__(self, name, context, bs: BitStream):
        super(Table, self).__init__(name, bs)
        self.fields = []
        self.value = self
        self.context = context

    def remove(self, name):
        delattr(self, name)
        for i in range(len(self.fields)):
            if self.fields[i].name == name:
                del self.fields[i]
                break

    def add_exist(self, field: Field):
        self.fields.append(field)
        setattr(self, field.name, field.value)

    def add_table(self, func, **kwargs):
        bs = self.bs
        if kwargs.__contains__('bs'):
            bs = kwargs['bs']
            del kwargs['bs']

        table = Table(func.__name__, self.context, bs)
        setattr(self, func.__name__, table)
        self.fields.append(table)

        table.begin = bs.pos()
        func(table, bs, **kwargs)
        table.end = bs.pos()


    def add_field(self, name, func, **kwargs):
        field = Field(name, self.bs)

        field.begin = self.bs.pos()
        field.value = func(**kwargs)
        field.end = self.bs.pos()

        setattr(self, name, field.value)
        self.fields.append(field)
        

    def add_fields(self, func, *names, **kwargs):
        fields = []
        for name in names:
            field = Field(name, self.bs)
            field.begin = self.bs.pos()
            setattr(self, name, None)
            self.fields.append(field)
            fields.append(field)
        
        func(self, self.bs, **kwargs)

        for field in fields:
            field.end = self.bs.pos()

    def get_value(self, name, def_value):
        if hasattr(self, name):
            return getattr(self, name)
        else:
            return def_value

    def get_value_by_path(self, path, def_value='Unknown'):
        field = self
        names = path.split('.')
        for name in names:
            try:
                field = getattr(field, name)
            except AttributeError as e:
                field = def_value
                break;

        return field