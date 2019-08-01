class Doc:
    def __init__(self):
        self.__fields = {}

    def __parse_title(self, line):
        if line.startswith('# '):
            return (1, line[2:].strip('\r\n '))
        elif line.startswith('## '):
            return (2, line[3:].strip())
        return (0,line)

    def parse(self,path):
        try:
            f = open(path, 'r')
        except FileNotFoundError as e:
            print(e)
            return
        
        prefix = []
        level = 0
        content = []
        line = f.readline()
        while line:
            cur_level,title = self.__parse_title(line)
            if cur_level > 0:
                if level > 0:
                    self.__fields['.'.join(prefix)] = ''.join(content)
                    content.clear()
                
                if cur_level == 1:
                    prefix = [title]
                elif cur_level == 2:
                    prefix = [prefix[0], title]
                level = cur_level
            
            content.append(line)
            line = f.readline()
        
        if level > 0:
            self.__fields['.'.join(prefix)] = ''.join(content)
            content.clear()

        f.close()

    def get(self, name):
        if self.__fields.__contains__(name):
            return self.__fields[name]
        else:
            return '**无文档**'