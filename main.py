import os

import javalang
import javalang.tree as Tree
import os, pickle
import re
import networkx as nx
import time


class TypeExceptin(Exception):
    "this is user's Exception for check the length of name "

    def __init__(self, str):
        self.str = str

    def __str__(self):
        print("该情况暂未处理:" + self.str)


class MethodNestingExceptin(Exception):
    "this is user's Exception for check the length of name "

    def __init__(self, str):
        self.str = str

    def __str__(self):
        print("方法嵌套:" + self.str)


class AST_parse():
    def __init__(self):
        # 存储所有控制流语句节点 path索引 -> [node,father_api,children_api,False],false代表father是否和控制语句的第一个api链接
        self.control_node_dict = dict()
        # {参数名，[包名.类名,[参数列表]]}
        self.var_dict = dict()
        self.last_api = -1
        self.now_api = None
        self.neighbor_dict = dict()
        self.all_neighbor_dict = list()
        self.api_list = list()
        self.all_api_list = list()
        self.G = nx.Graph()
        self.all_desc_path = dict()
        self.api_desc = str()
        # 存储所有项目内的api
        self.project_pack_dict = dict()
        # 存储项目内api的继承关系
        self.extend_dict = dict()
        # 存储所有标准库api信息
        self.pack_dict = self.load_pkl('api2desc.pkl')
        # 存储所有类所导入的包
        self.class_extend_methods = dict()
        # 记录每个包的路径
        self.pack_path_dict = dict()
        # 记录每个继承类的方法
        self.extend_class_methods = dict()

    def clear_self(self):
        self.control_node_dict = dict()
        # {参数名，[包名.类名,[参数列表]]}
        self.var_dict = dict()
        self.last_api = -1
        self.now_api = None
        self.neighbor_dict = dict()
        self.all_neighbor_dict = list()
        # self.api_list = list()
        self.all_api_list = list()
        self.api_desc = str()

    def get_project_api(self, dirname):
        for maindir, subdir, file_name_list in os.walk(dirname):
            for java_file in file_name_list:
                if java_file.endswith('.java'):
                    apath = os.path.join(maindir, java_file)
                    class_name = java_file.rstrip('.java')

                    try:
                        f_input = open(apath, 'r', encoding='utf-8')
                        f_read = f_input.read()
                        tree = javalang.parse.parse(f_read)
                    except:
                        print(f'文件{maindir}/{java_file}出现问题')
                        continue
                    # 此处需要修改
                    # maindir = maindir.lstrip('E:/java_project/github_file_4/')
                    # if not self.project_pack_dict.__contains__(maindir):
                    #     self.project_pack_dict[maindir] = dict()
                    # self.project_pack_dict[maindir][class_name] = list()

                    for path, node in tree:
                        # # 如过父亲节点中包含条件条件语句，则不予执行
                        # 提取导入类，并获得包信息
                        if isinstance(node, Tree.PackageDeclaration):
                            pakage_name = node.name
                            if not self.project_pack_dict.__contains__(pakage_name):
                                self.project_pack_dict[pakage_name] = dict()
                                self.pack_path_dict[pakage_name] = maindir
                            self.project_pack_dict[pakage_name][class_name] = list()
                        elif isinstance(node, Tree.ClassDeclaration):
                            if node.extends:
                                # extend_name = node.extends.name
                                self.extend_dict[f'{pakage_name}.{class_name}'] = f'{maindir}/{java_file}'

                        elif isinstance(node, Tree.MethodDeclaration):
                            modifier_types = {'public', 'protected', 'private', 'default'}
                            m_type = modifier_types.intersection(node.modifiers)
                            if not m_type:
                                m_type = 'default'
                            try:
                                self.project_pack_dict[pakage_name][class_name].append([node.name, f'{maindir}/{class_name}', m_type])
                            except UnboundLocalError as e:
                                # 当java文件没有所在包时
                                pakage_name = ''
                                self.project_pack_dict[pakage_name] = dict()
                                self.project_pack_dict[pakage_name][class_name] = list()
                                self.project_pack_dict[pakage_name][class_name].append([node.name, maindir])


    def get_extend_pakage(self, package_class_name):
        class_name = package_class_name.split('.')[-1]
        package_name = package_class_name.rstrip(f'.{class_name}')
        if self.extend_class_methods.__contains__(package_class_name):
            return self.extend_class_methods.get(package_class_name)
        # 如果继承的是标注库类
        elif self.pack_dict.__contains__(package_name):
            return [method_decs for method_decs in self.pack_dict.get(package_name).get(class_name) if not method_decs[-1] in ['public', 'protected']]
        # 如果继承的是包内类
        elif not self.pack_path_dict.__contains__(package_name):
            return False
        apath = f'{self.pack_path_dict.get(package_name)}/{class_name}.java'
        try:
            f_input = open(apath, 'r', encoding='utf-8')
            f_read = f_input.read()
            tree = javalang.parse.parse(f_read)
        except:
            print(f'文件{apath}出现问题')
            # TODO:处理返回的false
            return False
        # 分三级，0：同包方法，1：全路径引用，2：.*引用
        import_dict = [dict(), dict(), dict()]
        class_meths_dict = [dict(), dict(), dict()]
        class_methods_list = list()
        # 标记是否包含包信息
        has_PackageDeclaration = False
        # 标记Import是否结束
        has_Import = False
        for name in self.pack_dict.get('java.lang').keys():
            import_dict[2][name] = 'java.lang'
        for path, node in tree:
            if isinstance(node, Tree.PackageDeclaration):
                pakage_name = node.name
                has_PackageDeclaration = True
                pakage_inside_class = self.project_pack_dict.get(node.name)
                for name in pakage_inside_class.keys():
                    import_dict[0][name] = node.name
            elif isinstance(node, Tree.Import):
                # 当没有所属包时,抛弃次java文件
                if not has_PackageDeclaration:
                    break
                has_Import = True
                # undo .*情况node.path没有*
                # class_pack_dict   类名 -》 [包和[所有方法[方法名，参数（可能为none），返回值（可能为void）]]]
                # 需要判断该引用是否是标准库
                class_meths_dict, import_dict = self.parse_import_node(class_meths_dict, import_dict, node)
            # Import完成后，去除同名方法
            elif has_Import:
                has_Import = False
                import_dict[2].update(import_dict[1])
                import_dict[2].update(import_dict[0])
                import_dict = import_dict[2]
            if isinstance(node, Tree.ClassDeclaration) and self.extend_dict.__contains__(package_class_name):
                extend_name = node.extends.name
                extend_package_class_name = f'{import_dict.get(extend_name)}.{extend_name}'
                self.extend_dict[package_class_name] = extend_package_class_name
        # 将本class中的方法加入
        class_methods_list.extend(self.project_pack_dict.get(package_name).get(class_name))
        # if self.extend_class_methods.__contains__():
        if self.extend_dict.__contains__(package_class_name):
            class_methods_list.extend(self.get_extend_pakage(extend_package_class_name))
        self.extend_class_methods[package_class_name] = class_methods_list
        return class_methods_list



    def get_extend_methods(self):
        for package_class_name, apath in self.extend_dict.items():
            self.extend_class_methods[package_class_name] = self.get_extend_pakage(package_class_name)

    def parse_import_node(self, class_meths_dict, import_dict, node):
        # undo .*情况node.path没有*
        # class_pack_dict   类名 -》 [包和[所有方法[方法名，参数（可能为none），返回值（可能为void）]]]
        # 需要判断该引用是否是标准库


        if self.project_pack_dict.__contains__(node.path):
            pack_contain_class = self.project_pack_dict.get(node.path)
            # class_meths_dict[2].update(pack_contain_class)
            for key, value in pack_contain_class.items():
                class_meths_dict[2][key] = [method_decs for method_decs in value if not method_decs[-1] == 'private']
            for class_name in pack_contain_class.keys():
                import_dict[2][class_name] = node.path

        elif self.pack_dict.__contains__(node.path):
            pack_contain_class = self.pack_dict.get(node.path)
            # class_meths_dict[2].update(pack_contain_class)
            for key, value in pack_contain_class.items():
                class_meths_dict[2][key] = [method_decs for method_decs in value if not method_decs[-1] == 'private']
            for class_name in pack_contain_class.keys():
                import_dict[2][class_name] = node.path
        else:
            pakage_list = node.path.split('.')
            class_name = pakage_list[len(pakage_list) - 1]
            pack_name = pakage_list[0]
            for i in range(1, len(pakage_list) - 1):
                pack_name += f'.{pakage_list[i]}'
            if self.pack_dict.__contains__(pack_name):
                class_meths_dict[1][class_name] = self.pack_dict.get(pack_name).get(class_name)
                import_dict[1][class_name] = pack_name
            elif self.project_pack_dict.__contains__(pack_name):
                class_meths_dict[1][class_name] = self.project_pack_dict.get(pack_name).get(class_name)
                import_dict[1][class_name] = pack_name

        return class_meths_dict, import_dict

    def get_father_return_class(self, path, node):
        path_len = len(path) - 1
        if isinstance(path[path_len], list):
            path_len -= 1
        father_node = path[path_len]
        father_return_class = None
        # undo 如果是两层掉用，则拿到第二层的变量
        # 如果不包含在self.var_dict中，说明不是标准库函数
        if hasattr(father_node, 'qualifier') and (self.var_dict.__contains__(father_node.qualifier)):
            method_decs = self.get_overload_method(father_node)
            if method_decs:
                if len(method_decs) == 3:
                    father_return_class = method_decs[2]
        # 返回格式 包+类名
        return father_return_class

    def load_pkl(self, path):
        with open(path, 'rb') as f:
            data = pickle.load(f)
        return data

    def while_load_pkl(self, path):
        num = 0
        with open(path, 'rb') as f:
            while True:
                try:
                    aa = pickle.load(f)
                    # print(aa.__sizeof__())
                    num += len(aa)
                    # self.dump_pkl_notCover('desc_path_dict.pkl', aa)
                    # if(len(aa) == 141):
                    #     break
                    #     print('写入成功')
                except EOFError:
                    break
        print(num)

    def dump_pkl_cover(self, path, path_list):
        with open(path, 'wb') as f:
            pickle.dump(path_list, f)

    def dump_pkl_notCover(self, path, path_list):
        with open(path, 'ab') as f:
            pickle.dump(path_list, f)

    # undo 查询字面常量Literal是int,float,double,String,char[]中的哪一种
    def judge_Literal(self, node):
        literal = node.value
        type_name = None
        if literal[0] == '\'' and literal[-1:] == '\'':
            type_name = 'char[]'
        elif literal[0] == '\"' and literal[-1:] == '\"':
            type_name = 'java.lang.String'
        elif literal == 'true' or literal == 'false':
            type_name = 'boolean'
        elif re.compile(r'^[-+]?[0-9]+$').match(literal):
            type_name = 'int'
        elif re.compile(r'^[-+]?[0-9]+\.[0-9]+$').match(literal):
            type_name = 'float'
        return type_name

    # 通过函数调用节点的方法名及参数，查询出符合的库函数
    def get_overload_method(self, node):
        try:
            var_name = node.qualifier
            method_list = self.var_dict[var_name][1]
            overload_method = [method for method in method_list if method[0] == node.member]
            # undo 当重叠调用时，参数包含MethodInvocation，和MemberReference两种
            # 当时内部函数时，暂时添加参数返回值，无法确认重载方法
            if len(overload_method) > 0 and len(overload_method[0]) == 2:
                right_method = overload_method[0]
            elif len(overload_method) > 1:
                # 参数类型只包含java基本类型和标准库类
                # undo 如果参数为泛型的话，参数的类型可能为自定义类，该情况暂时抛弃
                # undo 如果参数中包含方法调用，则暂时抛弃
                argu_type_list = list()
                if not node.arguments:
                    raise MethodNestingExceptin("没有参数")
                for argument in node.arguments:
                    if isinstance(argument, Tree.MemberReference):
                        argu_type_list.append(self.var_dict.get(argument.member)[0])
                    elif isinstance(argument, Tree.Literal):
                        argu_type_list.append(self.judge_Literal(argument))
                    else:
                        raise MethodNestingExceptin("如果参数中包含方法调用，则随即返回一个参数数量相等的方法")

                # undo 此处应多次测试，并改用for循环比较每一项，防止出现泛型
                # right_method = [method for method in overload_method if (method[1].split(',') == argu_type_list)]
                right_method = None
                for method in overload_method:
                    if method[1].split(',') == argu_type_list:
                        right_method = method
                if not right_method:
                    raise MethodNestingExceptin(f"{self.var_dict[var_name][0]}.{node.member}没有找到匹配的重载函数")

            elif len(overload_method) == 1:
                right_method = overload_method[0]
            else:
                right_method = None
            # 返回类型：[方法名，[参数]，返回值]
            return right_method
        except TypeExceptin as e:
            print(e.str)
        except MethodNestingExceptin:
            argu_num = len(node.arguments)
            # right_method = [method for method in overload_method if (len(method[1].split(',')) == argu_num)][0]
            for method in overload_method:
                if method[1] and len(method[1].split(',')) == argu_num:
                    right_method = method
                    break
                elif (not method[1]) and argu_num == 0:
                    right_method = method
                    break
                else:
                    right_method = None
            return right_method
        except BaseException:
            pass

    # 每当添加新api时
    def update_control_dict(self, path, node):
        # 邻接表新建一行
        now_api_num = len(self.api_list) - 1
        self.G.add_node(now_api_num)
        self.neighbor_dict[now_api_num] = set()
        # 如果没有控制节点且有上一个api
        if not self.control_node_dict.keys() and self.last_api > -1:
            self.neighbor_dict.get(self.last_api).add(now_api_num)
            self.G.add_edge(self.last_api, now_api_num)
        for key in list(self.control_node_dict.keys()):
            # 如果控制节点被弹出，即该循环结束
            control_node = self.control_node_dict.get(key)
            path_num = int(key.split(',')[0])
            if len(path) <= path_num or not path[path_num] == control_node[0]:
                control_node[2] = now_api_num
                if not control_node[1] == -1:
                    self.neighbor_dict.get(control_node[1]).add(control_node[2])
                    self.G.add_edge(control_node[1], control_node[2])
                # 证明该循环中没有api
                if not control_node[3]:
                    # 环
                    if isinstance(control_node[0], Tree.WhileStatement) or isinstance(control_node[0],
                                                                                      Tree.ForStatement):
                        self.neighbor_dict.get(self.last_api).add(control_node[4])
                        self.G.add_edge(control_node[3], self.last_api)
                    self.neighbor_dict.get(self.last_api).add(control_node[2])
                    self.G.add_edge(self.last_api, control_node[2])
                self.control_node_dict.pop(key)
            # 如果循环还未结束，则链接fater和循环中第一个api
            elif self.last_api == -1:
                control_node[3] = False
            elif control_node[3]:
                control_node[4] = now_api_num
                self.neighbor_dict.get(control_node[1]).add(now_api_num)
                self.G.add_edge(control_node[1], now_api_num)
                control_node[3] = False
            else:
                self.neighbor_dict.get(self.last_api).add(now_api_num)
                self.G.add_edge(self.last_api, now_api_num)
        self.last_api = now_api_num

    def get_api_decs_lists(self):
        self.all_api_list.append(list(self.api_list))
        # 把索引转为api，之所以用索引是因为api有重名的
        # undo 只有一个api调用的方法被舍弃
        if nx.nodes(self.G):
            for num_path in nx.all_simple_paths(self.G, source=0, target=len(self.G.nodes) - 1):
                api_path = list()
                for num_api in num_path:
                    api_path.append(self.api_list[num_api])
                if self.all_desc_path.__contains__(self.api_desc):
                    self.all_desc_path[self.api_desc].append(api_path)
                    # undo
                    if len(self.all_desc_path[self.api_desc]) > 50:
                        break
                else:
                    self.all_desc_path[self.api_desc] = [api_path]
        self.api_desc = ''
        self.G.clear()
        self.api_list.clear()
        self.all_neighbor_dict.append(dict(self.neighbor_dict))
        self.neighbor_dict.clear()
        self.control_node_dict.clear()
        self.last_api = -1


    def parse_java_file(self, java_file):
        java_type = ['byte[]', 'char', 'short', 'int', 'long', 'float', 'double', 'boolean']
        # error_list = ['HistoricCaseInstanceCollectionResource.java', 'TaskCollectionResource.java',
        #               'CaseInstanceCollectionResource.java', 'DmnXMLConverter.java',
        #               'HistoricProcessInstanceCollectionResource.java', 'NetDbRenderer.java']
        self.clear_self()
        # print(f'正在处理文件{maindir}/{java_file}')
        # if java_file in error_list:
        #     continue
        # if java_file == 'TIFFIFD.java':
        #     print('.')
        apath = os.path.join(maindir, java_file)
        try:
            f_input = open(apath, 'r', encoding='utf-8')
            f_read = f_input.read()
            tree = javalang.parse.parse(f_read)
        except:
            print(f'文件{maindir}/{java_file}出现问题')
            return False
        f_input.seek(0)
        lines = f_input.readlines()

        import_dict = [dict(), dict(), dict()]
        class_meths_dict = [dict(), dict(), dict()]
        # 标记是否包含包信息
        has_PackageDeclaration = False
        # 标记Import是否结束
        has_Import = False
        class_meths_dict[2].update(self.pack_dict.get('java.lang'))
        for class_name in class_meths_dict.keys():
            import_dict[2][class_name] = 'java.lang'
        for path, node in tree:
            # 所有条件语句，待补充
            # # 如过父亲节点中包含条件条件语句，则不予执行
            # 提取导入类，并获得包信息

            if isinstance(node, Tree.PackageDeclaration):
                has_PackageDeclaration = True
                pakage_inside_class = self.project_pack_dict.get(node.name)
                class_meths_dict[0].update(pakage_inside_class)
                for class_name in pakage_inside_class.keys():
                    import_dict[0][class_name] = node.name

            elif isinstance(node, Tree.Import):
                # 当没有所属包时,抛弃次java文件
                if not has_PackageDeclaration:
                    break
                has_Import = True
                # undo .*情况node.path没有*
                # class_pack_dict   类名 -》 [包和[所有方法[方法名，参数（可能为none），返回值（可能为void）]]]
                # 需要判断该引用是否是标准库
                class_meths_dict, import_dict = self.parse_import_node(class_meths_dict, import_dict)
            # Import完成后，去除同名方法
            elif has_Import:
                has_Import = False
                class_meths_dict[2].update(class_meths_dict[1])
                class_meths_dict[2].update(class_meths_dict[0])
                class_meths_dict = class_meths_dict[2]
                import_dict[2].update(import_dict[1])
                import_dict[2].update(import_dict[0])
                import_dict = import_dict[2]

            # 为应对静态变量
            elif isinstance(node, Tree.ClassDeclaration):
                if node.extends:
                    extend_class_name = node.extends.name
                    extend_pack_name = import_dict.get(extend_class_name)
                    # pack_class_name = f'{extend_pack_name}.{extend_class_name}'
                    # 如果继承的是标准库类
                    if self.pack_dict.__contains__(extend_pack_name):
                        pass
                    # 如果继承的是项目内类
                    elif self.project_pack_dict.__contains__(extend_pack_name):
                        self.get_extend_class(f'{pack_name}.{node.name}', f'{extend_pack_name}.{extend_class_name}')
                for class_name in class_meths_dict.keys():
                    pack_name = import_dict.get(class_name)
                    self.var_dict[class_name] = [f'{pack_name}.{class_name}',
                                                 class_meths_dict.get(class_name)]
                # 为防止最后一个方法失效
                self.get_api_decs_lists()

            elif isinstance(node, Tree.MethodDeclaration):
                # pattern = f'\/\*(\s|.)*?\*\/(\s)*{node.name}'
                # f_input.seek(0)
                # re.findall(pattern, f_read)
                # if node.name == 'writeCookieValue':
                #     print('a')
                if node.name == 'run':
                    print('a')
                if not self.api_desc == '':
                    self.all_api_list.append(list(self.api_list))
                    self.all_neighbor_dict.append(dict(self.neighbor_dict))
                    # 把索引转为api，之所以用索引是因为api有重名的
                    # undo 只有一个api调用的方法被舍弃
                    if nx.nodes(self.G):
                        for num_path in nx.all_simple_paths(self.G, source=0, target=len(self.G.nodes) - 1):
                            api_path = list()
                            for num_api in num_path:
                                api_path.append(self.api_list[num_api])
                            if self.all_desc_path.__contains__(self.api_desc):
                                self.all_desc_path[self.api_desc].append(api_path)
                                # undo
                                if len(self.all_desc_path[self.api_desc]) > 50:
                                    break
                            else:
                                self.all_desc_path[self.api_desc] = [api_path]
                    self.api_desc = ''

                api_line = node.position.line - 2 - len(node.annotations)
                find_start = False
                # undo 如果该方法没有注释
                if '*/' not in lines[api_line]:
                    find_start = True
                if '*/' in lines[api_line] and '/*' in lines[api_line]:
                    find_start = True
                    self.api_desc = lines[api_line].strip().strip('/').strip('*')
                try:
                    while (not find_start):
                        s = lines[api_line - 20:api_line]
                        for i in range(1, 21):
                            if '/*' in s[-i]:
                                find_start = True
                                self.api_desc = str()
                                for j in range(1, i):
                                    this_line = s[-(i - j)].strip().lstrip('*')
                                    if this_line.startswith('TODO') or this_line.startswith(
                                            '@param') or this_line.startswith('@return') or \
                                            this_line.startswith('NOTE:') or this_line.startswith('test'):
                                        break
                                    if this_line.endswith('.'):
                                        self.api_desc += this_line
                                        break
                                    self.api_desc += this_line
                                break
                        api_line -= 20
                except IndexError:
                    self.api_desc = ''
                self.G.clear()
                self.api_list.clear()
                self.neighbor_dict.clear()
                self.control_node_dict.clear()
                self.last_api = -1


            elif isinstance(node, Tree.IfStatement) or isinstance(node, Tree.WhileStatement) or isinstance(
                    node, Tree.ForStatement):
                # 如果新的path长度恰好和之前相等，那么就会被覆盖
                if not self.api_desc == '':
                    self.control_node_dict[f'{len(path)},{hash(node)}'] = [node, self.last_api, None, True,
                                                                           None]

            # 通过path获得局部变量定义，未确定类
            elif isinstance(node, Tree.VariableDeclarator):
                path_len = len(path) - 1
                if isinstance(path[path_len], list):
                    path_len -= 1
                var_class_name = path[path_len].type.name
                if class_meths_dict.__contains__(var_class_name):
                    pack_name = import_dict.get(var_class_name)
                    self.var_dict[node.name] = [f'{pack_name}.{var_class_name}',
                                                class_meths_dict.get(var_class_name)]
                # 在这里加入java基本类型变量，为参数判断准备
                if var_class_name in java_type:
                    self.var_dict[node.name] = var_class_name

            # 形参，获取变量名及类
            elif isinstance(node, Tree.FormalParameter) and not self.api_desc == '':
                par_class_name = node.type.name
                if class_meths_dict.__contains__(par_class_name):
                    self.var_dict[node.name] = [f'{pack_name}.{class_name}',
                                                class_meths_dict.get(par_class_name)]
            # 方法调用，须与变量名关联，变量名与类关联，类与包信息关联
            # undo 多级调用根本没进来
            elif isinstance(node, Tree.MethodInvocation) and not self.api_desc == '':
                # print(node)
                # if node.member == 'endVisit':
                #     print('a')
                if self.var_dict.__contains__(node.qualifier):
                    # print(node)
                    var_name = node.qualifier
                    code_line = lines[node.position.line - 1]
                    method_decs = self.get_overload_method(node)
                    if method_decs:
                        if len(method_decs) == 3:
                            method_class = self.var_dict[var_name][0]
                            self.api_list.append(f'{method_class}.{method_decs[0]}({method_decs[1]})')
                        if len(method_decs) == 2:
                            self.api_list.append(f'{method_decs[1]}.{method_decs[0]}')
                        self.update_control_dict(path, node)
                # 当连续调用
                elif not node.qualifier:
                    var_father_return_class = self.get_father_return_class(path, node)
                    if not var_father_return_class is None:
                        # 当父节点方法返回值为None
                        if var_father_return_class == 'None.E':
                            self.api_list.append(f'E.{node.member}(UNKNOW)')
                            self.update_control_dict(path, node)
                        # 当父节点返回为正常类
                        else:
                            node.qualifier = var_father_return_class.split('.')[-1]
                            # 当父节点返回为正常类
                            if node.qualifier in import_dict.keys():
                                method_decs = self.get_overload_method(node)
                                if method_decs:
                                    self.api_list.append(
                                        f'{var_father_return_class}.{method_decs[0]}({method_decs[1]})')
                                    self.update_control_dict(path, node)

    def parse(self, dirname):

        self.get_project_api(dirname)
        self.get_extend_methods()
        # file_handle = open('1.txt', mode='w')
        # file_handle.truncate(0)
        for maindir, subdir, file_name_list in os.walk(dirname):
            for java_file in file_name_list:
                # try:
                if java_file.endswith('.java'):
                    self.parse_java_file(java_file)

        self.dump_pkl_notCover('desc_path_dict_2.pkl', self.all_desc_path)
        print(f'新增{len(self.all_desc_path)}条数据')
        self.dump_pkl_notCover('graph.pkl', self.all_api_list)
        self.dump_pkl_notCover('graph.pkl', self.all_neighbor_dict)

        # file_handle.close()


def write_file(path, str):
    with open(path, 'a') as file:
        file.write(str)


if __name__ == '__main__':
    # my_parse = AST_parse()
    # my_parse.parse('city-master')
    # my_parse.while_load_pkl('desc_path_dict_2.pkl')
    # my_parse.while_load_pkl('all_desc_path.pkl')
    # my_parse.parse('demo_test')
    # my_parse.parse('spring-session-core')

    # 处理github项目
    file_num = 0
    # maindir = 'E:/java_project/github_file_4'
    maindir = 'C:/Users/wkr/Desktop/项目/AST_parse_new'
    write_file('log.txt', '\n当前时间为：{}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))))
    write_file('log.txt', f'正在解析{maindir}')
    file_list = os.listdir(maindir)
    for subdir in file_list:
        my_parse = AST_parse()
        file_num += 1
        print(f'开始解析第{file_num}个文件{subdir}')

        # if file_num < 297:
        #     continue
        print('当前时间为：{}'.format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))))
        if os.path.isdir(f'{maindir}/{subdir}') or subdir.endswith('.java'):
            my_parse.parse(f'{maindir}/{subdir}')

# undo UNKNOW 已解决
# undo 两个局部变量名字一样怎么办 ,已解决
# undo CatchClauseParameter(annotations=None, modifiers=None, name=e, types=['IOException']
# undo 方法间的调用顺序  do


# undo 循环调用 已解决
# undo 多类测试
# undo 返回值，参数问题  java.util.Arrays.asList(T...)
# undo raplase为什么不在里面
# undo 生成路径 do
# undo 循环


