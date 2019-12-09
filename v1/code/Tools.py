#!/usr/bin/env python
import yaml, os, sqlite3, requests, re
from jinja2 import Template
from git import RemoteProgress, Repo


class TransTools(object):
    # 初始化所有 Github_PR 环境配置
    def __init__(self):
        with open('config.yaml', 'r', encoding="utf-8") as file:
            config = yaml.safe_load(file.read())
        self.db_path = config['istio']['db']['path']
        if not os.path.exists(self.db_path):
            os.mkdir(self.db_path)
        self.db = self.db_path + config['istio']['db']['db']
        self.github_token = config['istio']['github_token']
        self.graphql_v4 = config['istio']['graphql_v4']['url']

    # 创建数据库连接
    def get_cursor(self):
        # 连接数据库
        conn = sqlite3.connect(self.db)
        # 创建一个 cursor
        cursor = conn.cursor()
        return conn, cursor

    # 初始化数据库表
    def create_table(self):
        conn, cursor = self.get_cursor()
        cursor.execute("SELECT * FROM sqlite_master WHERE type='table' AND name='request_pull'")
        is_pr = cursor.fetchone()
        if is_pr is None:
            cursor.execute('''
                            create table request_pull(
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                pr_url varchar(300),
                                pr_number Int(20),
                                process smallint
                            )''')
            print("create table request_pull")
        else:
            print("table exists")

        # 如果 docs 数据表不存在，即创建一个
        cursor.execute("SELECT * FROM sqlite_master WHERE type='table' AND name='docs'")
        is_art = cursor.fetchone()
        if is_art is None:
            cursor.execute('''
                            create table docs (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                pr_number Int(20),
                                pr_url varchar(300),
                                pr_author varchar(500),
                                pr_merged_time varchar(300),
                                pr_version varchar(255),
                                pr_files varchar(2000),
                                process smallint
                            )''')
            print("create table docs")
        else:
            print("table docs exists")

        # author
        cursor.execute("SELECT * FROM sqlite_master WHERE type='table' AND name='author'")
        is_author = cursor.fetchone()
        if is_author is None:
            cursor.execute('''
                            create table author(
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                github_id varchar(255),
                                name varchar(255),
                                email varchar(255),
                                zh_trans_sum Integer(20),
                                company varchar(255),
                                location varchar(255)
                            )''')
            print("create table author")
        else:
            print("table author exists")

        # git_log_problems table
        cursor.execute("SELECT * FROM sqlite_master WHERE type='table' AND name='git_log_problems'")
        is_git_log_problems = cursor.fetchone()
        if is_git_log_problems is None:
            cursor.execute('''
                            create table git_log_problems(
                                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                file_path varchar(1000),
                                zh_version varchar(255),
                                github_id varchar(255),
                                pr_number Integer(32),
                                merged_time varchar(255)
                            )''')
            print("create table git_log_problems")
        else:
            print("table git_log_problems exists")

        """
        中文翻译字数统计表
        id 自增
        file_path 文件路径
        github_id 作者github_id
        zh_version 版本号
        flag 0 表示 add 1 表示 update
        merge_time 日期
        zh_sum 文件中包含的中文的字数
        pr_number url number
        """
        # zh_trans table
        cursor.execute("SELECT * FROM sqlite_master WHERE type='table' AND name='zh_trans'")
        is_zh_trans = cursor.fetchone()
        if is_zh_trans is None:
            cursor.execute('''
                               create table zh_trans(
                                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                                   github_id varchar(255),
                                   pr_number Integer(32),
                                   zh_version varchar(255),
                                   merge_time varchar(255),
                                   zh_sum Integer(32),
                                   flag smallint,
                                   file_path varchar(1000)
                               )''')
            print("create table zh_trans")
        else:
            print("table zh_trans exists")

        cursor.close()
        conn.commit()
        conn.close()

    # 调用 github  https://api.github.com/graphql (v4) 获取数据
    def get_data(self, query):
        r = requests.post(self.graphql_v4, json={"query": query}, headers={
            "Authorization": "token %s" % self.github_token,
            "Accept": "application/vnd.github.ocelot-preview+json",
            "Accept-Encoding": "gzip"
        })
        r.raise_for_status()
        reply = r.json()
        return reply

    '''
    获取所有的已经合并的 pr 列表 
    网址信息 https://github.com/istio/istio.io/pulls?q=is%3Apr+label%3Atranslation%2Fchinese+is%3Aclosed
    filter: states=MERGED,labels=translation/chinese,first=100(MAX)
    '''

    def get_all_merged_pr(self, is_next=False, next_cursor=""):
        all_data = []
        if not is_next:
            # 首次使用
            first_query = """
                query {
                      repository(name: "istio.io", owner: "istio") {
                        pullRequests(
                        first:100,
                        states:MERGED,
                        labels:"translation/chinese") {
                            pageInfo{
                                startCursor
                                endCursor
                                hasPreviousPage
                                hasNextPage
                            }
                            edges {
                                node {
                                  number
                                  url
                                }
                            }
                        }
                      }
                    }
                """
            result = self.get_data(first_query)
            next_cursor = result['data']['repository']['pullRequests']['pageInfo']['endCursor']
            has_next_page = result['data']['repository']['pullRequests']['pageInfo']['hasNextPage']
            prs = result['data']['repository']['pullRequests']['edges']
            for pr in prs:
                url = pr["node"]["url"]
                number = str(pr["node"]["number"])
                print(url, number)
                all_data.append([url, number])
            self.insert_merged_pr(all_data)
            if has_next_page:
                self.get_all_merged_pr(has_next_page, next_cursor)
        else:
            next_query = Template("""
                    query {
                        repository(name: "istio.io", owner: "istio") {
                            pullRequests(
                            first:100,
                            states:MERGED,
                            labels:"translation/chinese"
                            after: "{{ next_cursor }}")
                            {
                                pageInfo{
                                    startCursor
                                    endCursor
                                    hasPreviousPage
                                    hasNextPage
                                }
                                edges {
                                node {
                                  number
                                  url
                                }
                            }
                            }
                        }
                    }
                    """).render({'next_cursor': next_cursor})
            result = self.get_data(next_query)
            next_cursor = result['data']['repository']['pullRequests']['pageInfo']['endCursor']
            has_next_page = result['data']['repository']['pullRequests']['pageInfo']['hasNextPage']
            next_prs = result['data']['repository']['pullRequests']['edges']
            for pr in next_prs:
                url = pr["node"]["url"]
                number = str(pr["node"]["number"])
                print(url, number)
                all_data.append([url, number])
            self.insert_merged_pr(all_data)
            if has_next_page:
                self.get_all_merged_pr(has_next_page, next_cursor)

    # 插入数据到 request_pull 表
    def insert_merged_pr(self, prs):
        conn, cursor = self.get_cursor()
        for pr in prs:
            cursor.execute("select * from request_pull where pr_url = '" + pr[0] + "'")
            is_exist = cursor.fetchone()
            if is_exist is None:
                # process 0 未处理 1 已处理
                print("insert into request_pull (pr_url,pr_number,process) values ('" + pr[0] + "', '" + str(
                    pr[1]) + "',0)")
                cursor.execute("insert into request_pull (pr_url,pr_number,process) values ('" + pr[0] + "', '" + str(
                    pr[1]) + "',0)")
            else:
                print(pr[0], "db existed")
        cursor.close()
        conn.commit()
        conn.close()

    # 根据 pr url https://github.com/istio/istio.io/pull/5497 获取数据
    def get_pr_by_number(self, number):
        pr_query = Template("""
        {
          repository(name: "istio.io", owner: "istio") {
            pullRequest(number: {{number}}) {
              baseRef {
                name
              }
              files(first: 100) {
                edges {
                  node {
                    path
                  }
                }
              }
              state
              mergedAt
              author {
                login
              }
            }
          }
        }
        """).render({'number': number})
        result = self.get_data(pr_query)
        files = result['data']['repository']['pullRequest']['files']
        files = ','.join([f["node"]["path"] for f in files["edges"]])
        merge_time = result['data']['repository']['pullRequest']['mergedAt']
        base_ref = result['data']['repository']['pullRequest']['baseRef']['name']
        pr_author = result['data']['repository']['pullRequest']['author']['login']
        return files, merge_time, base_ref, pr_author

    # 更新 docs 表
    def update_docs_pr(self):
        conn, cursor = self.get_cursor()
        select_sql = "select * from request_pull where process= 0 order by id desc"
        cursor.execute(select_sql)
        prs = cursor.fetchall()
        insert_sql = "insert into docs (pr_number,pr_url,pr_author," \
                     "pr_merged_time,pr_version,pr_files,process) values (?, ?, ?, ?, ?, ?,?)"
        if len(prs) > 0:
            for pr in prs:
                pr_number = str(pr[2])
                pr_url = pr[1]
                docs_select = "select * from docs where  pr_number = {pr_number}".format(pr_number=pr_number)
                cursor.execute(docs_select)
                is_exist = cursor.fetchone()
                # time.sleep(1)
                if is_exist is None:
                    files, merge_time, base_ref, pr_author = self.get_pr_by_number(pr_number)
                    print("update doc ", (pr_number, pr_url, pr_author, merge_time, base_ref, files, 0))
                    cursor.execute(insert_sql, (pr_number, pr_url, pr_author, merge_time, base_ref, files, 0))
                    update_request_pull = "update request_pull set process=1 where pr_number='" + pr_number + "'"
                    cursor.execute(update_request_pull)
                else:
                    print(pr_number, " db existed")
            print("update docs success")
        else:
            print("no new db")
        cursor.close()
        conn.commit()
        conn.close()

    # 根据 github 账户获取用户信息
    def get_author_data(self, login):
        author_query = Template("""
                {
                user (login: {{login}}) {
                    location
                    email
                    name
                    company
                   }
               }
                """).render({'login': '"' + login + '"'})
        result = self.get_data(author_query)
        github_id = login
        name = result['data']['user']['name']
        email = result['data']['user']['email']
        company = result['data']['user']['company']
        location = result['data']['user']['location']
        return github_id, name, email, company, location

    # 更新已经贡献翻译的用户信息
    def update_author(self):
        conn, cursor = self.get_cursor()
        cursor = conn.cursor()
        cursor.execute("select  distinct(pr_author) from docs")
        all_author = cursor.fetchall()
        insert_sql = "insert into author (github_id,name,email," \
                     "company,location,zh_trans_sum) values (?, ?, ?, ?, ?, ?)"
        for a in all_author:
            cursor.execute("select * from author where github_id = '" + a[0] + "'")
            is_exist = cursor.fetchone()
            if is_exist is None:
                zh_trans_sum = 0
                github_id, name, email, company, location = self.get_author_data(a[0])
                print("update author ", a[0], (github_id, name, email, company, location, zh_trans_sum))
                cursor.execute(insert_sql, (github_id, name, email, company, location, zh_trans_sum))
            else:
                print(a[0], " db existed")
        conn.commit()
        cursor.close()
        conn.close()


class MyProgressPrinter(RemoteProgress):
    def update(self, op_code, cur_count, max_count=None, message=''):
        print(op_code, cur_count, max_count, cur_count / (max_count or 100.0), message or "NO MESSAGE")


class GitTools(object):
    # 初始化所有 Git 环境配置
    def __init__(self):
        with open('config.yaml', 'r', encoding="utf-8") as file:
            config = yaml.safe_load(file.read())
        self.start_time = config['istio']['init']['start_time']
        self.branch = config['istio']['branch']
        self.upstream = config['istio']['upstream']
        self.pull_flag = config['istio']['pull_flag']
        self.github_url = config['istio']['github_url']
        self.db_path = config['istio']['db']['path']
        if not os.path.exists(self.db_path):
            os.mkdir(self.db_path)
        self.db = self.db_path + config['istio']['db']['db']

    # 验证合法文件
    def is_valid(self, pr):
        # 从 docs 中查询 pr_version = self.branch 的所有的数据
        pr_files = []
        for f in pr[4].split(","):
            if (os.path.splitext(f)[1] == '.md' or
                    os.path.splitext(f)[1] == '.htm' or
                    os.path.splitext(f)[1] == '.html'):
                pr_files.append(f)
        return pr_files

    # 统计某个文件的中文数目
    def cn_word_count(self, content):
        """
        功能: 单文件-中文翻译字数统计
        """
        count = 0
        result = re.findall(u"[\u4e00-\u9fa5]", content)
        for cn in result:
            count += len(cn)
        return count

    # git diff 差异文件
    def get_cn_by_diff(self, show_content, pr_number):
        commit_dict = {

        }
        pattern = re.compile(r'#(\d+)')
        result = pattern.findall(show_content)[0]
        # pr_id 确定不重复计算
        if result == str(pr_number):
            for diff_split in show_content.split("diff --git"):
                if diff_split.find("a/content/zh/") != -1:
                    file_all = diff_split.split(" ")
                    file_name = file_all[1].replace("a/", "")
                    file_content = "".join(file_all)
                    cn_sum = self.cn_word_count(file_content)
                    commit_dict.setdefault(file_name, cn_sum)
        return commit_dict

    # 创建 istio 的本地分支 并建立本地分支与远程分支的关联
    def create_local_branch(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_path = os.path.dirname(current_dir)
        Repo.init('../istio.io')
        istio_repo = Repo(os.path.join(parent_path, 'istio.io'))
        if len(istio_repo.remotes) == 0:
            print("create remote origin.")
            origin = istio_repo.create_remote('origin', self.upstream)
        else:
            print("remote origin already exists.")
            origin = istio_repo.remote('origin')
        if self.pull_flag:
            for fetch_info in origin.fetch(progress=MyProgressPrinter()):
                print("......       fetch   ", fetch_info.ref, "        ......")
                print(" Updated %s to %s" % (fetch_info.ref, fetch_info.commit))
            if not istio_repo.active_branch.name == self.branch:
                # Setup a local tracking branch of a remote branch
                istio_repo.create_head(self.branch,
                                       origin.refs.master)  # create local branch "master" from remote "master"
                istio_repo.heads.master.set_tracking_branch(
                    origin.refs.master)  # set local "master" to track remote "master
                istio_repo.heads.master.checkout()  # checkout local "master" to working tree
                # Three above commands in one:
                # istio_repo.create_head('master', origin.refs.master).set_tracking_branch(origin.refs.master).checkout()
            print(istio_repo.git.pull())
        self.analysis_file(istio_repo)

    # 创建数据库连接
    def get_cursor(self):
        # 连接数据库
        conn = sqlite3.connect(self.db)
        # 创建一个 cursor
        cursor = conn.cursor()
        return conn, cursor

    # 插入无 git log 文件输出
    def insert_into_git_problems(self, cursor, file_name, github_id, pr_number, merged_time):
        sql = "select * from git_log_problems where file_path = '" + file_name + "'"
        data = cursor.execute(sql).fetchall()
        if len(data) > 0:
            print(file_name, " db existed")
        else:
            sql = " insert into  git_log_problems (file_path,zh_version," \
                  "github_id,pr_number,merged_time) values (?,?,?,?,?) "
            cursor.execute(sql, (file_name, self.branch, github_id, pr_number, merged_time))
            print(" git log_problems file_info insert into ", pr_number, github_id, merged_time, self.branch, file_name)

    # 统计中文数
    def get_zh_by_pr(self, repo, cursor, file_name, pr):
        pr_number, github_id, merged_time = pr[0], pr[1], pr[2]
        git = repo.git
        list_data = []
        try:
            content = git.log('--after=' + self.start_time, file_name)
            commits = []
            for line in content.split("\n"):
                if line.find("commit") != -1:
                    commits.append(line.split(" ")[-1])
            commits.reverse()
            for commit in commits:
                show_content = git.show(commit)
                commit_dict = self.get_cn_by_diff(show_content, pr_number)
                for k, v in commit_dict.items():
                    # 中文汉字数量大于 0 表示新增的翻译 为 0 表示添加的英文原文
                    if v > 0:
                        value = (pr_number, merged_time, github_id, k, v)
                        list_data.append(value)
        except BaseException as e:
            # 无 git log 信息的文件
            self.insert_into_git_problems(cursor, file_name, github_id, pr_number, merged_time)
        return list_data

    # 从数据库中获取 start_time 后的数据
    def get_all_data_by_pr_version(self, repo, cursor):
        cursor.execute(
            "select  pr_number,pr_author,pr_merged_time,pr_version,"
            "pr_files  from docs  where process = 0  and pr_version = "
            + "'" + self.branch + "'" + " and  pr_merged_time > '"
            + self.start_time + "'" + " order by pr_merged_time asc")
        data = cursor.fetchall()
        all_valid_data = []
        for pr in data:
            pr_files = self.is_valid(pr)
            for file_name in pr_files:
                list_data = self.get_zh_by_pr(repo, cursor, file_name, pr)
                all_valid_data.append(list_data)
        return all_valid_data

    # 开始分析本地文件
    def analysis_file(self, repo):
        conn, cursor = self.get_cursor()
        all_data = self.get_all_data_by_pr_version(repo, cursor)
        set_all_data = []
        # 去重
        for info in all_data:
            if len(info) > 0 and info not in set_all_data:
                set_all_data.append(info)
        # 相应的数据插入表中
        for insert_data in set_all_data:
            for tuple_data in insert_data:
                github_id, pr_number, merge_time, zh_sum, file_path \
                    = tuple_data[2], tuple_data[0], tuple_data[1], tuple_data[4], tuple_data[3]
                cursor.execute(
                    "select pr_number,zh_version from zh_trans where zh_version = '"
                    + self.branch + "' and file_path = '" + file_path + "'")
                is_exist = []
                for ii in cursor.fetchall():
                    if ii[0] not in is_exist:
                        is_exist.append(ii[0])
                # 某版本不存在某文件的记录 则是新增
                if len(is_exist) == 0:
                    flag = 0  # 新增翻译操作
                else:
                    flag = 1  # 更新翻译操作
                if pr_number in is_exist:
                    print("db existed", github_id, pr_number, self.branch, merge_time, zh_sum, flag, file_path)
                else:
                    print("insert db", github_id, pr_number, self.branch, merge_time, zh_sum, flag, file_path)
                    insert_sql = "insert into zh_trans (github_id,pr_number,zh_version," \
                                 "merge_time,zh_sum,flag,file_path)" \
                                 "values (?,?,?,?,?,?,?)"
                    cursor.execute(insert_sql,
                                   (github_id, pr_number, self.branch, merge_time, zh_sum, flag, file_path))
                    cursor.execute(
                        "update docs set process = 1 where pr_number = '" +
                        str(pr_number) + "' and pr_version = '" + self.branch + "'")
        conn.commit()
        cursor.close()
        conn.close()


def start_get_data():
    # 初始化配置参数
    trans = TransTools()
    # 初始化表
    trans.create_table()
    # 获取所有已经合并的 pr 并且插入 request_pull 表 process 0 未处理 1 已处理
    trans.get_all_merged_pr()
    # 更新 docs 表
    trans.update_docs_pr()
    # 更新 author 表
    trans.update_author()


def update_tables():
    git_tools = GitTools()
    git_tools.create_local_branch()


if __name__ == '__main__':
    start_get_data()
    update_tables()
