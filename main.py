import os

import javalang
import javalang.tree as Tree
import os, pickle
import re
import networkx as nx
import time
import sys


sys.setrecursionlimit(4000)
split_path = 'C:/Users/wkr/Desktop/项目/AST_parse_new/clicy-master/'
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

def log(say, path='./log.txt'):
    print(say)
    with open(path, 'a') as file:
        file.write(say + '\n')

def get_pack_name(package_class_name):
    class_name = package_class_name.split('.')[-1]
    package_name = package_class_name.rstrip(class_name).rstrip('.')
    return class_name, package_name


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
        #记录所有接口信息
        self.project_pack_interface_dict = dict()

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

    # 获得类及内部类中的方法
    def processing_project_api_nodes(self, tree, class_name, pakage_name = ''):
        out_class = []
        inner_class = []
        for path, node in tree:
            # 提取导入类，并获得包信息
            if isinstance(node, Tree.CompilationUnit):
                try:
                    out_class = [out_node for out_node in node.children[-1] if not out_node.name == class_name]
                    inner_class = [inner_node for inner_node in node.children[-1][0].body if
                                   isinstance(inner_node, Tree.ClassDeclaration)]

                except IndexError:
                    print(f'文件{maindir}/{class_name}.java获取包内api时出现问题')
                    break
                # if inner_class:
                #     break
                if node.package:
                    pakage_name = node.package.name
                    if not self.project_pack_dict.__contains__(pakage_name):
                        self.project_pack_dict[pakage_name] = dict()
                        self.pack_path_dict[pakage_name] = maindir
                    # 防止同包名
                    elif self.pack_path_dict[pakage_name] != maindir:
                        self.pack_path_dict[f'{pakage_name}_2'] = maindir
                    self.project_pack_dict[pakage_name][class_name] = list()
                else:
                    break

            elif isinstance(node, Tree.ConstructorDeclaration):
                params = list()
                for p in node.parameters:
                    params.append(p.type.name)
                if not self.project_pack_dict[pakage_name].__contains__(class_name):
                    self.project_pack_dict[pakage_name][class_name] = list()
                self.project_pack_dict[pakage_name][class_name].append([node.name, f'{maindir}/{class_name}', params,
                                                                        None, 'public'])
            elif isinstance(node, Tree.EnumDeclaration):
                break
            elif isinstance(node, Tree.ClassDeclaration) or isinstance(node, Tree.InterfaceDeclaration):
                # 如果包含内部类的话
                # TODO:内部类中的方法内部类还未解决
                if node in inner_class:
                    self.processing_project_api_nodes(node, f'{class_name}*{node.name}', pakage_name)
                elif node in out_class:
                    self.processing_project_api_nodes(node, node.name, pakage_name)
                else:
                    if isinstance(node, Tree.ClassDeclaration):
                    # 如果没有构造器加入一个构造器方法
                        constructors = [constructor for constructor in node.body if isinstance(node, Tree.ConstructorDeclaration)]
                        if not constructors:
                            if not self.project_pack_dict[pakage_name].__contains__(class_name):
                                self.project_pack_dict[pakage_name][class_name] = list()
                            # TODO:路径该怎么写
                            self.project_pack_dict[pakage_name][class_name].append(
                                [node.name, f'{maindir}/{class_name}', [], None, 'public'])
                    else:
                        if not self.project_pack_interface_dict.__contains__(pakage_name):
                            self.project_pack_interface_dict[pakage_name] = dict()
                        if not self.project_pack_interface_dict[pakage_name].__contains__(class_name):
                            self.project_pack_interface_dict[pakage_name][class_name] = list()
                    if node.extends:
                        # if f'{pakage_name}.{node.name}' == 'org.activiti.examples.DemoApplicationConfiguration':
                        #     print('a')
                        self.extend_dict[f'{pakage_name}.{class_name}'] = f'{maindir}/{class_name}.java'

            # elif isinstance(node, Tree.LocalVariableDeclaration):
            #     print('a')
            elif isinstance(node, Tree.MethodDeclaration) and not (isinstance(tree, Tree.CompilationUnit) and (path[-2] in inner_class
                    or path[-2] in out_class)):
                if isinstance(path[-2], Tree.InterfaceDeclaration):
                    m_type = 'public'
                else:
                    modifier_types = {'public', 'protected', 'private', 'default'}
                    m_type = ''.join(modifier_types.intersection(node.modifiers))
                    if not m_type:
                        m_type = 'default'
                    if 'static' in node.modifiers:
                        m_type = f'{m_type},static'
                params = list()
                for p in node.parameters:
                    params.append(p.type.name)
                if not self.project_pack_dict[pakage_name].__contains__(class_name):
                    self.project_pack_dict[pakage_name][class_name] = list()
                self.project_pack_dict[pakage_name][class_name].append([node.name, f'{maindir}/{class_name}', params,
                                                                        node.return_type.name if node.return_type else None,
                                                                        m_type])


    def get_project_api(self, dirname):

        for maindir, subdir, file_name_list in os.walk(dirname):
            for java_file in file_name_list:
                if java_file.endswith('.java'):
                    apath = os.path.join(maindir, java_file)
                    # print(apath)

                    class_name = java_file.rstrip('java').rstrip('.')
                    # if class_name == 'Other':
                    #     print('a')
                    try:
                        f_input = open(apath, 'r', encoding='utf-8')
                        f_read = f_input.read()
                    except:
                        print(f'文件{maindir}/{java_file}获得初步api时读取失败 ')
                        continue
                    try:
                        tree = javalang.parse.parse(f_read)
                    except:
                        print(f'文件{maindir}/{java_file}获得初步api时无法解析 ')
                        continue

                    self.processing_project_api_nodes(tree, class_name)

    # 获得参数和返回值的所在包
    # TODO:把导入包的内容存起来，容易溢出
    def get_re_param(self, dirname):
        for maindir, subdir, file_name_list in os.walk(dirname):
            for java_file in file_name_list:
                if java_file.endswith('.java'):
                    apath = os.path.join(maindir, java_file)
                    # print(apath)
                    class_name = java_file.rstrip('java').rstrip('.')
                    try:
                        f_input = open(apath, 'r', encoding='utf-8')
                        f_read = f_input.read()
                    except:
                        print(f'文件{maindir}/{java_file}获取返回值参数时读取文件失败')
                    try:
                        tree = javalang.parse.parse(f_read)
                    except:
                        print(f'文件{maindir}/{java_file}获取返回值参数时解析文件失败')
                        continue
                    # TODO:extend
                    import_dict = [dict(), dict(), dict()]
                    class_meths_dict = [dict(), dict(), dict()]
                    for key, value in self.pack_dict.get('java.lang').items():
                        class_meths_dict[2][key] = [method for method in value if method[-1] == 'public']
                    for temp_class_name in class_meths_dict[2].keys():
                        import_dict[2][temp_class_name] = 'java.lang'
                    for path, node in tree:
                        if isinstance(node, Tree.CompilationUnit):
                            # TODO:内部类暂时删掉
                            try:
                                out_class = [out_node for out_node in node.children[-1] if
                                             not out_node.name == class_name]
                                inner_class = [inner_node for inner_node in node.children[-1][0].body if
                                               isinstance(inner_node, Tree.ClassDeclaration)]
                            except:
                                break
                            # if inner_class:
                            #     break
                            # 提取导入类，并获得包信息
                            if node.package:
                                package_name = node.package.name
                                pakage_inside_class = self.project_pack_dict.get(node.package.name)
                                for key, value in pakage_inside_class.items():
                                    class_meths_dict[0][key] = [method for method in value if
                                                                not method[-1] in ['private', 'father_project']]
                                for temp_class_name in pakage_inside_class.keys():
                                    import_dict[0][temp_class_name] = node.package.name
                            else:
                                break
                            # Import完成后，去除同名方法
                            if node.imports:
                                for import_node in node.imports:
                                    class_meths_dict, import_dict = self.parse_import_node(class_meths_dict,
                                                                                           import_dict, import_node)
                            class_meths_dict[2].update(class_meths_dict[1])
                            class_meths_dict[2].update(class_meths_dict[0])
                            class_meths_dict = class_meths_dict[2]
                            import_dict[2].update(import_dict[1])
                            import_dict[2].update(import_dict[0])
                            import_dict = import_dict[2]
                        elif isinstance(node, Tree.InterfaceDeclaration) or isinstance(node, Tree.EnumDeclaration):
                            break
                        # elif isinstance(node, Tree.ConstructorDeclaration):
                        #     if other_class in vars() and node in other_class.body:
                        #         temp_class_name = other_class_name
                        #     else:
                        #         temp_class_name = class_name
                        #     params = list()
                        #     for p in node.parameters:
                        #         params.append(p.type.name)
                        #     all_method_list = self.project_pack_dict.get(package_name).get(temp_class_name)
                        #     for i in range(len(all_method_list)):
                        #         if all_method_list[i][0] == node.name and all_method_list[i][2] == params and \
                        #                 all_method_list[i][3] == None:
                        #             params.clear()
                        #             for p in node.parameters:
                        #                 params.append(f'{import_dict.get(p.type.name)}.{p.type.name}')
                        #             if return_type:
                        #                 self.project_pack_dict.get(package_name).get(temp_class_name)[i][
                        #                     3] = f'{import_dict.get(return_type)}.{return_type}'
                        #             self.project_pack_dict.get(package_name).get(temp_class_name)[i][
                        #                 2] = params
                        #             break

                        elif isinstance(node, Tree.ClassDeclaration):
                            other_class = None
                            if node in inner_class:
                                other_class = node
                                other_class_name = f'{class_name}*{node.name}'
                            elif node in out_class:
                                other_class = node
                                other_class_name = node.name

                        elif isinstance(node, Tree.MethodDeclaration) or isinstance(node, Tree.ConstructorDeclaration):
                            if other_class and node in other_class.body:
                                temp_class_name = other_class_name
                            else:
                                temp_class_name = class_name
                            params = list()
                            for p in node.parameters:
                                params.append(p.type.name)
                            if isinstance(node, Tree.ConstructorDeclaration):
                                return_type = None
                            else:
                                return_type = node.return_type.name if node.return_type else None
                            all_method_list = self.project_pack_dict.get(package_name).get(temp_class_name)
                            for i in range(len(all_method_list)):
                                if all_method_list[i][0] == node.name and all_method_list[i][2] == params and all_method_list[i][3] == return_type:
                                    params.clear()
                                    for p in node.parameters:
                                        params.append(f'{import_dict.get(p.type.name)}.{p.type.name}')
                                    if return_type:
                                        self.project_pack_dict.get(package_name).get(temp_class_name)[i][
                                            3] = f'{import_dict.get(return_type)}.{return_type}'
                                    self.project_pack_dict.get(package_name).get(temp_class_name)[i][
                                        2] = params
                                    break





    # TODO:会出现包名重复的问题
    def get_extend_pakage(self, package_class_name):
        # if package_class_name == 'org.apache.camel.routepolicy.quartz.SpringCronScheduledRoutePolicyTest':
        #     print('a')
        # print(package_class_name)
        if package_class_name == '':
            return []
        class_name, package_name = get_pack_name(package_class_name)
        if class_name.__contains__('*'):
            out_class_name = class_name.split('*')[0]
            inner_class_name = class_name.split('*')[1]
        else:
            out_class_name = class_name
            inner_class_name = class_name
        # class_name = package_class_name.split('.')[-1]
        # package_name = package_class_name.rstrip(class_name).rstrip('.')
        class_methods_list = list()
        if self.extend_class_methods.__contains__(package_class_name):
            return self.extend_class_methods.get(package_class_name)
        # 如果继承的是标注库类
        elif self.pack_dict.__contains__(package_name):
            father_methods_list = list(self.pack_dict.get(package_name).get(class_name))
            for method in father_methods_list:
                if method[-1] == 'protected':
                    method[-1] = 'father_protected'
                    class_methods_list.append(method)
                elif method[-1] in ['public', 'father_protected']:
                    class_methods_list.append(method)
            return class_methods_list
        # 如果继承的是包内类
        elif not self.pack_path_dict.__contains__(package_name):
            return class_methods_list
        # 为解决项目下有两个同名包
        try:
            class_methods_list.extend(self.project_pack_dict.get(package_name).get(class_name))
        except TypeError:
            return []
        apath = f'{self.pack_path_dict.get(package_name)}/{out_class_name}.java'
        if not os.path.exists(apath):
            package_name_2 = f'{package_name}_2'
            apath = f'{self.pack_path_dict.get(package_name_2)}/{out_class_name}.java'
        if not os.path.exists(apath):
            return []
        # TODO:
        # try:
        #     f_input = open(apath, 'r', encoding='utf-8')
        #     f_read = f_input.read()
        #     tree = javalang.parse.parse(f_read)
        # except:
        #     print(f'文件{apath}获取继承包信息时出现问题')
        #     return class_methods_list
        f_input = open(apath, 'r', encoding='utf-8')
        f_read = f_input.read()
        tree = javalang.parse.parse(f_read)
        # 分三级，0：同包方法，1：全路径引用，2：.*引用
        import_dict = [dict(), dict(), dict()]
        class_meths_dict = [dict(), dict(), dict()]
        extend_package_class_name = ''
        # 标记Import是否结束
        for name in self.pack_dict.get('java.lang').keys():
            import_dict[2][name] = 'java.lang'
        for path, node in tree:
            if isinstance(node, Tree.CompilationUnit):
                if node.package:
                    # pakage_name = node.package.name
                    pakage_inside_class = self.project_pack_dict.get(node.package.name)
                    try:
                        for name in pakage_inside_class.keys():
                            import_dict[0][name] = node.package.name
                    except:
                        pass
                else:
                    break
                if node.imports:
                    for import_node in node.imports:
                        class_meths_dict, import_dict = self.parse_import_node(class_meths_dict, import_dict, import_node)
                # Import完成后，去除同名方法
                import_dict[2].update(import_dict[1])
                import_dict[2].update(import_dict[0])
                import_dict = import_dict[2]

            # elif isinstance(node, Tree.ClassDeclaration) and self.extend_dict.__contains__(f'{package_name}.{node.name}'):
            elif isinstance(node, Tree.ClassDeclaration) and node.name == inner_class_name:
                try:
                    extend_name = node.extends.name
                    extend_package_class_name = f'{import_dict.get(extend_name)}.{extend_name}'
                    self.extend_dict[package_class_name] = extend_package_class_name
                    break
                except:
                    return class_methods_list

        # 将本class中的方法加入,如果包含内部类则舍弃
        # try:
        #     class_methods_list.extend(self.project_pack_dict.get(package_name).get(class_name))
        # except TypeError:
        #     return []
        # if self.extend_class_methods.__contains__():
        # 增添新属性：'father_protected'，子类可继承但跨包不可调用
        # 这条判断语句其实没用了，但是不删了吧
        if not extend_package_class_name == '' and self.extend_dict.__contains__(package_class_name):
            # TODO:此处未考虑父类为内部类或者同级类
            father_methods_list = list(self.get_extend_pakage(extend_package_class_name))
            for method in father_methods_list:
                if method[-1] == 'protected':
                    method[-1] = 'father_protected'
                    class_methods_list.append(method)
                elif method[-1] in ['public', 'father_protected']:
                    class_methods_list.append(method)
        #   self.project_pack_dict = dict()  中加入继承到的方法
        self.project_pack_dict[package_name][class_name] = class_methods_list
        self.extend_class_methods[package_class_name] = class_methods_list
        return class_methods_list



    def get_extend_methods(self):
        # for package_class_name, apath in self.extend_dict.items():
        for package_class_name in list(self.extend_dict.keys()):
            # apath = self.extend_dict.get(package_class_name)
            try:
                self.extend_class_methods[package_class_name] = self.get_extend_pakage(package_class_name)
            except:
                pass


    def parse_import_node(self, class_meths_dict, import_dict, node):
        # undo .*情况node.path没有*
        # class_pack_dict   类名 -》 [包和[所有方法[方法名，参数（可能为none），返回值（可能为void）]]]
        # 需要判断该引用是否是标准库
        if self.project_pack_dict.__contains__(node.path):
            pack_contain_class = self.project_pack_dict.get(node.path)
            # class_meths_dict[2].update(pack_contain_class)
            for key, value in pack_contain_class.items():
                class_meths_dict[2][key] = [method_decs for method_decs in value if method_decs[-1] == 'public']
            for class_name in pack_contain_class.keys():
                import_dict[2][class_name] = node.path

        elif self.pack_dict.__contains__(node.path):
            pack_contain_class = self.pack_dict.get(node.path)
            # class_meths_dict[2].update(pack_contain_class)
            for key, value in pack_contain_class.items():
                class_meths_dict[2][key] = [method_decs for method_decs in value if method_decs[-1] == 'public']
            for class_name in pack_contain_class.keys():
                import_dict[2][class_name] = node.path
        else:
            class_name = node.path.split('.')[-1]
            pack_name = node.path.rstrip(class_name).rstrip('.')
            if self.pack_dict.__contains__(pack_name):
                temp_class_methods = self.pack_dict.get(pack_name).get(class_name)
                if temp_class_methods:
                    class_meths_dict[1][class_name] = [method_decs for method_decs in self.pack_dict.get(pack_name).get(class_name) if method_decs[-1] == 'public']
                    import_dict[1][class_name] = pack_name
            elif self.project_pack_dict.__contains__(pack_name):
                temp_class_methods = self.project_pack_dict.get(pack_name).get(class_name)
                if temp_class_methods:
                    class_meths_dict[1][class_name] = [method_decs for method_decs in temp_class_methods if method_decs[-1] == 'public']
                    import_dict[1][class_name] = pack_name
        return class_meths_dict, import_dict

    def get_father_return_class(self, path):
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
                # TODO:返回值
                if len(method_decs) == 4:
                    father_return_class = method_decs[2]
                elif len(method_decs) == 5:
                    father_return_class = method_decs[3]
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

    # 根据给定的重载方法找到匹配的
    def get_overload_method_2(self, node, overload_method):
        try:
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
                    raise MethodNestingExceptin("没有找到匹配的重载函数,随即返回")

            elif len(overload_method) == 1:
                right_method = overload_method[0]
            else:
                right_method = None
            # 返回类型：[方法名，[参数]，返回值]
            return right_method
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
            if not right_method:
                right_method = overload_method[0]
            return right_method

    # 通过函数调用节点的方法名及参数，查询出符合的库函数
    def get_overload_method(self, node):
        try:
            var_name = node.qualifier
            method_list = self.var_dict[var_name][1]
            overload_method = [method for method in method_list if method[0] == node.member]
            # undo 当重叠调用时，参数包含MethodInvocation，和MemberReference两种
            # 当时内部函数时，暂时添加参数返回值，无法确认重载方法
            return self.get_overload_method_2(node, overload_method)
        except TypeExceptin as e:
            print(e.str)

        except BaseException:
            pass

    # 每当添加新api时
    def update_control_dict(self, path):
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
        self.var_dict.clear()
        self.api_list.clear()
        self.all_neighbor_dict.append(dict(self.neighbor_dict))
        self.neighbor_dict.clear()
        self.control_node_dict.clear()
        self.last_api = -1


    def parse_java_file(self, java_file, maindir):
        java_type = ['byte[]', 'char', 'short', 'int', 'long', 'float', 'double', 'boolean']
        # TODO:没有解决内部类的问题，例：'E:/java_project/github_file_4/3d-bin-container-packing-master\\core\\src\\main\\java\\com\\github\\skjolber\\packing\\iterator\\DefaultPermutationRotationIterator.java'
        error_list = ['DefaultPermutationRotationIterator.java', 'TranscodeScheme.java', 'TransactionalLock.java', 'package-info.java']
        if java_file in error_list:
            return False
        class_name = java_file.split('.')[0]
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
        except:
            print(f'文件{maindir}/{java_file}获得api序列时无法读取文件')
            return False
        try:
            tree = javalang.parse.parse(f_read)
        except:
            print(f'文件{maindir}/{java_file}获得api序列时解析失败')
            return False
        f_input.seek(0)
        lines = f_input.readlines()
        import_dict = [dict(), dict(), dict()]
        class_meths_dict = [dict(), dict(), dict()]
        for key, value in self.pack_dict.get('java.lang').items():
            class_meths_dict[2][key] = [method for method in value if method[-1] == 'public']
        for temp_class_name in class_meths_dict[2].keys():
            import_dict[2][temp_class_name] = 'java.lang'
        last_node_position = 0
        # print(apath)
        # if apath == 'E:/java_project/github_file/ambari-trunk\\ambari-server\\package-info.java':
        #     print('a')
        for path, node in tree:

            if isinstance(node, Tree.CompilationUnit):
                # TODO:内部类暂时删掉

                # 提取导入类，并获得包信息
                if node.package:
                    package_name = node.package.name
                    pakage_inside_class = self.project_pack_dict.get(node.package.name)
                    for key, value in pakage_inside_class.items():
                        class_meths_dict[0][key] = [method for method in value if
                                                    not method[-1] in ['private', 'father_project']]
                    for temp_class_name in pakage_inside_class.keys():
                        import_dict[0][temp_class_name] = node.package.name
                else:
                    break
                try:
                    out_class = [out_node for out_node in node.children[-1] if
                                 not out_node.name == class_name]
                    inner_class = [inner_node for inner_node in node.children[-1][0].body if
                                   isinstance(inner_node, Tree.ClassDeclaration)]
                    this_class_methods = self.project_pack_dict.get(package_name).get(class_name)
                    for temp_class in out_class:
                        this_class_methods.extend(self.project_pack_dict.get(package_name).get(temp_class.name))
                    for temp_class in inner_class:
                        this_class_methods.extend(self.project_pack_dict.get(package_name).get(f'{class_name}*{temp_class.name}'))
                except:
                    break
                # Import完成后，去除同名方法
                if node.imports:
                    for import_node in node.imports:
                        class_meths_dict, import_dict = self.parse_import_node(class_meths_dict, import_dict, import_node)
                class_meths_dict[2].update(class_meths_dict[1])
                class_meths_dict[2].update(class_meths_dict[0])
                class_meths_dict = class_meths_dict[2]
                import_dict[2].update(import_dict[1])
                import_dict[2].update(import_dict[0])
                import_dict = import_dict[2]
                # TODO:为防止最后一个方法失效
                self.get_api_decs_lists()
                # 为应对静态变量
                for temp_class_name in class_meths_dict.keys():
                    temp_pack_name = import_dict.get(temp_class_name)
                    try:
                        static_methods = [method for method in self.project_pack_dict.get(temp_pack_name).get(temp_class_name) if 'static' in method[-1]]
                    except:
                        continue
                    if static_methods:
                        self.var_dict[temp_class_name] = [f'{temp_pack_name}.{temp_class_name}',
                                                          static_methods]

            elif isinstance(node, Tree.InterfaceDeclaration) or isinstance(node, Tree.EnumDeclaration):
                break

            # 为应对静态变量
            # elif isinstance(node, Tree.ClassDeclaration):
            #     # this_class_methods = self.project_pack_dict.get(package_name).get(class_name)
            #     # 为应对静态变量
            #     for temp_class_name in class_meths_dict.keys():
            #         temp_pack_name = import_dict.get(temp_class_name)
            #         self.var_dict[temp_class_name] = [f'{temp_pack_name}.{temp_class_name}',
            #                                      class_meths_dict.get(temp_class_name)]


            elif isinstance(node, Tree.MethodDeclaration):
                # if node.name == 'stop':
                #     print('a')

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
                                # TODO
                                if len(self.all_desc_path[self.api_desc]) > 50:
                                    break
                            else:
                                self.all_desc_path[self.api_desc] = [api_path]
                    self.api_desc = ''
                # api_line = node.position.line - 2 - len(node.annotations)
                # if api_line > 20:
                #     s = lines[api_line - 19:api_line+1]
                # else:
                #     s = lines[0:api_line+1]
                # documentation = re.match("\/\/.*", ''.join(s))
                # print(documentation.group())
                api_line = node.position.line - 2 - len(node.annotations)
                s = lines[last_node_position:api_line+1]
                documentation = re.findall('//.*', ''.join(s))
                if documentation:
                    self.api_desc = ''.join(documentation)
                elif node.documentation:
                    self.api_desc = node.documentation
                else:

                    # undo 如果该方法没有注释
                    if '*/' not in lines[api_line]:
                        self.api_desc = ''
                    elif '*/' in lines[api_line] and '/*' in lines[api_line]:
                        self.api_desc = lines[api_line].strip().strip('/').strip('*')
                    else:
                        try:
                            doc_start_num = [i for i in range(1, len(s)+1) if '/*' in s[-i]]
                            if doc_start_num:
                                self.api_desc = ''.join(s[-(doc_start_num[-1]):])
                           
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
                pack_name = import_dict.get(par_class_name)
                if class_meths_dict.__contains__(par_class_name):
                    self.var_dict[node.name] = [f'{pack_name}.{par_class_name}',
                                                class_meths_dict.get(par_class_name)]

            # 识别new实例化为调用构造器方法，TODO:需要测试
            elif isinstance(node, Tree.ClassCreator) and not self.api_desc == '':
                creator_class_name = node.type.name
                if import_dict.__contains__(creator_class_name):
                    creator_methods = [method for method in class_meths_dict.get(creator_class_name) if method[0] == creator_class_name]
                    method_decs = self.get_overload_method_2(node, creator_methods)
                    if len(method_decs) == 4:
                        # method_class = self.var_dict[var_name][0]
                        self.api_list.append(f'{method_decs[0]}.{method_decs[0]}({method_decs[1]})')
                    if len(method_decs) == 5:
                        relative_path = f'./{method_decs[1].lstrip(split_path)}'
                        self.api_list.append(f'{relative_path}.{method_decs[0]}')
                    self.update_control_dict(path)




            # 方法调用，须与变量名关联，变量名与类关联，类与包信息关联
            elif isinstance(node, Tree.MethodInvocation) and not self.api_desc == '':
                # if node.member == 'toString':
                #     print('a')
                if self.var_dict.__contains__(node.qualifier):
                    var_name = node.qualifier
                    method_decs = self.get_overload_method(node)
                    if method_decs:
                        if len(method_decs) == 4:
                            method_class = self.var_dict[var_name][0]
                            self.api_list.append(f'./{method_class}.{method_decs[0]}({method_decs[1]})')
                        if len(method_decs) == 5:
                            relative_path = f'./{method_decs[1].lstrip(split_path)}'
                            self.api_list.append(f'{relative_path}.{method_decs[0]}')
                        self.update_control_dict(path)
                # 当连续调用
                elif not node.qualifier:
                    # 如果是调用本类方法
                    if isinstance(path[-1], Tree.StatementExpression):
                        try:
                            method_decs = [method for method in this_class_methods if method[0] == node.member][0]
                            if method_decs:
                                relative_path = f'./{method_decs[1].lstrip(split_path)}'
                                self.api_list.append(f'{relative_path}.{method_decs[0]}')
                                self.update_control_dict(path)
                                continue
                        except:
                            pass

                    var_father_return_class = self.get_father_return_class(path)
                    # TODO:返回
                    if var_father_return_class:
                        # 当父节点方法返回值为None
                        if var_father_return_class == 'None.E':
                            self.api_list.append(f'E.{node.member}(UNKNOW)')
                            self.update_control_dict(path)
                        # 当父节点返回为正常类
                        else:
                            node.qualifier = var_father_return_class.split('.')[-1]
                            # 当父节点返回为正常类
                            if node.qualifier in import_dict.keys():
                                method_decs = self.get_overload_method(node)
                                if method_decs:
                                    relative_path = f'./{var_father_return_class.lstrip(split_path)}'
                                    self.api_list.append(
                                        f'{relative_path}.{method_decs[0]}({method_decs[1]})')
                                    self.update_control_dict(path)
            try:
                last_node_position = node.position.line
            except:
                pass

    def parse(self, dirname):
        # self.while_load_pkl('desc_path_dict_2.pkl')
        self.get_project_api(dirname)
        self.get_extend_methods()
        self.get_re_param(dirname)
        # file_handle = open('1.txt', mode='w')
        # file_handle.truncate(0)
        for maindir, subdir, file_name_list in os.walk(dirname):
            for java_file in file_name_list:
                # try:
                if java_file.endswith('.java'):
                    # try:
                    #     self.parse_java_file(java_file, maindir)
                    # except Exception as e:
                    #     print(e)
                    #     pass
                    self.parse_java_file(java_file, maindir)

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
    # maindir = 'E:/java_project/github_file'
    maindir = 'C:/Users/wkr/Desktop/项目/AST_parse_new/clicy-master'
    write_file('log.txt', '\n当前时间为：{}\n'.format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))))
    write_file('log.txt', f'正在解析{maindir}')
    file_list = os.listdir(maindir)
    for subdir in file_list:
        my_parse = AST_parse()
        file_num += 1
        print(f'开始解析第{file_num}个文件{subdir}')

        # if file_num < 258:
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


