#!/usr/bin/env python

import requests
from jinja2 import Template
import sqlite3

token = ""
INIT_CHINESE = "2019-11-01T00:00:00Z"
db = "../db/db.sqlite"


def init():
    # 连接数据库
    conn = sqlite3.connect(db)
    # 创建一个 cursor
    cursor = conn.cursor()
    # 如果 request_pull is not exists,create the table request_pull.otherwise,insert into pr db
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


def update_docs():
    # 连接数据库
    conn = sqlite3.connect(db)
    # 创建一个 cursor
    cursor = conn.cursor()
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
                files, merge_time, base_ref, pr_author = get_pr_by_number(pr_number)
                print("update doc ", (pr_number, pr_url, pr_author, merge_time, base_ref, files, 0))
                cursor.execute(insert_sql, (pr_number, pr_url, pr_author, merge_time, base_ref, files, 0))
                update_request_pull = "update request_pull set process=1 where pr_number='" + pr_number + "'"
                cursor.execute(update_request_pull)
            else:
                print(pr_number, " db existed")
        print("update docs success")
    else:
        print("no new db")
    conn.commit()
    cursor.close()
    conn.close()


def update_author():
    # 连接数据库
    conn = sqlite3.connect(db)
    # 创建一个 cursor
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
            github_id, name, email, company, location = get_author_data(a[0])
            print("update author ", a[0], (github_id, name, email, company, location, zh_trans_sum))
            cursor.execute(insert_sql, (github_id, name, email, company, location, zh_trans_sum))
        else:
            print(a[0], " db existed")
    conn.commit()
    cursor.close()
    conn.close()


def get_author_data(login):
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
    result = get_data(author_query)
    github_id = login
    name = result['db']['user']['name']
    email = result['db']['user']['email']
    company = result['db']['user']['company']
    location = result['db']['user']['location']
    return github_id, name, email, company, location


def get_pr_by_number(number):
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
    result = get_data(pr_query)
    files = result['db']['repository']['pullRequest']['files']
    files = ','.join([f["node"]["path"] for f in files["edges"]])
    merge_time = result['db']['repository']['pullRequest']['mergedAt']
    base_ref = result['db']['repository']['pullRequest']['baseRef']['name']
    pr_author = result['db']['repository']['pullRequest']['author']['login']
    return files, merge_time, base_ref, pr_author


def get_data(query):
    r = requests.post("https://api.github.com/graphql",
                      json={"query": query},
                      headers={
                          "Authorization": "token %s" % token,
                          "Accept": "application/vnd.github.ocelot-preview+json",
                          "Accept-Encoding": "gzip"
                      })
    r.raise_for_status()
    reply = r.json()
    return reply


def update_merged_pr(prs):
    # 连接数据库
    conn = sqlite3.connect(db)
    # 创建一个 cursor
    cursor = conn.cursor()
    for pr in prs:
        cursor.execute("select * from request_pull where pr_url = '" + pr[0] + "'")
        is_exist = cursor.fetchone()
        if is_exist is None:
            # process 0 未处理 1 已处理
            print(
                "insert into request_pull (pr_url,pr_number,process) values ('" + pr[0] + "', '" + str(pr[1]) + "',0)")
            cursor.execute(
                "insert into request_pull (pr_url,pr_number,process) values ('" + pr[0] + "', '" + str(pr[1]) + "',0)")
        else:
            print(pr[0], "db existed")
    cursor.close()
    conn.commit()
    conn.close()


# 获取所有的 已经合并的 pr 列表
def get_issue_list(is_next=False, next_cursor=""):
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
        result = get_data(first_query)
        next_cursor = result['db']['repository']['pullRequests']['pageInfo']['endCursor']
        has_next_page = result['db']['repository']['pullRequests']['pageInfo']['hasNextPage']
        prs = result['db']['repository']['pullRequests']['edges']
        for pr in prs:
            url = pr["node"]["url"]
            number = str(pr["node"]["number"])
            all_data.append([url, number])
        update_merged_pr(all_data)
        if has_next_page:
            get_issue_list(has_next_page, next_cursor)
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
        result = get_data(next_query)
        next_cursor = result['db']['repository']['pullRequests']['pageInfo']['endCursor']
        has_next_page = result['db']['repository']['pullRequests']['pageInfo']['hasNextPage']
        next_prs = result['db']['repository']['pullRequests']['edges']
        for pr in next_prs:
            url = pr["node"]["url"]
            number = str(pr["node"]["number"])
            print(url, number)
            all_data.append([url, number])
        update_merged_pr(all_data)
        if has_next_page:
            get_issue_list(has_next_page, next_cursor)


def job():
    init()
    get_issue_list()
    update_docs()
    update_author()


if __name__ == '__main__':
    job()
